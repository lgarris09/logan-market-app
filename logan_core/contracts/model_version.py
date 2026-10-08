"""ADR-081 -- one name for the evidence model in force.

Bump this string in the same change as anything that alters what an
observation qualifies as, how evidence strength is derived, or how a
revision is classified. It is recorded with every notification candidate
and every feedback report so a decision can be read against the rules that
produced it, and so a change in those rules is never mistaken for a change
in the market.

It is a label, not a switch: nothing branches on its value.
"""

EVIDENCE_MODEL_VERSION = "beta1.0"
