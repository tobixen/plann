#!/usr/bin/env python

"""https://github.com/tobixen/plann/ - high-level cli against caldav servers.

Copyright (C) 2013-2022 Tobias Brox and other contributors.

See https://www.gnu.org/licenses/gpl-3.0.en.html for license information.

This is a new cli to be fully released in version 1.0, until then
quite much functionality will only be available through the legacy
calendar-cli.  For discussions on the directions, see
https://github.com/tobixen/calendar-cli/issues/88
"""

## This file should preferably just be a thin interface between public
## python libraries (including the plann library) and the command
## line.

## TODO: there is some logic in this file that isn't strictly tied to the
## cli as such.  It should be moved out and made available through
## `from plann import ...`

from plann.metadata import metadata
__version__ = metadata["version"]

import click
import os
import caldav
#import isodate
import datetime
import logging
import re
import sys
from plann.template import Template
from plann.config import interactive_config, config_section, read_config, expand_config_section
import tempfile
import subprocess
from plann.panic_planning import timeline_suggestion
from plann.lib import _now, _ensure_ts, parse_dt, parse_add_dur, parse_timespec, find_calendars, _summary, _procrastinate, tz, _relships_by_type, _get_summary, _relationship_text, _adjust_relations, parentlike, childlike

list_type = list

## should make some subclasses of click.ParamType:

## class DateOrDateTime - perhaps a subclass of click.DateTime, returns date
## if no time is given (can probably just be subclassed directly from
## click.DateTime?

## class DurationOrDateTime - perhaps a subclass of the above, should attempt
## to use pytimeparse if the given info is not a datetime.

## See https://click.palletsprojects.com/en/8.0.x/api/#click.ParamType and
## /usr/lib/*/site-packages/click/types.py on how to do this.

## TODO: maybe find those attributes through the icalendar library? icalendar.cal.singletons, icalendar.cal.multiple, etc
attr_txt_one = ['location', 'description', 'geo', 'organizer', 'summary', 'class', 'rrule', 'status']
attr_txt_many = ['category', 'comment', 'contact', 'resources', 'parent', 'child']
attr_time = ['dtstamp', 'dtstart', 'due', 'dtend', 'duration']
attr_int = ['priority']

@click.group()
## TODO: interactive config building
## TODO: language
@click.option('--show-native-timezone/--show-local-timezone', help="Show timestamps as they are in the calendar (default is to convert to local timezone)")
@click.option('--implicit-timezone', help="Timestamps entered without timezone is assumed to be in this timezone (default: local/system tz)")
@click.option('--store-timezone', help="Timestamps saved to the calendar should be converted to this timezone (default: same as --implicit-timezone)")
@click.option('-c', '--config-file', default=f"{os.environ.get('HOME')}/.config/calendar.conf")
@click.option('--skip-config/--read-config', help="Skip reading the config file")
@click.option('--config-section', default=["default"], multiple=True)
@click.option('--caldav-url', help="Full URL to the caldav server", metavar='URL')
@click.option('--caldav-username', '--caldav-user', help="Full URL to the caldav server", metavar='URL')
@click.option('--caldav-password', '--caldav-pass', help="Password for the caldav server", metavar='URL')
@click.option('--calendar-url', help="Calendar id, path or URL", metavar='cal', multiple=True)
@click.option('--calendar-name', help="Calendar name", metavar='cal', multiple=True)
@click.option('--raise-errors/--print-errors', help="Raise errors found on calendar discovery")
@click.pass_context
def cli(ctx, **kwargs):
    """
    CalDAV Command Line Interface, in development.

    This command will eventually replace calendar-cli.
    It's not ready for consumption.  Only use if you want to contribute/test.
    """
    ## The cli function will prepare a context object, a dict containing the
    ## caldav_client, principal and calendar
    
    ctx.ensure_object(dict)
    ## TODO: add all relevant connection parameters for the DAVClient as options
    ## TODO: logic to read the config file and edit kwargs from config file
    ## TODO: delayed communication with caldav server (i.e. if --help is given to subcommand)
    ## TODO: catch errors, present nice error messages
    conns = []
    ctx.obj['calendars'] = find_calendars(kwargs, kwargs['raise_errors'])
    for flag in ('show_native_timezone', 'store_timezone', 'implicit_timezone'):
        setattr(tz, flag, kwargs[flag])
    if not kwargs['skip_config']:
        config = read_config(kwargs['config_file'])
        if config:
            for meta_section in kwargs['config_section']:
                for section in expand_config_section(config, meta_section):
                    ctx.obj['calendars'].extend(find_calendars(config_section(config, section), raise_errors=kwargs['raise_errors']))

@cli.command()
@click.pass_context
def list_calendars(ctx):
    """
    Will output all calendars found
    """
    if not ctx.obj['calendars']:
        _abort("No calendars found!")
    else:
        output = "Accessible calendars found:\n"
        calendar_info = [(x.get_display_name(), x.url) for x in ctx.obj['calendars']]
        max_display_name = max([len(x[0]) for x in calendar_info])
        format_str= "%%-%ds %%s" % max_display_name
        click.echo_via_pager(output + "\n".join([format_str % x for x in calendar_info]) + "\n")

def _set_attr_options_(func, verb, desc=""):
    """
    decorator that will add options --set-category, --set-description etc
    """
    if verb:
        if not desc:
            desc = verb
        verb = f"{verb}-"
    else:
        verb = ""
    if verb == 'no-':
        for foo in attr_txt_one + attr_txt_many + attr_time + attr_int:
            func = click.option(f"--{verb}{foo}/--has-{foo}", default=None, help=f"{desc} ical attribute {foo}")(func)
    else:
        if verb == 'set-':
            attr__one = attr_txt_one + attr_time + attr_int
        else:
            attr__one = attr_txt_one
        for foo in attr__one:
            func = click.option(f"--{verb}{foo}", help=f"{desc} ical attribute {foo}")(func)
        for foo in attr_txt_many:
            func = click.option(f"--{verb}{foo}", help=f"{desc} ical attribute {foo}", multiple=True)(func)
    return func

def _abort(message):
    click.echo(message)
    raise click.Abort(message)

def _set_attr_options(verb="", desc=""):
    return lambda func: _set_attr_options_(func, verb, desc)

