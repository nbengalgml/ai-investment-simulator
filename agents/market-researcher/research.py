"""
Market Researcher core pipeline.
Importable by tests and by main.py.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Resolve shared/ whether running from Docker (/app/shared) or standalone
_SHARED = Path(__file__).parent.parent.parent / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from config import get_tickers
from data_models import MarketResearchSnapshot, StockSignal
from market_data import StockMarketData, fetch_stock_data
from news_feeds import (
    NewsArticle,
    RedditMentionData,
    SecFiling,
    fetch_batch_8k,
    fetch_sector_news,
    fetch_ticker_mentions,
    get_ticker_news_score,
)
import storage as _storage

logger = logging.getLogger(__name__)

_SCORING_SYSTEM = """\
You are a Market Research Analyst for an investment simulation (SIMULATION ONLY — not financial advice).

Score each stock 0–100 on three dimensions and compute the weighted composite:

momentum_score  (0–100) — recent price performance
  80–100 = strong positive (>10% 20d gain, near 52-week high)
  50–79  = moderate positive
  30–49  = neutral/mixed
  0–29   = negative momentum

fundamental_score (0–100) — analyst consensus and valuation
  80–100 = strong buy, price target well above current price (>15% upside)
  50–79  = buy/hold consensus
  30–49  = mixed/hold
  0–29   = sell or underperform

sentiment_score (0–100) — news coverage and social mention velocity
  80–100 = very positive news + high Reddit velocity
  50–79  = positive/neutral
  30–49  = mixed
  0–29   = negative

composite_score = momentum*0.40 + fundamental*0.35 + sentiment*0.25

