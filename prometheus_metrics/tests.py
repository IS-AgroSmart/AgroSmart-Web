import os
import subprocess

import pytest
from . import views


class FakeSubprocessException(Exception):
    pass


def fake_subprocess(*args, **kwargs):
    del (args, kwargs)  # unused
    raise FakeSubprocessException("fake!")


def test_returns_to_dir(fs, monkeypatch):
    original_dir = os.getcwd()
    fs.create_dir("/gitinfo")
    monkeypatch.setattr(subprocess, "check_output", fake_subprocess)

    try:
        views._get_git_info()
    except FakeSubprocessException:
        pass  # ignore the exception

    assert os.getcwd() == original_dir  # code should still have restored working dir
