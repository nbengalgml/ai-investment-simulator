from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import requests

_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
_HEADERS = {"User-Agent": "ai-investment-simulator research@simulation.invalid"}


@dataclass
class SecFiling:
    ticker: str
    form_type: str
    filed_date: str
    entity_name: str
    filing_url: str


def fetch_recent_8k(ticker: str, days_back: int = 30) -> Optional[SecFiling]:
    """Return the most recent 8-K filing for a ticker, or None."""
    end = datetime.utcnow().strftime("%Y-%m-%d")
    start = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    params = {
        "q": f'"{ticker}"',
        "forms": "8-K",
        "dateRange": "custom",
        "startdt": start,
        "enddt": end,
        "from": "0",
        "size": "1",
    }
    try:
        resp = requests.get(_SEARCH_URL, params=params, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        if not hits:
            return None
        src = hits[0].get("_source", {})
        return SecFiling(
            ticker=ticker.upper(),
            form_type=src.get("form_type", "8-K"),
            filed_date=src.get("file_date", ""),
            entity_name=src.get("entity_name", ticker),
            filing_url=(
                f"https://www.sec.gov/cgi-bin/browse-edgar"
                f"?action=getcompany&CIK={ticker}&type=8-K"
            ),
        )
    except Exception:
        return None


def fetch_batch_8k(tickers: list[str]) -> dict[str, Optional[SecFiling]]:
    return {t: fetch_recent_8k(t) for t in tickers}
