<h1 align="center">GEN_AI EMAIL SUGGESTED RESPONSE SYSTEM</h1>

<p align="center">
  <strong>A hybrid evaluator for AI-drafted support replies : defending its accuracy metric, not just reporting one.</strong>
</p>

<p align="center">
  <img src="https://cdn.simpleicons.org/python/3776AB" height="34" alt="Python" />
  &nbsp;&nbsp;&nbsp;
  <img src="https://cdn.simpleicons.org/anthropic/D97757" height="34" alt="Anthropic" />
  &nbsp;&nbsp;&nbsp;
  <img src="https://cdn.simpleicons.org/huggingface/FFD21E" height="34" alt="Hugging Face" />
  &nbsp;&nbsp;&nbsp;
  <img src="https://cdn.simpleicons.org/pytorch/EE4C2C" height="34" alt="PyTorch" />
  &nbsp;&nbsp;&nbsp;
  <img src="https://cdn.simpleicons.org/json/000000" height="34" alt="JSONL" />
  &nbsp;&nbsp;&nbsp;
  <img src="https://cdn.simpleicons.org/git/F05032" height="34" alt="Git" />
</p>

<p align="center">
  <sub>
    Python 3.11 · Anthropic Messages API · DeBERTa-v3-MNLI via Transformers · PyTorch (CPU) · JSONL · Git
  </sub>
</p>

---

## What ships

Three things, in the order they were built:

- **A dataset** — support threads, good replies, and deliberately broken ones. The ruler.
- **A generator** — thread in, reply out.
- **An evaluator** — reply in, accept/reject out, with the reason attached.

Plus the point of the exercise: **a validation run** that says how far the evaluator can be trusted.

### How it gets built

Approach: break "good" into criteria. Give each one the cheapest check that honestly measures it. Run them in two tiers, cheapest first, and stop early.

1. **Gates** — deterministic, no LLM. One failure sinks the reply.
2. **Judge** — LLM, binary, only on replies that survived the gates.


### The scope

This does not answer arbitrary email. The domain is narrowed until correctness is decidable. Each narrowing is load-bearing:

- **Closed world.** Every thread carries a `context` field holding the complete set of atomic facts an agent could know — account state, applicable policy, order references, what support can and cannot do. It is the CRM page an agent would have open. Anything a reply asserts outside it is invented *by construction*, which is what makes faithfulness checkable instead of arguable.
- **NLI Local Model Inclusion** A closed world lets the check be mechanical: split the reply into claims and ask, for each one, whether the context *entails* it. That is exactly the task NLI (natural language inference) models are trained on — given a premise and a statement, they return entailment, contradiction, or neither. The gate uses DeBERTa-v3-MNLI off the shelf, and only its "not entailed" verdict matters. Nothing is fine-tuned, and the model never sees a quality question — asking "is this supported by these facts?" is answerable, asking "is this reply good?" is not.
- **Transactional threads only.** They resolve against known facts. No advice, no negotiation.
- **Composition, not retrieval.** The generator is handed the context, so nothing here measures whether the right facts would have been found.
- **One defect per broken reply.** Each unacceptable reply carries exactly one deliberate defect and every defect maps to exactly one tier — a defect with no tier means either the tier is missing or the defect is not real.
- **Binary labels.** Accept or reject. No threshold to tune.
- **9 threads, English, single annotator.** Sized to test the method.

---

## Phases

Four passes. Each only makes sense once the previous one is fixed.

| | phase | what it does | status |
|---|---|---|---|
| **1** | **Dataset** | builds the ruler — good replies and broken ones | done |
| **2** | **Generator** | turns a thread into a reply | done |
| **3** | **Evaluator** | turns a reply into a verdict | done |
| **4** | **Validation** | says how far the verdict can be trusted | scaffolded, returning zeros |

---

## Logic flow

```
thread + context
      │
      ▼
  generator ──► reply (frozen to disk)
      │
      ▼
┌─────────────────────────────────────────┐
│ TIER 1 — GATES  (no LLM, pass/fail)     │
│  • fact gate    regex + set membership  │
│  • faithfulness NLI entailment          │
└─────────────────────────────────────────┘
      │
   any fail? ──yes──► REJECT (judge never runs; empty judge result ≠ approval)
      │
      no
      ▼
┌─────────────────────────────────────────┐
│ TIER 2 — SCORED  (LLM judge, binary)    │
│  coverage · resolution · next_step ·    │
│  tone · concision                       │
└─────────────────────────────────────────┘
      │
      ▼
   VERDICT
```

---