@cli.group()
@click.option('--interactive/--no-interactive-select', help="interactive filtering")
@click.option('--all/--none', default=None, help='Select all (or none) of the objects.  Overrides all other selection options.')
@click.option('--uid', multiple=True, help='select an object with a given uid (or select more object with given uids).  Overrides all other selection options')
@click.option('--abort-on-missing-uid/--ignore-missing-uid', default=False, help='Abort if (one or more) uids are not found (default: silently ignore missing uids).  Only effective when used with --uid')
@click.option('--todo/--no-todo', default=None, help='select only todos (or no todos)')
@click.option('--event/--no-event', default=None, help='select only events (or no events)')
@click.option('--include-completed/--exclude-completed', default=False, help='select only todos (or no todos)')
@_set_attr_options(desc="select by")
@_set_attr_options('no', desc="select objects without")
@click.option('--start', help='do a time search, with this start timestamp')
@click.option('--begin', 'start', help='alias for start')
@click.option('--from', 'start', help='alias for start')
@click.option('--end', help='do a time search, with this end timestamp (or duration)')
@click.option('--to', 'end', help='alias for end')
@click.option('--until', 'end', help='alias for end')
@click.option('--timespan', help='do a time search for this interval')
@click.option('--sort-key', help='use this attributes for sorting.  Templating can be used.  Prepend with - for reverse sort.  Special: "get_duration()" yields the duration or the distance between dtend and dtstart, or an empty timedelta', default=['{DTSTART:?{DUE:?(0000)?}?%F %H:%M:%S}{PRIORITY:?0?}'],  multiple=True)
@click.option('--skip-parents/--include-parents', help="Skip parents if it's children is selected.  Useful for finding tasks that can be started if parent depends on child", default=False)
@click.option('--skip-children/--include-children', help="Skip children if it's parent is selected.  Useful for getting an overview of the big picture if children are subtasks", default=False)
@click.option('--limit', help='Number of objects to show', type=int)
@click.option('--offset', help='Skip the first objects', type=int)
@click.option('--freebusyhack', help='removes almost everything from the ical and replaces the summary with the provided string.  (this option is to be replaced with something better in a future release)')
@click.option('--pinned-tasks/--no-pinned-tasks', default=None, help='select all/no pinned tasks')
@click.pass_context
def select(*largs, **kwargs):
    """Search command, allows listing, editing, etc

    This command is intended to be used every time one is to
    select/filter/search for one or more events/tasks/journals.  It
    offers a simple templating language built on top of python
    string.format for sorting and listing.  It offers several
    subcommands for doing things on the objects found.

    The command is powerful and complex, but may also be non-trivial
    in usage - hence there are some convenience-commands built for
    allowing the common use-cases to be done in easier ways (like
    agenda and fix-tasks-interactive)
    """
    return _select(*largs, **kwargs)

def _select(ctx, interactive=False, **kwargs):
    """
    wrapper function for __select.  Will honor the --interactive flag.
    """
    __select(ctx, **kwargs)
    if interactive:
        objs = ctx.obj['objs']
        ctx.obj['objs'] = []
        for obj in objs:
            if click.confirm(f"select {_summary(obj)}?"):
                ctx.obj['objs'].append(obj)

def __select(ctx, extend_objects=False, all=None, uid=[], abort_on_missing_uid=None, sort_key=[], skip_parents=None, skip_children=None, limit=None, offset=None, freebusyhack=None, pinned_tasks=None, **kwargs_):
    """
    select/search/filter tasks/events, for listing/editing/deleting, etc
    """
    if extend_objects:
        objs = ctx.obj.get('objs', [])
    else:
        objs = []
    ctx.obj['objs'] = objs

    ## TODO: move all search/filter/select logic to caldav library?
    
    ## handle all/none options
    if all is False: ## means --none.
        return
    if all:
        for c in ctx.obj['calendars']:
            objs.extend(c.objects())
        return

    kwargs = {}
    for kw in kwargs_:
        if kwargs_[kw] is not None and kwargs_[kw] != ():
            kwargs[kw] = kwargs_[kw]

    ## uid(s)
    missing_uids = []
    for uid_ in uid:
        comp_filter=None
        if kwargs_['event']:
            comp_filter='VEVENT'
        if kwargs_['todo']:
            comp_filter='VTODO'
        cnt = 0
        for c in ctx.obj['calendars']:
            try:
                objs.append(c.object_by_uid(uid_, comp_filter=comp_filter))
                cnt += 1
            except caldav.error.NotFoundError:
                pass
        if not cnt:
            missing_uids.append(uid_)
    if abort_on_missing_uid and missing_uids:
        _abort(f"Did not find the following uids in any calendars: {missing_uids}")
    if uid:
        return

    if pinned_tasks:
        kwargs['event'] = True
        kwargs['todo'] = None

    if kwargs_.get('start') or kwargs_.get('end'):
        if kwargs_.get('start'):
            kwargs['start'] = parse_dt(kwargs['start'])
        if kwargs_.get('end') and not isinstance(kwargs_.get('end'), datetime.date):
            rx = re.match(r'\+((\d+(\.\d+)?[smhdwy])+)', kwargs['end'])
            if rx:
                kwargs['end'] = parse_add_dur(kwargs.get('start', datetime.datetime.now()), rx.group(1))
            else:
                kwargs['end'] = parse_dt(kwargs['end'])
    elif kwargs_.get('timespan'):
        kwargs['start'], kwargs['end'] = parse_timespec(kwargs['timespan'])

    for attr in attr_txt_many:
        if len(kwargs_.get(attr, []))>1:
            raise NotImplementedError(f"is it really needed to search for more than one {attr}?")
        elif kwargs_.get(attr):
            kwargs[attr] = kwargs[attr][0]

    ## TODO: special handling of parent and child! (and test for that!)

    if 'start' in kwargs and 'end' in kwargs:
        kwargs['expand'] = True
    for c in ctx.obj['calendars']:
        objs.extend(c.search(**kwargs))

    if skip_children or skip_parents:
        i = 0
        while i < len(objs):
            obj = objs[i]
            if skip_children and obj.get_relatives(parentlike, fetch_objects=False):
                objs.pop(i)
                continue
            if skip_parents and obj.get_relatives(childlike, fetch_objects=False):
                objs.pop(i)
                continue
            i += 1

    if pinned_tasks is not None:
        ret_objs = []
        for obj in ctx.obj['objs']:
            if isinstance(obj, caldav.Event):
                if obj.icalendar_component.get('STATUS', '') != 'CANCELLED':
                    parents = _relships_by_type(obj, 'PARENT').get('PARENT',[])
                    if any(x for x in parents if isinstance(x, caldav.Todo) and x.icalendar_component.get('STATUS', 'NEEDS-ACTION') == 'NEEDS-ACTION') == pinned_tasks:
                        if kwargs_.get('todo'):
                            ## TODO: special handling for recurring tasks
                            ret_objs.extend([x for x in parents if isinstance(x, caldav.Todo)  and x.icalendar_component.get('STATUS', 'NEEDS-ACTION') == 'NEEDS-ACTION'])
                        else:
                            ret_objs.append(obj)
            if isinstance(obj, caldav.Todo) and not pinned_tasks:
                children = _relships_by_type(obj, 'CHILD').get('CHILD',[])
                if not any(x.icalendar_comp.get('STATUS', '')!='CANCELLED' for x in parents if isinstance(x, event.Event)):
                    ret_objs.append(obj)
        ctx.obj['objs'] = ret_objs

    ## OPTIMIZE TODO: sorting the list multiple times rather than once is a bit of brute force, if there are several sort keys and long list of objects, we should sort once and consider all sort keys while sorting
    ## TODO: Consider that an object may be expanded and contain lots of event instances.  We will then need to expand the caldav.Event object into multiple objects, each containing one recurrance instance.  This should probably be done on the caldav side of things.
    for skey in reversed(sort_key):
        ## If the key starts with -, sorting should be reversed
        if skey[0] == '-':
            reverse = True
            skey=skey[1:]
        else:
            reverse = False
        ## if the key contains {}, it should be considered to be a template
        if '{' in skey:
            fkey = lambda obj: Template(skey).format(**obj.icalendar_component)
        elif skey == 'get_duration()':
            fkey = lambda obj: obj.get_duration()
        else:
            fkey = lambda obj: obj.icalendar_component.get(skey)
        ctx.obj['objs'].sort(key=fkey, reverse=reverse)

    ## OPTIMIZE TODO: this is also suboptimal, if ctx.obj is a very long list
    if offset is not None:
        ctx.obj['objs'] = ctx.obj['objs'][offset:]
    if limit is not None:
        ctx.obj['objs'] = ctx.obj['objs'][0:limit]

    ## some sanity checks
    for obj in ctx.obj['objs']:
        comp = obj.icalendar_component
        dtstart = comp.get('dtstart')
        dtend = comp.get('dtend') or comp.get('due')
        if dtstart and dtend and dtstart.dt > dtend.dt:
            logging.error(f"task with uuid {comp['uid']} as dtstart after dtend/due")

    ## I need a way to copy time information from one calendar to another
    ## (typically between private and work calendars) without carrying over
    ## (too much potentially) private/confidential information.
    if freebusyhack:
        for obj in ctx.obj['objs']:
            comp = obj.icalendar_component
            attribs = list_type(comp.keys())
            for attr in attribs:
                if not attr in ('DUE', 'DTEND', 'DTSTART', 'DTSTAMP', 'UID', 'RRULE', 'SEQUENCE', 'EXDATE', 'STATUS', 'CLASS'):
                    del comp[attr]
                if attr == 'SUMMARY':
                    comp[attr] = freebusyhack

