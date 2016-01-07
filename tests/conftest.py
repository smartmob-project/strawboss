# -*- coding: utf-8 -*-

import asyncio
import functools
import os
import pytest
import sys

from collections import deque
from contextlib import contextmanager
from random import randint
from socket import socket, socketpair
from unittest import mock
from unittest.mock import patch


@contextmanager
def redirect_stdout(stream):
    """Context manager to temporarily replace the standard output."""

    old_stdout = sys.stdout
    sys.stdout = stream
    try:
        yield stream
    finally:
        sys.stdout = old_stdout


class StreamReaderAdapter(object):
    """File-like object that pushes data to an asyncio ``StreamReader``."""

    def __init__(self, stream):
        self._stream = stream

    def write(self, data):
        sys.stderr.write('sending: "%s".\n' % data)
        if isinstance(data, str):
            data = data.encode('utf-8')
        self._stream.feed_data(data)

    def flush(self):
        pass

    def close(self):
        self._stream.feed_eof()


@contextmanager
def capture_stdout():
    """Context manager that captures output in asyncio-style.

    Returns a ``asyncio.StreamReader`` instance from which you can read what is
    printed to the standard output.

    Unfortunately, pytest seems to have some special handing of the capfd and
    capsys fixtures and it doesn't seem to be possible to write this as a
    fixture, so we're stuck with a context manager.q

    """
    reader = asyncio.StreamReader()
    try:
        with redirect_stdout(StreamReaderAdapter(reader)):
            yield reader
    finally:
        reader.feed_eof()


@pytest.yield_fixture
def clock():
    """Fixture for freezing time during a test."""
    from datetime import datetime
    from freezegun import freeze_time
    with freeze_time(datetime.now()):
        yield

class MockSubprocess(object):
    """Mock implementation of asyncio ``Popen`` object."""

    def __init__(self, args, kwds):
        self._kwds = kwds
        #
        self.pid = randint(1, 9999)
        self.stdout = asyncio.StreamReader()
        #
        self._future = asyncio.Future()
        self._killed = False

    @property
    def env(self):
        """Retrieve the environment variables passed to the process."""
        return {k: v for k, v in self._kwds['env'].items()}

    def wait(self):
        """Wait until the process completes."""
        return self._future

    def mock_complete(self, exit_code=0):
        if not self._future.done():
            self._future.set_result(exit_code)

    def kill(self):
        if self._future.done():
            raise ProcessLookupError
        # Defer completion (as IRL).
        loop = asyncio.get_event_loop()
        loop.call_soon(self._future.set_result, -9)

class MockSubprocessFactory(object):
    def __init__(self):
        self._instances = []

    @property
    def instances(self):
        return self._instances[:]

    @property
    def last_instance(self):
        return self._instances[-1]

@pytest.yield_fixture
def subprocess_factory():
    """Fixture to mock asyncio subprocess creation.

    Each time ``asyncio.create_subprocess_exec`` is called, a future that
    resolves to a ``MockSubprocess`` object will be returned.

    """

    factory = MockSubprocessFactory()

    @functools.wraps(asyncio.create_subprocess_exec)
    def create_subprocess_exec(*args, **kwds):
        p = MockSubprocess(args, kwds)
        f = asyncio.Future()
        f.set_result(p)
        factory._instances.append(p)
        return f

    with patch('asyncio.create_subprocess_exec') as spawn:
        spawn.side_effect = create_subprocess_exec
        yield factory
