## This do testing all the way towards (a) calendar server(s)

## TODO: work in progress

from xandikos.web import XandikosBackend, XandikosApp
from plann.lib import find_calendars
from plann.cli import _add_todo, _select, _list, _check_for_panic, _interactive_relation_edit
from plann.panic_planning import timeline_suggestion
from caldav import Todo
import aiohttp
import aiohttp.web
import threading
import requests
from unittest.mock import MagicMock, patch
import asyncio
import os
import signal
import tempfile
import time
from tests.test_panic import datetime_

class InterruptXandikosServer:
    def graceful_exit_with_pdb(self):
        import pdb; pdb.set_trace()
        self.graceful_exit()
    graceful_exit_ = lambda: 1

interrupt_xandikos_server_singleton = InterruptXandikosServer()

## I've made three different attempts on starting up xandikos.
## I should eventually look through this once more, as it's still non-trivial to restart the xandikos-server.

## This function is currently not in use
## TODO: this is how I would like to start the xandikos server, but it didn't quite work out ...
## 1) the run_simple_server method does not work in threads due to signal
## handling (sort of solved, but ...)
## 2) it's difficult to stop the thread
def start_xandikos_server_foobar():
    ## We need to mock up a signal handler
    global interrupt_xandikos_server_singleton
    def add_signal_handler(signal, handler):
        interrupt_xandikos_server_singleton.graceful_exit = handler
    new_signal_handler = add_signal_handler
    _orig_get_event_loop = asyncio.get_event_loop
    def _new_get_event_loop(*largs, **kwargs):
        loop = _orig_get_event_loop(*largs, **kwargs)
        loop.add_signal_handler = new_signal_handler
        return loop
    asyncio.get_event_loop = _new_get_event_loop

    ## Start xandikos in a thread
    thread = threading.Thread(target=run_simple_server, kwargs={'current_user_principal': '/sometestuser', 'directory': '/tmp/xandikos/', 'autocreate': True})
    thread.start()
    assert thread.is_alive()
    return {
        'caldav_user': 'sometestuser',
        'caldav_password': 'pass1',
        'caldav_url': 'http://localhost:8080/'
    }

## This function is currently not in use
def start_xandikos_server_fork():
    ## It's simple to fork out a xandikos server, but somehow I can't get it to work with pytest
    pid = os.fork()
    if not pid:
        run_simple_server(current_user_principal='/sometestuser', directory='/tmp/xandikos/', autocreate=True)
    else:
        return {
            'caldav_user': 'sometestuser',
            'caldav_password': 'pass1',
            'caldav_url': 'http://localhost:8080/',
            'pid': pid
        }

def start_xandikos_server():
    ## Copying the code from the caldav test suite
    serverdir = tempfile.TemporaryDirectory()
    serverdir.__enter__()
    ## Most of the stuff below is cargo-cult-copied from xandikos.web.main
    ## Later jelmer created some API that could be used for this
    backend = XandikosBackend(path=serverdir.name)
    backend._mark_as_principal("/sometestuser/")
    backend.create_principal("/sometestuser/", create_defaults=True)
    mainapp = XandikosApp(
        backend, current_user_principal="sometestuser", strict=True
    )

    async def xandikos_handler(request):
        return await mainapp.aiohttp_handler(request, "/")

    xapp = aiohttp.web.Application()
    xapp.router.add_route("*", "/{path_info:.*}", xandikos_handler)
    ## https://stackoverflow.com/questions/51610074/how-to-run-an-aiohttp-server-in-a-thread
    xapp_loop = asyncio.new_event_loop()
    xapp_runner = aiohttp.web.AppRunner(xapp)
    asyncio.set_event_loop(xapp_loop)
    xapp_loop.run_until_complete(xapp_runner.setup())
    xapp_site = aiohttp.web.TCPSite(
        xapp_runner, host='localhost', port=8080
    )
    xapp_loop.run_until_complete(xapp_site.start())

    def aiohttp_server():
        xapp_loop.run_forever()

    xandikos_thread = threading.Thread(target=aiohttp_server)
    xandikos_thread.start()
    server_params = {
        "caldav_url": "http://localhost:8080",
        "caldav_password": "pass1",
        "caldav_user": "sometestuser",
        "xandikos_thread": xandikos_thread,
        "xandikos_app_loop": xapp_loop,
        "serverdir": serverdir,
        "xandikos_app_runner": xapp_runner
    }
    return server_params

def stop_xandikos_server(server_params):
    server_params['xandikos_app_loop'].stop()
    ## ... but the thread may be stuck waiting for a request ...
    def silly_request():
        try:
            requests.get(server_params["caldav_url"])
        except:
            pass
    threading.Thread(target=silly_request).start()
    i = 0
    while server_params['xandikos_app_loop'].is_running():
        time.sleep(0.05)
        i += 1
        assert i < 100
    server_params['xandikos_app_loop'].run_until_complete(server_params['xandikos_app_runner'].cleanup())
    i = 0
    while server_params['xandikos_thread'].is_alive():
        time.sleep(0.05)
        i += 1
        assert i < 100

    server_params['serverdir'].__exit__(None, None, None)

    
