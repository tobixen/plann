import pytest
from datetime import datetime, date
from plann.template import Template
from plann.lib import tz
import zoneinfo

"""
Testing the plann templating engine
"""

class TestTemplate:
    def setup_method(self):
        self.date = date(1990, 10, 10)
        tz.implicit_timezone='UTC'
        
    def test_formatting_with_timespec(self):
        template=Template("This is an ISO date: {date:%F}")
        text = template.format(date=self.date)
        assert text == "This is an ISO date: 1990-10-10"

        text = template.format(foo=self.date)
        assert text == "This is an ISO date: "
        
    def test_formatting_with_simple_default(self):
        template=Template("This is an ISO date: {date:?(date is missing)?%F}")
        text = template.format(date=self.date)
        assert text == "This is an ISO date: 1990-10-10"

        text = template.format(foo=self.date)
        assert text == "This is an ISO date: (date is missing)"

    def test_subvalue_with_default(self):
        template = Template("This is a year: {date.year:?NA?>5}")
        text = template.format(date=self.date)
        assert text == "This is a year:  1990"
        text = template.format(foo=self.date)
        assert text == "This is a year:    NA"

    def test_missing_replaced_with_advanced_default(self):
        template = Template("Date is maybe {date:?{foo}?%F}")
        text = template.format(date=self.date)
        assert text == "Date is maybe 1990-10-10"
        text = template.format(foo=self.date)
        assert text == "Date is maybe 1990-10-10"
        text = template.format(foo=self.date, date=self.date)
        assert text == "Date is maybe 1990-10-10"

    def test_missing_replaced_with_even_more_advanced_default(self):
        template = Template("Date is maybe {date:?{foo:?bar?}?%F}")
        text = template.format(date=self.date)
        assert text == "Date is maybe 1990-10-10"
        text = template.format(foo=self.date)
        assert text == "Date is maybe 1990-10-10"
        text = template.format(foo=self.date, date=self.date)
        assert text == "Date is maybe 1990-10-10"
        text = template.format()
        assert text == "Date is maybe bar"



        
