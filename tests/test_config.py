"""Tests for plann.config.interactive_config.

The interactive configuration writer must only emit keys that the caldav
config reader (extract_conn_params_from_section) and plann's find_calendars
actually consume - otherwise the prompt writes config that is silently
dropped at connect time (code review C8)."""

import builtins

from plann.config import interactive_config

try:
    from caldav.config import extract_conn_params_from_section
except ImportError:  ## caldav <= 3.2.1 has it as a private function
    from caldav.config import _extract_conn_params_from_section as extract_conn_params_from_section


def _drive(monkeypatch, inputs, secrets=None):
    """Run interactive_config feeding `inputs` to input() and `secrets` to
    getpass(), aborting at the save prompt.  Returns the (mutated) config."""
    inputs = list(inputs)
    secrets = list(secrets or [])

    def fake_input(prompt=""):
        return inputs.pop(0)

    def fake_getpass(prompt=""):
        return secrets.pop(0)

    monkeypatch.setattr(builtins, "input", fake_input)
    monkeypatch.setattr("plann.config.getpass", fake_getpass)

    config = {}
    return interactive_config(config, config_file="/nonexistent/never-written.conf")


def test_interactive_config_only_writes_consumable_keys(monkeypatch):
    ## one value per prompt key, in order, then 'abort' at the save prompt
    inputs = [
        "https://calendar.example.com/dav",  # caldav_url
        "user",                              # caldav_user
        "http://proxy.example.com",          # caldav_proxy
        "true",                              # caldav_ssl_verify_cert
        "https://calendar.example.com/cal",  # calendar_url
        "My Calendar",                       # calendar_name
        "",                                  # features (skip - would be resolved)
        "",                                  # inherits (skip)
        "timewarrior",                       # extra_config.time_tracking
        "abort",                             # save-state command
    ]
    config = _drive(monkeypatch, inputs, secrets=["hunter2"])
    section = config["default"]

    ## the ssl key must be caldav_-prefixed, otherwise caldav drops it
    assert "caldav_ssl_verify_cert" in section
    assert "ssl_verify_cert" not in section

    ## keys plann does not consume must not be written
    assert "language" not in section
    assert "timezone" not in section

    ## time tracking rides in the extra_config sub-dict find_calendars passes on
    assert section["extra_config"]["time_tracking"] == "timewarrior"


def test_interactive_config_connection_keys_survive_extractor(monkeypatch):
    """Everything the writer emits as a connection parameter must be picked up
    by caldav's extractor - the C8 bug was that ssl_verify_cert was dropped."""
    inputs = [
        "https://calendar.example.com/dav",  # caldav_url
        "user",                              # caldav_user
        "http://proxy.example.com",          # caldav_proxy
        "true",                              # caldav_ssl_verify_cert
        "",                                  # calendar_url
        "",                                  # calendar_name
        "",                                  # features
        "",                                  # inherits
        "",                                  # time_tracking
        "abort",
    ]
    config = _drive(monkeypatch, inputs, secrets=["hunter2"])
    conn = extract_conn_params_from_section(config["default"])
    assert conn["url"] == "https://calendar.example.com/dav"
    assert conn["username"] == "user"
    assert conn["password"] == "hunter2"
    assert conn["proxy"] == "http://proxy.example.com"
    assert "ssl_verify_cert" in conn