## The tiers, briefly

**Gates** — pass/fail, one failure sinks the reply. No LLM, deliberately.
- Fact gate: every identifier and amount in the reply must appear in the context. Free, instant, verifiable by reading two strings.
- Faithfulness gate: split into claims, ask DeBERTa-v3-MNLI if each is entailed.
- Neither has an *opinion* — that's the point. "A model trained on entailment says this is unsupported" > "an LLM said it seemed unsupported."

**Scored** — runs only if gates pass, only because no cheap check exists.
- Five criteria: `coverage`, `resolution`, `next_step`, `tone`, `concision`. Both questions answered? Right action? Clear expectation set? Reads like a person? Signal buried?
- Order matters: `coverage` runs first because it's the only criterion with ground truth (`thread.issues`), anchoring the judge on evidence before the subjective ones.
- Every verdict must quote the words that decided it. A verdict you can't point at isn't a verdict.
- Binary, not 1–5. A five-point scale needs a defensible anchor per level, and every anchor is a paragraph someone can argue with. Binary compares directly to a binary human label, no threshold in between.

---

## The dataset

- 9 threads, 21 replies, 11 acceptable.
- Each unacceptable reply carries **exactly one** deliberate defect; every defect maps to **exactly one** tier. No tier ⇒ the tier is missing or the defect isn't real.
- Traps are hand-written, not generated — a model can't be relied on to fabricate a refund policy on demand, and the point of a trap is knowing precisely what's wrong.
- One thread is marked `gate_applicable: false` because it is conversational and makes no checkable factual claims. It is excluded from the gate, and the exclusion is reported rather than absorbed.
- The human `acceptable` label is authored by hand — never derived from the evaluator.

---

## What's in the build

**Evaluation design**

- **Closed-world context** — every thread ships its complete fact set
- **Two-tier evaluator** — deterministic gates, then an LLM judge
- **Non-LLM gates** — regex fact check + NLI entailment, zero cost per call
- **NLI probe harness** — 14 labeled pairs, falsifies the model before it's trusted
- **Claim filter** — drops questions and pleasantries before the gate runs
- **Gate skip flag** — `gate_applicable: false`, exclusions reported not absorbed
- **Binary judge** — 5 criteria, one call, quote-backed verdicts
- **Criterion ordering** — the ground-truth criterion first, anchoring the rest
- **Short-circuit aggregation** — the judge never runs after a gate failure
- **Empty ≠ approved** — `judge_ran` distinguishes skipped from passed
- **Per-tier diagnostics** — `Verdict.failures` names which tier claimed what

**Engineering**

- **Provider seam** — `LLM` protocol, injected; offline stub or real client, so the whole pipeline runs and is testable without an API key
- **Lazy model imports** — the fact gate runs with no torch installed
- **Frozen replies** — one generation per prompt version, git as the history; iterating on the judge changes one variable at a time
- **Prompt versioning** — `prompt_version` on every generated row, v1 preserved inline with what changed and why
- **Overwrite guard** — `--force` required to replace the frozen set
- **Refusal handling** — `LLMRefusal` raised, the run survives, the row is flagged
- **Defensive parsing** — JSON fences stripped, raises rather than guesses
- **Dataset integrity check** — invariants, duplicate ids, class balance

---

## Layout

| path | what lives there |
|---|---|
| `src/evalsys/schema.py` | `Defect`, `Message`, `Thread`, `LabeledReply` — and the tier mapping |
| `src/evalsys/dataset.py` | JSONL loading + integrity checks |
| `src/evalsys/llm.py` | provider seam — `LLM` protocol, offline stub, real client |
| `src/evalsys/generator.py` | thread → reply |
| `src/evalsys/gates.py` | the pass/fail tier — fact gate + NLI faithfulness gate |
| `src/evalsys/judge.py` | the scored tier, five criteria, one call |
| `src/evalsys/evaluate.py` | gates-then-scored aggregation |
| `scripts/nli_probe.py` | falsification test for the NLI model |
| `scripts/generate.py` | freezes generated replies to disk |
| `scripts/validate.py` | phase 4 — kappa, recall, tier check, exclusions |

```bash
# dataset integrity
PYTHONPATH=src python -c "from evalsys import dataset as d; t=d.load_threads(); r=d.load_replies(); print(d.summary(t,r)); print(d.check(t,r) or 'OK')"

# does the NLI model deserve the gate?
PYTHONPATH=src python scripts/nli_probe.py

# full pipeline, offline
PYTHONPATH=src python scripts/validate.py --dry-run
```
