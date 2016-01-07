# -*- coding: utf-8 -*-

import asyncio
import os
import re
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
    load_procfile.return_value = {
        'foo': {
            'cmd': 'false',
            'env': {},
        },
    }
    # Automatically trigger CTRL-C a short while from now.
    event_loop.call_later(1.0, os.kill, os.getpid(), signal.SIGINT)
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

@mock.patch('dotenvfile.loadfile')
@mock.patch('procfile.loadfile')
def test_main_idempotent_ctrl_c(load_procfile, load_dotenvfile,
                                subprocess_factory, capfd, event_loop):
    load_procfile.return_value = {
        'foo': {
            'cmd': 'false',
            'env': {},
        },
    }
    # Automatically trigger CTRL-C a short while from now.
    #
    # NOTE: intentionally schedule this twice to simulate the case where we get
    #       two CTRL-C events before we can react.
    event_loop.call_later(1.0, os.kill, os.getpid(), signal.SIGINT)
    event_loop.call_later(1.0, os.kill, os.getpid(), signal.SIGINT)
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

@mock.patch('sys.argv', ['strawboss', '--no-env', '--scale=*:2'])
@mock.patch('dotenvfile.loadfile')
@mock.patch('procfile.loadfile')
def test_main_cli(load_procfile, load_dotenvfile,
                  subprocess_factory, capfd, event_loop):
    load_procfile.return_value = {
        'foo': {
            'cmd': 'false',
            'env': {},
        },
    }
    # Automatically trigger CTRL-C a short while from now.
    event_loop.call_later(1.0, os.kill, os.getpid(), signal.SIGINT)
    # Run the main function!
    main()
    stdout, stderr = capfd.readouterr()
    # Error log should be empty.
    assert stderr.strip() == ''
    # Output log should contain start & stop info for each subprocess.
    #
    # NOTE: we strip timestamps and PIDs from the logs since they don't matter
    #       here and it makes comparisons simpler.
    lines = stdout.strip().split('\n')
    lines = [re.sub(r'\(\d+\)', r'(?)', line.split(' ', 1)[1]) for line in lines]
    expected_lines = []
    for i in range(2):
        expected_lines.extend([
            '[strawboss] foo.%d(?) spawned.' % i,
            '[strawboss] foo.%d(?) killed.' % i,
            '[strawboss] foo.%d(?) completed with exit status -9.' % i,
        ])
    print(lines)
    assert len(subprocess_factory.instances) > 0
    assert set(lines) == set(expected_lines)

@mock.patch('dotenvfile.loadfile')
@mock.patch('procfile.loadfile')
def test_main_envfile(load_procfile, load_dotenvfile,
                      subprocess_factory, capfd, event_loop):
    load_procfile.return_value = {
        'foo': {
            'cmd': 'false',
            'env': {
                'ENV1': 'bar',
            },
        },
    }
    load_dotenvfile.return_value = {
        'ENV2': 'meh',
        'ENV3': 'qux',
    }
    # Automatically trigger CTRL-C a short while from now.
    event_loop.call_later(1.0, os.kill, os.getpid(), signal.SIGINT)
    # Run the main function!
    main([])
    stdout, stderr = capfd.readouterr()
    # Error log should be empty.
    assert stderr.strip() == ''
    # Output log should contain start & stop info for each subprocess.
    #
    # NOTE: we strip timestamps and PIDs from the logs since they don't matter
    #       here and it makes comparisons simpler.
    lines = [line.split(' ', 1)[1] for line in stdout.strip().split('\n')]
    expected_lines = []
    for p in subprocess_factory.instances:
        env = {k: p.env[k] for k in ('ENV1', 'ENV2', 'ENV3')}
        assert env == {
            'ENV1': 'bar',
            'ENV2': 'meh',
            'ENV3': 'qux',
        }
        expected_lines.extend([
            '[strawboss] foo.0(%d) spawned.' % p.pid,
            '[strawboss] foo.0(%d) killed.' % p.pid,
            '[strawboss] foo.0(%d) completed with exit status -9.' % p.pid,
        ])
    print(lines)
    assert len(subprocess_factory.instances) > 0
    assert set(lines) == set(expected_lines)
