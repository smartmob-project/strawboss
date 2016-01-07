# -*- coding: utf-8 -*-

import pytest

from strawboss import cli, version

#def test_version(capture):
#    with capture:
#        with pytest.raises(SystemExit) as error:
#            cli.parse_args(['--version'])
#        assert error.value.args[0] == 0
#    capture.compare(version)

def test_envfile():
    arguments = cli.parse_args([])
    assert arguments.envfiles == ['.env']

    arguments = cli.parse_args(['--envfile', 'sample.env'])
    assert arguments.envfiles == ['sample.env']

    arguments = cli.parse_args([
        '--envfile', 'sample.env',
        '--envfile', 'more.env',
    ])
    assert arguments.envfiles == ['sample.env', 'more.env']

def test_no_env():
    arguments = cli.parse_args([])
    assert arguments.use_env

    arguments = cli.parse_args(['--no-env'])
    assert not arguments.use_env

def test_procfile():
    arguments = cli.parse_args([])
    assert arguments.procfile == 'Procfile'

    arguments = cli.parse_args(['--procfile', 'Procfile.txt'])
    assert arguments.procfile == 'Procfile.txt'

def test_scale():
    arguments = cli.parse_args([])
    assert arguments.scale == [('*', 1)]

    arguments = cli.parse_args(['--scale', 'web:2'])
    assert arguments.scale == [('*', 1), ('web', 2)]

    arguments = cli.parse_args(['--scale', 'web:2', '--scale', 'worker:3'])
    assert arguments.scale == [('*', 1), ('web', 2), ('worker', 3)]
