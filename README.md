# Belief Revision Agent
### 02180 Introduction to Artificial Intelligence — SP25, DTU

A from-scratch propositional logic belief revision engine implementing CNF
conversion, resolution-based entailment, and the AGM postulate framework.

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
├── main.py                    ← runnable demo (start here)
│
├── src/
│   ├── formula.py             ← AST nodes: Atom, Not, And, Or, Implies, Biconditional
│   ├── parser.py              ← string → Formula  (e.g. "p -> q")
│   ├── cnf.py                 ← CNF conversion pipeline
│   ├── resolution.py          ← entails(B, φ) — the core entailment function
│   └── belief_base.py         ← BeliefBase with priority order
│
├── tests/
│   ├── __init__.py
│   └── test_entailment.py     ← 101 tests (formula, parser, CNF, resolution, AGM)
│
├── README.md                  ← this file
├── MEMBER_B_REPORT.md         ← full implementation report
├── assigment .md              ← original assignment brief
└── taskdistribution.md        ← member task split
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
| Demo 2 — CNF Clause Sets | Visually shows the CNF clause list output for 5 representative formulas |
| Demo 3 — Ordered Belief Base | Realistic scenario (rain/fog → bus); shows priority order and `least_entrenched()` |
| Demo 4 — Parser Round-trip | Prints each input string alongside its parsed AST, including right-associative `→` |
| Demo 5 — AGM Postulate Patterns | Verifies the 5 required postulate patterns: Success, Inclusion, Vacuity, Consistency, Extensionality |

---

## 5. Running the Tests

### Run all 101 tests

```powershell
# From the project root (with venv activated)
python -m pytest tests/ -v
```

Or without activation:

```powershell
$python = "c:/Users/khush/Desktop/Artifical Intelligence lecture/Belief-Revision agent/.venv/Scripts/python.exe"
Set-Location "c:\Users\khush\Desktop\Artifical Intelligence lecture\Belief-Revision agent"
& $python -m pytest tests/test_entailment.py -v
```

### Run a specific test class only

```powershell
# Only the entailment tests
python -m pytest tests/test_entailment.py::TestEntails -v

# Only the parser tests
python -m pytest tests/test_entailment.py::TestParser -v

# Only the CNF tests
python -m pytest tests/test_entailment.py::TestCNFConversion -v

# Only the AGM pattern tests
python -m pytest tests/test_entailment.py::TestAGMPatterns -v
```

### Run a single test by name

```powershell
python -m pytest tests/test_entailment.py::TestEntails::test_modus_ponens -v
```

### Expected test result

```
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.0.3
collected 101 items

tests/test_entailment.py::TestFormulaEquality::test_atom_equal           PASSED
tests/test_entailment.py::TestFormulaEquality::test_atom_not_equal        PASSED
...
tests/test_entailment.py::TestAGMPatterns::test_extensionality_pattern    PASSED

============================= 101 passed in 0.30s =============================
```

### Test coverage by area

| Test Class | Count | What it covers |
|-----------|-------|----------------|
| `TestFormulaEquality` | 11 | AST equality, hashing, `atoms()` |
| `TestParser` | 20 | All operators, precedence, Unicode, error cases |
| `TestLiteralHelpers` | 6 | `negate_literal`, tautology detection |
| `TestCNFConversion` | 15 | Each CNF pass, De Morgan, distributivity |
| `TestIsUnsatisfiable` | 9 | SAT/UNSAT at clause level |
| `TestEntails` | 20 | All inference patterns + edge cases |
| `TestAGMPatterns` | 7 | Logical foundations of the 5 AGM postulates |

---

## 6. Using the Engine in Your Own Code

All source files are in `src/`. Add `src/` to your Python path or run from the project root.

### Import and use `entails()`

```python
import sys
sys.path.insert(0, 'src')

from formula import Atom, Not, And, Or, Implies, Biconditional
from resolution import entails

p = Atom('p')
q = Atom('q')
r = Atom('r')

# Modus ponens: {p, p→q} ⊨ q ?
print(entails([p, Implies(p, q)], q))          # True

# Is q entailed by just p?
print(entails([p], q))                          # False

# Does a contradictory base entail everything?
print(entails([p, Not(p)], q))                  # True  (ex falso)

# Does an empty base entail a tautology?
print(entails([], Or(p, Not(p))))               # True
```

### Parse formulas from strings

```python
from parser import parse

f1 = parse("p -> q")            # Implies(Atom('p'), Atom('q'))
f2 = parse("~p | (q & r)")      # Or(Not(p), And(q, r))
f3 = parse("p <-> q")           # Biconditional(p, q)
f4 = parse("p -> q -> r")       # Implies(p, Implies(q, r))  ← right-assoc

print(entails([f1, parse("p")], parse("q")))    # True
```

### Supported formula syntax

| Operator | ASCII | Unicode |
|----------|-------|---------|
| Negation | `~p` or `-p` | `¬p` |
| Conjunction | `p & q` | `p ∧ q` |
| Disjunction | `p \| q` | `p ∨ q` |
| Implication | `p -> q` | `p → q` |
| Biconditional | `p <-> q` | `p ↔ q` |
| Grouping | `(p & q)` | |

### Use the BeliefBase with priority order

```python
from belief_base import BeliefBase
from resolution import entails

bb = BeliefBase()

# Priority 0 = most entrenched (background knowledge)
bb.add(Implies(Or(Atom('rain'), Atom('fog')), Atom('bus')), priority=0)

# Priority 5 = less entrenched (recent observation, first to be dropped)
bb.add(Atom('rain'), priority=5)

# Check entailment against the full base
print(entails(bb.formulas(), Atom('bus')))      # True

# Find the formula to remove first during contraction
print(bb.least_entrenched())                    # rain
```

### Inspect CNF clauses directly

```python
from cnf import to_cnf_clauses

clauses = to_cnf_clauses(Implies(Atom('p'), Atom('q')))
print(clauses)   # [frozenset({'~p', 'q'})]

clauses = to_cnf_clauses(parse("p <-> q"))
print(clauses)   # [frozenset({'~p', 'q'}), frozenset({'~q', 'p'})]
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
