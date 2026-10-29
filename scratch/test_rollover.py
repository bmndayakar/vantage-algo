import datetime as dt

def is_in_rollover_window(tc: int, server_offset: float = 2.0, start_ist: str = "02:15", end_ist: str = "03:30") -> bool:
    if tc > 0:
        dt_srv = dt.datetime.utcfromtimestamp(tc)
        dt_utc = dt_srv - dt.timedelta(hours=server_offset)
        dt_ist = dt_utc + dt.timedelta(hours=5, minutes=30)
    else:
        dt_ist = dt.datetime.now()

    try:
        s_parts = start_ist.strip().split(":")
        e_parts = end_ist.strip().split(":")
        s_min = int(s_parts[0]) * 60 + int(s_parts[1])
        e_min = int(e_parts[0]) * 60 + int(e_parts[1])
        c_min = dt_ist.hour * 60 + dt_ist.minute
        if s_min <= e_min:
            return s_min <= c_min < e_min
        else:
            return c_min >= s_min or c_min < e_min
    except Exception:
        return False

# Test at 02:40 AM IST:
# If server_offset = 2.0 (EET) -> 02:40 IST is 21:10 UTC -> 23:10 broker server time
# Epoch for 2026-10-28 23:10:00 UTC = 1793229000
dt_srv = dt.datetime(2026, 10, 28, 23, 10, 0)
tc = int(dt_srv.replace(tzinfo=dt.timezone.utc).timestamp())
print("Is 02:40 IST in rollover window?", is_in_rollover_window(tc, server_offset=2.0))

# Test at 14:00 IST (London session):
dt_srv_day = dt.datetime(2026, 10, 28, 10, 30, 0)
tc_day = int(dt_srv_day.replace(tzinfo=dt.timezone.utc).timestamp())
print("Is 14:00 IST in rollover window?", is_in_rollover_window(tc_day, server_offset=2.0))

