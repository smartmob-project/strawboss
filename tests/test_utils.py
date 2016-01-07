# -*- coding: utf-8 -*-

import pytest

from strawboss import parse_scale, merge_envs, now

def test_scale():
    assert parse_scale('foo:2') == ('foo', 2)

def test_scale_invlid():
    with pytest.raises(ValueError) as exc:
        print(parse_scale('foo:bar'))
    assert str(exc.value) == 'Invalid scale "foo:bar".'

def test_merge_envs_0_dicts():
    assert merge_envs() == {}

def test_merge_envs_1_dict():
    assert merge_envs({}) == {}
    assert merge_envs({'foo': 'bar'}) == {'foo': 'bar'}
    assert merge_envs({'foo': 'bar', 'meh': 'qux'}) == {
        'foo': 'bar',
        'meh': 'qux',
    }

def test_now():
    assert now().tzinfo is None
    assert now(utc=True).tzinfo is not None
