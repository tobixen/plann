from dataclasses import dataclass
import zoneinfo
import datetime
import dateutil
import dateutil.parser
import re

## Singleton (aka global variable)
@dataclass
class Tz():
    """
    Singleton class storing timezone preferences

    (floating time not supported yet)
    """
    show_native_timezone: bool=False
    _implicit_timezone: zoneinfo.ZoneInfo = None
    _store_timezone: zoneinfo.ZoneInfo = zoneinfo.ZoneInfo('UTC')

    @property
    def implicit_timezone(self):
        return self._implicit_timezone
    
    @property
    def store_timezone(self):
        return self._store_timezone

    @implicit_timezone.setter
    def implicit_timezone(self, value):
        if value:
            self._implicit_timezone = zoneinfo.ZoneInfo(value)
            if not self.store_timezone:
                self._store_timezone = self._implicit_timezone

    @store_timezone.setter
    def store_timezone(self, value):
        if value:
            self._store_timezone = zoneinfo.ZoneInfo(value)

tz=Tz()

def _now():
    return datetime.datetime.now().astimezone(tz.implicit_timezone)

def _ensure_ts(dt):
    """
    TODO: do we need this?  it's a bit overlapping with parse_dt
    """
    if hasattr(dt, 'dt'):
        dt = dt.dt
    if dt is None:
        return datetime.datetime(1970,1,1).astimezone(tz.implicit_timezone)
    if isinstance(dt, datetime.datetime):
        if not dt.tzinfo:
            return dt.replace(tzinfo=tz.implicit_timezone).astimezone(tz.implicit_timezone)
        else:
            return dt
    return datetime.datetime(dt.year, dt.month, dt.day, tzinfo=tz.implicit_timezone).astimezone(tz.implicit_timezone)

def parse_dt(input, return_type=None, for_storage=False):
    ret = _parse_dt(input, return_type)
    if for_storage:
        ret = ret.astimezone(tz.store_timezone)
    return ret
    
def _parse_dt(input, return_type=None):
    """
    Convenience-method, it is very liberal in what it accepts as input:

    * Date string or datetime string (uses dateutil.parser)
    * datetime or date
    * VDDDTypes from the icalendar library
    * strings like "+2h" means "two hours in the future"

    If return_type is date, return a date - if return_type is
    datetime, return a datetime.  If no return_type is given, try to
    guess if we should return a date or a datetime.  Datetime should
    always have a timezone.
    """
    if hasattr(input, 'dt'):
        input = input.dt
    if isinstance(input, datetime.datetime):
        if return_type is datetime.date:
            return input.date()
        return _ensure_ts(input)
    if isinstance(input, datetime.date):
        if return_type is datetime.datetime:
            return _ensure_ts(input)
        return input
    ## dateutil.parser.parse does not recognize '+2 hours', like date does.
    if input.startswith('+'):
        ret = parse_add_dur(datetime.datetime.now(), input[1:])
    else:
        ret = dateutil.parser.parse(input)
    if return_type is datetime.datetime:
        return _ensure_ts(ret)
    elif return_type is datetime.date:
        return ret.date()
    elif ret.time() == datetime.time(0,0) and len(input)<12 and not '00:00' in input and not '0000' in input:
        return ret.date()
    else:
        return _ensure_ts(ret)


def parse_add_dur(dt, dur, for_storage=False, ts_allowed=False):
    """
    duration may be something like this:
      * 1s (one second)
      * 3m (three minutes, not months
      * 3.5h
      * 1y1w
    
    It may also be a ISO8601 duration

    Returns the dt plus duration.

    If no dt is given, return the duration.

    TODO: months not supported yet
    TODO: return of delta in years not supported yet
    TODO: ISO8601 duration not supported yet
    """
    if dt and not (isinstance(dt, datetime.date)):
        dt = parse_dt(dt)
    time_units = {
        's': 1, 'm': 60, 'h': 3600,
        'd': 86400, 'w': 604800,
        'y': 1314000
    }
    while dur:
        rx = re.match(r'([+-]?\d+(?:\.\d+)?)([smhdwy])(.*)', dur)
        if not rx:
            if ts_allowed:
                return parse_dt(dur)
            else:
                raise ValueError(f"A duration (like 3h for three hours) expected, but got: {dur}")
        i = float(rx.group(1))
        u = rx.group(2)
        dur = rx.group(3)
        if u=='y' and dt:
            dt = datetime.datetime.combine(datetime.date(dt.year+int(i), dt.month, dt.day), dt.time(), tzinfo=dt.tzinfo)
        else:
            diff = datetime.timedelta(0, i*time_units[u])
            if dt:
                dt = dt + diff
    if dt:
        return dt.astimezone(tz.store_timezone) if for_storage else dt
    else:
        return diff
   

def parse_timespec(timespec, for_storage=False):
    ret = _parse_timespec(timespec)
    if for_storage:
        ret = (x and x.astimezone(tz.store_timezone) for x in ret)
    return ret

def _parse_timespec(timespec):
    """parses a timespec and return two timestamps

    The ISO8601 interval format, format 1, 2 or 3 as described at
    https://en.wikipedia.org/wiki/ISO_8601#Time_intervals should be
    accepted, though it may be dependent on
    https://github.com/gweis/isodate/issues/77 or perhaps
    https://github.com/dateutil/dateutil/issues/1184 
    
    The calendar-cli format (i.e. 2021-01-08 15:00:00+1h) should be accepted

    Two timestamps should be accepted.

    One timestamp should be accepted, and the second return value will be None.
    """
    if isinstance(timespec, datetime.date):
        return (timespec,timespec)

    if (
            isinstance(timespec, tuple) and
            len(timespec)==2 and
            isinstance(timespec[0], datetime.date) and
            isinstance(timespec[1], datetime.date)):
        return timespec
    
    ## calendar-cli format, 1998-10-03 15:00+2h
    if '+' in timespec:
        rx = re.match(r'(.*)\+((?:\d+(?:\.\d+)?[smhdwy])+)$', timespec)
        if rx:
            start = parse_dt(rx.group(1))
            end = parse_add_dur(start, rx.group(2))
            return (start, end)
    try:
        ## parse("2015-05-05 2015-05-05") does not throw the ParserError
        if timespec.count('-')>3:
            raise dateutil.parser.ParserError("Seems to be two dates here")
        ret = parse_dt(timespec)
        return (ret,None)
    except dateutil.parser.ParserError:
        split_by_space = timespec.split(' ')
        if len(split_by_space) == 2:
            return (parse_dt(split_by_space[0]), parse_dt(split_by_space[1]))
        elif len(split_by_space) == 4:
            return (parse_dt(f"{split_by_space[0]} {split_by_space[1]}"), parse_dt(f"{split_by_space[2]} {split_by_space[3]}"))
        else:
            raise ValueError(f"couldn't parse time interval {timespec}")

    raise NotImplementedError("possibly a ISO time interval")
