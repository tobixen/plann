from plann import panic_planning
from datetime import datetime, timedelta

def test_timeline():
    timeline = panic_planning.TimeLine()
    timeline.add(
        begin=datetime(year=2025, month=2, day=25, hour=20),
        end=datetime(year=2025, month=2, day=25, hour=20, minute=30), obj=5)
    timeline.add(
        begin=datetime(year=2025, month=2, day=25, hour=20, minute=30),
        end=datetime(year=2025, month=2, day=25, hour=20, minute=40), obj=6)
    timeline.add(
        begin=datetime(year=2025, month=2, day=26, hour=20, minute=30),
        end=datetime(year=2025, month=2, day=26, hour=20, minute=40), obj=7)
    timeline.add(
        begin=datetime(year=2025, month=2, day=26, hour=10, minute=30),
        end=datetime(year=2025, month=2, day=26, hour=10, minute=40), obj=8)
    foo = timeline.get(datetime(year=2025, month=2, day=26, hour=20, minute=35))
    assert foo['end'] == datetime(year=2025, month=2, day=26, hour=20, minute=40)
    foo = timeline.get(datetime(year=2025, month=2, day=26, hour=12, minute=35))
    assert foo['end'] == datetime(year=2025, month=2, day=26, hour=20, minute=30)
    foo = timeline.get(datetime(year=2025, month=2, day=27, hour=12, minute=35))
    assert foo['begin'] == datetime(year=2025, month=2, day=26, hour=20, minute=40)
    assert not 'end' in foo
    foo = timeline.get(datetime(year=2020, month=2, day=27, hour=12, minute=35))
    assert foo['end'] == datetime(year=2025, month=2, day=25, hour=20, minute=00)
    assert not 'begin' in foo
    (opening, slack_balance) = timeline.find_opening(last_possibility=datetime(year=2025, month=3, day=25, hour=20), duration=timedelta(days=2))
    assert slack_balance == timedelta(0)
    assert not 'end' in opening
    (opening, slack_balance) = timeline.find_opening(last_possibility=datetime(year=2025, month=2, day=28, hour=20), duration=timedelta(days=2))
    assert slack_balance > timedelta(0)
    assert not 'begin' in opening
    timeline.pad_slack(end=datetime(year=2025, month=2, day=26, hour=12, minute=45), duration=timedelta(seconds=3600))
    timeline.pad_slack(end=datetime(year=2025, month=2, day=26, hour=22, minute=45), duration=timedelta(days=2))
