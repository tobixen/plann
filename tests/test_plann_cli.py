## Check https://click.palletsprojects.com/en/8.1.x/testing/

from plann.cli import edit
from plann.commands import _process_add_args


def _option_names(cmd):
    names = set()
    for param in cmd.params:
        names.update(param.opts)
    return names


def _find_option(cmd, name):
    for param in cmd.params:
        if name in param.opts:
            return param
    return None


def test_edit_exposes_comma_list_options():
    """categories and resources are both exposed in singular + plural for both
    add (append) and the existing set (replace) verbs - so the user does not
    have to remember which form to use."""
    names = _option_names(edit)
    for opt in (
        '--add-category',
        '--add-categories',
        '--add-resource',
        '--add-resources',
        '--set-category',
        '--set-categories',
        '--set-resources',
    ):
        assert opt in names, f"missing {opt}"


def test_no_set_resource_singular():
    """There is deliberately no --set-resource (singular replace)."""
    assert '--set-resource' not in _option_names(edit)


def test_set_category_marked_deprecated():
    """--set-category keeps working (it appends) but its help flags it as
    deprecated in favour of --add-category / --set-categories."""
    opt = _find_option(edit, '--set-category')
    assert opt is not None
    assert 'deprecat' in (opt.help or '').lower()


def test_process_add_args():
    """--add-* options are collected as (canonical_property, tokens) to append:
    plural splits on comma, singular keeps it literal."""
    kwargs = {
        'add_category': ('a,b',),
        'add_categories': ('x,y',),
        'add_resource': ('R1,R2',),
        'add_resources': ('S1,S2',),
        'set_summary': 'unrelated',
    }
    result = _process_add_args(kwargs)
    assert ('categories', ['a,b']) in result
    assert ('categories', ['x', 'y']) in result
    assert ('resources', ['R1,R2']) in result
    assert ('resources', ['S1', 'S2']) in result
    ## add_* keys are consumed; unrelated keys are left untouched
    assert not any(k.startswith('add_') for k in kwargs)
    assert 'set_summary' in kwargs
