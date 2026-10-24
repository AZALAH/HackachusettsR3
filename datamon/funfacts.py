"""Loading-screen cards: robotics jokes, fun facts, and DataMon tips.

Shown under the loader's progress bar, video-game style. Facts are kept to
well-documented history so nothing on screen is made up; dataset sizes are
stated loosely ("about", "over") rather than to the last episode.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional

JOKE = "ROBOT JOKE"
FACT = "FUN FACT"
TIP = "PRO TIP"


@dataclass(frozen=True)
class Card:
    label: str
    text: str


CARDS: List[Card] = [
    # Jokes
    Card(JOKE, "Why did the robot go on vacation? It needed to recharge its batteries."),
    Card(JOKE, "A robot walks into a bar and orders something to loosen up. "
               "The bartender hands it a screwdriver."),
    Card(JOKE, "There are 10 kinds of robots: those that understand binary, "
               "and those that don't."),
    Card(JOKE, "My robot kept dropping frames, so I told it to get a grip."),
    Card(JOKE, "Why are robot arms so calm under pressure? Nerves of steel."),
    Card(JOKE, "What's a robot's favourite music? Heavy metal, played on a loop."),
    Card(JOKE, "Garbage in, garbage out. Except here, the garbage learns to "
               "drive a robot arm."),
    Card(JOKE, "A robot's least favourite chore is labelling data. "
               "Same as everyone else's."),
    Card(JOKE, "I told my robot a UDP joke. I'm not sure it got it, "
               "and it didn't care."),
    # Facts
    Card(FACT, "\u201cRobot\u201d comes from the Czech word robota, meaning forced "
               "labour. It first appeared in Karel \u010capek's 1920 play R.U.R."),
    Card(FACT, "Isaac Asimov coined the word \u201crobotics\u201d in his 1941 short "
               "story \u201cLiar!\u201d."),
    Card(FACT, "The first industrial robot, Unimate, went to work on a General "
               "Motors assembly line in 1961."),
    Card(FACT, "Shakey, built at SRI from 1966, was the first mobile robot that "
               "could reason about its own actions."),
    Card(FACT, "A radio signal takes between about 3 and 22 minutes to reach Mars, "
               "so rovers can't be joysticked from Earth. They drive partly on "
               "their own."),
    Card(FACT, "DROID, one of the datasets in this demo, holds about 76,000 robot "
               "demonstrations recorded in hundreds of real scenes."),
    Card(FACT, "BridgeData V2, the other dataset here, has over 60,000 robot "
               "demonstrations across dozens of environments."),
    # Tips
    Card(TIP, "Not sure about a recording? The Review queue lets a human make "
              "the call, and every decision is logged."),
    Card(TIP, "New here? Press \u201cStart guided tour\u201d in the sidebar for a "
              "narrated walkthrough."),
    Card(TIP, "Collapsed the sidebar? Click the glowing teal arrow in the "
              "top-left to bring it back."),
    Card(TIP, "Save your robot's settings as a profile and reload them in one "
              "click next session."),
]


def pick_cards(count: int, rng: Optional[random.Random] = None) -> List[Card]:
    """Pick ``count`` distinct cards, always mixing at least one joke and fact."""
    rng = rng or random.Random()
    jokes = [card for card in CARDS if card.label == JOKE]
    facts = [card for card in CARDS if card.label == FACT]
    chosen = [rng.choice(jokes), rng.choice(facts)][:max(0, count)]
    rest = [card for card in CARDS if card not in chosen]
    rng.shuffle(rest)
    chosen.extend(rest[: max(0, count - len(chosen))])
    rng.shuffle(chosen)
    return chosen
