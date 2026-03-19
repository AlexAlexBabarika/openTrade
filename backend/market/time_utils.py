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


def period_to_startdate(period: str) -> datetime:
    """Convert period to start date."""
    delta = PERIOD_TO_DELTA[period]
    if delta is None:
        raise ValueError(f"Invalid period: {period}")
    start = datetime.now(timezone.utc) - delta
    return start.strftime("%Y-%m-%d")
