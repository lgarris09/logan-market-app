"""Sprint 3.6.8 Block 1 -- the first live LLM provider in this codebase.
Owner-approved (see docs/DECISIONS.md's Sprint 3.6.8 Block 1 ADR): official
`anthropic` Python SDK, model `claude-sonnet-5`.

Terminates all Anthropic-SDK-specific structure entirely inside this class --
`ask_engine.py`'s orchestration only ever sees `AskLlmProvider`/`AskLlmAnswer`/
`AskLlmProviderError` (ask_llm_provider.py). Mirrors
receptors/providers/fmp.py's FmpEarningsProvider discipline: a missing API
key fails loudly at construction (no fixture/demo fallback for this
provider), every real failure mode (network, timeout, API error, refusal,
empty response) raises the one domain error type, and nothing here ever
fabricates a result.
"""

import os
from typing import Literal, Optional

import anthropic

from .ask_context import OpportunityContext
from .ask_llm_provider import AskLlmAnswer, AskLlmProviderError, build_system_prompt

ANTHROPIC_API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
DEFAULT_MODEL = "claude-sonnet-5"
# A grounded answer is a short, few-sentence composition over data the
# pipeline already computed -- not open-ended generation -- so this is
# deliberately well below the SDK's general "don't lowball max_tokens"
# guidance for long-form output; the system prompt itself also instructs a
# concise answer.
DEFAULT_MAX_TOKENS = 1024
# Short and bounded on purpose: a provider that's slow to respond should
# fail fast into the deterministic fallback (requirement: "no LLM failure
# should break the existing opportunity experience") rather than let one
# request hang the route for the SDK's 10-minute default.
DEFAULT_TIMEOUT_SECONDS = 15.0
# The task is "compose a concise, grounded answer from data STRATUS already
# computed," not open-ended reasoning -- low effort keeps this fast and
# cheap, consistent with choosing claude-sonnet-5 over claude-opus-5 for the
# same cost/latency reasons.
DEFAULT_EFFORT: Literal["low"] = "low"


class AnthropicAskLlmProvider:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        client: Optional[anthropic.Anthropic] = None,
    ) -> None:
        # API key comes only from environment configuration (explicit
        # `api_key` param is for tests to inject a fake one -- never a
        # hardcoded default, never read from source control). Resolved
        # eagerly, not lazily on first call, so a missing key fails loudly
        # at construction -- same discipline as FmpEarningsProvider.
        resolved_key = (
            api_key
            if api_key is not None
            else os.environ.get(ANTHROPIC_API_KEY_ENV_VAR)
        )
        if not resolved_key and client is None:
            raise AskLlmProviderError(
                f"{ANTHROPIC_API_KEY_ENV_VAR} is not set. AnthropicAskLlmProvider "
                "requires a real API key from environment configuration -- there is "
                "no fixture/demo fallback for this provider."
            )
        self._model = model
        # Callers may inject their own client (tests use this to mock the
        # transport) -- mirrors FmpEarningsProvider's own `client` param.
        self._client = client or anthropic.Anthropic(
            api_key=resolved_key,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            # Fail toward the deterministic fallback quickly rather than the
            # SDK's default 2 retries with exponential backoff -- a single
            # retry still absorbs a one-off transient blip without risking a
            # long hang on a genuinely down provider.
            max_retries=1,
        )

    def generate(self, context: OpportunityContext, question: str) -> AskLlmAnswer:
        system_prompt = build_system_prompt(context)

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=DEFAULT_MAX_TOKENS,
                output_config={"effort": DEFAULT_EFFORT},
                system=system_prompt,
                # Structurally separate from the system prompt -- the
                # question is sent as its own `user` turn, never
                # concatenated into `system_prompt`'s text. This is the
                # actual prompt-injection guardrail: even if the question
                # contains text like "ignore previous instructions," it
                # arrives as user content the model is explicitly told (in
                # the system prompt) to treat as untrusted, not as a second
                # system instruction.
                messages=[{"role": "user", "content": question}],
            )
        except anthropic.APITimeoutError as exc:
            raise AskLlmProviderError(f"Anthropic API timed out: {exc}") from exc
        except anthropic.RateLimitError as exc:
            raise AskLlmProviderError(f"Anthropic API rate limited: {exc}") from exc
        except anthropic.APIConnectionError as exc:
            raise AskLlmProviderError(
                f"Anthropic API connection failed: {exc}"
            ) from exc
        except anthropic.APIStatusError as exc:
            raise AskLlmProviderError(
                f"Anthropic API request failed (status {exc.status_code}): {exc}"
            ) from exc
        except anthropic.AnthropicError as exc:
            raise AskLlmProviderError(f"Anthropic API call failed: {exc}") from exc

        if response.stop_reason == "refusal":
            category = (
                response.stop_details.category
                if response.stop_details is not None
                else None
            )
            raise AskLlmProviderError(
                f"Anthropic API declined to answer (category={category!r})"
            )

        text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
        if not text:
            raise AskLlmProviderError("Anthropic API returned an empty response")

        return AskLlmAnswer(text=text, model=response.model)