@select.command()
@click.pass_context
def list_categories(ctx):
    """
    List all categories used in the selection
    """
    cats = _cats(ctx)
    for c in cats:
        click.echo(c)

def _cats(ctx):
    categories = set()
    for obj in ctx.obj['objs']:
        cats = obj.icalendar_component.get('categories')
        if cats:
            categories.update(cats.cats)
    return categories

list_type = list

@select.command()
@click.option('--ics/--no-ics', default=False, help="Output in ics format")
@click.option('--template', default="{DTSTART:?{DUE:?(date missing)?}?%F %H:%M:%S %Z}: {SUMMARY:?{DESCRIPTION:?(no summary given)?}?}")
@click.option('--top-down/--flat-list', help="Check relations and list the relations in a hierarchical way")
@click.option('--bottom-up/--flat-list', help="List parents (dependencies) in a hierarchical way (cannot be combined with top-down)")
@click.pass_context
def list(ctx, ics, template, top_down=False, bottom_up=False):
    """
    Print out a list of tasks/events/journals
    """
    return _list(ctx.obj['objs'], ics, template, top_down=top_down, bottom_up=bottom_up)

def _list(objs, ics=False, template="{DTSTART:?{DUE:?(date missing)?}?%F %H:%M:%S %Z}: {SUMMARY:?{DESCRIPTION:?(no summary given)?}?}", top_down=False, bottom_up=False, indent=0, echo=True, uids=None):
    """
    Actual implementation of list

    TODO: will crash if there are loops in the relationships
    TODO: if there are parent/child-relationships that aren't bidrectionally linked, we may get problems
    """
    if indent>8:
        import pdb; pdb.set_trace()
    if ics:
        if not objs:
            return
        icalendar = objs.pop(0).icalendar_instance
        for obj in objs:
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
            output.extend(_list(below, template=template, top_down=top_down, bottom_up=bottom_up, indent=indent+2, echo=False))
            if indent and top_down:
                ## Include all siblings as same-level nodes
                ## Use the top-level uids to avoid infinite recursion
                ## TODO: siblings are probably not being handled correctly here.  Should write test code and investigate.
                output.extend(_list(relations['SIBLING'], template=template, top_down=top_down, bottom_up=bottom_up, indent=indent, echo=False, uids=uids))
        for p in above:
            ## The item should be part of a sublist.  Find and add the top-level item, and the full indented list under there - recursively.
            puid = p.icalendar_component['UID']
            if not puid in uids:
                output.extend(_list([p], template=template, top_down=top_down, bottom_up=bottom_up, indent=indent, echo=False, uids=uids))
    if echo:
        click.echo_via_pager("\n".join(output))
    return output

@select.command()
@click.pass_context
def print_uid(ctx):
    """
    Convenience command, prints UID of first item

    This can also be achieved by using select with template and limit
    """
    click.echo(ctx.obj['objs'][0].icalendar_component['UID'])

@select.command()
@click.pass_context
def print_ical(ctx):
    """
    Dumps everything selected as an ICS feed
    """
    for obj in ctx.obj['objs']:
        click.echo(obj.data)

@select.command()
@click.option('--multi-delete/--no-multi-delete', default=None, help="Delete multiple things without confirmation prompt")
@click.pass_context
def delete(ctx, multi_delete, **kwargs):
    """
    Delete the selected item(s)
    """
    objs = ctx.obj['objs']
    if multi_delete is None and len(objs)>1:
        multi_delete = click.confirm(f"OK to delete {len(objs)} items?")
    if len(objs)>1 and not multi_delete:
        _abort(f"Not going to delete {len(objs)} items")
    for obj in objs:
        obj.delete()

@select.command()
@click.option('--pdb/--no-pdb', default=None, help="Interactive edit through pdb (experts only)")
@click.option('--add-category', default=None, help="Delete multiple things without confirmation prompt", multiple=True)
@click.option('--postpone', help="Add something to the DTSTART and DTEND/DUE")
@click.option('--interactive-ical/--no-interactive-ical', help="Edit the ical interactively")
@click.option('--interactive-relations/--no-interactive-relations', help="Edit the relationships")
@click.option('--interactive/--no-interactive', help="Interactive edit")
@click.option('--cancel/--uncancel', default=None, help="Mark task(s) as cancelled")
@click.option('--complete/--uncomplete', default=None, help="Mark task(s) as completed")
@click.option('--complete-recurrence-mode', default='safe', help="Completion of recurrent tasks, mode to use - can be 'safe', 'thisandfuture' or '' (see caldav library for details)")
@_set_attr_options(verb='set')
@click.pass_context
def edit(*largs, **kwargs):
    """
    Edits a task/event/journal
    """
    return _edit(*largs, **kwargs)

