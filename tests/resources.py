"""Explicit resource ownership for local test fixtures.

Pass ExitStack.callback for resources inside a temporary-directory scope, or
TestCase.addCleanup for resources whose lifetime is the whole test. Register the
directory/file first so LIFO cleanup closes connections before removing files.
"""
from pathlib import Path


def close_with(cleanup, resource):
    cleanup(resource.close)
    return resource


def dispose_with(cleanup, engine):
    cleanup(engine.dispose)
    return engine


def close_first_with(cleanup, result):
    """Own the connection returned with a production qualification summary."""
    cleanup(result[0].close)
    return result


def remove_file(path):
    Path(path).unlink(missing_ok=True)
