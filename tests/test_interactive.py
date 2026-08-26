from unittest.mock import MagicMock, patch

import pytest
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


def test_set_relations_blank_line_does_not_orphan_children():
    """A blank or comment line left behind in the relations editor used to
    abort (the old get_obj raised NotImplementedError).  _get_obj_from_line
    returns None instead, so an unguarded parent silently reaches
    _adjust_relations(None, children) - which strips the children's PARENT
    relation and saves them.  A stray newline must never mutate data."""
    from plann.interactive import _set_relations_from_text_list

    calendar = MagicMock()
    calendar.object_by_uid.return_value = MagicMock()

    ## "uidA", then a blank line the user left behind, then an indented child
    some_list = ['uidA: task A', '   ', '  uidB: task B']

    with patch('plann.interactive._adjust_relations') as adjust:
        with pytest.raises(NotImplementedError):
            _set_relations_from_text_list(calendar, some_list)

    for call in adjust.call_args_list:
        assert call.args[0] is not None, "_adjust_relations called with parent=None"
