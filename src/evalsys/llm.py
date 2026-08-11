"""Provider interface for the generator and the judge.

Both halves of the system need the same thing — text in, text out — so they share
one interface. That's what lets phase 2 and 3 run offline against MockLLM and
switch to a real provider by swapping one object.

Reading conventions match dataset.py: WHY / HOW / laddered TODO.
"""

from __future__ import annotations

import os
from typing import Protocol

from matplotlib import text

# WHY a Protocol rather than an ABC: nothing here needs shared implementation, and a Protocol is structural
#   Docs: https://docs.python.org/3/library/typing.html#typing.Protocol


class LLM(Protocol):
    """Anything that can turn a system + user prompt into text."""

    def complete(self, system: str, user: str, max_tokens: int = 2000) -> str:
        ...


# ─── MockLLM — offline, no key required ──────────────────────────────────────

class MockLLM:
    """Canned responses, keyed by a marker in the prompt."""

    def __init__(
        self,
        responses: dict[str, str] | None = None,
        fallback: str = "MOCK: no canned response matched.",
    ) -> None:
        self.responses = responses or {}
        self.fallback = fallback

    def complete(self, system: str, user: str, max_tokens: int = 2000) -> str:
       
        for marker, reply in self.responses.items():
            if marker in user:
                return reply
        return self.fallback
    
    
#Refusal class as to identify errors
class LLMRefusal(RuntimeError):
    """The Model refused to answer. No reply at all"""


MODEL = "claude-sonnet-5"
# I was recommended to: 
        # constrain the output format hard (single integer plus a short rationale, one criterion per call, explicit rubric anchors), 
        # and if you need a stable number, sample the judge 3× and take the median for judge consistency.)
class ClaudeLLM:
    """Thin wrapper over the Messages API."""

    def __init__(self, model: str = MODEL) -> None:
        import anthropic
        self.model = model
        self.client = anthropic.Anthropic()
        

    def complete(self, system: str, user: str, max_tokens: int = 8000) -> str:

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        
        if response.stop_reason == "refusal":
            raise LLMRefusal(f"model refused (stop_reason=refusal), model={self.model}")
        
        text = next(b.text for b in response.content if b.type == "text")
        
        if text is None:
            raise LLMRefusal(
                f"no text block (stop_reason={response.stop_reason}, model={self.model})"
            )
        
        return text
 
# ─── choosing a provider ─────────────────────────────────────────────────────

def get_llm() -> LLM:
    """MockLLM unless a key is present."""
    
    if os.environ.get("ANTHROPIC_API_KEY"):
        return ClaudeLLM()
    return MockLLM()
    ...
