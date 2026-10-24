"""Tests for the shared branding helpers."""

from __future__ import annotations

from datamon.branding import (
    PRIMARY,
    inject_global_css,
    render_brand_header,
)


class _FakeSt:
    def __init__(self):
        self.markdown_calls = []

    def markdown(self, body, unsafe_allow_html=False):
        self.markdown_calls.append((body, unsafe_allow_html))


def test_inject_global_css_emits_style_with_primary():
    fake = _FakeSt()
    inject_global_css(fake)
    assert len(fake.markdown_calls) == 1
    body, unsafe = fake.markdown_calls[0]
    assert unsafe is True
    assert "<style>" in body
    assert PRIMARY in body


def test_brand_header_shows_wordmark():
    fake = _FakeSt()
    render_brand_header(fake)
    body, unsafe = fake.markdown_calls[0]
    assert unsafe is True
    assert "DataMon".replace("Mon", "") in body  # "Data" prefix present
    assert "Mon" in body
