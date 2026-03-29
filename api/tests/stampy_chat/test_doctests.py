"""Run doctests from modules with heavy imports by importing just the functions."""
import doctest
import types


def _make_module(name, **funcs):
    """Create a minimal module with just the functions we want to doctest."""
    mod = types.ModuleType(name)
    for k, v in funcs.items():
        setattr(mod, k, v)
    return mod


def test_expand_blocks_doctests():
    from stampy_chat.prompts import _expand_blocks
    mod = _make_module("prompts", _expand_blocks=_expand_blocks)
    results = doctest.testmod(mod)
    assert results.failed == 0, f"{results.failed} doctest(s) failed"


def test_max_ref_in_history_doctests():
    from stampy_chat.chat import _max_ref_in_history
    mod = _make_module("chat", _max_ref_in_history=_max_ref_in_history)
    results = doctest.testmod(mod)
    assert results.failed == 0, f"{results.failed} doctest(s) failed"
