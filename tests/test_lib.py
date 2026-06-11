from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from caldav import Calendar, Todo

from plann.lib import (
    _add_category,
    _adjust_ical_relations,
    _procrastinate,
    _set_something,
    _split_vcal,
    _summary,
    add_time_tracking,
    add_time_tracking_timew,
)

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

## find_calendars also tested in test_functional.py

class TestFindCalendars:
    """The heavy lifting (connection parameter extraction, URL resolution
    from features, calendar lookup) is delegated to the caldav library -
    these tests only verify the plann-side glue."""

    ## auto-connect hints instead of a caldav_url - the caldav library
    ## resolves the URL from these.  (A dict rather than a profile name like
    ## "ecloud" to keep the test independent of compatibility_hints, and a
    ## username without @ to avoid triggering RFC6764 network discovery)
    features = {'auto-connect.url': {'domain': 'calendar.example.com', 'scheme': 'https', 'basepath': '/dav'}}

    def _find_calendars(self, args):
        from plann.lib import find_calendars
        with patch('caldav.davclient.DAVClient.principal') as principal:
            cal = object()
            principal.return_value.calendars.return_value = [cal]
            principal.return_value.get_calendars.return_value = [cal]
            return find_calendars(args, raise_errors=True), cal

    def test_explicit_url(self):
        calendars, cal = self._find_calendars({
            'caldav_url': 'https://calendar.example.com/dav',
            'caldav_user': 'user', 'caldav_pass': 'hunter2'})
        assert calendars == [cal]

    def test_features_without_url(self):
        """A config section without caldav_url should work when the URL can
        be derived from the features (auto-connect.url hints)."""
        calendars, cal = self._find_calendars({
            'caldav_user': 'user', 'caldav_pass': 'hunter2',
            'features': self.features})
        assert calendars == [cal]

    def test_no_connection_params(self):
        calendars, cal = self._find_calendars({})
        assert calendars == []

    def test_extra_params(self):
        class FakeCalendar:
            pass
        from plann.lib import find_calendars
        with patch('caldav.davclient.DAVClient.principal') as principal:
            cal = FakeCalendar()
            principal.return_value.calendars.return_value = [cal]
            principal.return_value.get_calendars.return_value = [cal]
            calendars = find_calendars({
                'caldav_url': 'https://calendar.example.com/dav',
                'caldav_extra_params': {'time_tracking': ['timew']}},
                raise_errors=True)
        assert calendars == [cal]
        assert cal.extra_params == {'time_tracking': ['timew']}

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

#def test_split_vcals():
## TODO

def test_split_vcal():
    ## This VCALENDAR contains three events, but only two separate
    ## event components as one of the events is a recurrence object.
    ## According to the CalDAV standard it should be wrapped in two VCALENDAR
    input = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//eome//prodid//en_DK
BEGIN:VTIMEZONE
TZID:Europe/Oslo
X-LIC-LOCATION:Europe/Oslo
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:20251026T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:20250330T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
UID:2025-09-27-189a6563aa65236c@techtalks.com
SUMMARY:Varnish - the world's fastest web cache
DTSTART:20250927T103000Z
DTEND:20250927T110000Z
DESCRIPTION: A talk about Varnish
LOCATION:Room 1: Dubulti 2
END:VEVENT
BEGIN:VEVENT
SUMMARY:recurrence with attendee one single item
DTSTART;TZID=Europe/Zurich:20240101T090000
DTEND;TZID=Europe/Zurich:20240101T180000
UID:test1
DESCRIPTION:this is the recurrent series
TRANSP:OPAQUE
RRULE:FREQ=WEEKLY;BYDAY=TU,WE,TH
END:VEVENT
BEGIN:VEVENT
SUMMARY:single item
DTSTART;TZID=Europe/Zurich:20240605T090000
DTEND;TZID=Europe/Zurich:20240605T170000
UID:test1
DESCRIPTION:this is the single item assigning a attendee to just one event
ATTENDEE:foo.bar@corge.baz
RECURRENCE-ID:20240605T070000Z
END:VEVENT
END:VCALENDAR
"""
    output = _split_vcal(input)
    assert(len(output) == 2)
