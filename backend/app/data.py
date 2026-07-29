from .models import Opportunity


DEMO_OPPORTUNITIES = [
    Opportunity(
        id="nvda-margin-watch",
        category="stocks",
        title="A watchlist company now matches 91% of your framework",
        summary=(
            "The price pulled back while revenue expectations remained stable. "
            "Free-cash-flow strength and AI infrastructure exposure remain intact."
        ),
        why_it_matters=(
            "You consistently prioritize durable cash generation, long-term demand, "
            "and buying after overreactions."
        ),
        score=91,
        urgency="now",
        change_label="Down 8.4% this week",
        source_label="Market + earnings data",
    ),
    Opportunity(
        id="injury-line-move",
        category="sports",
        title="An injury update moved the line before most casual bettors reacted",
        summary=(
            "The market moved 2.5 points after a late availability update. "
            "The current price is materially different from the opening line."
        ),
        why_it_matters=(
            "You follow line movement and prefer situations where new information "
            "has not been fully reflected across every book."
        ),
        score=87,
        urgency="important",
        change_label="Line moved 2.5 pts",
        source_label="Odds + injury feed",
    ),
    Opportunity(
        id="poly-probability-shift",
        category="polymarket",
        title="A followed market moved 17% after new information",
        summary=(
            "The probability changed quickly, but the related source material is "
            "not yet reflected consistently across similar markets."
        ),
        why_it_matters=(
            "You asked Logan to flag large probability shifts and explain the event "
            "driving the move before you open the market."
        ),
        score=84,
        urgency="watch",
        change_label="+17% probability",
        source_label="Polymarket + news",
    ),
]
