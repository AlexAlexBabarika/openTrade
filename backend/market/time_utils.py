from datetime import datetime, timezone

from backend.market.shared_config import PERIOD_TO_DELTA


def period_to_startdate(period: str) -> str:
    """Convert period label to ISO start date (UTC) for provider APIs."""
    delta = PERIOD_TO_DELTA.get(period)
    if delta is None:
        from backend.market.shared_config import ALLOWED_PERIODS

        allowed = ", ".join(sorted(ALLOWED_PERIODS))
        raise ValueError(f"Invalid period '{period}'. Use one of: {allowed}")
    start = datetime.now(timezone.utc) - delta
    return start.strftime("%Y-%m-%d")
