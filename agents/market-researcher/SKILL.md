# SKILL.md — market-researcher

> **SIMULATION ONLY** — not financial advice.

## SEC EDGAR Query Patterns

8-K search (earnings events, material news):
```
GET https://efts.sec.gov/LATEST/search-index
  ?q="NVDA"&forms=8-K&dateRange=custom&startdt=YYYY-MM-DD&enddt=YYYY-MM-DD
  &from=0&size=1
User-Agent: ai-investment-simulator research@simulation.invalid
```
Rate limit: be conservative — fetch only top 5 tickers per cycle.
Key fields in response: `file_date`, `form_type`, `entity_name`.

## NewsAPI Query Construction

Combine sector term with top tickers using OR:
```python
query = '"AI" OR "NVDA" OR "MSFT" OR "GOOGL" OR "META" OR "AMZN"'
client.get_everything(q=query, language="en", sort_by="publishedAt",
                      page_size=20, from_param=from_date)
```
Free tier: 100 requests/day, articles up to 30 days old.
Filter to articles mentioning each ticker for per-ticker score.

## Reddit Sentiment Scoring

Subreddits: r/wallstreetbets, r/investing, r/stocks
Method: `subreddit.hot(limit=50)` per subreddit.

Scoring rubric:
- **Mention count** — word-boundary regex match: `\bNVDA\b`
- **Sentiment** — keyword scoring on post title (see `shared/news_feeds/sentiment.py`)
  - Positive words: beat, surge, rally, upgrade, strong, record, bullish, growth...
  - Negative words: miss, decline, downgrade, weak, loss, bearish, cut...
  - Score = (pos − neg) / (pos + neg) → [-1, 1]
- **Velocity bonus** — mention_count > 10 adds +15 to sentiment contribution

## yfinance Data Extraction

```python
t = yf.Ticker("NVDA")
info = t.info  # dict with currentPrice, trailingPE, recommendationKey, targetMeanPrice...
hist = t.history(period="3mo")  # OHLCV DataFrame

# Momentum: 20-day price return
momentum_20d = (current_price - hist["Close"].iloc[-20]) / hist["Close"].iloc[-20] * 100

# Analyst consensus values: "strong_buy", "buy", "hold", "sell", "underperform", "none"
consensus = info.get("recommendationKey", "none")
```

Key `info` fields:
| Field | Meaning |
|---|---|
| `currentPrice` | Latest price |
| `previousClose` | Prior session close |
| `trailingPE` | P/E ratio |
| `fiftyTwoWeekHigh/Low` | 52-week range |
| `recommendationKey` | Analyst consensus |
| `targetMeanPrice` | Consensus price target |
| `numberOfAnalystOpinions` | Analyst count |

## Algorithmic Scoring Fallback

When `ANTHROPIC_API_KEY` is absent:

**momentum_score**:
- ≥15% 20d gain → 90 | ≥10% → 80 | ≥5% → 70 | ≥0% → 55 | <0% → 40/25/10

**fundamental_score base**:
- strong_buy → 90 | buy → 75 | hold → 50 | sell/underperform → 25

**fundamental_score adjustment**:
- analyst_price_target upside >20% → +10 | upside <-10% → -15

**sentiment_score**:
- `(news_sentiment * 25 + 50) + (reddit_sentiment * 25 + 50)) / 2`
- mention_count >10 → +15 | >5 → +8
- headline_count >5 → +10

**composite**:
`momentum*0.40 + fundamental*0.35 + sentiment*0.25`
