"""Tests for the shared branding helpers and artwork."""

from __future__ import annotations

import base64

from datamon.art import CAR_SVG, MASCOT_SVG, mascot_img, svg_data_uri
from datamon.branding import (
    PRIMARY,
    brand_header_html,
    clock_html,
    inject_global_css,
    login_hero_html,
    render_brand_header,
)


class _FakeSt:
    def __init__(self):
        self.markdown_calls = []
        self.html_calls = []

    def markdown(self, body, unsafe_allow_html=False):
        self.markdown_calls.append((body, unsafe_allow_html))

    def html(self, body, unsafe_allow_javascript=False):
        self.html_calls.append((body, unsafe_allow_javascript))


def test_inject_global_css_emits_style_with_primary():
    fake = _FakeSt()
    inject_global_css(fake)
    body, unsafe = fake.markdown_calls[0]
    assert unsafe is True
    assert "<style>" in body
    assert PRIMARY in body


def test_global_css_keeps_the_sidebar_arrow():
    fake = _FakeSt()
    inject_global_css(fake)
    body = fake.markdown_calls[0][0]
    assert "stExpandSidebarButton" in body
    assert 'div[data-testid="stToolbar"],' not in body  # never hide the toolbar


def test_brand_header_shows_wordmark_and_mascot():
    fake = _FakeSt()
    render_brand_header(fake)
    body, allow_js = fake.html_calls[0]
    assert allow_js is False  # no clock, no script needed
    assert "Data<span>Mon</span>" in body
    assert "data:image/svg+xml;base64," in body


def test_dashboard_header_includes_the_running_clock():
    fake = _FakeSt()
    render_brand_header(fake, clock=True)
    body, allow_js = fake.html_calls[0]
    assert allow_js is True
    assert "dm-clock" in body and "setInterval" in body


def test_clock_marks_hours_in_binary():
    html = clock_html()
    for hour in range(1, 13):
        assert f">{hour:b}</span>" in html


def test_header_without_clock_has_no_script():
    assert "<script" not in brand_header_html(clock=False)


def test_login_hero_is_branded_and_script_free():
    html = login_hero_html()
    assert "Data<span>Mon</span>" in html
    assert "ROBOTICS &amp; HARDWARE" in html
    assert "<script" not in html


def test_svg_artwork_round_trips_through_data_uri():
    for svg in (MASCOT_SVG, CAR_SVG):
        uri = svg_data_uri(svg)
        decoded = base64.b64decode(uri.split(",", 1)[1]).decode("utf-8")
        assert decoded == svg
        assert "<script" not in svg
        assert "prefers-reduced-motion" in svg


def test_mascot_img_has_alt_text():
    assert 'alt="DataMon robot holding a shield"' in mascot_img(64)