def _interactive_edit(obj):
    if 'BEGIN:VEVENT' in obj.data:
        objtype = 'event'
    elif 'BEGIN:VTODO' in obj.data:
        objtype = 'todo'
    elif 'BEGIN:VJOURNAL' in obj.data:
        objtype = 'journal'
    else:
        assert False
    if objtype != 'todo':
        raise NotImplementedError("interactive editing only implemented for tasks")
    comp = obj.icalendar_component
    summary = _summary(comp)
    dtstart = comp.get('DTSTART')
    pri = comp.get('PRIORITY', 0)
    due = obj.get_due()
    if not dtstart or not due:
        click.echo(f"task without dtstart or due found, please run set-task-attribs subcommand.  Ignoring {summary}")
        return
    dtstart = _ensure_ts(dtstart)
    click.echo(f"pri={pri} {dtstart:%F %H:%M:%S %Z} - {due:%F %H:%M:%S %Z}: {summary}")
    input = click.prompt("postpone <n>d / ignore / part(ially-complete) / complete / split / cancel / set foo=bar / edit / family / pdb?", default='ignore')
    if input == 'ignore':
        return
    elif input == 'part':
        interactive_split_task(obj, partially_complete=True, too_big=False)
    elif input == 'split':
        interactive_split_task(obj, too_big=False)
    elif input.startswith('postpone'):
        ## TODO: make this into an interactive recursive function
        parent = _procrastinate([obj], input.split(' ')[1], with_children='interactive', with_parent='interactive', with_family='interactive', check_dependent="interactive", err_callback=click.echo, confirm_callback=click.confirm)
    elif input == 'complete':
        obj.complete(handle_rrule=True)
    elif input == 'cancel':
        comp['STATUS'] = 'CANCELLED'
    elif input.startswith('set '):
        input = input[4:].split('=')
        assert len(input) == 2
        _set_something(obj, input[0], input[1])
    elif input == 'edit':
        _interactive_ical_edit([obj])
    elif input == 'family':
        _interactive_relation_edit([obj])
    elif input == 'pdb':
        click.echo("icalendar component available as comp")
        click.echo("caldav object available as obj")
        click.echo("do the necessary changes and press c to continue normal code execution")
        click.echo("happy hacking")
        import pdb; pdb.set_trace()
    else:
        click.echo(f"unknown instruction '{input}' - ignoring")
        return
    obj.save()


def _set_something(obj, arg, value):
    comp = obj.icalendar_component
    if arg in ('child', 'parent'):
        for val in value:
            obj.set_relation(reltype=arg, other=val)
    elif arg == 'duration':
        duration = parse_add_dur(dt=None, dur=value)
        obj.set_duration(duration)
    else:
        if arg in comp:
            comp.pop(arg)
        comp.add(arg, value)

def _editor(sometext):
    with tempfile.NamedTemporaryFile(mode='w', encoding='UTF-8', delete=False) as tmpfile:
        tmpfile.write(sometext)
        fn = tmpfile.name
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or ""
    if not '/' in editor:
        for path in os.environ.get("PATH", "").split(os.pathsep):
            full_path = os.path.join(path, editor)
            if os.path.exists(full_path) and os.access(full_path, os.X_OK):
                editor = full_path
                break
    for ed in (editor, '/usr/bin/vim', '/usr/bin/vi', '/usr/bin/emacs', '/usr/bin/nano', '/usr/bin/pico', '/bin/vi'):
        if os.path.isfile(ed) and os.access(ed, os.X_OK):
            break
    foo = subprocess.run([ed, fn])
    with open(fn, "r") as tmpfile:
        ret = tmpfile.read()
    os.unlink(fn)
    return ret

def _interactive_ical_edit(objs):
    ical = "\n".join([x.data for x in objs])
    data = _editor(ical)
    data = data.strip()
    icals = _split_vcal(data)
    assert len(icals) == len(objs)
    for new,obj in zip(icals, objs):
        ## Should probably assert that the UID is the same ...
        ## ... or, leave it to the calendar server to handle changed UIDs
        obj.data = new
        obj.save()

def _interactive_relation_edit(objs):
    if not objs:
        return
    indented_family = "\n".join(_list(
        objs, top_down=True, echo=False,
        template="{UID}: {SUMMARY:?{DESCRIPTION:?(no summary given)?}?} (STATUS={STATUS:-})"))
    edited = _editor(indented_family)
    _set_relations_from_text_list(objs[0].parent, edited.split("\n"))

def _set_relations_from_text_list(calendar, some_list, parent=None, indent=0):
    """
    Takes a list of indented strings identifying some relationships,
    ensures parent and child is

    Caveats:
    * Currently it does not support RFC 9253 and enforces RELTYPE to be PARENT or CHILD
    * Currently it also lacks Support for multiple parents
    * Relation type SIBLING is ignored
    """
    ## Logic:
    ## * If a parent is not set and indent is 0, make sure the item has either no parents or multiple parents
    ## * For all following lines where the indent is higher than the expected indent, recurse over the lines that are indented
    ## * If a parent is set, collect all children (all lines with expected indent), then make sure all children has parent correctly set, and make sure the parent has those and no more children.
    ## * Return a list of changes done.

    ## Internal methods
    def count_indent(line):
        """count the left hand spaces on a line"""
        j = 0
        while j<len(line):
            if line[j] == '\t':
                j+=8
            elif line[j] == ' ':
                j+=1
            else:
                return j
        return None
    
    def get_obj(line):
        """Check the uuid on the line and return the caldav object"""
        uid = line.lstrip().split(':')[0]
        if not uid:
            raise NotImplementedError("No uid - what now?")
        return calendar.object_by_uid(uid)
    
    i=0
    if parent:
        children = []
    while i<len(some_list):
        line = some_list[i]
        line_indent = count_indent(line)

        ## empty line
        if line_indent is None:
            i += 1
            continue

        ## unexpected - indentation going backwards
        if line_indent < indent:
            raise NotImplementedError("unexpected indentation 0")

        ## indentation going forward - recurse over the indented section
        #if line_indent > indent or (line_indent == indent and i>0): # TODO: think this more through?  The last is supposed to rip existing children from lines without a following indented sublist
        if line_indent > indent:
            if not i:
                raise NotImplementedError("unexpected indentation 1")
            j=i
            while j<len(some_list):
                new_indent = count_indent(some_list[j])
                if new_indent is None or new_indent==indent:
                    break
                if new_indent < line_indent and new_indent != indent:
                    raise NotImplementedError("unexpected indentation 2")
                j+=1
            _set_relations_from_text_list(calendar, some_list[i:j], parent=get_obj(some_list[i-1]), indent=line_indent)
            i=j
            continue

        ## Unindented line without a parent.
        if line_indent == indent and not parent:
            ## Noop as for now but ... TODO ... shouldn't be
            ## TODO: if no indented list follows, then remove all children.
            ## TODO: if the object has a parent, remove it
            i+=1
            continue

        ## Unindented line with a parent.  Should be a direct child under parent
        if line_indent == indent and parent:
            children.append(get_obj(some_list[i]))
            i+=1
            continue
        
        ## TODO: look through all the conditions above.  should we ever be here?
        import pdb; pdb.set_trace()
    if parent:
        pmutated = _adjust_relations(parent, {'CHILD': {str(x.icalendar_component['UID']) for x in children}})
        for child in children:
            cmutated = _adjust_relations(child, {'PARENT': {str(parent.icalendar_component['UID'])}})
            if cmutated:
                child.save()
        if pmutated:
            parent.save()

