"""Hand-computed ground truth test cases for metric validation.

Each test case specifies:
- before/after token sequences
- Expected metric values (computed by hand)
- Tolerance for floating-point comparison
- Explanatory notes

These test cases form the acceptance criteria for Milestone 1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class MetricTestCase:
    """Single test case for metric validation.

    Attributes:
        name: Unique test case identifier
        before: Original token sequence (as integer IDs)
        after: Transformed token sequence
        expected: Dict mapping metric_id to expected value
        tolerance: Acceptable floating-point error (default 1e-6)
        notes: Human-readable explanation
    """

    name: str
    before: Sequence[int]
    after: Sequence[int]
    expected: dict[str, float]
    tolerance: float = 1e-6
    notes: str = ""


# Test Case 1: Transposition
# [a,b,c] → [a,c,b] (one adjacent swap)
CASE_TRANSPOSITION = MetricTestCase(
    name="transposition",
    before=[0, 1, 2],
    after=[0, 2, 1],
    expected={
        # Edit & overlap metrics
        "ned.value": 1 / 3,  # One transposition, normalized by max(3,3)
        "lcsr.value": 2 / 3,  # LCS length 2, original length 3
        "pmr.value": 2 / 3,  # LCS-based alignment: 2 out of 3 match
        "jsdset.value": 0.0,  # Same set {0,1,2}
        "jsdbag.value": 0.0,  # Same multiset counts
        # Distributional metrics
        "cosdist": 0.0,  # Same frequency vector [1,1,1]
        "jsdiv": 0.0,  # Identical distributions
        "h_delta": 0.0,  # Same entropy (uniform)
        # Structural metrics
        "rord.value": 0.0,  # LCS tokens [0,1] or [0,2] both preserve order
        # Length metrics
        "lr.ratio": 1.0,  # Length ratio 3/3
        "lr_delta": 0.0,  # |1 - 3/3|
    },
    notes="Single transposition: [a,b,c] → [a,c,b]. RORD=0 because LCS preserves order.",
)

# Test Case 2: Identity
# [a,a,a] → [a,a,a] (no change)
CASE_IDENTITY = MetricTestCase(
    name="identity",
    before=[0, 0, 0],
    after=[0, 0, 0],
    expected={
        "ned.value": 0.0,
        "lcsr.value": 1.0,
        "pmr.value": 1.0,
        "jsdset.value": 0.0,
        "jsdbag.value": 0.0,
        "cosdist": 0.0,
        "jsdiv": 0.0,
        "h_delta": 0.0,
        "rord.value": 0.0,
        "lr.ratio": 1.0,
        "lr_delta": 0.0,
    },
    notes="Identity sequence (no change)",
)

# Test Case 3: Single Insertion
# [a,b,c] → [a,b,c,d] (one token added at end)
CASE_INSERTION = MetricTestCase(
    name="insertion",
    before=[0, 1, 2],
    after=[0, 1, 2, 3],
    expected={
        "ned.value": 1 / 4,  # One insertion, normalized by max(3,4)=4
        "lcsr.value": 1.0,  # LCS=3 (entire original), 3/3=1
        "pmr.value": 1.0,  # All original positions match (with LCS alignment)
        "jsdset.value": 1 / 4,  # |{0,1,2} ∪ {0,1,2,3}| = 4, intersection=3; dist=1-3/4
        "jsdbag.value": 1 / 4,  # min_sum=3, max_sum=4; dist=1-3/4
        "lr.ratio": 4 / 3,  # Length ratio 4/3
        "lr_delta": 1 / 3,  # |1 - 4/3|
        # Note: Other metrics would need actual computation
        # For now, we'll test core metrics only
    },
    notes="Single insertion at end: [a,b,c] → [a,b,c,d]",
)

# Test Case 4: Single Deletion
# [a,b,c,d] → [a,b,c] (one token removed)
CASE_DELETION = MetricTestCase(
    name="deletion",
    before=[0, 1, 2, 3],
    after=[0, 1, 2],
    expected={
        "ned.value": 1 / 4,  # One deletion, normalized by max(4,3)=4
        "lcsr.value": 3 / 4,  # LCS=3, original length=4
        "pmr.value": 3 / 4,  # 3 out of 4 positions match
        "lr.ratio": 3 / 4,  # Length ratio 3/4
        "lr_delta": 1 / 4,  # |1 - 3/4|
    },
    notes="Single deletion at end: [a,b,c,d] → [a,b,c]",
)

# Test Case 5: Single Substitution
# [a,b,c] → [a,x,c] (middle token replaced)
CASE_SUBSTITUTION = MetricTestCase(
    name="substitution",
    before=[0, 1, 2],
    after=[0, 9, 2],
    expected={
        "ned.value": 1 / 3,  # One substitution, normalized by max(3,3)
        "lcsr.value": 2 / 3,  # LCS=2 ([0,2]), original=3
        "pmr.value": 2 / 3,  # 2 out of 3 match (positions 0 and 2)
        "lr.ratio": 1.0,  # Same length
        "lr_delta": 0.0,
    },
    notes="Single substitution: [a,b,c] → [a,x,c]",
)

# Test Case 6: Complete Reversal
# [a,b,c,d] → [d,c,b,a] (perfect reversal)
CASE_REVERSAL = MetricTestCase(
    name="reversal",
    before=[0, 1, 2, 3],
    after=[3, 2, 1, 0],
    expected={
        "ned.value": 2 / 4,  # 2 operations (depends on DL implementation)
        "lcsr.value": 1 / 4,  # LCS=1 (any single token)
        "pmr.value": 0.0,  # No positional matches
        "jsdset.value": 0.0,  # Same set
        "jsdbag.value": 0.0,  # Same counts
        "rord.value": 1.0,  # All C(4,2)=6 pairs inverted
        "lr.ratio": 1.0,  # Same length
        "lr_delta": 0.0,
    },
    notes="Complete reversal: [a,b,c,d] → [d,c,b,a]",
)

# Test Case 7: Empty Sequences
# [] → [] (both empty)
CASE_EMPTY_IDENTITY = MetricTestCase(
    name="empty_identity",
    before=[],
    after=[],
    expected={
        "ned.value": 0.0,  # By convention
        "lr.ratio": 1.0,  # Define 0/0 as 1.0
        "lr_delta": 0.0,
    },
    tolerance=1e-6,
    notes="Empty sequences (identity)",
)

# Test Case 8: One Empty
# [] → [a] (insertion from nothing)
CASE_EMPTY_TO_SINGLE = MetricTestCase(
    name="empty_to_single",
    before=[],
    after=[0],
    expected={
        "ned.value": 1.0,  # One insertion, normalized by max(0,1)=1
        "lcsr.value": 0.0,  # Define as 0 when before is empty
        "pmr.value": 0.0,  # No matches possible
    },
    notes="Empty → single token",
)

# Test Case 9: Single Token Identity
# [a] → [a] (single token, no change)
CASE_SINGLE_IDENTITY = MetricTestCase(
    name="single_identity",
    before=[5],
    after=[5],
    expected={
        "ned.value": 0.0,
        "lcsr.value": 1.0,
        "pmr.value": 1.0,
        "lr.ratio": 1.0,
        "lr_delta": 0.0,
    },
    notes="Single token identity",
)

# Test Case 10: Zero Overlap
# [a,b,c] → [x,y,z] (complete substitution)
CASE_ZERO_OVERLAP = MetricTestCase(
    name="zero_overlap",
    before=[0, 1, 2],
    after=[9, 10, 11],
    expected={
        "ned.value": 1.0,  # Three substitutions, normalized by 3
        "lcsr.value": 0.0,  # LCS=0
        "pmr.value": 0.0,  # No matches
        "jsdset.value": 1.0,  # No set overlap; dist=1.0
        "jsdbag.value": 1.0,  # No bag overlap
        "lr.ratio": 1.0,  # Same length
        "lr_delta": 0.0,
    },
    notes="Zero vocabulary overlap: [a,b,c] → [x,y,z]",
)

# Collection of all test cases
TOY_SEQUENCES = [
    CASE_TRANSPOSITION,
    CASE_IDENTITY,
    CASE_INSERTION,
    CASE_DELETION,
    CASE_SUBSTITUTION,
    CASE_REVERSAL,
    CASE_EMPTY_IDENTITY,
    CASE_EMPTY_TO_SINGLE,
    CASE_SINGLE_IDENTITY,
    CASE_ZERO_OVERLAP,
]


__all__ = [
    "MetricTestCase",
    "TOY_SEQUENCES",
    "CASE_TRANSPOSITION",
    "CASE_IDENTITY",
    "CASE_INSERTION",
    "CASE_DELETION",
    "CASE_SUBSTITUTION",
    "CASE_REVERSAL",
    "CASE_EMPTY_IDENTITY",
    "CASE_EMPTY_TO_SINGLE",
    "CASE_SINGLE_IDENTITY",
    "CASE_ZERO_OVERLAP",
]
