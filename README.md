# AI Investment Simulator

> **SIMULATION ONLY**: All portfolio recommendations, trade simulations, and performance projections are for educational and entertainment purposes only. This is not financial advice. No real trades are executed. Past simulated performance does not indicate future real-world results. The creators of this system are not licensed financial advisors.

An autonomous, multi-agent AI investment company that simulates a real investment firm using Claude-powered agents.

## Quick Start

```bash
cp .env.example .env
# Fill in your API keys in .env
docker compose up --build -d
```

- API: http://localhost:8000
- Frontend: http://localhost:3000
- Via Nginx: http://localhost:80

## Development

See [CLAUDE.md](CLAUDE.md) for commands, architecture, and agent details.

## Architecture

Nine specialized AI agents (CEO, Product Manager, Market Researcher, Analyst, Developer, Frontend Developer, QA Engineer, Scheduler, Deployment) collaborate to analyze markets and simulate portfolio management. All data persists as JSON flat files under `data/`. The FastAPI backend serves `shared/` as an API layer; the React frontend polls it every 60 seconds.

## Environment Variables

Copy `.env.example` to `.env` and fill in:
- `ANTHROPIC_API_KEY` — Claude API key
- `NEWSAPI_KEY` — NewsAPI free tier
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` — Reddit PRAW app credentials
