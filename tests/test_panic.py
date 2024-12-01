from plann import panic_planning
from datetime import datetime, timedelta
from unittest import mock
from caldav import Todo,Event
from caldav.lib.vcal import create_ical

def datetime_(*largs, **kwargs):
    ret = datetime(*largs, **kwargs)
    if not 'tzinfo' in kwargs:
        ret = ret.astimezone()
    return ret

def test_timeline():
    timeline = panic_planning.TimeLine()
    timeline.add(
        begin=datetime_(year=2025, month=2, day=25, hour=20),
        end=datetime_(year=2025, month=2, day=25, hour=20, minute=30), obj=5)
    timeline.add(
        begin=datetime_(year=2025, month=2, day=25, hour=20, minute=30),
        end=datetime_(year=2025, month=2, day=25, hour=20, minute=40), obj=6)
    timeline.add(
        begin=datetime_(year=2025, month=2, day=26, hour=20, minute=30),
        end=datetime_(year=2025, month=2, day=26, hour=20, minute=40), obj=7)
    timeline.add(
        begin=datetime_(year=2025, month=2, day=26, hour=10, minute=30),
        end=datetime_(year=2025, month=2, day=26, hour=10, minute=40), obj=8)
    foo = timeline.get(datetime_(year=2025, month=2, day=26, hour=20, minute=35))
    assert foo['end'] == datetime_(year=2025, month=2, day=26, hour=20, minute=40)
    foo = timeline.get(datetime_(year=2025, month=2, day=26, hour=12, minute=35))
    assert foo['end'] == datetime_(year=2025, month=2, day=26, hour=20, minute=30)
    foo = timeline.get(datetime_(year=2025, month=2, day=27, hour=12, minute=35))
    assert foo['begin'] == datetime_(year=2025, month=2, day=26, hour=20, minute=40)
    assert not 'end' in foo
    foo = timeline.get(datetime_(year=2020, month=2, day=27, hour=12, minute=35))
    assert foo['end'] == datetime_(year=2025, month=2, day=25, hour=20, minute=00)
    assert not 'begin' in foo
    (opening, slack_balance) = timeline.find_opening(last_possibility=datetime_(year=2025, month=3, day=25, hour=20), duration=timedelta(days=2))
    assert slack_balance == timedelta(0)
    assert not 'end' in opening
    (opening, slack_balance) = timeline.find_opening(last_possibility=datetime_(year=2025, month=2, day=28, hour=20), duration=timedelta(days=2))
    assert slack_balance > timedelta(0)
    assert not 'begin' in opening
    timeline.pad_slack(end=datetime_(year=2025, month=2, day=26, hour=12, minute=45), duration=timedelta(seconds=3600))
    timeline.pad_slack(end=datetime_(year=2025, month=2, day=26, hour=22, minute=45), duration=timedelta(days=2))

def test_timeline_add():
    t = lambda hour: datetime_(year=2025, month=2, day=25, hour=hour)
    timeline = panic_planning.TimeLine()
    
    assert len(timeline) == 0
    
    timeline.add(begin=t(14), end=t(15), obj='14')
    assert len(timeline) == 2
    assert timeline[0]['begin'] == t(14)
    assert timeline[0]['obj'] == '14'
    assert timeline[1]['begin'] == t(15)

    timeline.add(begin=t(12), end=t(13), obj='12')
    assert len(timeline) == 4
    assert timeline[0]['begin'] == t(12)
    assert timeline[0]['obj'] == '12'
    assert timeline[1]['begin'] == t(13)
    assert timeline[2]['begin'] == t(14)
    assert timeline[2]['obj'] == '14'
    assert timeline[3]['begin'] == t(15)
    
    timeline.add(begin=t(13), end=t(14), obj='13')
    assert len(timeline) == 4
    assert timeline[0]['begin'] == t(12)
    assert timeline[0]['obj'] == '12'
    assert timeline[1]['begin'] == t(13)
    assert timeline[1]['obj'] == '13'
    assert timeline[2]['begin'] == t(14)
    assert timeline[2]['obj'] == '14'
    assert timeline[3]['begin'] == t(15)

def create_obj(comp_class='VTODO', duehour=None, **data):
    if duehour:
        tomorrow = (datetime.now() + timedelta(days=1)).replace(minute=0, second=0)
        data['due'] = tomorrow.replace(hour=duehour)
        data['dtstart'] = tomorrow.replace(hour=duehour-1)
    compclass={'VEVENT': Event, 'VTODO': Todo}
    ical = create_ical(**data)
    return compclass[data.get('objtype', 'VEVENT')](client=None, url=f"https://example.com/{data['uid']}", data=ical)
    
def test_timeline_suggestion():
    pri1 = create_obj(uid=1, priority=1, duehour=12)
    pri2 = create_obj(uid=2, priority=1, duehour=10)
    pri3 = create_obj(uid=3, priority=1, duehour=14)

    ctx = mock.Mock
    ctx.obj = {'objs': [pri1, pri2, pri3]}

    timeline = panic_planning.timeline_suggestion(ctx, hours_per_day=23)

    ## Can we make asserts that are robust enough not to fail should the algorithm change completely?
    ## The only requirement is that it creates a timeline, isn't it?
    assert timeline[0]['begin']>=datetime.now().astimezone()
    assert len([x['obj'] for x in timeline if 'obj' in x]) == 3
    assert len(set([x['obj'].url for x in timeline if 'obj' in x])) == 3

    ## parents should always be handled after children
    pri3.icalendar_component.add('RELATED_TO', 'https://example.com/2', parameters={'RELTYPE': 'CHILD'})
    pri2.icalendar_component.add('RELATED_TO', 'https://example.com/3', parameters={'RELTYPE': 'PARENT'})
    
    timeline = panic_planning.timeline_suggestion(ctx, hours_per_day=23)
    #['x' for x in assert 
