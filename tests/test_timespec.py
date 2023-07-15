import pytest
from datetime import datetime, date, timedelta, timezone
from plann.lib import tz
from plann.lib import parse_timespec, parse_dt, parse_add_dur, _ensure_ts

utc = timezone.utc

class TestParseTimestamp:
    @pytest.mark.parametrize("input", ["2012-12-12", "2011-11-11 11:11:11", datetime(2011, 11, 11, 11, 11, 11), date(2012, 12, 12), "+14d"])
    def testParseDt(self, input):
        tz.implicit_timezone = 'Europe/Helsinki'
        ts = parse_dt(input)
        if input == '+14d':
            assert ts > datetime.now().astimezone(tz.implicit_timezone)
        else:
            assert ts in (
                datetime(2011, 11, 11, 11, 11, 11, tzinfo=tz.implicit_timezone),
                date(2012, 12, 12))
        ts = parse_dt(input, return_type=datetime)
        if input == '+14d':
            assert ts > datetime.now().astimezone(tz.implicit_timezone)
        else:
            assert ts in (
                datetime(2011, 11, 11, 11, 11, 11, tzinfo=tz.implicit_timezone),
                datetime(2012, 12, 12, 0, 0, tzinfo=tz.implicit_timezone))
        ts = parse_dt(input, return_type=date)
        if input == '+14d':
            assert ts > date.today()
        else:
            assert ts in (
                date(2011, 11, 11), date(2012, 12, 12))

    @pytest.mark.parametrize("dt,dur,expected", [
        (date(2020,2,20),'1d',date(2020,2,21)),
        (date(2020,2,20),'+1d',date(2020,2,21)),
        ("2020-02-20",'+1d',date(2020,2,21)),

        ## Should this yield a date or a datetime?  TODO!
        #(date(2020,2,20),'1s',date(2020,2,20)),

        (datetime(2020,2,20),'1s', datetime(2020,2,20,0,0,1)),
        (datetime(2020,2,20),'2m', datetime(2020,2,20,0,2,0)),
        (datetime(2020,2,20),'3h', datetime(2020,2,20,3,0,0)),
        (datetime(2020,2,20),'4d', datetime(2020,2,24)),
        (datetime(2020,2,20),'1w1s', datetime(2020,2,27,0,0,1)),
        (datetime(2020,2,20),'2y1d', datetime(2022,2,21)),
        (None, '1s', timedelta(seconds=1))
         ])
    def test_parseAddDur(self, dt, dur, expected):
         if isinstance(dt, datetime):
             dt = dt.replace(tzinfo=tz.implicit_timezone)
         if isinstance(expected, datetime):
             expected = expected.replace(tzinfo=tz.implicit_timezone)
         assert parse_add_dur(dt, dur) == expected

    def _testTimeSpec(self, expected):
        expected_tz=tz.implicit_timezone
        if not expected_tz:
            expected_tz = datetime.now().astimezone().tzinfo
        for input in expected:
            def stz(dt):
                if dt and isinstance(dt, datetime):
                    return dt.replace(tzinfo=expected_tz)
                return dt
            expv = tuple([stz(x) for x in expected[input]])
            assert parse_timespec(input)== expv

    @pytest.mark.skip(reason="Not implemented yet, waiting for feedback on https://github.com/gweis/isodate/issues/77")
    def testIsoIntervals(self):
        raise pytest.SkipTest("")
        expected = {
            "2007-03-01T13:00:00Z/2008-05-11T15:30:00Z":
                (datetime(2007,3,1,13), datetime(2008,5,11,15,30)),
            "2007-03-01T13:00:00Z/P1Y2M10DT2H30M":
                (datetime(2007,3,1,13), datetime(2008,5,11,15,30)),
            "P1Y2M10DT2H30M/2008-05-11T15:30:00Z":
                (datetime(2007,3,1,13), datetime(2008,5,11,15,30))
        }
        self._testTimeSpec(expected)

    @pytest.mark.parametrize("tz_",['UTC', 'Pacific/Tongatapu', None])
    def testOneTimestamp(self, tz_):
        expected = {
            "2007-03-01T13:00:00":
                (datetime(2007,3,1,13), None),
            "2007-03-01 13:00:00":
                (datetime(2007,3,1,13), None),
        }
        tz.implicit_timezone = tz_
        self._testTimeSpec(expected)

    def testOneDate(self):
        expected = {
            "2007-03-01":
                (date(2007,3,1), None)
        }
        self._testTimeSpec(expected)
        
    def testTwoTimestamps(self):
        expected = {
            "2007-03-01T13:00:00 2007-03-11T13:30:00":
                (datetime(2007,3,1,13), datetime(2007,3,11,13,30)),
            "2007-03-01 13:00:00 2007-03-11 13:30:00":
                (datetime(2007,3,1,13), datetime(2007,3,11,13,30)),
        }
        self._testTimeSpec(expected)

    def testTwoDates(self):
        expected = {
            "2007-03-01 2007-03-11":
                (date(2007,3,1), date(2007,3,11))
        }
        self._testTimeSpec(expected)

    def testCalendarCliFormat(self):
        expected = {
            "2007-03-01T13:00:00+10d":
                (datetime(2007,3,1,13), datetime(2007,3,11,13)),
            "2007-03-01T13:00:00+2h":
                (datetime(2007,3,1,13), datetime(2007,3,1,15)),
            "2007-03-01T13:00:00+2.5h":
                (datetime(2007,3,1,13), datetime(2007,3,1,15,30)),
            "2007-03-01T13:00:00+2h30m":
                (datetime(2007,3,1,13), datetime(2007,3,1,15,30)),
            "2007-03-01+10d":
                (date(2007,3,1), date(2007,3,11))
        }
        self._testTimeSpec(expected)

def test_ensure_ts():
    now = datetime.now()
    utcnow = now.astimezone(utc)
    implicitnow = now.replace(tzinfo=tz.implicit_timezone)

    assert(_ensure_ts(now) == implicitnow)
    assert(_ensure_ts(utcnow) == utcnow)
    assert(_ensure_ts(implicitnow) == implicitnow)
