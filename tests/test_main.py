# -*- coding: utf-8 -*-

import asyncio
import os
import signal
import pytest

from unittest import mock
from strawboss import main

@mock.patch('dotenvfile.loadfile')
def test_main_procfile_not_found(load_dotenvfile,
                                 subprocess_factory, capfd, event_loop):
    loop = asyncio.get_event_loop()
    # Run the main function.
    with pytest.raises(SystemExit) as exc:
        main(['--procfile', './does-not-exist', '--no-env'])
    assert int(str(exc.value)) == 2
    # Since the Procfile does not exist, we get an error.
    _, stderr = capfd.readouterr()
    assert stderr.strip() == 'Procfile not found at "./does-not-exist".'

@mock.patch('dotenvfile.loadfile')
@mock.patch('procfile.loadfile')
def test_main_procfile_empty(load_procfile, load_dotenvfile,
                             subprocess_factory, capfd, event_loop):
    loop = asyncio.get_event_loop()
    load_procfile.return_value = {}
    # Run the main function.
    with pytest.raises(SystemExit) as exc:
        main(['--no-env'])
    assert int(str(exc.value)) == 2
    # Since the Procfile is empty, we get an error.
    _, stderr = capfd.readouterr()
    assert stderr.strip() == 'Nothing to run.'

@mock.patch('dotenvfile.loadfile')
@mock.patch('procfile.loadfile')
def test_main(load_procfile, load_dotenvfile, subprocess_factory, capfd, event_loop):
    loop = asyncio.get_event_loop()
    load_procfile.return_value = {
        'foo': {
            'cmd': 'false',
            'env': {},
        },
    }
    # Automatically trigger CTRL-C a short while from now.
    loop.call_later(1.0, os.kill, os.getpid(), signal.SIGINT)
    # Run the main function!
    main(['--no-env'])
    stdout, stderr = capfd.readouterr()
    # Error log should be empty.
    assert stderr.strip() == ''
    # Output log should contain start & stop info for each subprocess.
    #
    # NOTE: we strip timestamps from the logs since they don't matter here.
    lines = stdout.strip().split('\n')
    lines = [line.split(' ', 1)[1] for line in lines]
    expected_lines = []
    for p in subprocess_factory.instances:
        expected_lines.extend([
            '[strawboss] foo.0(%d) spawned.' % p.pid,
            '[strawboss] foo.0(%d) killed.' % p.pid,
            '[strawboss] foo.0(%d) completed with exit status -9.' % p.pid,
        ])
    assert len(subprocess_factory.instances) > 0
    assert set(lines) == set(expected_lines)