## we start with a monolithic test testing various aspects
## of the plann towards a server - but eventually it would
## be better to make many small tests, and reset the calendar
## server to some known state prior to each test
## (interrupt_xandikos_server_singleton.graceful_exit() causes locking problem)
def test_plann():
    conn_details = start_xandikos_server()
    try:
        ctx = MagicMock()
        ctx.obj = dict()
        ctx.obj['calendars'] = find_calendars(conn_details, raise_errors=True)
        todo1 = _add_todo(ctx, summary=['make plann good'], set_due='2012-12-20 23:15:00', set_dtstart='2012-12-20 22:15:00')
        todo2 = _add_todo(ctx, summary=['make plann even better'], set_parent=[todo1.icalendar_component['uid']], set_due='2012-12-21 23:15:00', set_dtstart='2012-12-21 22:15:00')
        _select(ctx, todo=True, skip_children=True)
        assert len(ctx.obj['objs'])==1
        _select(ctx, todo=True, skip_parents=True)
        _list(ctx, top_down=True)
        _list(ctx, bottom_up=True)
        assert len(ctx.obj['objs'])==1
        _select(ctx, todo=True)
        assert len(ctx.obj['objs'])==2
        _select(ctx, summary='make plann good')
        ## this breaks with xandikos
        #assert len(ctx.obj['objs'])==1
        _select(ctx, summary='make plann good', todo=True)
        assert len(ctx.obj['objs'])==1

        _select(ctx, event=True)
        assert len(ctx.obj['objs'])==0
        _select(ctx, todo=True)
        assert len(ctx.obj['objs'])==2
        ## panic planning, timeline_suggestion.
        ## We have two tasks in the calendar, each with one hour duration
        timeline = timeline_suggestion(ctx, hours_per_day=24)
        assert(timeline.count() == 2)
        foo = timeline.get(datetime_(year=2012, month=12, day=20, hour=22, minute=35))
        assert foo['begin'] == datetime_(year=2012, month=12, day=20, hour=22, minute=15)
        assert foo['end'] == datetime_(year=2012, month=12, day=20, hour=23, minute=15)

        ## panic planning, timeline_suggestion with timeline_end
        ## Those two tasks should be neatly stacked up 
        assert len(ctx.obj['objs'])==2
        timeline = timeline_suggestion(ctx, timeline_end=datetime_(year=2011, month=11, day=11, hour=11, minute=11), hours_per_day=24)
        assert(timeline.count() == 2)
        foo = timeline.get(datetime_(year=2011, month=11, day=11, hour=11, minute=10))
        assert foo['begin'] == datetime_(year=2011, month=11, day=11, hour=10, minute=11)
        assert foo['end'] == datetime_(year=2011, month=11, day=11, hour=11, minute=11)
        foo = timeline.get(datetime_(year=2011, month=11, day=11, hour=10, minute=10))
        assert foo['begin'] == datetime_(year=2011, month=11, day=11, hour=9, minute=11)
        assert foo['end'] == datetime_(year=2011, month=11, day=11, hour=10, minute=11)
        
        ## fix_timeline feature
        _check_for_panic(ctx, timeline_start='2010-10-10', timeline_end=datetime_(year=2011, month=11, day=11, hour=11, minute=11), hours_per_day=24, fix_timeline=True, include_all_events=True)
        _select(ctx, event=True)
        assert len(ctx.obj['objs'])==2
        ## Re-running it should be a noop
        _check_for_panic(ctx, timeline_start='2010-10-10', timeline_end=datetime_(year=2011, month=11, day=11, hour=11, minute=11), hours_per_day=24, fix_timeline=True, include_all_events=True)
        _select(ctx, event=True)
        assert len(ctx.obj['objs'])==2

        ## We now have one task with one subtask, and both tasks have children
        ## events.
        ## Testing the interactive relation edit - if doing nothing in the
        ## editor, the algorithm should change nothing.
        cal_pre_interactive_relation_edit = "\n".join([x.data for x in ctx.obj['objs']])
        passthrough = lambda x: x
        with patch('plann.cli._editor', new=passthrough) as _editor:
            _interactive_relation_edit((ctx.obj['objs']))

        for obj in ctx.obj['objs']:
            obj.load()
        cal_post_interactive_relation_edit = "\n".join([x.data for x in ctx.obj['objs']])
        assert cal_post_interactive_relation_edit == cal_pre_interactive_relation_edit

        ## Now we delete the last two lines in the file.  That should cause changes in the relations
        skiplastlines = lambda x: "\n".join(x.split("\n")[0:-2])+"\n\n"
        with patch('plann.cli._editor', new=skiplastlines) as _editor:
            _interactive_relation_edit((ctx.obj['objs']))

        for obj in ctx.obj['objs']:
            obj.load()

        cal_post_interactive_relation_edit = "\n".join([x.data for x in ctx.obj['objs']])
        assert cal_post_interactive_relation_edit == cal_pre_interactive_relation_edit

    finally:
        stop_xandikos_server(conn_details)

## TODO:
## Things to be tested: lib._procrastinate, cli._select, cli._cats, cli._list, cli._interactive_edit, cli._set_something, cli._interactive_ical_edit, cli._edit, cli._check_for_panic, _add_todo, _agenda, _check_due, 
