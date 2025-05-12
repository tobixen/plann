import pytest
from unittest.mock import patch
from caldav import Todo, Calendar
from plann.lib import _summary,  _procrastinate, _adjust_ical_relations, _add_category, _set_something, add_time_tracking_timew, add_time_tracking
from datetime import datetime, timedelta
from datetime import timezone


utc=timezone.utc
todo = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Example Corp.//CalDAV Client//EN
BEGIN:VTODO
UID:19970901T130000Z-123404@host.com
DTSTAMP:19970901T130000Z
DTSTART:19970415T133000Z
DUE:19970416T045959Z
SUMMARY:Fix a party
DESCRIPTION:Buy some food and drinks, clean up the place, hang up some baloons
PRIORITY:2
STATUS:NEEDS-ACTION
END:VTODO
END:VCALENDAR"""

## find_calendars tested in test_functional.py

def test_summary():
    t = Todo()
    t.data = todo
    assert(_summary(t) == "Fix a party")
    assert(_summary(t.icalendar_component) == "Fix a party")
    t.icalendar_component.pop('SUMMARY')
    assert(_summary(t) == "Buy some food and drinks, clean up the place, hang up some baloons")
    t.icalendar_component.pop('DESCRIPTION')
    assert(_summary(t) == "19970901T130000Z-123404@host.com")
    
@pytest.mark.parametrize("method", [add_time_tracking_timew, add_time_tracking])
@patch("plann.lib.subprocess.run")
def test_add_time_tracking_timew(mock_run, method):
    ts1 = datetime(2020, 2, 20, 20, 2)
    ts2 = datetime(2020, 2, 20, 20, 20)
    obj = Todo()
    obj.data = todo
    obj.parent=Calendar()
    obj.parent.extra_config={'time_tracking': ['timew']}
    
    method(obj, ts1, ts2)

    mock_run.assert_called_once()
    cmd_arr = mock_run.mock_calls[0].args[0]
    assert cmd_arr[0:5] == ['timew', 'track', '2020-02-20T20:02', '-', '2020-02-20T20:20']


def test_add_set_category():
    t = Todo()
    t.data = todo
    _add_category(t, 'foo')
    assert 'CATEGORIES:foo' in t.data
    _add_category(t, 'bar')
    set(t.icalendar_component['CATEGORIES'].cats) == {'foo', 'bar'}
    _set_something(t, 'category', 'zoo')
    set(t.icalendar_component['CATEGORIES'].cats) == {'foo', 'bar', 'zoo'}
    _set_something(t, 'categories', 'zoo,bar')
    set(t.icalendar_component['CATEGORIES'].cats) == {'bar', 'zoo'}

## _hasreltype is skipped as for now (too small and only used in _procrastinate)

## _procrastinate is quite complex because of the relationship handling.
## With the defaults, the only "functional" stuff it's doing is to call
## obj.set_due, which can easily be mocked up.
def test_procrastinate_without_relations():
    t = Todo()
    t.data = todo
    with patch.object(t, 'save'):
        with patch.object(t, 'set_due', return_value=None) as set_due_mocked:
            ## procrasting an overdue task should always end up with a future due
            _procrastinate([t], '10d')
            assert(set_due_mocked.call_count == 1)
            timearg = set_due_mocked.call_args[0][0]
            assert(timearg.astimezone(utc) <=
                   datetime.now().astimezone(utc)+timedelta(days=10))
            assert(timearg.astimezone(utc) >
                   datetime.now().astimezone(utc)+timedelta(days=9, hours=23, minutes=59))

            ## In 2033, surely plann must be obsoleted by AI-tools, let's add 20 years to that to be sure
            future = datetime(2053, 1, 1, 12, 0, 0).astimezone(utc)
            t.icalendar_component.pop('DUE')
            t.icalendar_component.add('DUE', future)
            _procrastinate([t], '10d')
            assert(set_due_mocked.call_count == 2)
            timearg = set_due_mocked.call_args[0][0]
            assert(timearg.astimezone(utc) == future+timedelta(days=10))

def test_adjust_ical_relations():
    t = Todo()
    t.data = todo

    ## populate some children and parents, series A and B, serial 0 and 2:
    for reltype in ['CHILD', 'PARENT']:
        for series in ('A', 'B'):
            for num in (0,2):
                t.icalendar_component.add('RELATED-TO', f"{reltype}-{series}{num}", parameters={'RELTYPE': reltype})
    ical_data1 = t.data

    ## This should keep all the parents, add all missing A-children, and remove all B-children
    assert not _adjust_ical_relations(t, {})
    assert(t.data == ical_data1)
    _adjust_ical_relations(t, {'CHILD': {'CHILD-A0', 'CHILD-A1', 'CHILD-A2'}}) is True
    assert(t.data != ical_data1)
    
    rels = t.get_relatives(reltypes={'CHILD'}, fetch_objects=False)

    assert(rels['CHILD'] == {'CHILD-A0', 'CHILD-A1', 'CHILD-A2'})
    
    ## CHILD should be the only key now
    rels.pop('CHILD')
    assert not rels
    
    rels = t.get_relatives(fetch_objects=False)
    ## should return both parents and children
    ## parent list should be unchanged
    assert(rels['PARENT'] == {'PARENT-A0', 'PARENT-A2', 'PARENT-B0', 'PARENT-B2'})
    assert(rels['CHILD'] == {'CHILD-A0', 'CHILD-A1', 'CHILD-A2'})

#def test_split_vcal():
## TODO    
