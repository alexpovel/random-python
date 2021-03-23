from datetime import datetime
from sys import version_info

if version_info >= (3, 9):
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
else:
    from backports.zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    _LOCAL_TZ = ZoneInfo("localtime")
except ZoneInfoNotFoundError:
    _LOCAL_TZ = ZoneInfo("Europe/Berlin")


def now(tzinfo=_LOCAL_TZ):
    return datetime.now(tz=tzinfo)


def aware_timestamp(utc_epoch, tzinfo=_LOCAL_TZ):
    """Turns a UTC Unix epoch timestamp into a timezone-aware datetime object."""
    return datetime.utcfromtimestamp(utc_epoch).replace(tzinfo=tzinfo)
