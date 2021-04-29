from contextlib import contextmanager
import os


# https://stackoverflow.com/a/24176022
@contextmanager
def cd(newdir):
    """
    Context manager that changes the working dir and restores it on exit
    Args:
        newdir: The target directory
    """
    prevdir = os.getcwd()
    try:
        os.chdir(newdir)
        yield
    finally:
        os.chdir(prevdir)
