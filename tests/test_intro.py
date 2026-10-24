"""Tests for the post-login intro loader and login input hygiene."""

from __future__ import annotations

from datamon import intro
from datamon.auth import verify_password
from datamon.intro import LOADING_SECONDS, loading_html


def test_loading_html_contains_welcome_and_robot():
    html = loading_html(LOADING_SECONDS)
    assert "Welcome to" in html and "DataMon" in html
    assert "datamon-robot" in html
    assert "datamon-fill" in html


def test_loading_html_respects_custom_duration():
    assert "3s" in loading_html(3)


def test_loading_html_is_a_full_document():
    # It runs in an iframe, so it must be a standalone HTML document.
    assert "<html" in loading_html().lower()


def test_popin_js_reaches_parent_document():
    assert "window.parent.document" in intro._POPIN_JS
    assert "datamonPopin" in intro._POPIN_JS


def test_login_tolerates_surrounding_spaces_after_strip():
    assert verify_password("judge".strip(), " Hello World! ".strip()) == "judge"
    assert verify_password(" programmer ".strip(), " 101010 ".strip()) == "programmer"


def test_reduced_motion_block_present():
    assert "prefers-reduced-motion" in loading_html()
