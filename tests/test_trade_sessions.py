
import pytest
from datetime import datetime, time, date
from utils.trade_sessions import detect_trade_session

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
