from unittest.mock import MagicMock, patch  # noqa: F401

from caldav import Todo


def test_todos_missing_treats_priority_zero_as_undefined():
    """PRIORITY:0 is RFC 5545 "undefined priority", and plann treats it as
    such everywhere else (`comp.get('PRIORITY', 0)`, _mass_reprioritize).
    set-task-attribs must therefore still offer to set a priority on such a
    task - filtering on "property absent" alone skips exactly the tasks the
    feature exists to fix."""
    from plann.commands import _todos_missing

    def _todo(uid, extra):
        return Todo(data=(
            "BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VTODO\n"
            f"UID:{uid}\nSUMMARY:{uid}\n{extra}END:VTODO\nEND:VCALENDAR"))

    absent = _todo('no-priority', '')
    zero = _todo('zero-priority', 'PRIORITY:0\n')
    real = _todo('real-priority', 'PRIORITY:3\n')

    missing = _todos_missing([absent, zero, real], 'priority')
    uids = {x.icalendar_component['UID'] for x in missing}
    assert uids == {'no-priority', 'zero-priority'}
