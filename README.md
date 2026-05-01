# Belief Revision Agent
### 02180 Introduction to Artificial Intelligence — SP25, DTU

A from-scratch propositional logic belief revision engine implementing CNF
conversion, resolution-based entailment, the AGM postulate framework,
possible-worlds plausibility ordering, and a Mastermind AI reasoning core.

**235 tests — all passing.**

---

## Table of Contents

1. [Requirements](#1-requirements)
2. [Project Structure](#2-project-structure)
3. [Setup — First Time Only](#3-setup--first-time-only)
4. [Running the Demo](#4-running-the-demo)
5. [Running the Tests](#5-running-the-tests)
6. [Using the Engine in Your Own Code](#6-using-the-engine-in-your-own-code)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Requirements

| Requirement | Minimum Version | Notes |
|-------------|----------------|-------|
| Python | 3.10 or later | 3.12 recommended |
| pytest | 9.0 or later | only needed for tests |
| No other packages | — | implementation uses stdlib only |

Check your Python version:

```bash
python --version
```

---

## 2. Project Structure

```
Belief-Revision agent/
│
├── main.py                       ← runnable demo (start here — 8 demos)
│
├── src/
│   ├── formula.py                ← AST nodes: Atom, Not, And, Or, Implies, Biconditional
│   ├── parser.py                 ← string → Formula  (e.g. "p -> q")
│   ├── cnf.py                    ← CNF conversion pipeline (4-pass)
│   ├── resolution.py             ← entails(B, φ) — core entailment via resolution
│   ├── belief_base.py            ← BeliefBase with priority / entrenchment order
│   ├── revision_engine.py        ← expand / contract / revise (Levi identity, AGM)
│   ├── plausibility_order.py     ← Optional 1: possible-worlds belief revision
│   └── mastermind.py             ← Optional 2: Mastermind AI via belief revision
│
├── tests/
│   ├── __init__.py
│   ├── test_entailment.py        ← 101 tests: formula, parser, CNF, resolution, AGM patterns
│   ├── test_belief_base.py       ← 40 tests: BeliefBase mutation, priority, entrenchment
│   ├── test_agm.py               ← 53 tests: full AGM K*1–K*5 and K÷1–K÷5 postulates
│   └── test_optional.py          ← 41 tests: PlausibilityOrder and MastermindAgent
│
├── docs/
│   ├── assigment .md             ← original assignment brief
│   ├── taskdistribution.md       ← member task split
│   ├── MEMBER_B_REPORT.md        ← Khush's implementation report
│   └── SIMPLE_GUIDE.md           ← quick-start guide
│
└── README.md                     ← this file
```

---

## 3. Setup — First Time Only

### Option A — Use the virtual environment (recommended)

A `.venv` folder is already present in the project. Activate it and install pytest:

**Windows (PowerShell):**
```powershell
# Navigate to the project folder
cd "c:\Users\khush\Desktop\Artifical Intelligence lecture\Belief-Revision agent"

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Install pytest (only needed once)
pip install pytest
```

**Windows (Command Prompt):**
```cmd
cd "c:\Users\khush\Desktop\Artifical Intelligence lecture\Belief-Revision agent"
.venv\Scripts\activate.bat
pip install pytest
```

**macOS / Linux:**
```bash
cd "Belief-Revision agent"
source .venv/bin/activate
pip install pytest
```

### Option B — Use the Python executable directly (no activation needed)

Replace `python` in every command below with the full path to the venv Python:

```
c:\Users\khush\Desktop\Artifical Intelligence lecture\Belief-Revision agent\.venv\Scripts\python.exe
```

---

## 4. Running the Demo

The demo shows the complete pipeline working: parser → CNF → resolution → belief base.

```powershell
# From the project root (with venv activated)
python main.py
```

Or using the full path if the venv is not activated:

```powershell
$python = "c:/Users/khush/Desktop/Artifical Intelligence lecture/Belief-Revision agent/.venv/Scripts/python.exe"
Set-Location "c:\Users\khush\Desktop\Artifical Intelligence lecture\Belief-Revision agent"
& $python main.py
```

### Expected Output

```
*** Belief Revision Agent — Implementation Demo ***
    02180 Intro to AI, SP25  |  Member B: Entailment Engine

============================================================
  Demo 1 — Basic Entailment (Member B)
============================================================
  [✓  TRUE ]  Modus Ponens:  {p, p→q} ⊨ q
  [✓  TRUE ]  Modus Tollens: {p→q, ¬q} ⊨ ¬p
  [✓  TRUE ]  Hypothetical Syllogism: {p→q, q→r} ⊨ p→r
  [✓  TRUE ]  Disjunctive Syllogism: {p∨q, ¬p} ⊨ q
  [✗  FALSE]  Not entailed:  {p} ⊭ q  (should be False)
  [✓  TRUE ]  Tautology:     {} ⊨ p∨¬p  (empty base, tautology)
  [✓  TRUE ]  Ex falso:      {p, ¬p} ⊨ q  (contradictory base)

============================================================
  Demo 2 — CNF Clause Sets
============================================================
  p → q
    → (q ∨ ~p)
  ...

============================================================
  Demo 3 — Ordered Belief Base
============================================================
  [✓  TRUE ]  Base ⊨ bus_taken (because rain → bus)
  ...

*** All demos complete ***
```

### What Each Demo Section Does

| Demo | Description |
|------|-------------|
| Demo 1 — Basic Entailment | Classical inference patterns: modus ponens, modus tollens, ex falso, tautology |
| Demo 2 — CNF Clause Sets | Shows the CNF clause list output for 5 representative formulas |
| Demo 3 — Ordered Belief Base | Realistic scenario (rain/fog → bus); priority order and `least_entrenched()` |
| Demo 4 — Parser Round-trip | Prints each input string alongside its parsed AST |
| Demo 5 — AGM Postulate Patterns | Verifies the 5 required postulate foundations |
| Demo 6 — Revision Engine | Full expand / contract / revise cycle with AGM verification |
| Demo 7 — Plausibility Order | Possible-worlds lexicographic revision (Optional Task 1) |
| Demo 8 — Mastermind AI | Belief-revision-based codebreaker solving 3 different secrets (Optional Task 2) |

---

## 5. Running the Tests

### Run all 235 tests

```powershell
# From the project root (with venv activated)
python -m pytest tests/ -v
```

Or without activation:

```powershell
$python = "c:/Users/khush/Desktop/Artifical Intelligence lecture/Belief-Revision agent/.venv/Scripts/python.exe"
Set-Location "c:\Users\khush\Desktop\Artifical Intelligence lecture\Belief-Revision agent"
& $python -m pytest tests/ -v
```

### Run a specific test file

```powershell
python -m pytest tests/test_entailment.py -v    # 101 tests — Member B (Khush)
python -m pytest tests/test_belief_base.py -v   # 40 tests  — Member A
python -m pytest tests/test_agm.py -v           # 53 tests  — Member C (AGM postulates)
python -m pytest tests/test_optional.py -v      # 41 tests  — Optional Tasks 1 & 2
```

### Run a specific test class only

```powershell
python -m pytest tests/test_entailment.py::TestEntails -v
python -m pytest tests/test_agm.py::TestRevisionSuccess -v
python -m pytest tests/test_optional.py::TestMastermindAgent -v
```

### Expected test result

```
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.0.3
collected 235 items

tests/test_agm.py::TestRevisionSuccess::test_success_simple           PASSED
...
tests/test_optional.py::TestPlayMastermind::test_returns_positive_int  PASSED

============================ 235 passed in 12.64s ============================
```

### Test coverage by area

| Test File | Count | What it covers |
|-----------|-------|----------------|
| `test_entailment.py` | 101 | Formula AST, parser, CNF passes, resolution, AGM patterns |
| `test_belief_base.py` | 40 | Add/remove/clear, priority order, `least_entrenched()`, Alice vs Bob |
| `test_agm.py` | 53 | Revision K\*1–K\*5, contraction K÷1–K÷5, integration scenarios |
| `test_optional.py` | 41 | World evaluation, plausibility order revision/contraction, Mastermind score + agent |

---

## 6. Using the Engine in Your Own Code

All source files are in `src/`. Add `src/` to your Python path or run from the project root.

### Import and use `entails()`

```python
import sys
sys.path.insert(0, 'src')

from formula import Atom, Not, And, Or, Implies
from resolution import entails

p, q, r = Atom('p'), Atom('q'), Atom('r')

print(entails([p, Implies(p, q)], q))     # True  — modus ponens
print(entails([p], q))                    # False — not entailed
print(entails([p, Not(p)], q))            # True  — ex falso
print(entails([], Or(p, Not(p))))         # True  — tautology
```

### Parse formulas from strings

```python
from parser import parse

f1 = parse("p -> q")
f2 = parse("~p | (q & r)")
f3 = parse("p <-> q")
f4 = parse("p -> q -> r")   # right-associative: p → (q → r)

print(entails([f1, parse("p")], parse("q")))   # True
```

### Supported formula syntax

| Operator | ASCII | Unicode |
|----------|-------|---------|
| Negation | `~p` or `-p` | `¬p` |
| Conjunction | `p & q` | `p ∧ q` |
| Disjunction | `p \| q` | `p ∨ q` |
| Implication | `p -> q` | `p → q` |
| Biconditional | `p <-> q` | `p ↔ q` |

### Use the BeliefBase with priority order

```python
from belief_base import BeliefBase

bb = BeliefBase()
bb.add(Implies(Or(Atom('rain'), Atom('fog')), Atom('bus')), priority=0)  # background
bb.add(Atom('rain'), priority=5)                                          # observation

print(entails(bb.formulas(), Atom('bus')))   # True
print(bb.least_entrenched())                 # rain  (priority=5, removed first)
```

### Expand, contract, and revise (AGM)

```python
from belief_base import BeliefBase
from revision_engine import RevisionEngine

bb = BeliefBase()
bb.add(Atom('rain'), priority=0)
bb.add(Implies(Atom('rain'), Atom('wet')), priority=0)
eng = RevisionEngine(bb)

print(entails(eng.bb.formulas(), Atom('wet')))    # True

eng.revise(Not(Atom('rain')))                      # new evidence: no rain
print(entails(eng.bb.formulas(), Not(Atom('rain'))))  # True
print(eng.is_consistent())                         # True
```

### Plausibility order (Optional Task 1)

```python
from plausibility_order import PlausibilityOrder

po = PlausibilityOrder(['rain', 'wet'])
po.assert_belief(Implies(Atom('rain'), Atom('wet')))
po.assert_belief(Atom('rain'))

print(po.entails(Atom('wet')))            # True

po.revise(Not(Atom('rain')))
print(po.entails(Not(Atom('rain'))))      # True
```

### Mastermind AI (Optional Task 2)

```python
from mastermind import play_mastermind

n = play_mastermind((3, 1, 4, 2), verbose=True)
print(f"Solved in {n} guesses")
```

---

## 7. Troubleshooting

### `ModuleNotFoundError: No module named 'formula'`

**Cause:** Python cannot find the `src/` directory.  
**Fix:** Run commands from the project root, or add `src/` to the path:

```python
import sys
sys.path.insert(0, 'src')
```

### `ModuleNotFoundError: No module named 'pytest'`

**Cause:** pytest is not installed in the active environment.  
**Fix:**

```powershell
pip install pytest
```

Or if using the venv Python directly:

```powershell
& "c:/Users/khush/Desktop/Artifical Intelligence lecture/Belief-Revision agent/.venv/Scripts/python.exe" -m pip install pytest
```

### `RecursionError: maximum recursion depth exceeded`

**Cause:** An extremely deeply nested formula (depth > 5000).  
**Fix:** Increase the limit at the top of your script:

```python
import sys
sys.setrecursionlimit(10000)
```

### `ParseError: Unexpected character ...`

**Cause:** The formula string contains a character the parser does not recognise (e.g. `=`, `^`, `!`).  
**Fix:** Use the supported operators — see the syntax table in Section 6.

### Tests pass locally but not on another machine

**Cause:** Different Python version or missing venv.  
**Fix:** Recreate the venv on the other machine:

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
.venv\Scripts\Activate.ps1      # Windows PowerShell
pip install pytest
```

---

*Belief Revision Agent — 02180 Intro to AI, SP25, DTU*  
*Member B implementation: formula AST, parser, CNF, resolution, entailment*
