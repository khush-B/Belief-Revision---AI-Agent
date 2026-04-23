"""
main.py — Belief Revision Agent Demo
=====================================
Demonstrates Member B's logical entailment engine plus the full pipeline
(Members A + B + C integrated).

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
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print("\n*** Belief Revision Agent — Implementation Demo ***")
    print("    02180 Intro to AI, SP25  |  Member B: Entailment Engine\n")

    demo_basic_entailment()
    demo_cnf_trace()
    demo_belief_base()
    demo_parser()
    demo_agm_patterns()

    print("\n*** All demos complete ***\n")
