# Journal for genai_emailthreads:

* Domain modeling with value objects : Thread/Message dataclasses are "value objects" - immutuable recrods defined by their data not their identity

Modeled the problem's nouns (threads, messages as types)

* Serialization : difference between using data at rest like JSON on the disk before data in memory(objects) , all systems have this seam of parsing at boundary working with the saved data. "parse dont validate"

* Parse dont validate because
w.o it 
we would work on incosistent input thats been modified, unpredictable system states, less error reporting, and unclear type declearation , 

    Basically the Moment data enters system we make a threat.

* Factory methods : 

such as Message(*mm) vs explciti ( cls(sender= ...))

* prompt as data, not as string : making a tunable system with prompts assembled from structured pieces

unclear where used 

## Evalator (Harness)

* stategy pattern - each criterion interchangable behind the shape of (record ,reply) -> verdict .

Gates and Scored crtieria are tehsame callable change, we just chnage how the harness treats the result 

half built with defect enum mapping to the tiers , show me example of adding criterion

* Short Circuit with gates : gates then scored flow , stops scoring if it hits the restrictions , same structure as a validarion chain or a middle ware stack

* Scorecard as an accumulater , tags the replies rather than scoring them with a number

Model + Harness

* Seperation of th epure and impure - impure codde does I/O ( model calls, reads files,  non deterministic)

"Pure code" just transforms the data ( aggregating verdicts into a score , deciding pass/fail )

To debug verdicts without a call 

* Fixtures / recordered responses- general practice of savid real models outputs , pracice called "golden files or fixtures"

# Stages

### 1.1:

Built the shape for the ruler which shapes the messages as somehting to obejctively score against

Wrote Restrictive and Scoring gates as to label the messages in a tier classifier 

schema also includes the support thread built , inclusing the message formatting and serialization plumbing needed for the program

Lastly a labeled reply same pattern for the eval to actually score on??? 

### 1.2 :  in dataset.py

Wrote the datase.py file which runs and loads the json threads , applies labeling , and checks against errors as well as a summary report

### 1.3 : 

thread.json

each thread has shape of a 
    id , category , messages, context, issues, ideal_reply 

thread building 

would currently be scored against NLI primarily good for natural language . but a seperate determinisitc gate for referenced numbers should be inlcuded if we are trying to test for that 

NLI Gate first


replies.jsonl

    the actual validation set
    it contains a human verdict, the defects of replies , and are many per reply 
    its the answer key rather than a cosine reference vector

### 2.1 :

llm.py

Components include: 
MockLLM - System to send in a fake response as to test the system. Responses are deterministic
ClaudLLM- currently just a claude model call intializing with tehc lient and model also with a .complete method as create replies off the context : returns the models suggestion reply in a list of string objects 

also wrote the Refusal error class as to identify errors when actually calling through the class.

Before a model call- 
export the environment variable into os.eviron with
$env:ANTHROPIC_API_KEY = "sk-ant-..."

### 2.2 :

generator.py

turned the reply objective from a arbitrary bot suggestion to more of customer support to test against context in the threads.

    system prompt- is what gets fed to the agent , additionally  we build the system prompt off the gates that we have defined. Addressing them in natural language.  
    
[PRACTICE] doing the system prompt

Done. 

- evaluator :
    - needs agrregator running off our version runs to see gated passes before a judge call. 
    - cosine similarity
    - faithfulness gate
    - cosine similarity 
    - fact - deterministic check
    - judge call at the very end

### 2.2b 

NLI Probe test per llm definition - a capability test before you build the gate — you're checking whether an off-the-shelf MNLI model can actually make the distinctions your gate depends on.

prompted claude through - asking " Test the NLI to verify its sentence pairing capanilities and wether it will help with the response context" 

After testing and tweaking the NLI weaknesses are:
- overpromises 
- question/pleasenataries 

Contradiction claims are what we are guarding against and what the model can truly identify with a claim ,
showing the importance in testing with context vs the raw claim of the reply. 

### 3.1 : 

validate.py

The file running validation with kappa calculation , trap recall - being how many of the broken replies were actually caught by the evaluator and correctness of the evaluator

finished and ready for testing needing the actual replies to the disk 

validate.py now adds and audit for the failed replies

additionally, since its really good at catching traps, the main problem is false positives so I added that in the audit as well

### 3.2 :

TESTING

$env:ANTHROPIC_API_KEY = "sk-ant-..."      # PowerShell
$env:PYTHONPATH = "src"

python scripts/generate.py --force          # ~9 calls, real replies to disk
python scripts/validate.py                  # ~21 calls, real judge


- things to note include : thinking maxed the tokens at 2000 tokens - raised to 8000
- noted the judge consistency prompting question if judge agrees with itself (called self-consistency), not adding becuase of the 3x api calls.


### 3.2b :

false positives in trap recall because of traps that still should get passed , 

trap_recall filters on reply.defect != Defect.NONE, which gives 12 — but it scores a catch as not verdict.acceptable.

There are two traps that should be sent anyway however they were rejected :
2 were Human Labeled_ Pass with a Defect
2 of the same were Labeled_ Rejected with a different defect

also hurting raw agreement

### 3.3c :

NLI faithfulness gat emits a single defect label being (contradicts_context) while covering invented_policy, overpromise, and contradicts_context 

the rejection is still right , with no vocabulary to label it with documented wrong attribution.

### 4.1 :

generated.jsonl && python scripts/score_generated.py

the generated replies being scored under the evaluator whose accuracy is verified and evaluated.





