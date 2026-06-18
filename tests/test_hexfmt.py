"""Tests for hex/ASCII parsing and formatting."""

import pytest

from fae_toolkit.core.hexfmt import parse_hex, to_ascii, to_hex


def test_parse_spaced():
    assert parse_hex("01 03 00 0A") == bytes([1, 3, 0, 10])


def test_parse_contiguous():
    assert parse_hex("0103000A") == bytes([1, 3, 0, 10])


def test_parse_with_prefixes_and_commas():
    assert parse_hex("0x01, 0x03, 0xFF") == bytes([1, 3, 255])


def test_parse_empty():
    assert parse_hex("   ") == b""


def test_parse_odd_contiguous_raises():
    with pytest.raises(ValueError):
        parse_hex("010")


def test_parse_bad_token_raises():
    with pytest.raises(ValueError):
        parse_hex("01 ZZ")


def test_to_hex_and_ascii():
    assert to_hex(bytes([1, 3, 10])) == "01 03 0A"
    assert to_ascii(b"AB\x00\xff") == "AB.."
