## This do testing all the way towards (a) calendar server(s)

## TODO: work in progress

from xandikos.web import run_simple_server
from plann.lib import find_calendars
import threading
from unittest.mock import MagicMock

def start_xandikos_server():
    start_simple_server_with_defaults = lambda: run_simple_server
    thread = threading.Thread(target=run_simple_server, kwargs={'current_user_principal': '/sometestuser', 'directory': '/tmp/xandikos/', 'autocreate': True})
    thread.start()
    assert thread.is_alive()
    return {
        'caldav_user': 'sometestuser',
        'caldav_password': 'pass1',
        'caldav_url': 'http://localhost:8080/'
    }

## we start with a monolithic test testing various aspects
## of the plann towards a server - but eventually it would
## be better to make many small tests, and reset the calendar
## server to some known state prior to each test
def test_plann():
    conn_details = start_xandikos_server()
    ctx = MagicMock()
    #calendars = find_calendars(conn_details, raise_errors=True)

## TODO:
## Things to be tested: lib._procrastinate, lib.find_calendars, cli._select, cli._cats, cli._list, cli._interactive_edit, cli._set_something, cli._interactive_ical_edit, cli._edit, cli._check_for_panic, _add_todo, _agenda, _check_due, 