Respond ONLY with a JSON array — no markdown, no explanation."""


def _score_algorithmic(signal: StockSignal) -> StockSignal:
    """Rule-based scoring — used when Claude is unavailable."""
    m = signal.momentum_20d_pct
    if m >= 15:
        ms = 90.0
    elif m >= 10:
        ms = 80.0
    elif m >= 5:
        ms = 70.0
    elif m >= 0:
        ms = 55.0
    elif m >= -5:
        ms = 40.0
    elif m >= -10:
        ms = 25.0
    else:
        ms = 10.0

    consensus = (signal.analyst_consensus or "none").lower()
    fs_base = {"strong_buy": 90.0, "strongbuy": 90.0, "buy": 75.0, "hold": 50.0,
               "sell": 25.0, "underperform": 25.0}.get(consensus, 50.0)
    if signal.analyst_price_target and signal.current_price:
        upside = (signal.analyst_price_target - signal.current_price) / signal.current_price * 100
        if upside > 20:
            fs_base = min(100.0, fs_base + 10)
        elif upside < -10:
            fs_base = max(0.0, fs_base - 15)

    news_c = signal.news_sentiment_score * 25 + 50
    reddit_c = signal.reddit_sentiment_score * 25 + 50
    if signal.reddit_mention_count > 10:
        reddit_c = min(100.0, reddit_c + 15)
    elif signal.reddit_mention_count > 5:
        reddit_c = min(100.0, reddit_c + 8)
    if signal.news_headline_count > 5:
        news_c = min(100.0, news_c + 10)
    ss = (news_c + reddit_c) / 2

    signal.momentum_score = round(ms, 1)
    signal.fundamental_score = round(fs_base, 1)
    signal.sentiment_score = round(ss, 1)
    signal.composite_score = round(ms * 0.40 + fs_base * 0.35 + ss * 0.25, 1)
    return signal


def _score_with_claude(signals: list[StockSignal]) -> list[StockSignal]:
    """Claude-based scoring with algorithmic fallback on any error."""
    try:
        from claude_client import ClaudeClient

        payload = [
            {
                "ticker": s.ticker,
                "momentum_20d_pct": s.momentum_20d_pct,
                "price_change_1d_pct": s.price_change_1d_pct,
                "current_price": s.current_price,
                "week_52_high": s.week_52_high,
                "week_52_low": s.week_52_low,
                "pe_ratio": s.pe_ratio,
                "analyst_consensus": s.analyst_consensus,
                "analyst_price_target": s.analyst_price_target,
                "news_headline_count": s.news_headline_count,
                "news_sentiment_score": s.news_sentiment_score,
                "reddit_mention_count": s.reddit_mention_count,
                "reddit_sentiment_score": s.reddit_sentiment_score,
                "recent_8k": s.recent_8k_summary,
            }
            for s in signals
        ]
        user_msg = (
            f"Score these {len(signals)} stocks. Return a JSON array where each element has: "
            "ticker, momentum_score, fundamental_score, sentiment_score, composite_score.\n\n"
            f"Data:\n{json.dumps(payload, indent=2)}"
        )
        raw = ClaudeClient().analyze(system=_SCORING_SYSTEM, user_message=user_msg)
        scores = json.loads(raw)
        score_map = {item["ticker"]: item for item in scores}
        for s in signals:
            if s.ticker in score_map:
                row = score_map[s.ticker]
                s.momentum_score = float(row.get("momentum_score", 50))
                s.fundamental_score = float(row.get("fundamental_score", 50))
                s.sentiment_score = float(row.get("sentiment_score", 50))
                s.composite_score = float(row.get("composite_score", 50))
        return signals
    except Exception as exc:
        logger.warning("Claude scoring failed (%s) — using algorithmic fallback", exc)
        return [_score_algorithmic(s) for s in signals]


def run_research_cycle(sector: str, use_claude: bool = True) -> MarketResearchSnapshot:
    tickers = get_tickers(sector)
    logger.info("Research cycle start: sector=%s tickers=%s", sector, tickers)

    # ── 1. Market data (yfinance) ─────────────────────────────────────────────
    market_data: dict[str, StockMarketData] = {}
    for ticker in tickers:
        try:
            market_data[ticker] = fetch_stock_data(ticker)
        except Exception as exc:
            logger.warning("yfinance failed for %s: %s", ticker, exc)

    # ── 2. News articles ──────────────────────────────────────────────────────
    news_articles: list[NewsArticle] = []
    try:
        news_articles = fetch_sector_news(sector=sector, tickers=tickers)
        logger.info("NewsAPI: %d articles", len(news_articles))
    except Exception as exc:
        logger.warning("NewsAPI error: %s", exc)

    # ── 3. Reddit mentions ────────────────────────────────────────────────────
    reddit_data: dict[str, RedditMentionData] = {}
    try:
        reddit_data = fetch_ticker_mentions(tickers)
        logger.info("Reddit: mentions fetched for %d tickers", len(reddit_data))
    except Exception as exc:
        logger.warning("Reddit error: %s", exc)

    # ── 4. SEC EDGAR 8-K (top 5 tickers to stay under rate limits) ───────────
    sec_data: dict[str, Optional[SecFiling]] = {}
    try:
        sec_data = fetch_batch_8k(tickers[:5])
        filed = sum(1 for v in sec_data.values() if v)
        logger.info("SEC EDGAR: %d filings found", filed)
    except Exception as exc:
        logger.warning("SEC EDGAR error: %s", exc)

    # ── 5. Assemble StockSignal objects ───────────────────────────────────────
    signals: list[StockSignal] = []
    for ticker in tickers:
        md = market_data.get(ticker)
        if md is None:
            logger.warning("No market data for %s — skipping", ticker)
            continue

        n_count, n_sent = (
            get_ticker_news_score(ticker, news_articles) if news_articles else (0, 0.0)
        )
        reddit = reddit_data.get(ticker.upper())
        filing = sec_data.get(ticker)

        signals.append(
            StockSignal(
                ticker=md.ticker,
                company_name=md.company_name,
                sector=md.sector,
                current_price=md.current_price,
                price_change_1d_pct=md.price_change_1d_pct,
                momentum_20d_pct=md.momentum_20d_pct,
                week_52_high=md.week_52_high,
                week_52_low=md.week_52_low,
                pe_ratio=md.pe_ratio,
                market_cap=md.market_cap,
                analyst_consensus=md.analyst_consensus,
                analyst_price_target=md.analyst_price_target,
                analyst_count=md.analyst_count,
                next_earnings_date=md.next_earnings_date,
                news_headline_count=n_count,
                news_sentiment_score=n_sent,
                reddit_mention_count=reddit.mention_count if reddit else 0,
                reddit_sentiment_score=reddit.sentiment_score if reddit else 0.0,
                recent_8k_summary=(
                    f"{filing.form_type} filed {filing.filed_date} — {filing.entity_name}"
                    if filing else None
                ),
            )
        )

    # ── 6. Score ──────────────────────────────────────────────────────────────
    if use_claude and os.getenv("ANTHROPIC_API_KEY"):
        signals = _score_with_claude(signals)
    else:
        signals = [_score_algorithmic(s) for s in signals]

    # ── 7. Build snapshot ─────────────────────────────────────────────────────
    data_sources = ["yfinance"]
    if news_articles:
        data_sources.append("NewsAPI")
    if any(v.mention_count > 0 for v in reddit_data.values()):
        data_sources.append("Reddit PRAW")
    if any(v for v in sec_data.values()):
        data_sources.append("SEC EDGAR")

    snapshot = MarketResearchSnapshot(
        snapshot_id=f"snap-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}",
        timestamp=datetime.now(timezone.utc),
        sector=sector,
        target_market=sector,
        stocks=signals,
        data_sources=data_sources,
    )

    # ── 8. Persist ────────────────────────────────────────────────────────────
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H")
    out_path = _storage.DATA_DIR / "research" / "market_snapshots" / f"{ts}_{sector}.json"
    _storage.write_json(out_path, snapshot.model_dump(mode="json"))
    logger.info("Snapshot saved → %s (%d stocks)", out_path.name, len(signals))

    return snapshot
