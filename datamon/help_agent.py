"""Grounded in-app help agent for the operator dashboard.

This is NOT a live language model. It answers questions about DataMon's UI from a
fixed, authored knowledge base, so it needs no API key, makes no network call,
cannot leak a secret, and cannot invent an answer that the code does not support.
A judge can click a pre-written question or type a free-form one; a lightweight
keyword score picks the closest entry, and anything with no good match returns an
honest "I can't answer that" plus the topics it does cover.

Every answer here is written to match what the dashboard and ``datamon`` modules
actually do. If a feature changes, update the matching entry.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

_STOPWORDS = {
    "the", "a", "an", "is", "are", "do", "does", "how", "what", "why", "when",
    "where", "which", "to", "of", "in", "on", "for", "and", "or", "i", "you",
    "it", "this", "that", "can", "my", "me", "with", "about", "if",
}


@dataclass(frozen=True)
class QA:
    question: str          # the pre-written question shown as a clickable prompt
    answer: str            # the authored, grounded answer
    keywords: tuple = field(default_factory=tuple)  # extra match terms


KNOWLEDGE_BASE: List[QA] = [
    QA(
        "What is DataMon?",
        "DataMon is a pre-training quality gate for robot demonstration data. It "
        "scores each recording, explains the score, and routes it to clean, "
        "review, or quarantine — so bad data is caught before it ever reaches "
        "model training.",
        ("overview", "purpose", "what", "datamon", "do"),
    ),
    QA(
        "How does the ingest gate decide accept, review, or reject?",
        "Each episode gets a 0–100 score. At or above the accept line it's "
        "accepted; below the reject line it's rejected; in between it's held for "
        "review. Hard integrity failures — dropped frames, non-finite values, "
        "missing or gibberish labels, or fewer than five frames — are quarantined "
        "regardless of score.",
        ("gate", "accept", "reject", "review", "score", "bands", "decide", "quarantine"),
    ),
    QA(
        "What do the quality band sliders do?",
        "They set the two pass marks. The left value is the reject line; the right "
        "value is the accept line. Anything scoring between them goes to the "
        "review queue for a human to decide. The reject line can't be higher than "
        "the accept line.",
        ("slider", "bands", "threshold", "pass", "mark", "quality"),
    ),
    QA(
        "How do I use the review queue?",
        "Open the Review queue tab. Each held episode shows its score and reasons. "
        "Promote a good one to clean, reject a bad one to quarantine, or request "
        "recollection to keep it in review and flag that it should be recorded "
        "again. Every action is appended to the audit trail.",
        ("review", "queue", "promote", "reject", "recollect", "operator", "approve"),
    ),
    QA(
        "What is a robot profile?",
        "A saved set of a rig's settings — expected capture rate, channel ranges, "
        "allowed-static channels, and task family. Save it once in the Robot "
        "profile expander, then reapply it in one click instead of retyping the "
        "thresholds for each collection.",
        ("profile", "robot", "rig", "settings", "save", "channel", "fps"),
    ),
    QA(
        "What does the anomaly score mean?",
        "It's an empirical upper-tail rank: how unusual an episode looks compared "
        "to clean reference episodes, from 0 to 1. Higher means more atypical. It "
        "is a rank, NOT a probability that the demonstration is bad — treat it as "
        "a lead to investigate, not a verdict.",
        ("anomaly", "score", "rank", "unusual", "probability"),
    ),
    QA(
        "How do I upload a recording?",
        "On the Ingest gate tab, use the upload panel. Add a task description if "
        "the file doesn't carry one, choose a parquet file (up to the 50 MB demo "
        "limit), preview the gate's decision, then press Process to store the "
        "exact evaluated episode.",
        ("upload", "parquet", "file", "ingest", "import"),
    ),
    QA(
        "What is the audit trail?",
        "A durable log of every routing decision, keyed by the episode's content "
        "ID. It records who chose what and when, and it's never overwritten — so "
        "you can always answer why a given recording was accepted, rejected, or "
        "sent back.",
        ("audit", "history", "trail", "log", "manifest", "decision"),
    ),
    QA(
        "What data sources are available?",
        "The demo ships with bounded, checksum-verified slices of two real public "
        "robot datasets: DROID-100 and BridgeData V2. Pick the source in the "
        "sidebar. No videos are downloaded and the total is only a few megabytes.",
        ("data", "source", "dataset", "droid", "bridge", "bridgedata"),
    ),
    QA(
        "Is this safe to put on the public internet?",
        "No — it's a trusted-file local demo. The login is demo-grade, not "
        "production SSO, and there's no TLS or real user database. See SECURITY.md "
        "before exposing it on a network; it lists the controls a real deployment "
        "would need.",
        ("safe", "security", "public", "deploy", "internet", "login", "secure"),
    ),
    QA(
        "How do I take the guided tour?",
        "In the sidebar, click 'Start guided tour'. It walks the whole interface "
        "step by step with on-screen captions, a pointing arrow, and narration "
        "audio. Turn on 'Reduce motion' first if you'd rather the arrow didn't "
        "animate.",
        ("tour", "tutorial", "walkthrough", "guide", "narration", "help"),
    ),
]


def _tokens(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 1]


def _score(query_tokens: List[str], qa: QA) -> int:
    haystack = set(_tokens(qa.question)) | {k.lower() for k in qa.keywords}
    return sum(1 for token in query_tokens if token in haystack)


def suggested_questions() -> List[str]:
    """The pre-written questions to show as clickable prompts."""
    return [qa.question for qa in KNOWLEDGE_BASE]


def answer(query: str) -> str:
    """Return the grounded answer best matching a free-form or clicked question."""
    query = (query or "").strip()
    if not query:
        return (
            "Ask me about the gate, the review queue, robot profiles, the anomaly "
            "score, uploading data, the audit trail, security, or the guided tour."
        )

    # An exact match on a pre-written question always wins.
    for qa in KNOWLEDGE_BASE:
        if query.lower() == qa.question.lower():
            return qa.answer

    query_tokens = _tokens(query)
    best: Optional[QA] = None
    best_score = 0
    for qa in KNOWLEDGE_BASE:
        score = _score(query_tokens, qa)
        if score > best_score:
            best, best_score = qa, score

    if best is None or best_score == 0:
        topics = ", ".join(
            q.question.rstrip("?").lower() for q in KNOWLEDGE_BASE[:5]
        )
        return (
            "I can only answer questions about DataMon's interface, and I don't "
            f"have a grounded answer for that. Try asking about: {topics}, and more."
        )
    return best.answer
