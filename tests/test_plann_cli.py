## Check https://click.palletsprojects.com/en/8.1.x/testing/

from unittest.mock import patch

from caldav import Todo
from click.testing import CliRunner

import plann.cli as cli_mod
import plann.commands as commands_mod
from plann.cli import _LazyCalendars, cli, edit
from plann.commands import _process_add_args, _sort_key_function

_TODO = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Example Corp.//CalDAV Client//EN
BEGIN:VTODO
UID:{uid}
DTSTAMP:19970901T130000Z
SUMMARY:task {uid}
PRIORITY:{priority}
END:VTODO
END:VCALENDAR"""


def _todo(uid, priority):
    obj = Todo()
    obj.data = _TODO.format(uid=uid, priority=priority)
    return obj


def test_sort_key_function_priority():
    """A bare property name sorts on that icalendar property."""
    reverse, fkey = _sort_key_function('PRIORITY')
    assert reverse is False
    objs = [_todo('a', 3), _todo('b', 1), _todo('c', 2)]
    objs.sort(key=fkey)
    assert [str(o.icalendar_component['UID']) for o in objs] == ['b', 'c', 'a']


def test_sort_key_function_reverse():
    """A leading '-' reverses the sort."""
    reverse, fkey = _sort_key_function('-PRIORITY')
    assert reverse is True
    objs = [_todo('a', 3), _todo('b', 1), _todo('c', 2)]
    objs.sort(key=fkey, reverse=reverse)
    assert [str(o.icalendar_component['UID']) for o in objs] == ['a', 'c', 'b']


def test_sort_key_function_compiles_template_once():
    """A template sort key must be compiled once, not rebuilt on every
    comparison during the sort (code review E2)."""
    objs = [_todo(uid, p) for uid, p in (('a', 3), ('b', 1), ('c', 2), ('d', 5), ('e', 4))]
    with patch('plann.commands.Template', wraps=commands_mod.Template) as template_cls:
        reverse, fkey = _sort_key_function('{PRIORITY}')
        objs.sort(key=fkey, reverse=reverse)
    assert template_cls.call_count == 1
    assert [str(o.icalendar_component['UID']) for o in objs] == ['b', 'c', 'a', 'e', 'd']


def test_configure_command_registered():
    """The interactive configuration is wired into the click CLI as
    `plann configure` (code review C8 re-wiring)."""
    assert 'configure' in cli.commands


def test_lazy_calendars_resolves_once():
    """_LazyCalendars defers discovery until first use, then caches it."""
    calls = []

    def discover():
        calls.append(1)
        return ['a', 'b']

    lazy = _LazyCalendars(discover)
    assert calls == []          ## not resolved just by constructing
    assert len(lazy) == 2       ## first access triggers discovery
    assert list(lazy) == ['a', 'b']
    assert lazy[0] == 'a'
    assert bool(lazy) is True
    assert calls == [1]         ## resolved exactly once


def test_calendar_discovery_deferred_for_help():
    """Showing subcommand --help must not trigger calendar discovery (which
    talks to the network), even with a caldav_url given (code review E1)."""
    calls = []
    orig = cli_mod.find_calendars

    def spy(*a, **k):
        calls.append(1)
        return orig(*a, **k)

    cli_mod.find_calendars = spy
    try:
        res = CliRunner().invoke(
            cli, ['--skip-config', '--caldav-url', 'http://example.invalid/', 'select', '--help'])
        assert res.exit_code == 0, res.output
        assert calls == [], "discovery should be deferred when only showing help"
    finally:
        cli_mod.find_calendars = orig


def _option_names(cmd):
    names = set()
    for param in cmd.params:
        names.update(param.opts)
    return names


def _find_option(cmd, name):
    for param in cmd.params:
        if name in param.opts:
            return param
    return None


def test_edit_exposes_comma_list_options():
    """categories and resources are both exposed in singular + plural for both
    add (append) and the existing set (replace) verbs - so the user does not
    have to remember which form to use."""
    names = _option_names(edit)
    for opt in (
        '--add-category',
        '--add-categories',
        '--add-resource',
        '--add-resources',
        '--set-category',
        '--set-categories',
        '--set-resources',
    ):
        assert opt in names, f"missing {opt}"


def test_no_set_resource_singular():
    """There is deliberately no --set-resource (singular replace)."""
    assert '--set-resource' not in _option_names(edit)


def test_set_category_marked_deprecated():
    """--set-category keeps working (it appends) but its help flags it as
    deprecated in favour of --add-category / --set-categories."""
    opt = _find_option(edit, '--set-category')
    assert opt is not None
    assert 'deprecat' in (opt.help or '').lower()


def test_process_add_args():
    """--add-* options are collected as (canonical_property, tokens) to append:
    plural splits on comma, singular keeps it literal."""
    kwargs = {
        'add_category': ('a,b',),
        'add_categories': ('x,y',),
        'add_resource': ('R1,R2',),
        'add_resources': ('S1,S2',),
        'set_summary': 'unrelated',
    }
    result = _process_add_args(kwargs)
    assert ('categories', ['a,b']) in result
    assert ('categories', ['x', 'y']) in result
    assert ('resources', ['R1,R2']) in result
    assert ('resources', ['S1', 'S2']) in result
    ## add_* keys are consumed; unrelated keys are left untouched
    assert not any(k.startswith('add_') for k in kwargs)
    assert 'set_summary' in kwargs
