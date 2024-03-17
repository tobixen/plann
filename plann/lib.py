"""Collection of various utility functions moved out from cli.py

TODO: Should consider to remove the leading underscore from many of
them, document them and write up test code.

TODO: make a separate class for relations.  (perhaps in the caldav library?)

TODO: Sort all this mess.  Split out things that are interactive?
"""

import datetime
import caldav
import logging
from collections import defaultdict
from plann.template import Template
from plann.timespec import tz, _now, _ensure_ts, parse_dt, parse_add_dur, parse_timespec
import click ## TODO - this should be removed, eventually

## TODO: maybe find those attributes through the icalendar library? icalendar.cal.singletons, icalendar.cal.multiple, etc
attr_txt_one = ['location', 'description', 'geo', 'organizer', 'summary', 'class', 'rrule', 'status']
attr_txt_many = ['category', 'comment', 'contact', 'resources', 'parent', 'child'] ## category is an odd-ball, it should be categories - but we need a lot more test code before we can change that.
attr_time = ['dtstamp', 'dtstart', 'due', 'dtend', 'duration']
attr_int = ['priority']

def _split_vcal(ical):
    ical = ical.strip()
    icals = []
    while ical.startswith("BEGIN:VCALENDAR\n"):
        pos = ical.find("\nEND:VCALENDAR") + 14
        icals.append(ical[:pos])
        ical = ical[pos:].lstrip()
    return icals

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

def _add_category(obj, category):
    comp = _icalendar_component(obj)
    if 'categories' in comp:
        cats = comp.pop('categories').cats
    else:
        cats = []
    if hasattr(category, 'split'):
        category = category.split(',')
    cats.extend(category)
    comp.add('categories', cats)

def _summary(obj):
    i = _icalendar_component(obj)
    return i.get('summary') or i.get('description') or i.get('uid')

childlike = {'CHILD', 'NEXT', 'FINISHTOSTART'}
parentlike = {'PARENT', 'FIRST', 'DEPENDS-ON', 'STARTTOFINISH'}

def _procrastinate(objs, delay, check_dependent="error", with_children=False, with_family=False, with_parent=False, err_callback=print, confirm_callback=lambda x: False, recursivity=0):
    if delay in ('0', '9s', '0m', '0h', '0d', datetime.timedelta(0)):
        ## Do nothing!
        return
    assert recursivity<16 ## TODO: better error message.  Probably we have some kind of relationship loop here.
    for x in objs:
        if not hasattr(x, 'set_due'):
            continue
        if x.icalendar_component.get('STATUS', 'NEEDS-ACTION') == 'COMPLETED':
            continue
        if x.icalendar_component.get('RELATED-TO'):
            if with_family == 'interactive':
                with_family = confirm_callback("There are relations - postpone the whole family tree?")
            if not with_family and with_parent == 'interactive' and x.get_relatives(parentlike, fetch_objects=False):
                with_parent = confirm_callback("There exists (a) parent(s) - postpone the parent?")
            if not with_family and with_children == 'interactive' and x.get_relatives(childlike, fetch_objects=False):
                with_children = confirm_callback("There exists children - postpone the children?")
        if with_family:
            ## TODO: refactor.  Make relations into a class.
            parents_ = x.get_relatives(reltypes=parentlike)
            parents = set()
            for rel_type in parents_:
                parents.update(parents_[rel_type])
            if parents:
                _procrastinate(parents, delay, check_dependent, with_children, with_family, with_parent, err_callback, confirm_callback, recursivity=recursivity+1)
                continue
            else:
                _procrastinate([x], delay, check_dependent, with_children=True, with_family=False, with_parent=False, err_callback=err_callback, confirm_callback=confirm_callback, recursivity=recursivity+1)
                continue
        if with_parent:
            parents = x.get_relatives(reltypes=parentlike)
            for rel_type in parents: ## Should only be PARENT as for now.
                _procrastinate(parents[rel_type], delay, check_dependent, with_children=True, with_family=False, with_parent=False, err_callback=err_callback, confirm_callback=confirm_callback, recursivity=recursivity+1)

        chk_parent = 'return' if check_dependent else False
        if isinstance(delay, datetime.date):
            new_due = delay
        else:
            old_due = _ensure_ts(x.get_due())
            new_due = _now()
            if old_due:
                new_due = max(new_due, old_due)
            new_due = parse_add_dur(new_due, delay, ts_allowed=True, for_storage=True)
            ## Let's force the due to be a timestamp
            if not isinstance(new_due, datetime.datetime):
                new_due = datetime.datetime(ts.year, ts.month, ts.day)
        parent = x.set_due(new_due, move_dtstart=True, check_dependent=chk_parent)
        if parent:
            if check_dependent in ("error", "interactive"):
                i = x.icalendar_component
                summary = _summary(i)
                p = parent.icalendar_component
                if p.get('STATUS') == 'COMPLETED':
                    _procrastinate([x], new_due, check_dependent=False, err_callback=err_callback, confirm_callback=confirm_callback, recursivity=recursivity+1)
                else:
                    err_callback(f"{summary} could not be postponed due to parent {_summary(p)} with due {_ensure_ts(p['DUE'])} and priority {p.get('priority', 0)}")
                    if check_dependent == "interactive" and p.get('priority', 9)>2 and confirm_callback("procrastinate parent?"):
                        _procrastinate([parent], new_due+max(parent.get_duration()+x.get_duration()+datetime.timedelta(minutes=1), datetime.timedelta(minutes=1)), check_dependent=check_dependent, err_callback=err_callback, confirm_callback=confirm_callback, recursivity=recursivity+1)
                        _procrastinate([x], new_due, check_dependent=check_dependent, err_callback=err_callback, confirm_callback=confirm_callback, recursivity=recursivity+1)
            elif check_dependent == "return":
                return parent
        else:
            x.save()
        if with_children:
            ## TODO: refactor.  Make relations into a class.
            children_ = x.get_relatives(reltypes=childlike)
            children = set()
            for rel_type in children_:
                children.update(children_[rel_type])
            _procrastinate(children, delay, check_dependent, with_children=True, with_family=False, with_parent=False, err_callback=err_callback, confirm_callback=confirm_callback, recursivity=recursivity+1)