def _edit(ctx, add_category=None, cancel=None, interactive_ical=False, interactive_relations=False, interactive=False, complete=None, complete_recurrence_mode='safe', postpone=None, **kwargs):
    """
    Edits a task/event/journal
    """
    if 'recurrence_mode' in kwargs:
        complete_recurrence_mode = kwargs.pop('recurrence_mode')
    _process_set_args(ctx, kwargs)
    if interactive_ical:
        _interactive_ical_edit(ctx.obj['objs'])
    if interactive_relations:
        _interactive_relation_edit(ctx.obj['objs'])

    for obj in ctx.obj['objs']:
        if interactive:
            _interactive_edit(obj)
        comp = obj.icalendar_component
        if kwargs.get('pdb'):
            click.echo("icalendar component available as comp")
            click.echo("caldav object available as obj")
            click.echo("do the necessary changes and press c to continue normal code execution")
            click.echo("happy hacking")
            import pdb; pdb.set_trace()
        for arg in ctx.obj['set_args']:
            _set_something(obj, arg, ctx.obj['set_args'][arg])
        if add_category:
            if 'categories' in comp:
                cats = comp.pop('categories').cats
            else:
                cats = []
            cats.extend(add_category)
            comp.add('categories', cats)
        if complete:
            obj.complete(handle_rrule=complete_recurrence_mode, rrule_mode=complete_recurrence_mode)
        elif complete is False:
            obj.uncomplete()
        if cancel:
            comp.status='CANCELLED'
        elif cancel is False:
            comp.status='NEEDS-ACTION'
        if postpone:
            for attrib in ('DTSTART', 'DTEND', 'DUE'):
                if comp.get(attrib):
                    comp[attrib].dt = parse_add_dur(comp[attrib].dt, postpone).astimezone(tz.store_timezone)
        obj.save()


@select.command()
@click.pass_context
@click.option('--recurrence-mode', default='safe', help="Completion of recurrent tasks, mode to use - can be 'safe', 'thisandfuture' or '' (see caldav library for details)")
def complete(ctx, **kwargs):
    """
    Convenience command, mark tasks as completed

    The same result can be obtained by running this subcommand:

      `edit --complete`
    """
    return _edit(ctx, complete=True, **kwargs)

@select.command()
@click.option('--hours-per-day', help='how many hours per day you expect to be able to dedicate to those tasks/events', default=4)
#@click.option('--limit', help='break after finding this many "panic"-items', default=4096)
@click.option('--timeline-start', help='Timeline starting point (default=now)')
@click.option('--timeline-end', help='Timeline ending point (default=in 1 year)')
@click.option('--include-all-events/--no-extra-events', help='Include all events (and selected tasks)')
@click.option('--print-timeline/--no-print-timeline', help='Print a possible timeline')
@click.option('--fix-timeline/--no-fix-timeline', help='Make events from the tasks and pin them to the calendar')
@click.pass_context
def check_for_panic(ctx, **kwargs):
    """Check if we need to panic

    Assuming we can spend a limited time per day on those tasks
    (because one also needs to sleep and do other things that are not
    included in the calendar, or maybe some tasks can only be done
    while the sun is shining), all tasks/events are processed in order
    (assumed to be ordered by DTSTART).  The algorithm is supposed to
    find if there are tasks that cannot be accomplished before the
    DUE.  In that case, one should either PANIC or move the DUE.

    Eventually it will report the total amount of slack found (time we
    can slack off and still catch all the deadlines) as well as the
    minimum slack (how long one may snooze before starting working on
    those tasks).

    TODO: Only tasks supported so far.  It should also warn on
    overlapping events and substract time spent on events.
    """
    for x in list_type(kwargs.keys()):
        if kwargs[x] is None:
            del kwargs[x]
    return _check_for_panic(ctx, **kwargs)

def _check_for_panic(ctx, hours_per_day, output=True, print_timeline=True, fix_timeline=False, timeline_start=None, timeline_end=None, include_all_events=False):
    if not timeline_start:
        timeline_start = _now()
    else:
        timeline_start = parse_dt(timeline_start, datetime.datetime)
    if not timeline_end:
        timeline_end = parse_add_dur(timeline_start, '+1y')
    timeline_end = parse_dt(timeline_end, datetime.datetime)
    if include_all_events:
        ctx.obj['objs'] = [x for x in ctx.obj['objs'] if not 'BEGIN:VEVENT' in x.data]
        _select(ctx, event=True, start=timeline_start, end=timeline_end, extend_objects=True)
    possible_timeline = timeline_suggestion(ctx, hours_per_day=hours_per_day, timeline_end=timeline_end)
    def summary(obj):
        if obj is None:
            return "-- unallocated time --"
        if isinstance(obj, str):
            return obj
        return _summary(obj)
        
    if (print_timeline):
        click.echo("Calculated timeline suggestion:")
        for foo in possible_timeline:
            if 'begin' in foo:
                click.echo(f"{foo['begin']:%FT%H:%M %Z} {summary(foo.get('obj'))}")

    if output:
        click.echo()
        click.echo("THESE TASKS WILL NEED TO BE PROCRASTINATED:")
        for foo in possible_timeline:
            if 'begin' in foo and 'obj' in foo and not isinstance(foo['obj'], str):
                if _ensure_ts(foo['begin'])<timeline_start:
                    click.echo(f"{foo['obj'].get_due():%FT%H%M %Z} {foo['obj'].icalendar_component.get('PRIORITY', 0)} {_summary(foo['obj'])}")

    if fix_timeline:
        for i in range(len(possible_timeline)-1):
            foo = possible_timeline[i]
            next = possible_timeline[i+1]
            if 'begin' in foo and 'obj' in foo and not isinstance(foo['obj'], str):
                if _ensure_ts(foo['begin'])>timeline_start:
                    obj = foo['obj']
                    if isinstance(obj, caldav.Todo):
                        comp = obj.icalendar_component
                        ## TODO: copy other attributes?
                        _add_event(ctx, summary=_summary(obj), timespec=(foo['begin'], next['begin']), set_status='TENTATIVE', first_calendar=True, set_parent=[comp['UID']])
    return possible_timeline

@select.command()
@click.pass_context
def sum_hours(ctx, **kwargs):
    raise NotImplementedError()

## TODO: all combinations of --first-calendar, --no-first-calendar, --multi-add, --no-multi-add should be tested
@cli.group()
@click.option('-l', '--add-ical-line', multiple=True, help="extra ical data to be injected")
@click.option('--multi-add/--no-multi-add', default=None, help="Add things to multiple calendars")
@click.option('--first-calendar/--no-first-calendar', default=None, help="Add things only to the first calendar found")
@click.pass_context
def add(ctx, **kwargs):
    """
    Save new objects on calendar(s)
    """
    if len(ctx.obj['calendars'])>1 and kwargs['multi_add'] is False:
        _abort("Giving up: Multiple calendars given, but --no-multi-add is given")
    ## TODO: crazy-long if-conditions can be refactored - see delete on how it's done there
    if (kwargs['first_calendar'] or
        (len(ctx.obj['calendars'])>1 and
         not kwargs['multi_add'] and
         not click.confirm(f"Multiple calendars given.  Do you want to duplicate to {len(ctx.obj['calendars'])} calendars? (tip: use option --multi-add or --first-calendar to avoid this prompt in the future)"))):
        calendar = ctx.obj['calendars'][0]
        ## TODO: we need to make sure f"{calendar.name}" will always work or something
        if (kwargs['first_calendar'] is not False and
            (kwargs['first_calendar'] or
            click.confirm(f"First calendar on the list has url {calendar.url} - should we add there? (tip: use --calendar-url={calendar.url} or --first-calendar to avoid this prompt in the future)"))):
            ctx.obj['calendars'] = [ calendar ]
        else:
            _abort("Giving up: Multiple calendars found/given, please specify which calendar you want to use")

    if not ctx.obj['calendars']:
        _abort("Giving up: No calendars given")

    ctx.obj['ical_fragment'] = "\n".join(kwargs['add_ical_line'])

