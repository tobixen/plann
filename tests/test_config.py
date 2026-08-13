import sys
from unittest.mock import patch

import pytest

from plann.config import PasswordCommandError, password_from_command
from plann.lib import find_calendars


def _script(code):
    """A shell command running `code` in the interpreter running the tests"""
    return f"{sys.executable} -c {code!r}"


def test_password_from_command_string_is_run_through_the_shell():
    assert password_from_command(_script("print('sekrit')")) == 'sekrit'


def test_password_from_command_list_is_run_without_shell():
    assert password_from_command([sys.executable, '-c', "print('sekrit')"]) == 'sekrit'


def test_password_from_command_uses_first_line_only():
    """`pass show` prints the password on the first line, metadata below"""
    assert password_from_command(_script("print('sekrit'); print('login: luser')")) == 'sekrit'


def test_password_from_command_keeps_significant_whitespace():
    assert password_from_command(_script("print(' sek rit ')")) == ' sek rit '


def test_password_from_command_rejects_nonzero_exit():
    with pytest.raises(PasswordCommandError, match='exited with status 3'):
        password_from_command(_script("import sys; print('sekrit'); sys.exit(3)"))


def test_password_from_command_rejects_empty_output():
    with pytest.raises(PasswordCommandError, match='did not print a password'):
        password_from_command(_script("pass"))


def test_password_from_command_rejects_blank_first_line():
    with pytest.raises(PasswordCommandError, match='did not print a password'):
        password_from_command(_script("print(); print('sekrit')"))


def test_password_from_command_rejects_missing_executable():
    with pytest.raises(PasswordCommandError, match='could not run password command'):
        password_from_command(['plann-no-such-executable'])


@patch("plann.lib.caldav.DAVClient")
def test_find_calendars_resolves_pass_command(davclient):
    """caldav_pass_command must reach DAVClient as `password`, and never as itself"""
    find_calendars({
        'caldav_url': 'http://caldav.example.com/',
        'caldav_user': 'luser',
        'caldav_pass_command': _script("print('sekrit')"),
    }, raise_errors=True)
    conn_params = davclient.call_args.kwargs
    assert conn_params['password'] == 'sekrit'
    assert conn_params['username'] == 'luser'
    assert conn_params['url'] == 'http://caldav.example.com/'
    assert 'pass_command' not in conn_params


@patch("plann.lib.caldav.DAVClient")
def test_find_calendars_accepts_password_command_spelling(davclient):
    """--caldav-password-command lands in kwargs as caldav_password_command"""
    find_calendars({
        'caldav_url': 'http://caldav.example.com/',
        'caldav_password_command': _script("print('sekrit')"),
    }, raise_errors=True)
    conn_params = davclient.call_args.kwargs
    assert conn_params['password'] == 'sekrit'
    assert 'password_command' not in conn_params


@patch("plann.lib.caldav.DAVClient")
def test_find_calendars_explicit_password_wins_over_pass_command(davclient, caplog):
    """Backward compatibility - an existing hardcoded password keeps working untouched.

    The password command must not even be run, so it is set to something that
    would raise PasswordCommandError if it were.
    """
    find_calendars({
        'caldav_url': 'http://caldav.example.com/',
        'caldav_pass': 'plaintext',
        'caldav_pass_command': 'exit 1',
    }, raise_errors=True)
    assert davclient.call_args.kwargs['password'] == 'plaintext'
    assert 'ignoring the password command' in caplog.text


@patch("plann.lib.caldav.DAVClient")
def test_find_calendars_without_connection_does_not_run_pass_command(davclient):
    """No server to connect to - the password command should not be run at all"""
    assert find_calendars({'caldav_pass_command': 'exit 1'}, raise_errors=True) == []
    davclient.assert_not_called()
