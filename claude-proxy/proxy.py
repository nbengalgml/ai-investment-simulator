#!/usr/bin/env python3
"""
Local Claude proxy — routes Anthropic API calls through the `claude` CLI.

The `claude` CLI uses your existing Claude.ai OAuth session, so no API key
is required. Docker containers call this proxy via host.docker.internal.

Usage:
    python3 claude-proxy/proxy.py

Then in .env:
    CLAUDE_PROXY_URL=http://host.docker.internal:8090
"""
import json
import logging
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [proxy] %(levelname)s %(message)s",
)
logger = logging.getLogger("proxy")

PORT = int(os.getenv("CLAUDE_PROXY_PORT", "8090"))
CLAUDE_BIN = os.getenv("CLAUDE_BIN", "claude")


def _call_claude(system: str, user_msg: str, max_tokens: int) -> str:
    """Call `claude --print` with the composed prompt, return text response."""
    # Pass system as a preamble so Claude sees clear role + task separation
    prompt = f"{system}\n\n---\n\n{user_msg}" if system else user_msg

    result = subprocess.run(
        [CLAUDE_BIN, "--print", prompt],
        capture_output=True, text=True, timeout=300,
    )
    stdout = result.stdout.strip()
    if result.returncode != 0:
        err = (result.stderr or stdout or "unknown error").strip()
        logger.error("claude exited %d: %s", result.returncode, err[:300])
        return f"[proxy error: {err[:300]}]"
    if not stdout:
        logger.warning("claude returned empty stdout (stderr=%s)", result.stderr[:200])
        return ""
    logger.debug("claude response: %s…", stdout[:120])
    return stdout


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._ok({"status": "ok"})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path not in ("/v1/messages",):
            self.send_response(404)
            self.end_headers()
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except Exception as exc:
            self._error(400, str(exc))
            return

        # Extract system prompt
        sys_param = body.get("system", "")
        if isinstance(sys_param, list):
            system = "\n".join(
                b.get("text", "") for b in sys_param
                if isinstance(b, dict) and b.get("type") == "text"
            )
        else:
            system = str(sys_param)

        # Extract last user message
        messages = body.get("messages", [])
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                content = m.get("content", "")
                if isinstance(content, list):
                    user_msg = " ".join(
                        b.get("text", "") for b in content
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                else:
                    user_msg = str(content)
                break

        logger.info("→ claude | system=%d chars user=%d chars", len(system), len(user_msg))
        text = _call_claude(system, user_msg, body.get("max_tokens", 4096))
        logger.info("← claude | response=%d chars", len(text))

        self._ok({
            "id": "msg_proxy",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": text}],
            "model": body.get("model", "claude-proxy"),
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        })

    def _ok(self, data: dict):
        payload = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _error(self, code: int, msg: str):
        self.send_response(code)
        self.end_headers()
        self.wfile.write(json.dumps({"error": msg}).encode())

    def log_message(self, fmt, *args):
        pass  # suppress default access log — we use our own logger


if __name__ == "__main__":
    # Verify claude CLI is reachable
    check = subprocess.run([CLAUDE_BIN, "--version"], capture_output=True, text=True)
    if check.returncode != 0:
        logger.error("claude CLI not found at '%s'. Is it on PATH?", CLAUDE_BIN)
        sys.exit(1)
    logger.info("claude %s", check.stdout.strip())

    server = HTTPServer(("0.0.0.0", PORT), _Handler)
    logger.info("Claude proxy listening on http://0.0.0.0:%d", PORT)
    logger.info("Set in .env: CLAUDE_PROXY_URL=http://host.docker.internal:%d", PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Proxy stopped")
