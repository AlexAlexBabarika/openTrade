from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta

PERIOD_TO_DELTA = {
    "1d": timedelta(days=1),
    "5d": timedelta(days=5),
    "1w": timedelta(weeks=1),
    "1mo": relativedelta(months=1),
    "3mo": relativedelta(months=3),
    "6mo": relativedelta(months=6),
    "1y": relativedelta(years=1),
    "2y": relativedelta(years=2),
    "5y": relativedelta(years=5),
    "10y": relativedelta(years=10),
    "max": timedelta(days=365 * 10),
}


def period_to_startdate(period: str) -> str:
    """Convert period label to ISO start date (UTC) for provider APIs."""
    delta = PERIOD_TO_DELTA.get(period)
    if delta is None:
        allowed = ", ".join(sorted(PERIOD_TO_DELTA))
        raise ValueError(f"Invalid period '{period}'. Use one of: {allowed}")
    start = datetime.now(timezone.utc) - delta
    return start.strftime("%Y-%m-%d")
