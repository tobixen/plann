"""Collection of various utility functions moved out from cli.py

TODO: Should consider to remove the leading underscore from many of
them, document them and write up test code.
"""

import caldav
import datetime
import dateutil
import dateutil.parser
import logging
import re

def _now():
    return datetime.datetime.now().astimezone(datetime.timezone.utc)

def _ensure_ts(dt):
    if dt is None:
        return datetime.datetime(1970,1,1)
    if hasattr(dt, 'dt'):
        dt = dt.dt
    if isinstance(dt, datetime.datetime):
        return dt.astimezone(datetime.timezone.utc)
    return datetime.datetime(dt.year, dt.month, dt.day).astimezone(datetime.timezone.utc)

def parse_dt(input, return_type=None):
    """Parse a datetime or a date.

    If return_type is date, return a date - if return_type is
    datetime, return a datetime.  If no return_type is given, try to
    guess if we should return a date or a datetime.

    """
    if isinstance(input, datetime.datetime):
        if return_type is datetime.date:
            return input.date()
        return input
    if isinstance(input, datetime.date):
        if return_type is datetime.datetime:
            return datetime.datetime.combine(input, datetime.time(0,0))
        return input
    ## dateutil.parser.parse does not recognize '+2 hours', like date does.
    if input.startswith('+'):
        return parse_add_dur(datetime.datetime.now(), input[1:])
    ret = dateutil.parser.parse(input)
    if return_type is datetime.datetime:
        return ret
    elif return_type is datetime.date:
        return ret.date()
    elif ret.time() == datetime.time(0,0) and len(input)<12 and not '00:00' in input and not '0000' in input:
        return ret.date()
    else:
        return ret

def parse_add_dur(dt, dur):
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
        rx = re.match(r'([+-]?\d+(?:\.\d+)?)([smhdw])(.*)', dur)
        assert rx ## TODO: create some nicer error message (timedelta expected but not found)
        i = float(rx.group(1))
        u = rx.group(2)
        dur = rx.group(3)
        if u=='y' and dt:
            dt = datetime.datetime.combine(datetime.date(dt.year+i, dt.month, dt.day), dt.time())
        else:
            diff = datetime.timedelta(0, i*time_units[u])
            if dt:
                dt = dt + diff
    if dt:
        return dt
    else:
        return diff
   

## TODO ... (and should be moved somewhere else?)
def parse_timespec(timespec):
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

def find_calendars(args, raise_errors):
    def list_(obj):
        """
        For backward compatibility, a string rather than a list can be given as
        calendar_url, calendar_name.  Make it into a list.
        """
        if not obj:
            obj = []
        if isinstance(obj, str) or isinstance(obj, bytes):
            obj = [ obj ]
        return obj

    def _try(meth, kwargs, errmsg):
        try:
            ret = meth(**kwargs)
            assert(ret)
            return ret
        except:
            logging.error("Problems fetching calendar information: %s - skipping" % errmsg)
            if raise_errors:
                raise
            else:
                return None

    conn_params = {}
    for k in args:
        if k.startswith('caldav_') and args[k]:
            key = k[7:]
            if key == 'pass':
                key = 'password'
            if key == 'user':
                key = 'username'
            conn_params[key] = args[k]
    calendars = []
    if conn_params:
        client = caldav.DAVClient(**conn_params)
        principal = _try(client.principal, {}, conn_params['url'])
        if not principal:
            return []
        calendars = []
        tries = 0
        for calendar_url in list_(args.get('calendar_url')):
            if '/' in calendar_url:
                calendar = principal.calendar(cal_url=calendar_url)
            else:
                calendar = principal.calendar(cal_id=calendar_url)
            tries += 1
            if _try(calendar.get_display_name, {}, calendar.url):
                calendars.append(calendar)
        for calendar_name in list_(args.get('calendar_name')):
            tries += 1
            calendar = _try(principal.calendar, {'name': calendar_name}, '%s : calendar "%s"' % (conn_params['url'], calendar_name))
            calendars.append(calendar)
        if not calendars and tries == 0:
            calendars = _try(principal.calendars, {}, "conn_params['url'] - all calendars")
    return calendars or []

def _summary(i):
    if hasattr(i, 'icalendar_component'):
        i = i.icalendar_component
    return i.get('summary') or i.get('description') or i.get('uid')

def _procrastinate(objs, delay, check_dependent="error", err_callback=print, confirm_callback=lambda x: False):
    for x in objs:
        chk_parent = 'return' if check_dependent else False
        if isinstance(delay, datetime.date):
            new_due = delay
        else:
            old_due = x.get_due().astimezone(datetime.timezone.utc)
            new_due = datetime.datetime.now().astimezone(datetime.timezone.utc)
            if old_due:
                new_due = max(new_due, old_due)
            new_due = parse_add_dur(new_due, delay)
            new_due = new_due.astimezone(datetime.timezone.utc)
        parent = x.set_due(new_due, move_dtstart=True, check_dependent=chk_parent)
        if parent:
            if check_dependent in ("error", "interactive"):
                i = x.icalendar_component
                summary = _summary(i)
                p = parent.icalendar_component
                err_callback(f"{summary} could not be postponed due to parent {_summary(p)} with due {p['DUE'].dt} and priority {p.get('priority', 0)}")
                if check_dependent == "interactive" and p.get('priority', 9)>2 and confirm_callback("procrastinate parent?"):
                    _procrastinate([parent], new_due+max(parent.get_duration(), datetime.timedelta(1)), check_dependent)
                    _procrastinate([x], new_due, check_dependent)
            elif check_dependent == "return":
                return parent
        else:
            x.save()
