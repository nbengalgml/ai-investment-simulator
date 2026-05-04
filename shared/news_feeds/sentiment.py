import re

_POSITIVE = frozenset({
    "beat", "beats", "surge", "surged", "surges", "rally", "rallied", "rallies",
    "upgrade", "upgraded", "strong", "strength", "record", "bullish", "growth",
    "profit", "revenue", "gain", "gains", "rose", "rise", "jumped", "outperform",
    "buy", "positive", "exceed", "exceeded", "better", "expand", "expansion",
    "win", "wins", "boost", "boosted", "accelerate", "high", "breakout",
})

_NEGATIVE = frozenset({
    "miss", "misses", "missed", "decline", "declines", "declined", "fall", "falls",
    "fell", "downgrade", "downgraded", "weak", "weakness", "loss", "losses",
    "bearish", "cut", "drop", "drops", "dropped", "underperform", "sell",
    "negative", "disappoint", "disappointed", "lower", "contract", "contraction",
    "lose", "layoff", "layoffs", "warning", "risk", "concern", "slowdown",
})


def score_text(text: str) -> float:
    """Keyword-based sentiment score in [-1, 1]."""
    words = re.findall(r"\b\w+\b", text.lower())
    pos = sum(1 for w in words if w in _POSITIVE)
    neg = sum(1 for w in words if w in _NEGATIVE)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 4)
