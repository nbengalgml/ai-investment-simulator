from typing import Final

SECTOR_TICKERS: Final[dict[str, list[str]]] = {
    "AI": ["NVDA", "MSFT", "GOOGL", "META", "AMZN", "AMD", "ORCL", "CRM", "PLTR", "SOUN"],
    "cloud": ["MSFT", "AMZN", "GOOGL", "CRM", "SNOW", "DDOG", "NET", "ZS", "MDB", "HUBS"],
    "networking": ["CSCO", "ANET", "JNPR", "CIEN", "EXTR", "CALX", "LITE", "VIAV", "INFN", "RBBN"],
    "alternative_energy": ["ENPH", "FSLR", "RUN", "NOVA", "SEDG", "PLUG", "BE", "ARRY", "CSIQ", "JKS"],
    "gas": ["XOM", "CVX", "COP", "EOG", "PXD", "DVN", "HAL", "SLB", "BKR", "MPC"],
    "finance": ["JPM", "BAC", "WFC", "GS", "MS", "C", "AXP", "BLK", "SCHW", "COF"],
}


def get_tickers(sector: str) -> list[str]:
    key = sector.lower().replace(" ", "_").replace("-", "_")
    return SECTOR_TICKERS.get(key, SECTOR_TICKERS["AI"])
