from plann import panic_planning
from datetime import datetime, timedelta

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
