from unittest.mock import MagicMock, patch

from caldav import Todo

from tests.test_lib import todo


def test_interactive_edit_start_without_time_tracking_config():
    """The interactive prompt now advertises `start`, but add_time_tracking
    raises NotImplementedError when extra_config.time_tracking is unset - the
    default.  That must be reported as a message, not an unhandled traceback
    that tears down the rest of the check-due session."""
    from plann.interactive import _interactive_edit

    obj = Todo(data=todo)
    obj.parent = MagicMock(extra_config={})

    with patch('plann.interactive.click.prompt', side_effect=['start', 'ignore']):
        with patch('plann.interactive.click.echo') as echo:
            _interactive_edit(obj)

    printed = " ".join(str(c) for c in echo.call_args_list)
    assert 'time_tracking' in printed or 'time tracking' in printed.lower()
