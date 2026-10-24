"""Tests for the post-login loader, the reveal script, and login input hygiene."""

from __future__ import annotations

import random

from datamon import intro
from datamon.auth import verify_password
from datamon.funfacts import CARDS, FACT, JOKE, Card, pick_cards


def test_loading_seconds_is_reasonable():
    assert 1 <= intro.LOADING_SECONDS <= 30


def test_loader_html_has_bar_robot_cards_and_timing():
    html = intro.loader_html(9, cards=[Card(JOKE, "beep </script> boop")])
    assert "Welcome to Data" in html
    assert "dm-l-fill" in html and "dm-l-car" in html
    assert "data:image/svg+xml;base64," in html  # mascot + car artwork
    assert "var DURATION = 9000, FADE = 700;" in html
    # Card text is JSON-escaped so it can't close the script tag early.
    assert "beep <\\/script> boop" in html
    assert "prefers-reduced-motion" in html
    assert "__" not in html.replace("__proto__", "")  # every placeholder filled


def test_loader_phases_are_ordered():
    thresholds = [threshold for threshold, _ in intro.LOADER_PHASES]
    assert thresholds == sorted(thresholds) and thresholds[0] == 0


def test_render_loading_runs_warmup_and_survives_its_failure():
    class _FakeSt:
        def __init__(self):
            self.html_calls = []

        def markdown(self, *args, **kwargs):
            pass

        def html(self, body, **kwargs):
            self.html_calls.append(kwargs)

    fake = _FakeSt()
    calls = []

    def warmup():
        calls.append("ran")
        raise RuntimeError("dataset offline")

    intro.render_loading(fake, warmup=warmup, total_seconds=0)
    assert calls == ["ran"]
    assert fake.html_calls == [{"unsafe_allow_javascript": True}]


def test_reveal_token_is_sanitized():
    html = intro.reveal_html('abc"; alert(1); //')
    assert 'token = "abcalert1"' in html
    assert "dm-revealing" in html and "dm-hide-slot" in html


def test_pick_cards_mixes_a_joke_and_a_fact_without_repeats():
    for seed in range(20):
        cards = pick_cards(3, random.Random(seed))
        assert len(cards) == 3 == len(set(cards))
        labels = {card.label for card in cards}
        assert JOKE in labels and FACT in labels


def test_every_card_is_short_enough_to_read_while_loading():
    for card in CARDS:
        assert card.text.strip() and len(card.text) <= 170


def test_login_tolerates_surrounding_spaces_after_strip():
    assert verify_password("judge".strip(), " Hello World! ".strip()) == "judge"
    assert verify_password(" programmer ".strip(), " 101010 ".strip()) == "programmer"
