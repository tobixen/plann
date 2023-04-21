import pytest
from datetime import datetime, date
from plann.lib import tz
from plann.lib import parse_timespec

class TestParseTimestamp:
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

