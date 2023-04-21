## This do testing all the way towards (a) calendar server(s)

## TODO: work in progress

from xandikos.web import run_simple_server
import threading
from unittest.mock import MagicMock

def start_xandikos_server():
    start_simple_server_with_defaults = lambda: run_simple_server(current_user_principal='/sometestuser', directory='/tmp/xandikos/', autocreate=True)
    thread = threading.Thread(target=start_simple_server_with_defaults)
    thread.start()
    return thread

## we start with a monolithic test testing various aspects
## of the plann towards a server - but eventually it would
## be better to make many small tests, and reset the calendar
## server to some known state prior to each test
def test_plann():
    mythread = start_xandikos_server()
    ctx = MagicMock()
    ctx.obj = {'foo': 'bar'}
    ## TODO ... work in progress
