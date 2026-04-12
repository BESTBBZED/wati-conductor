"""Staff roster used for default ticket assignment."""

import random

STAFF_MEMBERS = [
    "Sam",
    "Alice",
    "Bob",
    "Charlie",
    "Diana",
    "Emma",
    "Frank",
    "Grace",
]


def get_random_staff() -> str:
    """Pick a random staff member for ticket assignment."""
    return random.choice(STAFF_MEMBERS)
