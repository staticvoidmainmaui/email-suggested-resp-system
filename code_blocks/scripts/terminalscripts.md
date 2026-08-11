
# render_threads , Generator(Mock(mock_reply)).generate test

```
python -c "
from evalsys.llm import MockLLM
from evalsys import dataset as d
from evalsys.generator import Generator, render_thread
t = d.load_threads()['t-001']
print(render_thread(t))
print('---')
print(Generator(MockLLM({'t-001': 'canned billing reply'})).generate(t))
"
```

Thread t-001 (billing)



Known facts:
- Account shows two successful charges of $49 on the same billing cycle, refs 88412 and 88530.
- Ref 88530 was created by a retry after a webhook timeout and is a confirmed duplicate.
- Duplicate charges are refunded in full once confirmed; no approval needed from the customer.
- Refunds post to the original card in 5-10 business days depending on the bank.
- The webhook retry bug was fixed in the 12 Mar release; it cannot affect future cycles.
- Support cannot change a customer's billing date.

Conversation:
[customer] Hi - I was charged $49 twice this month for my Pro plan. Order refs 88412 and 88530. Can you refund the duplicate? Also, please tell me why it happened, I don't want it recurring next month.
---
canned billing reply

# gate check without model call - check_facts
```
python -c "
from evalsys import dataset as d
from evalsys.gates import check_facts
t = d.load_threads()['t-001']
print(check_facts('I have refunded \$49 on ref 88530.', t))
print(check_facts('I have refunded \$79 on ref 88350.', t))
"
```

