# -*- coding: utf-8 -*-

import asyncio
import datetime
import pytest
import sys

from collections import deque
from contextlib import contextmanager
from random import randint
from strawboss import run_once, run_and_respawn, now
from unittest.mock import patch

from .conftest import capture_stdout


@pytest.mark.asyncio
def test_run_once(event_loop, clock, subprocess_factory):
    with capture_stdout() as capture:
        # Start the process.
        s = asyncio.Future()
        sys.stderr.write('scheduling.\n')
        t = event_loop.create_task(run_once(
            'worker.0', 'work', None,
            shutdown=s, loop=event_loop,
        ))
        sys.stderr.write('blocking on 1st line.\n')
        line = yield from capture.readline()
        line = line.decode('utf-8').rstrip()
        p = subprocess_factory.last_instance
        assert line == '%s [strawboss] worker.0(%d) spawned.' % (
            now().isoformat(), p.pid,
        )
        # Grab some output from the process.
        p.stdout.feed_data(b'stuff.\n')
        sys.stderr.write('blocking on 2nd line.\n')
        line = yield from capture.readline()
        line = line.decode('utf-8').rstrip()
        assert line == '%s [worker.0] stuff.' % (
            now().isoformat(),
        )
        # Trigger EOF from the process.
        p.stdout.feed_eof()
        sys.stderr.write('blocking on 3rd line.\n')
        line = yield from capture.readline()
        line = line.decode('utf-8').rstrip()
        assert line == '%s [strawboss] EOF from worker.0(%d).' % (
            now().isoformat(), p.pid,
        )
        # Wait until the process completes.
        p.mock_complete(1)
        sys.stderr.write('blocking on 4th line.\n')
        line = yield from capture.readline()
        line = line.decode('utf-8').rstrip()
        assert line == '%s [strawboss] worker.0(%d) completed with exit status %d.' % (
            now().isoformat(), p.pid, 1,
        )
        # Check that we got the exit status.
        status = yield from t
        assert status == 1


@pytest.mark.asyncio
def test_run_once_shutdown(event_loop, clock, subprocess_factory):
    with capture_stdout() as capture:
        # Start the process.
        s = asyncio.Future()
        t = event_loop.create_task(run_once(
            'worker.0', 'work', None,
            shutdown=s, loop=event_loop,
        ))
        line = yield from capture.readline()
        line = line.decode('utf-8').rstrip()
        p = subprocess_factory.last_instance
        assert line == '%s [strawboss] worker.0(%d) spawned.' % (
            now().isoformat(), p.pid,
        )
        # Kill the process early.
        s.set_result(None)
        line = yield from capture.readline()
        line = line.decode('utf-8').rstrip()
        assert line == '%s [strawboss] worker.0(%d) killed.' % (
            now().isoformat(), p.pid,
        )
        # Wait for the process to complete.
        line = yield from capture.readline()
        line = line.decode('utf-8').rstrip()
        assert line == '%s [strawboss] worker.0(%d) completed with exit status %d.' % (
            now().isoformat(), p.pid, -9,
        )
        # Check that we got the exit status.
        status = yield from t
        assert status == -9


@pytest.mark.asyncio
def test_run_once_shutdown_already_complete(event_loop, clock,
                                            subprocess_factory):
    with capture_stdout() as capture:
        # Start the process.
        s = asyncio.Future()
        t = event_loop.create_task(run_once(
            'worker.0', 'work', None,
            shutdown=s, loop=event_loop,
        ))
        line = yield from capture.readline()
        line = line.decode('utf-8').rstrip()
        p = subprocess_factory.last_instance
        assert line == '%s [strawboss] worker.0(%d) spawned.' % (
            now().isoformat(), p.pid,
        )
        # Request cancellation when the process is already completed.
        p.mock_complete(0)
        s.set_result(None)
        line = yield from capture.readline()
        line = line.decode('utf-8').rstrip()
        assert line == '%s [strawboss] worker.0(%d) completed with exit status %d.' % (
            now().isoformat(), p.pid, 0,
        )
        # Check that we got the exit status.
        status = yield from t
        assert status == 0



@pytest.mark.asyncio
def test_run_and_respawn(event_loop, clock, subprocess_factory):
    with capture_stdout() as capture:
        # Start the process.
        s = asyncio.Future()
        t = event_loop.create_task(run_and_respawn(
            name='worker.0',
            cmd='work',
            env=None,
            shutdown=s,
            loop=event_loop,
        ))
        line = yield from capture.readline()
        line = line.decode('utf-8').rstrip()
        p1 = subprocess_factory.last_instance
        assert line == '%s [strawboss] worker.0(%d) spawned.' % (
            now().isoformat(), p1.pid,
        )
        # Wait for the process to complete.
        #
        # Since we haven't signaled the shutdown event, the worker will be
        # respawned.
        p1.mock_complete(0)
        line = yield from capture.readline()
        line = line.decode('utf-8').rstrip()
        assert line == '%s [strawboss] worker.0(%d) completed with exit status %d.' % (
            now().isoformat(), p1.pid, 0,
        )
        sys.stderr.write('blocking on 1st line.\n')
        line = yield from capture.readline()
        line = line.decode('utf-8').rstrip()
        p2 = subprocess_factory.last_instance
        assert line == '%s [strawboss] worker.0(%d) spawned.' % (
            now().isoformat(), p2.pid,
        )
        # Request shutdown.
        s.set_result(None)
        line = yield from capture.readline()
        line = line.decode('utf-8').rstrip()
        assert line == '%s [strawboss] worker.0(%d) killed.' % (
            now().isoformat(), p2.pid,
        )
        # Wait for the process to complete.
        p2.mock_complete(-9)
        line = yield from capture.readline()
        line = line.decode('utf-8').rstrip()
        assert line == '%s [strawboss] worker.0(%d) completed with exit status %d.' % (
            now().isoformat(), p2.pid, -9,
        )
