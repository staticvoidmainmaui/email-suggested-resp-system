"""Thread in, suggested reply out. Phase 2.

The generator is the thing being measured. Keep it honest and keep it dumb: one
prompt, one call, no retries, no self-critique. If it starts checking its own
work you're measuring the evaluator's ability to grade a system that already
graded itself, and the phase 4 numbers stop meaning anything.

Reading conventions match dataset.py / llm.py: WHY / HOW / laddered TODO.
"""

from __future__ import annotations

from .llm import LLM
from .schema import Thread

# ─── what the generator is allowed to see ────────────────────────────────────
# Thread has six fields. Only two go in the prompt:
#
#   messages  ✓  the conversation
#   context   ✓  the closed world — "assume retrieval worked"
#
#   issues        ✗ pre-decomposed intent. Handing it over makes MISSED_ISSUE
#                   uncatchable, because you told it what not to miss.
#   ideal_reply   ✗ it's the answer.
#   critical_facts ✗ the evaluator's checklist of which numbers matter.
#   gate_applicable ✗ evaluator metadata, means nothing to a drafter.


SYSTEM_PROMPT = """\
You are an expert email reply writer. You draft the reply someone would otherwise
have had to write off the top of their head, so it should read like a person
wrote it, not like a template got filled in.

Work from the known facts you are given and nothing else. Those facts are the
only thing you know about this situation. If replying well would need something
that isn't in there, don't fill the gap - say you will confirm and follow up.

Read the whole thread before you start. Address every distinct thing the sender
raised, not just the first one or the loudest one. Two questions asked means two
questions answered.

Match the sender's register - formal if they were formal, relaxed if they were.
Say what happens next and who does it, concretely enough that nobody has to write
back just to ask. Keep it as short as the situation allows.

Plain email prose. No markdown, no subject line, no preamble about what you are
about to write - just the reply body.
"""



def render_thread(thread: Thread) -> str:
    """Thread -> the user-turn text."""
  
    
    #\n AND * makes it so that a  -c , -c , space , conversation : , [customer] [body] , [customer] [body] is printed
    text = "\n".join([
        f"Thread {thread.id} ({thread.category})",
        "",
        "Known facts:",
        *[f"- {fact}" for fact in thread.context],
        "",
        "Conversation:",
        *[f"[{m.sender}] {m.body}" for m in thread.messages]
    ])
    
    return text
    

class Generator:
    """Drafts a suggested reply for a support thread."""

    def __init__(self, llm: LLM) -> None:
        self.llm = llm

    def generate(self, thread: Thread) -> str:
        response = self.llm.complete(system=SYSTEM_PROMPT, user=render_thread(thread))
        return response
        
        





# ─── SYSTEM PROMPT EARLIER VERSION ,  kept for the writeup ───────────────────────────────────
# Prompt iterations are evidence. "I changed the prompt and the gate pass-rate
# moved" is a result you can report; keeping the old text makes it reproducible.
#
# SYSTEM_PROMPT_V1 = """\
#   You are a expert email reply writer. You can evaluate the context of the conversation and provide a helpful response.
#   Start by understanding and adressing the context and the style of a reply.
#
#   Objective: Provide a helpful and accurate email response in the context of a conversation.
#   Being a email reply suggestor assistance as top priority, where possible replies is the primary goal.
#   Resolving and providing a "right answer" comes as a secondary goal but is still important if possible.
#
#   For resolving a customer support problem follow these steps:
#   - Check the customer's account for any recent changes
#   - Review any related communications
#   - If no protocol solution is understand , stay emperical and provide a tentative response.
#   For conversations:
#   - always keep the tone professional and helpful.
#   - address the issue directly
#   - provide a clear and concise response
#
#   Make factual claims only if hte provided context supports them; otherwise say you will follow up.
# """
#
# What changed and why:
#   ~ "only the provided context" moved to the top and got teeth. In v1 it was the
#     last line, after two competing objectives — and it's the single instruction
#     the faithfulness gate tests compliance with. Buried, a gate failure is the
#     prompt's fault rather than the model's, and you'd be measuring yourself.
#   - dropped the "check the customer's account / review related communications"
#     steps. The model has no account to check; those are retrieval actions it
#     can't take, and instructions a model cannot follow are how you get invented
#     facts. Retrieval is assumed done — that's what the known facts are.
#   - dropped "conversations vs. support problems" as separate branches. Nothing
#     tells it which mode it's in, so the branch is a coin flip.
#   + "address every distinct thing the sender raised" — v1 had no coverage rule,
#     and MISSED_ISSUE is a defect in the dataset.
#   + "say what happens next and who does it" — same reason, NO_NEXT_STEP.
#   ~ "always professional" became match-the-register. Professional-by-default is
#     how you get a stiff reply to a casual email, which is BAD_TONE.
#   - still no length cap in tokens, on purpose: VERBOSE is a scored criterion,
#     and capping length means the judge never sees a verbose reply, so that
#     criterion would report a meaningless 100%.

# Here we build the system prompt off the gates that we have defined. Addressing them in natural language.
