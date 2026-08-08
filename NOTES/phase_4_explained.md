Phase 4 pipeline 

Compare Verdict.accepted to LabeledReply.acceptable → kappa.

Compare Verdict.predicted_defect to LabeledReply.defect → per-tier precision/recall. 

* The thing being scored in Phase 4 is the evaluator.

# Calibration 

However you cant claim the judge is any good so it needs calibration through the replies.jsonl set , where on 21 fabricated replies where I knew the answer , it agreed with a human k=0.7

Rough analogy: replies.jsonl is the exam with a marking scheme you use to certify the grader. generated.jsonl is the ungraded coursework the certified grader then handles.