def _split_vcal(ical):
    ical = ical.strip()
    icals = []
    while ical.startswith("BEGIN:VCALENDAR\n"):
        pos = ical.find("\nEND:VCALENDAR") + 14
        icals.append(ical[:pos])
        ical = ical[pos:].lstrip()
    return icals

@add.command()
@click.pass_context
@click.option('-d', '--ical-data', '--ical', help="ical object to be added")
@click.option('-f', '--ical-file', type=click.File('rb'), help="file containing ical data")
def ical(ctx, ical_data, ical_file):
    ical = ""
    if (ical_file):
        ical = ical + ical_file.read().decode()
    if (ical_data):
        ical = ical + ical_data
    if not ical:
        ical = sys.stdin.read()
    if ctx.obj['ical_fragment']:
        ical = ical.replace('\nEND:', f"{ctx.obj['ical_fragment']}\nEND:")
    if 'BEGIN:VCALENDAR' in ical:
        icals = _split_vcal(ical)
    else:
        icals = [ ical ]
    for ical in icals:
        for c in ctx.obj['calendars']:
            ## TODO: this may not be an event - should make a Calendar.save_object method
            c.save_event(ical)

def _process_set_args(ctx, kwargs):
    ctx.obj['set_args'] = {}
    for x in kwargs:
        if kwargs[x] is None or kwargs[x]==():
            continue
        if x == 'set_rrule':
            rrule = {}
            for split1 in kwargs[x].split(';'):
                k,v = split1.split('=')
                rrule[k] = v
            ctx.obj['set_args']['rrule'] = rrule
        elif x == 'set_category':
            ctx.obj['set_args']['categories'] = kwargs[x]
        elif x.startswith('set_'):
            ctx.obj['set_args'][x[4:]] = kwargs[x]
    for arg in ctx.obj['set_args']:
        if arg in attr_time and arg != 'duration':
            ctx.obj['set_args'][arg] = parse_dt(ctx.obj['set_args'][arg])

    if 'summary' in kwargs:
        ctx.obj['set_args']['summary'] = ctx.obj['set_args'].get('summary', '') + kwargs['summary']
    if 'ical_fragment' in kwargs:
        ctx.obj['set_args']['ics'] = kwargs['ical_fragment']

@add.command()
@click.argument('summary', nargs=-1)
@_set_attr_options(verb='set')
@click.pass_context
def todo(ctx, **kwargs):
    return _add_todo(ctx, **kwargs)

def _add_todo(ctx, **kwargs):
    """
    Creates a new task with given SUMMARY

    Examples: 

    kal add todo "fix all known bugs in plann"
    kal add todo --set-due=2050-12-10 "release plann version 42.0.0"
    """
    if not 'status' in kwargs:
        kwargs['status'] = 'NEEDS-ACTION'
    kwargs['summary'] = " ".join(kwargs['summary'])
    _process_set_args(ctx, kwargs)
    if not ctx.obj['set_args']['summary']:
        _abort("denying to add a TODO with no summary given")
        return
    for cal in ctx.obj['calendars']:
        todo = cal.save_todo(ical=ctx.obj.get('ical_fragment', ""), **ctx.obj['set_args'], no_overwrite=True)
        click.echo(f"uid={todo.id}")
    return todo

@add.command()
## TODO
@click.argument('summary')
@click.argument('timespec')
@_set_attr_options(verb='set')
@click.pass_context
def event(ctx, timespec, **kwargs):
    """
    Creates a new event with given SUMMARY at the time specifed through TIMESPEC.

    TIMESPEC is an ISO-formatted date or timestamp, optionally with a postfixed interval
.
    Examples:

    kal add event "final bughunting session" 2004-11-25+5d
    kal add event "release party" 2004-11-30T19:00+2h
    """
    _add_event(ctx, timespec, **kwargs)

def _add_event(ctx, timespec, **kwargs):
    _process_set_args(ctx, kwargs)
    for cal in ctx.obj['calendars']:
        (dtstart, dtend) = parse_timespec(timespec)
        event = cal.save_event(dtstart=dtstart, dtend=dtend, **ctx.obj['set_args'], no_overwrite=True)
        click.echo(f"uid={event.id}")

def journal():
    click.echo("soon you should be able to add journal entries to your calendar")
    raise NotImplementedError("foo")

## CONVENIENCE COMMANDS

@cli.command()
@click.pass_context
def agenda(ctx):
    """
    Convenience command, prints an agenda

    This command is slightly redundant, same results may be obtained by running those two commands in series:
    
      `select --event --start=now --end=+7d --limit=16 list`
    
      `select --todo --sort '{DTSTART:?{DUE:?(0000)?}?%F %H:%M:%S}' --sort '{PRIORITY:?0}' --end=+7d --limit=16 list --bottom-up`

    agenda is for convenience only and takes no options or parameters.
    Use the select command for advanced usage.  See also USAGE.md.
    """
    return _agenda(ctx)

def _agenda(ctx):
    start = datetime.datetime.now()
    _select(ctx=ctx, start=start, event=True, end='+7d', limit=16, sort_key=['{DTSTART:%F %H:%M:%S}', 'get_duration()'])
    objs = ctx.obj['objs']
    _select(ctx=ctx, todo=True, end='+7d', limit=16, sort_key=['{DTSTART:?{DUE:?(0000)?}?%F %H:%M:%S}', '{PRIORITY:?0?}'], skip_parents=True)
    ctx.obj['objs'] = objs + ["======"] + ctx.obj['objs']
    return _list(ctx.obj['objs'])

@cli.group()
@click.pass_context
def interactive(ctx):
    """Interactive convenience commands

    Various workflow procedures that will prompt the user for input.

    Disclaimer: This is quite experimental stuff.  The maintainer is
    experimenting with his own task list and testing out daily
    procedures, hence it's also quite optimized towards whatever
    work-flows that seems to work out for the maintainer of the
    plann.  Things are changed rapidly without warnings and the
    interactive stuff is not covered by any test code whatsoever.
    """


@interactive.command()
@click.pass_context
def manage_tasks(ctx):
    """
    This goes through the daily task management procedures:
    * set-task-attribs
    * agenda
    * check-due
    * split-huge-tasks
    * split-high-pri-tasks
    * dismiss-panic
    """
    ## TODO: pinned tasks for the previous week.
    ## * Go through the events ... for each of them, ask if it was done or not
    ## * If the event was done, mark the task as completed
    ## * If the event wasn't done, mark the event as cancelled
    click.echo("Checking if there are any huge tasks that may need to be split")
    _split_huge_tasks(ctx)
    click.echo("Checking if there are any high-priority tasks ... it's adviceable to split them up into subtasks with a shorter due-date")
    _split_high_pri_tasks(ctx)
    click.echo("Checking if there is any missing metadata on your tasks ...")
    _set_task_attribs(ctx)
    click.echo("Here is your upcoming agenda, have a quick look through it")
    _agenda(ctx)
    click.echo("Checking if we should go in 'panic mode', perhaps it's needed to procrastinate some lower-priority tasks")
    _dismiss_panic(ctx, hours_per_day=24)
    click.echo("Going through your near-due tasks")
    _check_due(ctx)
    click.echo("New panic check.  (Eventually, press ctrl-c and start working on the tasks rather than obsessing over them ...)")
    _dismiss_panic(ctx, hours_per_day=8)

