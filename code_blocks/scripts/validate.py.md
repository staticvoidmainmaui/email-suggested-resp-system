PS C:\Users\alejm\VSCodeProjects\genAIinbox_suggestions> python scripts/validate.py
provider: claude-sonnet-5
[1/21] r-001a (t-001)
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 202/202 [00:00<00:00, 2495.70it/s]
[2/21] r-001b (t-001)
[3/21] r-001c (t-001)
[4/21] r-001d (t-001)
[5/21] r-002a (t-002)
[6/21] r-002b (t-002)
[7/21] r-002c (t-002)
[8/21] r-002d (t-002)
[9/21] r-003a (t-003)
[10/21] r-003b (t-003)
[11/21] r-004a (t-004)
[12/21] r-004b (t-004)
[13/21] r-005a (t-005)
[14/21] r-005b (t-005)
[15/21] r-006a (t-006)
[16/21] r-006b (t-006)
[17/21] r-007a (t-007)
[18/21] r-007b (t-007)
[19/21] r-008a (t-008)
[20/21] r-008b (t-008)
[21/21] r-009a (t-009)

=======================================================
replies evaluated   21
raw agreement       17/21
cohen's kappa       0.63
trap recall         12/12
caught by own tier  7/12
exclusions          {'gate_skipped': 1, 'judge_skipped': 4, 'parse_failed': 0}
=======================================================

      reply     labelled              tier    claimed by the evaluator
------------------------------------------------------------------------------------
WRONG r-001b    wrong_fact            gate    ['wrong_resolution']
WRONG r-001c    invented_policy       gate    ['wrong_resolution']
OK    r-001d    missed_issue          scored  ['missed_issue']
OK    r-002b    no_next_step          scored  ['missed_issue', 'wrong_resolution', 'no_next_step']
OK    r-002c    bad_tone              scored  ['missed_issue', 'wrong_resolution', 'no_next_step', 'bad_tone']   <- human said ACCEPTABLE
OK    r-002d    verbose               scored  ['missed_issue', 'verbose']   <- human said ACCEPTABLE
WRONG r-003b    overpromise           gate    ['contradicts_context']   <- judge never ran (gate sank it)
OK    r-004b    no_next_step          scored  ['missed_issue', 'wrong_resolution', 'no_next_step', 'bad_tone', 'verbose']
OK    r-005b    contradicts_context   gate    ['contradicts_context']   <- judge never ran (gate sank it)
OK    r-006b    wrong_resolution      scored  ['wrong_resolution']
WRONG r-007b    overpromise           gate    ['contradicts_context']   <- judge never ran (gate sank it)
WRONG r-008b    contradicts_context   gate    ['wrong_resolution', 'no_next_step']
------------------------------------------------------------------------------------