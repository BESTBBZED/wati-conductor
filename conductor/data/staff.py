"""Staff/employee data for ticket assignment."""

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
    """Get a random staff member name."""
    return random.choice(STAFF_MEMBERS)
