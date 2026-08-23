"""Sprint 3.6.8 Block 1 -- deterministic, in-repo Ask LLM provider, explicitly
NOT live. Same discipline as logan_core's FixtureEarningsProvider/
FixtureMarketDataProvider (receptors/providers/fixture.py): exists so the
full grounded-answer orchestration (ask_engine.py's generate_grounded_answer)
can be proven end-to-end -- success, failure, malformed responses -- without
ever calling a real LLM API in the automated test suite.
"""

from typing import Optional, Sequence

from .ask_context import OpportunityContext
from .ask_llm_provider import AskLlmAnswer, AskLlmProviderError, ConversationTurn

FIXTURE_MODEL_NAME = "fixture-ask-llm (not live)"


class FixtureAskLlmProvider:
    """Configured with exactly one outcome per instance -- a canned answer,
    or an exception to raise -- covering both the "grounded LLM success" and
    every failure-mode test case (unavailable, timeout, malformed) with the
    same simple shape. Records every call (context, question, history) it
    received, so tests can assert the real OpportunityContext, the real
    question text, and (Sprint 3.6.8 Block 3) the real bounded conversation
    history were passed through unmodified -- the "structured context passed
    correctly", "prompt-injection cannot override system grounding", and
    "conversation history threaded correctly" checks all read this.
    """

    def __init__(
        self,
        answer: Optional[str] = None,
        error: Optional[Exception] = None,
        model: str = FIXTURE_MODEL_NAME,
    ) -> None:
        if answer is None and error is None:
            raise ValueError(
                "FixtureAskLlmProvider requires either `answer` or `error` -- "
                "a fixture with neither is not a usable test double."
            )
        self._answer = answer
        self._error = error
        self._model = model
        self.calls: list[
            tuple[OpportunityContext, str, tuple[ConversationTurn, ...]]
        ] = []

    def generate(
        self,
        context: OpportunityContext,
        question: str,
        history: Sequence[ConversationTurn] = (),
    ) -> AskLlmAnswer:
        self.calls.append((context, question, tuple(history)))
        if self._error is not None:
            raise self._error
        assert self._answer is not None  # guaranteed by __init__'s own check
        return AskLlmAnswer(text=self._answer, model=self._model)


def malformed_response_error() -> AskLlmProviderError:
    """A ready-made "the provider returned something we can't trust" fixture
    -- e.g. an empty response, or a refusal -- for tests that don't need to
    author their own error message."""
    return AskLlmProviderError("fixture: provider returned an empty/malformed response")
