"""Collection of various utility functions moved out from cli.py

TODO: Should consider to remove the leading underscore from many of
them, document them and write up test code.

TODO: Move time handling to a separate timespec.py
"""

import caldav
import datetime
import dateutil
import dateutil.parser
import logging
import re
from dataclasses import dataclass
import zoneinfo
from collections import defaultdict

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

def parse_dt(input, return_type=None):
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
        rx = re.match(r'([+-]?\d+(?:\.\d+)?)([smhdwy])(.*)', dur)
        assert rx ## TODO: create some nicer error message (timedelta expected but not found)
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
        return dt
    else:
        return diff
   

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

def _icalendar_component(obj):
    try:
        return obj.icalendar_component
    except AttributeError:
        ## assume obj is an icalendar_component
        return obj

def _summary(i):
    i = _icalendar_component(i)
    return i.get('summary') or i.get('description') or i.get('uid')

childlike = {'CHILD', 'NEXT', 'FINISHTOSTART'}
parentlike = {'PARENT', 'FIRST', 'DEPENDS-ON', 'STARTTOFINISH'}

def _procrastinate(objs, delay, check_dependent="error", with_children=False, with_family=False, with_parent=False, err_callback=print, confirm_callback=lambda x: False, recursivity=0):
    assert recursivity<16 ## TODO: better error message.  Probably we have some kind of relationship loop here.
    for x in objs:
        if x.icalendar_component.get('RELATED-TO'):
            if with_family == 'interactive':
                with_family = confirm_callback("There are relations - postpone the whole family tree?")
            if not with_family and with_parent == 'interactive' and _hasreltype(x, parentlike):
                with_parent = confirm_callback("There exists (a) parent(s) - postpone the parent?")
            if not with_family and with_children == 'interactive' and _hasreltype(x, childlike):
                with_children = confirm_callback("There exists children - postpone the children?")
        if with_family:
            parents = x.get_relatives(reltypes=parentlike)
            if parents:
                _procrastinate(parents, delay, check_dependent, with_children, with_family, with_parent, err_callback, confirm_callback, recursivity=recursivity+1)
                continue
            else:
                _procrastinate([x], delay, check_dependent, with_children=True, with_family=False, with_parent=False, err_callback=err_callback, confirm_callback=confirm_callback, recursivity=recursivity+1)
                continue
        if with_parent:
            parents = x.get_relatives(reltypes=parentlike)
            _procrastinate(parents, delay, check_dependent, with_children=True, with_family=False, with_parent=False, err_callback=err_callback, confirm_callback=confirm_callback, recursivity=recursivity+1)
        
        chk_parent = 'return' if check_dependent else False
        if isinstance(delay, datetime.date):
            new_due = delay
        else:
            old_due = _ensure_ts(x.get_due())
            new_due = _now()
            if old_due:
                new_due = max(new_due, old_due)
            new_due = parse_add_dur(new_due, delay)
        parent = x.set_due(new_due, move_dtstart=True, check_dependent=chk_parent)
        if parent:
            if check_dependent in ("error", "interactive"):
                i = x.icalendar_component
                summary = _summary(i)
                p = parent.icalendar_component
                err_callback(f"{summary} could not be postponed due to parent {_summary(p)} with due {_ensure_ts(p['DUE'])} and priority {p.get('priority', 0)}")
                if check_dependent == "interactive" and p.get('priority', 9)>2 and confirm_callback("procrastinate parent?"):
                    _procrastinate([parent], new_due+max(parent.get_duration(), datetime.timedelta(1)), check_dependent=check_dependent, err_callback=err_callback, confirm_callback=confirm_callback, recursivity=recursivity+1)
                    _procrastinate([x], new_due, check_dependent=check_dependent, err_callback=err_callback, confirm_callback=confirm_callback, recursivity=recursivity+1)
            elif check_dependent == "return":
                return parent
        else:
            x.save()
        if with_children:
            children = x.get_relatives(reltypes=childlike) ## TODO: consider reverse relationships
            _procrastinate(children, delay, check_dependent, with_children=True, with_family=False, with_parent=False, err_callback=err_callback, confirm_callback=confirm_callback, recursivity=recursivity+1)

def _adjust_relations(obj, relations_wanted={}):
    """
    obj is an event/task/journal object from caldav library.
    relations_wanted is a dict with RELTYPE as key and list or set of UUIDs as value.
    reltypes in OBJ that does not exist in RELATIONS_WANTED will be ignored.
    TODO: NOT SUPPORTED YET:
    If {'childlike'=>[]} or {'parentlike'=>[]} is in the dict, then:
      1) All "parentlike" or "childlike" relations not in relations_wanted will be wiped
      2) The original RELTYPE will be kept if ... TODO: we need another parameter for this

    Does not save the object.
    """
    rels = obj.get_relatives(fetch_objects=False)
    iobj = _icalendar_component(obj)
    mutated = False
    for rel_type in relations_wanted:
        if (not rel_type in rels) or rels[rel_type] != relations_wanted[rel_type]:
            mutated = True
        rels[rel_type] = relations_wanted[rel_type]
    if not mutated:
        return False
            
    if 'RELATED-TO' in iobj:
        iobj.pop('RELATED-TO')

    for rel_type in rels:
        for uid in rels[rel_type]:
            iobj.add('RELATED-TO', uid, parameters={'RELTYPE': rel_type})

    return True

## TODO: As for now, this one will throw the user into the python debugger if inconsistencies are found.
## It for sure cannot be like that when releasing plann 1.0!
def _relships_by_type(obj, reltype_wanted=None):
    backreltypes = {'CHILD': 'PARENT', 'PARENT': 'CHILD', 'undefined': 'CHILD', 'SIBLING': 'SIBLING'}
    rels_by_type = obj.get_relatives(reltype_wanted)
    ret = defaultdict(list)
    for reltype in rels_by_type:
        for other in rels_by_type[reltype]:
            ret[reltype].append(other)
            
            ## Consistency check ... TODO ... look more into breakages
            other_rels = other.get_relatives(fetch_objects=False)
            back_rel_types = set()
            for back_rel_type in other_rels:
                if str(obj.icalendar_component['UID']) in other_rels[back_rel_type]:
                    back_rel_types.add(back_rel_type)

            if len(back_rel_types) > 1:
                import pdb; pdb.set_trace()
                ## Inconsistency has to be manually fixed: more than one related-to property pointing from other to obj
                1
            if len(back_rel_types) == 0:
                import pdb; pdb.set_trace()
                ## Inconsistency will be automatically fixed: no related-to property pointing from other to obj
                ## adding the missing back rel
                other.icalendar_component.add('RELATED-TO', str(obj.icalendar_component['UID']), parameters={'RELTYPE': backreltypes[reltype]})
            else:
                if back_rel_types != { backreltypes[reltype] }:
                    import pdb; pdb.set_trace()
                    ## Inconsistency has to be manually fixed: object and other points to each other, but reltype does not match
                    1
    return ret

def _get_summary(obj):
    i = _icalendar_component(obj)
    return i.get('summary') or i.get('description') or i.get('uid')

def _relationship_text(obj, reltype_wanted=None):
    rels = obj.get_relatives(fetch_objects=False, reltype_wanted=reltype_wanted)
    if not rels:
        return "(None)"
    ret = []
    for rel in rels:
        objs = []
        for relobj in rels[rel]:
            objs.append(_get_summary(relobj))
        ret.append(rel + "\n" + "\n".join(objs) + "\n")
    return "\n".join(ret)
