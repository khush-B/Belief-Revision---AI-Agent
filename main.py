"""
main.py — Belief Revision Agent Demo
=====================================
Demonstrates the full pipeline:
  Member A  — Ordered belief base with priority / entrenchment
  Member B  — CNF conversion + resolution-based logical entailment
  Member C  — Expand / contract / revise engine, AGM postulates
  Optional 1 — Plausibility-order possible-worlds belief revision
  Optional 2 — Mastermind AI using belief revision as the reasoning core

Run:
    cd "Belief-Revision agent"
    python main.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from formula import Atom, Not, And, Or, Implies, Biconditional
from parser import parse
from resolution import entails
from belief_base import BeliefBase
from revision_engine import RevisionEngine
from plausibility_order import PlausibilityOrder
from mastermind import MastermindAgent, play_mastermind, score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def show(description: str, result: bool) -> None:
    symbol = "✓  TRUE " if result else "✗  FALSE"
    print(f"  [{symbol}]  {description}")


# ---------------------------------------------------------------------------
# Demo 1 — Basic entailment
# ---------------------------------------------------------------------------

def demo_basic_entailment() -> None:
    section("Demo 1 — Basic Entailment (Member B)")

    p = Atom('p');  q = Atom('q');  r = Atom('r')

    show("Modus Ponens:  {p, p→q} ⊨ q",
         entails([p, Implies(p, q)], q))

    show("Modus Tollens: {p→q, ¬q} ⊨ ¬p",
         entails([Implies(p, q), Not(q)], Not(p)))

    show("Hypothetical Syllogism: {p→q, q→r} ⊨ p→r",
         entails([Implies(p, q), Implies(q, r)], Implies(p, r)))

    show("Disjunctive Syllogism: {p∨q, ¬p} ⊨ q",
         entails([Or(p, q), Not(p)], q))

    show("Not entailed:  {p} ⊭ q  (should be False)",
         entails([p], q))

    show("Tautology:     {} ⊨ p∨¬p  (empty base, tautology)",
         entails([], Or(p, Not(p))))

    show("Ex falso:      {p, ¬p} ⊨ q  (contradictory base)",
         entails([p, Not(p)], q))


# ---------------------------------------------------------------------------
# Demo 2 — CNF conversion trace
# ---------------------------------------------------------------------------

def demo_cnf_trace() -> None:
    section("Demo 2 — CNF Clause Sets")
    from cnf import to_cnf_clauses

    examples = [
        ("p → q",       Implies(Atom('p'), Atom('q'))),
        ("p ↔ q",       Biconditional(Atom('p'), Atom('q'))),
        ("¬(p ∧ q)",    Not(And(Atom('p'), Atom('q')))),
        ("p ∨ (q ∧ r)", Or(Atom('p'), And(Atom('q'), Atom('r')))),
        ("p ∨ ¬p",      Or(Atom('p'), Not(Atom('p')))),
    ]

    for label, formula in examples:
        clauses = to_cnf_clauses(formula)
        clause_str = " ∧ ".join(
            "(" + " ∨ ".join(sorted(c)) + ")" for c in clauses
        ) if clauses else "⊤  (tautology — empty clause set)"
        print(f"  {label}")
        print(f"    → {clause_str}\n")


# ---------------------------------------------------------------------------
# Demo 3 — Belief Base with priority order
# ---------------------------------------------------------------------------

def demo_belief_base() -> None:
    section("Demo 3 — Ordered Belief Base")

    bb = BeliefBase()
    rain  = Atom('rain')
    fog   = Atom('fog')
    bus   = Atom('bus_taken')

    # Background knowledge (most entrenched, priority 0)
    bb.add(Implies(Or(rain, fog), bus), priority=0)
    bb.add(Implies(Not(rain), fog),     priority=0)

    # Observations (less entrenched, priority 5)
    bb.add(rain, priority=5)

    print(f"  Belief base: {bb}")
    print(f"  Formulas: {bb.formulas()}")
    print()

    show("Base ⊨ bus_taken (because rain → bus)",
         entails(bb.formulas(), bus))

    show("Base ⊨ (rain ∨ fog) [directly holds]",
         entails(bb.formulas(), Or(rain, fog)))

    show("Base ⊭ ¬rain (rain is in the base)",
         not entails(bb.formulas(), Not(rain)))

    print(f"\n  Least entrenched formula: {bb.least_entrenched()}")


# ---------------------------------------------------------------------------
# Demo 4 — Parser round-trip
# ---------------------------------------------------------------------------

def demo_parser() -> None:
    section("Demo 4 — Parser Round-trip")

    formulas_str = [
        "p -> q",
        "~p | q",
        "(p & q) -> r",
        "p <-> (q | r)",
        "~(p & ~q) -> r",
        "p -> q -> r",    # right-associative: p -> (q -> r)
    ]

    for s in formulas_str:
        f = parse(s)
        print(f"  Input:  {s!r}")
        print(f"  AST:    {f!r}")
        print()


# ---------------------------------------------------------------------------
# Demo 5 — AGM Postulate Sanity (Member C's tests will build on this)
# ---------------------------------------------------------------------------

def demo_agm_patterns() -> None:
    section("Demo 5 — AGM Postulate Patterns")

    p = Atom('p');  q = Atom('q');  r = Atom('r')

    # Success:   revised belief base should entail the revision formula
    show("Success pattern:    {φ} ⊨ φ",
         entails([p], p))

    # Inclusion: result ⊆ B ∪ {φ}
    show("Inclusion pattern:  {p,q,r} ⊨ r  (r stays after expansion)",
         entails([p, q, r], r))

    # Vacuity:   if B ⊭ ¬φ, then B * φ = B + φ (no contraction needed)
    show("Vacuity:            {p} ⊭ ¬q  (should be False → vacuous expansion OK)",
         not entails([p], Not(q)))

    # Consistency: {p,q} is consistent (does not entail ⊥)
    show("Consistency:        {p,q} ⊭ p∧¬p  (base is consistent)",
         not entails([p, q], And(p, Not(p))))

    # Extensionality: φ ≡ ψ → (B * φ) ≡ (B * ψ)
    show("Extensionality:     p ≡ ¬¬p  (p ⊨ ¬¬p)",
         entails([p], Not(Not(p))))
    show("Extensionality:     ¬¬p ≡ p  (¬¬p ⊨ p)",
         entails([Not(Not(p))], p))


# ---------------------------------------------------------------------------
# Demo 6 — Revision Engine (Member C)
# ---------------------------------------------------------------------------

def demo_revision_engine() -> None:
    section("Demo 6 — Revision Engine: expand / contract / revise (Member C)")

    rain  = Atom('rain')
    sunny = Atom('sunny')
    coat  = Atom('coat')

    bb = BeliefBase()
    bb.add(rain,                   priority=0)   # strongly believe it's raining
    bb.add(Implies(rain, coat),    priority=0)   # rain → wear a coat
    bb.add(Not(sunny),             priority=5)   # weakly believe not sunny

    eng = RevisionEngine(bb)

    show("Before revision: base ⊨ coat  (rain → coat, rain in base)",
         entails(eng.bb.formulas(), coat))
    show("Before revision: base ⊨ ¬sunny",
         entails(eng.bb.formulas(), Not(sunny)))

    print("\n  → Revising: new weather report says it is sunny (¬rain)\n")
    eng.revise(Not(rain))

    show("After revise(¬rain): base ⊨ ¬rain",
         entails(eng.bb.formulas(), Not(rain)))
    show("After revise(¬rain): base is consistent",
         eng.is_consistent())

    print("\n  → Contracting away 'coat'...\n")
    eng.contract(coat)
    show("After contract(coat): base ⊭ coat",
         not entails(eng.bb.formulas(), coat))

    print()
    print("  AGM Postulates demonstrated:")
    show("  K*1 Success:      revise(¬rain) → base ⊨ ¬rain",
         entails(eng.bb.formulas(), Not(rain)))
    show("  K*4 Consistency:  base is consistent after revision",
         eng.is_consistent())


# ---------------------------------------------------------------------------
# Demo 7 — Plausibility Order (Optional Task 1)
# ---------------------------------------------------------------------------

def demo_plausibility_order() -> None:
    section("Demo 7 — Plausibility Order / Possible-Worlds Revision (Optional 1)")

    atoms = ['rain', 'wet', 'bus']
    po = PlausibilityOrder(atoms)

    rain = Atom('rain')
    wet  = Atom('wet')
    bus  = Atom('bus')

    print("  Initial state: all 8 worlds equally plausible (rank 0)\n")
    show("  {} ⊨ rain?  (no beliefs yet — should be False)",
         po.entails(rain))

    print("\n  → Asserting: rain → wet\n")
    po.assert_belief(Implies(rain, wet))
    show("  After rain→wet: ⊨ (rain→wet)?", po.entails(Implies(rain, wet)))

    print("\n  → Asserting: rain\n")
    po.assert_belief(rain)
    show("  After rain: ⊨ rain?",    po.entails(rain))
    show("  After rain: ⊨ wet?",     po.entails(wet))

    print("\n  Most plausible worlds after asserting rain:")
    for w in po.most_plausible():
        print(f"    {po.world_to_str(w)}")

    print("\n  → Revision: new evidence — it is NOT raining\n")
    po.revise(Not(rain))

    show("  After revise(¬rain): ⊨ ¬rain?", po.entails(Not(rain)))
    show("  After revise(¬rain): min worlds all satisfy ¬rain?",
         all('rain' not in w for w in po.most_plausible()))

    print("\n  Most plausible worlds after revise(¬rain):")
    for w in po.most_plausible():
        print(f"    {po.world_to_str(w)}")


# ---------------------------------------------------------------------------
# Demo 8 — Mastermind AI (Optional Task 2)
# ---------------------------------------------------------------------------

def demo_mastermind() -> None:
    section("Demo 8 — Mastermind AI via Belief Revision (Optional 2)")

    print("  The agent maintains a belief base of 1296 candidate codes.")
    print("  Feedback from each guess is treated as a revision: impossible")
    print("  codes are contracted from the belief state.\n")

    test_cases = [
        (1, 2, 3, 4),
        (6, 6, 5, 5),
        (3, 1, 4, 2),
    ]

    for secret in test_cases:
        print(f"  Secret: {secret}")
        n = play_mastermind(secret, verbose=True)
        print()

    print("  Belief-revision mapping:")
    print("    • Initial state:  all 1296 codes believed possible")
    print("    • Each feedback:  inconsistent codes contracted (¬code_i added)")
    print("    • make_guess():   pick a code still believed possible (minimax)")
    print("    • Solved when:    exactly 1 code remains in the belief base")




if __name__ == '__main__':
    print("\n*** Belief Revision Agent — Implementation Demo ***")
    print("    02180 Intro to AI, SP25  |  Members A + B + C + Optionals\n")

    demo_basic_entailment()
    demo_cnf_trace()
    demo_belief_base()
    demo_parser()
    demo_agm_patterns()
    demo_revision_engine()
    demo_plausibility_order()
    demo_mastermind()

    print("\n*** All demos complete ***\n")