@interactive.command()
@click.option('--limit', help='If more than limit overdue tasks are found, probably we should do a mass procrastination rather than going through one and one task')
@click.option('--lookahead', help='Look-ahead time - check tasks that needs to be completed in the near future', default='+16h')
@click.pass_context
def check_due(ctx, limit, lookahead):
    """
    Go through overdue or near-future-due tasks, one by one, and deal with them
    """
    return _check_due(ctx, limit, lookahead)

def _check_due(ctx, limit=16, lookahead='16h'):
    end_ = parse_add_dur(datetime.datetime.now(), lookahead)
    _select(ctx=ctx, todo=True, end=end_, limit=limit, sort_key=['{PRIORITY:?0?} {DTSTART:?{DUE:?(0000)?}?%F %H:%M:%S}'])
    objs = ctx.obj['objs']
    for obj in objs:
        ## client side filtering in case the server returns too much
        ## TODO: should be moved to the caldav library
        ## TODO: consider the limit ... we may risk that nothing comes up due to the limit above
        comp = obj.icalendar_component
        dtstart = comp.get('dtstart') or comp.get('due')
        dtstart = _ensure_ts(dtstart)
        if dtstart.strftime("%F%H%M") > end_.strftime("%F%H%M"):
            continue
        _interactive_edit(obj)

@interactive.command()
@click.option('--hours-per-day', help='how many hours per day you expect to be able to dedicate to those tasks/events', default=4)
@click.option('--lookahead', help='timespan to investigate', default='60d')
@click.pass_context
def dismiss_panic(ctx, hours_per_day, lookahead='60d'):
    """Checks workload, procrastinates tasks

    Search for panic points, checks if they can be solved by
    procrastinating tasks, comes up with suggestions
    """
    return _dismiss_panic(ctx, hours_per_day, f"+{lookahead}")

def _dismiss_panic(ctx, hours_per_day, lookahead='60d'):
    ## TODO: fetch both events and tasks
    lookahead=f"+{lookahead}"
    _select(ctx=ctx, todo=True, end=lookahead)
    timeline = _check_for_panic(ctx=ctx, output=False, hours_per_day=hours_per_day, timeline_end=lookahead, include_all_events=True)

    if not timeline or _ensure_ts(timeline[0]['begin'])>_now():
        click.echo("No need to panic :-)")
        return

    for priority in range(9,0,-1):
        first_low_pri_tasks = []
        other_low_pri_tasks = []
        lpt = first_low_pri_tasks
        for item in timeline:
            if isinstance(item.get('obj', ''), str):
                continue
            if _ensure_ts(item['begin'])>_now():
                if not lpt:
                    break
                lpt = other_low_pri_tasks
            if item['obj'].icalendar_component.get('priority', 0) != priority:
                continue
            lpt.append(item)
        if not first_low_pri_tasks:
            continue

        click.echo(f"Tasks that needs to be postponed (priority={priority}):")
        for item in first_low_pri_tasks:
            obj = item['obj']
            comp = obj.icalendar_component
            summary = _summary(comp)
            due = obj.get_due()
            dtstart = _ensure_ts(comp.get('dtstart') or comp.get('due'))
            click.echo(f"Should have started: {item['begin']:%F %H:%M:%S %Z} - Due: {due:%F %H:%M:%S %Z}: {summary}")

        if priority == 1:
            _abort("PANIC!  Those are all high-priority tasks and cannot be postponed!")

        if priority == 2:
            _abort("PANIC!  Those tasks cannot be postponed.  Maybe you want to cancel some of them?  (interactive cancelling not supported yet)")

        procrastination_time = (_now()-_ensure_ts(first_low_pri_tasks[0]['begin']))/2
        if procrastination_time.days:
            procrastination_time = f"{procrastination_time.days+1}d"
        else:
            procrastination_time = f"{procrastination_time.seconds//3600+1}h"
        procrastination_time = click.prompt(f"Push the due-date with ... (press O for one-by-one)", default=procrastination_time)
        if procrastination_time == 'O':
            for item in first_low_pri_tasks:
                _interactive_edit(item['obj'])
        else:
            _procrastinate([x['obj'] for x in first_low_pri_tasks], procrastination_time,  check_dependent='interactive', err_callback=click.echo, confirm_callback=click.confirm)

        if other_low_pri_tasks:
            click.echo(f"There are {len(other_low_pri_tasks)} later pri>={priority} tasks selected which should maybe probably be considered to be postponed a bit as well")
            procrastination_time = click.prompt(f"Push the due-date for those with ...", default='0h')
            if procrastination_time not in ('0', '0h', '0m', '0d', 0):
                _procrastinate([x['obj'] for x in other_low_pri_tasks], procrastination_time, check_dependent='interactive', err_callback=click.echo, confirm_callback=click.confirm)

@interactive.command()
@click.pass_context
def update_config(ctx):
    """
    Edit the config file interactively
    """
    raise NotImplementedError()

@interactive.command()
@click.option('--threshold', help='tasks with a higher estimate than this should be split into subtasks', default='4h')
@click.option('--max-lookahead', help='ignore tasks further in the future than this', default='30d')
@click.option('--limit-lookahead', help='only consider the first x tasks', default=32)
@click.pass_context
def split_huge_tasks(ctx, threshold, max_lookahead, limit_lookahead):
    """
    finds tasks in the upcoming future that have a too big estimate and suggests to split it into subtasks
    """
    return _split_huge_tasks(ctx, threshold, max_lookahead, limit_lookahead)

def _split_huge_tasks(ctx, threshold='4h', max_lookahead='60d', limit_lookahead=640):
    _select(ctx=ctx, todo=True, end=f"+{max_lookahead}", limit=limit_lookahead, sort_key=['{DTSTART:?{DUE:?(0000)?}?%F %H:%M:%S}', '{PRIORITY:?0?}'])
    objs = ctx.obj['objs']
    threshold = parse_add_dur(None, threshold)
    for obj in objs:
        if obj.get_duration() > threshold:
            interactive_split_task(obj)

@interactive.command()
@click.option('--max-lookahead', help='ignore tasks further in the future than this', default='30d')
@click.option('--threshold', help='tasks with this or lower priority should always have children', default=2)
@click.option('--limit-lookahead', help='only consider the first x tasks', default=32)
@click.pass_context
def split_high_pri_tasks(ctx, threshold, max_lookahead, limit_lookahead):
    """Tasks with very high priority (1,2) indicates a hard DUE that
    cannot be moved - the actual work should probably be done long
    time before the deadline.  To preserve the deadline, avoid getting
    surprised at the new years eve that there are still high-priority
    tasks that needs to be done this year, and make it possible to
    procrastinate the work itself it's strongly recommended to split
    the high priority tasks - make one or more child tasks for
    actually doing the work, and leave the parent task as a
    placeholder for just storing the hard deadline (rename it to
    something like "verify that the work has been done and/or
    delivered", set the time estimate to some few minutes).
    """
    return _split_high_pri_tasks(ctx, threshold, max_lookahead, limit_lookahead)