def _adjust_ical_relations(obj, relations_wanted={}):
    """
    obj is an event/task/journal object from caldav library or icalendar library.
    relations_wanted is a dict with RELTYPE as key and list or set of UUIDs as value.
    reltypes in OBJ that does not exist in RELATIONS_WANTED will be ignored.
    TODO: NOT SUPPORTED YET:
    If {'childlike'=>[]} or {'parentlike'=>[]} is in the dict, then:
      1) All "parentlike" or "childlike" relations not in relations_wanted will be wiped
      2) The original RELTYPE will be kept if ... TODO: we need another parameter for this

    Does not save the object.  Does not consider reverse relations, that's up to the caller.
    """
    rels = obj.get_relatives(fetch_objects=False)
    iobj = _icalendar_component(obj)
    mutated = defaultdict(dict)
    for rel_type in relations_wanted:
        if not rel_type in rels and relations_wanted[rel_type]:
            mutated['added'][rel_type] = set(rels[rel_type])
        if set(rels[rel_type]) != set(relations_wanted[rel_type]):
            mutated['removed'][rel_type] = set(rels[rel_type]) - set(relations_wanted[rel_type])
            mutated['added'][rel_type] = set(relations_wanted[rel_type]) - set(rels[rel_type]) 
        rels[rel_type] = relations_wanted[rel_type]
    if not mutated:
        return {}

    if 'RELATED-TO' in iobj:
        iobj.pop('RELATED-TO')

    for rel_type in rels:
        for uid in rels[rel_type]:
            iobj.add('RELATED-TO', uid, parameters={'RELTYPE': rel_type})

    return mutated

def _remove_reverse_relations(obj, removed_rels):
    """
    obj is an object that may have "lost" some relations,
    removed_rels is the relation-dict of "lost" relations,
    and this function will ensure the objects does not link back here.
    """
    for reltype in removed_rels:
        for uid in removed_rels[reltype]:
            rev_obj = obj.parent.object_by_uid(uid)
            rels = rev_obj.get_relatives(fetch_objects=False)
            backreltypes = rels.keys()
            ## TODO: should only consider the reverse relationship - check reltype attribute
            for backreltype in backreltypes:
                rels[backreltype] = rels[backreltype] - {str(obj.icalendar_component['UID'])}
            _adjust_ical_relations(rev_obj, rels)
            rev_obj.save()

## TODO: consolidate with similar code in the caldav library
def _adjust_relations(parent, children):
    """
    * Only classic parent/child-relations covered so far
    * Only one-parent-per-child covered so far
    * All relations should be bidirectional
    * siblings are not supported
    """
    if not parent:
        for child in children:
            old_parents = child.get_relatives('PARENT', fetch_objects=False)
            if len(old_parents['PARENT']) == 1:
                _remove_reverse_relations(child, old_parents)
                _adjust_ical_relations(child, {'PARENT': set()})
                child.save()
        return
    pmutated = _adjust_ical_relations(parent, {'CHILD': {str(x.icalendar_component['UID']) for x in children}})
    for child in children:
        cmutated = _adjust_ical_relations(child, {'PARENT': {str(parent.icalendar_component['UID'])}})
        if cmutated:
            _remove_reverse_relations(child, cmutated['removed'])
            child.save()
    if pmutated:
        parent.save()
        _remove_reverse_relations(parent, pmutated['removed'])

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
                other.save()
            else:
                if back_rel_types != { backreltypes[reltype] }:
                    import pdb; pdb.set_trace()
                    ## Inconsistency has to be manually fixed: object and other points to each other, but reltype does not match
                    1
    return ret

