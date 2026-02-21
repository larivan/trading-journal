
import pytest
from datetime import datetime, time, date

from utils.trade_sessions import (
    detect_trade_session,
    _ensure_date,
    _ensure_time,
    _resolve_tz,
)

# Test with a fixed timezone context if possible, 
# but detect_trade_session accepts local_tz_label.

def test_detect_frankfurt_open():
    # Frankfurt Open is 08:00 Frankfurt time.
    # Frankfurt is usually UTC+1 or UTC+2.
    # We'll use "UTC+1" (CET) as local_tz for simplicity of mental math, 
    # OR we can assume the user is in Moscow (UTC+3) and calculate accordingly.
    
    # Let's align with the module's logic. It converts input time (naive, interpreted as local_tz) 
    # to target timezone (Berlin).
    
    # If I am in UTC+3 (Moscow), and it's 10:00, that's 07:00 UTC -> 08:00 Berlin (winter).
    # Berlin windows: 08:00 - 09:00.
    
    # Date: Winter (Jan 1)
    d = date(2023, 1, 1)
    t = time(10, 30) # 10:30 MSK (UTC+3) -> 07:30 UTC -> 08:30 CET
    
    session = detect_trade_session(d, t, local_tz_label="UTC+3")
    # 08:30 is inside Frankfurt (08-09).
    # But wait, logic iterates priority: London -> Frankfurt -> NY.
    # London windows: 08:00-10:00 (LOKZ).
    # 07:30 UTC -> 07:30 London. Not started yet (starts 08:00).
    # So it falls through to Frankfurt.
    # Frankfurt: 08:00-09:00.
    # 08:30 is in window.
    assert session == "Frankfurt"

def test_detect_london_open():
    # London (LOKZ) 08:00 - 10:00 London time.
    # Winter: London is UTC+0.
    # MSK: UTC+3.
    # We need 08:30 London -> 11:30 MSK.
    
    d = date(2023, 1, 1)
    t = time(11, 30) # 11:30 MSK -> 08:30 UTC (London)
    
    session = detect_trade_session(d, t, local_tz_label="UTC+3")
    assert session == "LOKZ"

def test_detect_ny_open():
    # NY (NYKZ) 08:00 - 10:00 NY time.
    # Winter: NY is UTC-5.
    # MSK: UTC+3.
    # Diff: 8 hours.
    # 08:30 NY -> +8 -> 16:30 MSK.
    
    d = date(2023, 1, 1)
    t = time(16, 30)
    
    session = detect_trade_session(d, t, local_tz_label="UTC+3")
    assert session == "NYKZ"

def test_detect_lunch():
    # London Lunch: 10:00 - 12:00 London time.
    # 10:30 London -> 13:30 MSK.
    
    d = date(2023, 1, 1)
    t = time(13, 30)
    
    session = detect_trade_session(d, t, local_tz_label="UTC+3")
    assert session == "Lunch"

def test_detect_pre_ny():
    # Pre-NY: 07:00 - 08:00 NY time.
    # 07:30 NY -> 15:30 MSK.
    
    d = date(2023, 1, 1)
    t = time(15, 30)
    
    session = detect_trade_session(d, t, local_tz_label="UTC+3")
    assert session == "Pre-NY"

def test_detect_other():
    # Late night
    d = date(2023, 1, 1)
    t = time(23, 00)
    
    session = detect_trade_session(d, t, local_tz_label="UTC+3")
    # "Other" is usually valid if returned, checking implementation...
    # It returns "Other" or last value of TRADE_SESSION_VALUES.
    # "Other" is in TRADE_SESSION_VALUES.
    assert session == "Other"

def test_unsupported_timezone():
    # Should probably raise error or handle gracefully?
    # Implementation raises ValueError for invalid label in _resolve_tz.
    with pytest.raises(ValueError):
        detect_trade_session(date(2023,1,1), time(12,0), local_tz_label="INVALID")


class TestEnsureDate:
    def test_date_object(self):
        d = date(2026, 1, 15)
        assert _ensure_date(d) == d

    def test_datetime_extracts_date(self):
        dt = datetime(2026, 1, 15, 10, 30)
        assert _ensure_date(dt) == date(2026, 1, 15)

    def test_string_iso(self):
        assert _ensure_date("2026-01-15") == date(2026, 1, 15)

    def test_string_dot_format(self):
        assert _ensure_date("15.01.2026") == date(2026, 1, 15)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _ensure_date("not-a-date")

    def test_unsupported_type_raises(self):
        with pytest.raises((ValueError, TypeError)):
            _ensure_date(12345)


class TestEnsureTime:
    def test_time_object(self):
        t = time(10, 30)
        assert _ensure_time(t) == t

    def test_datetime_extracts_time(self):
        dt = datetime(2026, 1, 15, 10, 30)
        assert _ensure_time(dt) == time(10, 30)

    def test_string_hhmmss(self):
        assert _ensure_time("10:30:00") == time(10, 30, 0)

    def test_string_hhmm(self):
        assert _ensure_time("10:30") == time(10, 30)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _ensure_time("not-a-time")

    def test_unsupported_type_raises(self):
        with pytest.raises((ValueError, TypeError)):
            _ensure_time(99999)


class TestResolveTz:
    def test_utc_plus_offset(self):
        from datetime import timezone, timedelta
        tz = _resolve_tz("UTC+3")
        assert tz == timezone(timedelta(hours=3))

    def test_utc_minus_offset(self):
        from datetime import timezone, timedelta
        tz = _resolve_tz("UTC-5")
        assert tz == timezone(timedelta(hours=-5))

    def test_iana_name(self):
        from zoneinfo import ZoneInfo
        tz = _resolve_tz("Europe/Moscow")
        assert isinstance(tz, ZoneInfo)

    def test_invalid_label_raises(self):
        with pytest.raises(ValueError):
            _resolve_tz("BADTZ")


class TestDetectSessionWithLocalTzLabel:
    def test_iana_tz_label_override(self):
        """detect_trade_session принимает IANA-имя в local_tz_label."""
        d = date(2023, 1, 1)
        # 11:30 Europe/Moscow = 08:30 UTC = 08:30 London → LOKZ
        t = time(11, 30)
        session = detect_trade_session(d, t, local_tz_label="Europe/Moscow")
        assert session == "LOKZ"

    def test_string_date_and_time_inputs(self):
        """detect_trade_session принимает строки вместо объектов date/time."""
        session = detect_trade_session("2023-01-01", "11:30:00", local_tz_label="UTC+3")
        assert session == "LOKZ"

    def test_datetime_inputs(self):
        """detect_trade_session принимает datetime-объекты."""
        dt_date = datetime(2023, 1, 1)
        dt_time = datetime(2023, 1, 1, 11, 30)
        session = detect_trade_session(dt_date, dt_time, local_tz_label="UTC+3")
        assert session == "LOKZ"