def _split_high_pri_tasks(ctx, threshold=2, max_lookahead='60d', limit_lookahead=640):
    _select(ctx=ctx, todo=True, end=f"+{max_lookahead}", limit=limit_lookahead, sort_key=['{DTSTART:?{DUE:?(0000)?}?%F %H:%M:%S}', '{PRIORITY:?0?}'])
    objs = ctx.obj['objs']
    for obj in objs:
        if obj.icalendar_component.get('PRIORITY') and obj.icalendar_component.get('PRIORITY') <= threshold:
            ## TODO: get_relatives refactoring
            relations = obj.get_relations(fetch_object=False)
            if not 'CHILD' in relations:
                interactive_split_task(obj, too_big=False)

def interactive_split_task(obj, partially_complete=False, too_big=True):
    comp = obj.icalendar_component
    summary = comp.get('summary') or comp.get('description') or comp.get('uid')
    estimate = obj.get_duration()
    tbm = ""
    if too_big:
        tbm = ", which is too big."
    click.echo(f"{summary}: estimate is {estimate}{tbm}")
    click.echo("Relationships:\n")
    click.echo(_relationship_text(obj))
    if partially_complete:
        splitout_msg = "So you've been working on this?"
    else:
        splitout_msg = "Do you want to fork out some subtasks?"
    if click.confirm(splitout_msg):
        cnt = 1
        if partially_complete:
            default = f"Work on {summary}"
        else:
            default = f"Plan how to do {summary}"
        while True:
            summary = click.prompt("Name for the subtask", default=default)
            default=""
            if not summary:
                break
            cnt += 1
            todo = obj.parent.save_todo(summary=summary, parent=[comp['uid']])
            obj.load()
            if partially_complete:
                todo.complete()
                break
        new_estimate_suggestion = f"{estimate.total_seconds()//3600//cnt+1}h"
        new_estimate = click.prompt("what is the remaining estimate for the parent task?", default=new_estimate_suggestion)
        obj.set_duration(parse_add_dur(None, new_estimate), movable_attr='dtstart') ## TODO: verify
        new_summary = click.prompt("Summary of the parent task?", default=obj.icalendar_component['SUMMARY'])
        obj.icalendar_component['SUMMARY'] = new_summary
        postpone = click.prompt("Should we postpone the parent task?", default='0h')
        if postpone != '0h':
            _procrastinate([obj], postpone, check_dependent='interactive', err_callback=click.echo, confirm_callback=click.confirm)
        obj.save()

@interactive.command()
@click.pass_context
def set_task_attribs(ctx):
    """Interactively populate missing attributes to tasks

    Convenience method for tobixen-style task management.  Assumes
    that all tasks ought to have categories, a due date, a priority
    and a duration (estimated minimum time to do the task) set and ask
    for those if it's missing.

    See also USER_GUIDE.md, TASK_MANAGEMENT.md and NEXT_LEVEL.md
    """
    click.echo("All tasks ought to have categories, due-time, time-estimate and a priority ... checking if anything is missing")
    _set_task_attribs(ctx)

def _set_task_attribs(ctx):
    """
    actual implementation of set_task_attribs
    """
    ## Tasks missing a category
    LIMIT = 16

    def _set_something_(something, help_text, help_url=None, default=None, objs=None):
        cond = {f"no_{something}": True}
        something_ = 'categories' if something == 'category' else something
        if something == 'duration':
            something_ = 'dtstart'
            cond['no_dtstart'] = True
        _select(ctx=ctx, todo=True, limit=LIMIT, sort_key=['{DTSTART:?{DUE:?(0000)?}?%F %H:%M:%S}', '{PRIORITY:?0?}'], **cond)
        ## Doing some client-side filtering due to calendar servers that don't support the RFC properly
        ## TODO: "Incompatibility workarounds" should be moved to the caldav library
        objs_ = [x for x in ctx.obj['objs'] if not x.icalendar_component.get(something_)]

        ## add all non-duplicated objects from objs to objs_
        uids_ = {x.icalendar_component['UID'] for x in objs_}
        for obj in objs or []:
            if not obj.icalendar_component['UID'] in uids_:
                obj.load()
                objs_.append(obj)
        objs = objs_

        if objs:
            if something == 'duration':
                objs = [x for x in objs if x.icalendar_component.get('due')]
            num = len(objs)
            if num == LIMIT:
                num = f"{LIMIT} or more"
            click.echo(f"There are {num} tasks with no {something} set.")
            click.echo(help_url)
            if something == 'category':
                _select(ctx=ctx, todo=True)
                cats = list_type(_cats(ctx))
                cats.sort()
                click.echo("List of existing categories in use (if any):")
                click.echo("\n".join(cats))
            click.echo(f"For each task, {help_text}")
            click.echo(f'(or enter "completed!" with bang but without quotes if the task is already done)')
            for obj in objs:
                comp = obj.icalendar_component
                summary = _summary(comp)
                value = click.prompt(summary, default=default)
                if value == 'completed!':
                    obj.complete()
                    obj.save()
                    continue
                if something == 'category':
                    comp.add(something_, value.split(','))
                elif something == 'due':
                    _procrastinate([obj], parse_dt(value, datetime.datetime), check_dependent='interactive', err_callback=click.echo, confirm_callback=click.confirm)
                elif something == 'duration':
                    obj.set_duration(parse_add_dur(None, value), movable_attr='DTSTART')
                else:
                    comp.add(something_, value)
                    if hasattr(comp[something], 'dt'):
                        if not comp[something].dt.tzinfo:
                            comp[something].dt = com[something].dt.astimezone(tz.store_timezone)
                obj.save()
            click.echo()
        return objs

    ## Tasks missing categories
    _set_something_('category', "enter a comma-separated list of CATEGORIES to be added", "https://github.com/tobixen/plann/blob/master/TASK_MANAGEMENT.md#categories-resources-concept-refid")

    ## Tasks missing a due date.  Save those objects (workaround for https://gitlab.com/davical-project/davical/-/issues/281)
    duration_missing = _set_something_('due', "enter the DUE DATE (default +2d)", default="+2d", help_url="https://github.com/tobixen/plann/blob/master/TASK_MANAGEMENT.md#dtstart-due-duration-completion")

    _set_something_('priority', 'Enter the PRIORITY', help_url='https://github.com/tobixen/plann/blob/master/TASK_MANAGEMENT.md#priority', default="5")

    ## Tasks missing a duration
    _set_something_('duration', """Enter the DURATION (i.e. 5h or 2d)""", help_url="https://github.com/tobixen/plann/blob/master/TASK_MANAGEMENT.md#dtstart-due-duration-completion", objs=duration_missing)

if __name__ == '__main__':
    cli()