def _relationship_text(obj, reltype_wanted=None):
    rels = obj.get_relatives(reltypes=reltype_wanted)
    if not rels:
        return "(None)"
    ret = []
    for reltype in rels:
        objs = []
        for relobj in rels[reltype]:
            objs.append(_summary(relobj))
        ret.append(reltype + "\n" + "\n".join(objs) + "\n")
        return "\n".join(ret)

## TODO - this needs to be better documented.  What's the difference between _process_set_arg and _set_something?  Do they overlap?  Are they intended to be used together?
def _process_set_arg(arg, value, keep_category=False):
    ret = {}
    if arg in attr_time and arg != 'duration':
        ret[arg] = parse_dt(value, for_storage=True)
    elif arg == 'duration':
        ret[arg] = parse_add_dur(dt=None, dur=value)
    elif arg == 'rrule':
        rrule = {}
        for split1 in value.split(';'):
            k,v = split1.split('=')
            rrule[k] = v
        ret[arg] = rrule
    elif arg in ('category', 'categories'):
        if hasattr(value, 'split'):
            value = value.split(',')
        elif len(value) == 1 and arg == 'categories' and ',' in value[0]:
            value = value[0].split(',')
        if not keep_category:
            arg = 'categories'
        ret[arg] = value
    else:
        ret[arg] = value
    return ret

def _set_something(obj, arg, value):
    """
    set_something is used when editing objects.
    The arg and value is already processed through _process_set_arg
    """
    arg = arg.lower()
    comp = obj.icalendar_component
    if arg in ('child', 'parent'):
        for val in value:
            obj.set_relation(reltype=arg, other=val)
    elif arg == 'duration':
        obj.set_duration(duration)
    elif arg in ('due', 'dtend'): ## TODO: dtstart!
        getattr(obj, f"set_{arg}")(value, move_dtstart=True, check_dependent=True)
    elif arg == 'category':
        _add_category(obj, value)
    else:
        if arg in comp:
            comp.pop(arg)
        comp.add(arg, value)


## TODO: should be rewritten a bit, we should have a create_list method that does not call on click.echo directly
## let the caller decide if click is to be used or not.
## Use the yield method to avoid having to generate the full list prior to printing to screen
def _list(objs, ics=False, template="{DTSTART:?{DUE:?(date missing)?}?%F %H:%M:%S %Z}: {SUMMARY:?{DESCRIPTION:?(no summary given)?}?}", top_down=False, bottom_up=False, indent=0, echo=True, uids=None, filter=lambda obj: obj.icalendar_component.get('STATUS', '') not in ('CANCELLED', 'COMPLETED')):
    """
    Actual implementation of list

    TODO: will crash if there are loops in the relationships
    TODO: if there are parent/child-relationships that aren't bidrectionally linked, we may get problems
    """
    if indent>32:
        import pdb; pdb.set_trace()
    if ics:
        if not objs:
            return
        icalendar = objs.pop(0).icalendar_instance
        for obj in objs:
            if not filter(obj):
                continue
            icalendar.subcomponents.extend(obj.icalendar_instance.subcomponents)
        click.echo(icalendar.to_ical())
        return
    if isinstance(template, str):
        template=Template(template)
    output = []
    if uids is None:
        uids = set()

    for obj in objs:
        if isinstance(obj, str):
            output.append(obj)
            continue

        if not filter(obj):
            continue

        uid = obj.icalendar_component['UID']
        if uid in uids and not 'RECURRENCE-ID' in obj.icalendar_component:
            continue
        else:
            uids.add(uid)

        above = []
        below = []
        if top_down or bottom_up:
            relations = _relships_by_type(obj)
            parents = relations['PARENT']
            children = relations['CHILD']
            ## in a top-down view, the (grand)*parent should be shown as a top-level item rather than the object.
            ## in a bottom-up view, the (grand)*child should be shown as a top-level item rather than the object.
            if top_down:
                above = parents
                below = children
            if bottom_up:
                above = children
                below = parents
            if indent:
                above = []
        if not above:
            ## This should be a top-level thing
            output.append(" "*indent + template.format(**obj.icalendar_component))
            ## Recursively add children in an indented way
            output.extend(_list(below, template=template, top_down=top_down, bottom_up=bottom_up, indent=indent+2, echo=False, filter=filter))
            if indent and top_down:
                ## Include all siblings as same-level nodes
                ## Use the top-level uids to avoid infinite recursion
                ## TODO: siblings are probably not being handled correctly here.  Should write test code and investigate.
                output.extend(_list(relations['SIBLING'], template=template, top_down=top_down, bottom_up=bottom_up, indent=indent, echo=False, uids=uids, filter=filter))
        for p in above:
            ## The item should be part of a sublist.  Find and add the top-level item, and the full indented list under there - recursively.
            puid = p.icalendar_component['UID']
            if not puid in uids:
                output.extend(_list([p], template=template, top_down=top_down, bottom_up=bottom_up, indent=indent, echo=False, uids=uids, filter=filter))
    if echo:
        click.echo_via_pager("\n".join(output))
    return output
