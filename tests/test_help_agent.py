"""Tests for the grounded in-app help agent."""

from __future__ import annotations

from datamon.help_agent import (
    KNOWLEDGE_BASE,
    answer,
    suggested_questions,
)


def test_exact_question_returns_its_answer():
    qa = KNOWLEDGE_BASE[0]
    assert answer(qa.question) == qa.answer


def test_keyword_match_finds_gate_answer():
    reply = answer("how do accept and reject thresholds work?")
    assert "accept" in reply.lower() and "reject" in reply.lower()


def test_keyword_match_finds_review_queue():
    reply = answer("how do I promote an episode?")
    assert "promote" in reply.lower()


def test_anomaly_answer_keeps_honest_framing():
    reply = answer("what is the anomaly score")
    assert "rank" in reply.lower()
    assert "not a probability" in reply.lower()


def test_unknown_question_returns_honest_fallback():
    reply = answer("what's the weather in Boston tomorrow?")
    assert "don't have a grounded answer" in reply.lower()


def test_empty_question_offers_topics():
    reply = answer("")
    assert "ask me about" in reply.lower()


def test_suggested_questions_match_knowledge_base():
    assert suggested_questions() == [qa.question for qa in KNOWLEDGE_BASE]
    assert len(suggested_questions()) >= 8


def test_security_answer_is_honest_about_demo_grade():
    reply = answer("is this secure enough for the public internet?")
    assert "demo" in reply.lower()
    assert "security.md" in reply.lower()
