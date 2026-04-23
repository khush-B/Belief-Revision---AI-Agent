"""
cnf.py — Conjunctive Normal Form (CNF) Conversion
===================================================
Transforms any propositional Formula into a list of clauses in CNF.

A formula is in CNF when it is a conjunction (AND) of clauses, where
each clause is a disjunction (OR) of *literals*, and a literal is either
a propositional variable (positive literal) or its negation (negative
literal).

Conversion algorithm — four deterministic passes
-------------------------------------------------
  Pass 1  eliminate_biconditional
          φ ↔ ψ  →  (φ → ψ) ∧ (ψ → φ)

  Pass 2  eliminate_implication
          φ → ψ  →  ¬φ ∨ ψ

  Pass 3  push_negation_inward  (NNF — Negation Normal Form)
          ¬¬φ    →  φ                 (double-negation)
          ¬(φ∧ψ) →  ¬φ ∨ ¬ψ          (De Morgan #1)
          ¬(φ∨ψ) →  ¬φ ∧ ¬ψ          (De Morgan #2)

  Pass 4  distribute_or_over_and  (→ CNF)
          φ ∨ (ψ ∧ χ)  →  (φ ∨ ψ) ∧ (φ ∨ χ)
          (φ ∧ ψ) ∨ χ  →  (φ ∨ χ) ∧ (ψ ∨ χ)

Then the CNF tree is flattened into a Python list of frozensets.

Known limitation
----------------
  The standard distribution step can produce exponentially many clauses in
  the worst case (e.g. (p1∧q1)∨(p2∧q2)∨…∨(pn∧qn) → O(2^n) clauses).
  For the belief-revision context (small knowledge bases) this is acceptable.
  A Tseitin transformation would avoid the blowup at the cost of introducing
  auxiliary variables — left as a documented extension point.

Literal representation
----------------------
  Positive literal  →  the atom name as a plain string, e.g. "rain"
  Negative literal  →  the atom name prefixed with "~",   e.g. "~rain"
  This convention is shared with resolution.py.
"""

from __future__ import annotations
import sys
from typing import List, FrozenSet

from formula import Formula, Atom, Not, And, Or, Implies, Biconditional

# Increase recursion limit to handle moderately deep formula trees.
# A deeply nested formula (depth > 500) would still be unusual in practice.
sys.setrecursionlimit(5000)

# Type aliases for clarity
Literal = str                    # "p" or "~p"
Clause  = FrozenSet[Literal]     # frozenset of literals (one clause)


# ---------------------------------------------------------------------------
# Literal helpers
# ---------------------------------------------------------------------------

def negate_literal(lit: Literal) -> Literal:
    """
    Return the complement of a literal.

    "p"  → "~p"
    "~p" → "p"

    After CNF conversion, literals always have at most one leading '~',
    so this is safe. A double-negation "~~p" would be a bug in the
    conversion pipeline and is caught in push_negation_inward.
    """
    if lit.startswith('~'):
        return lit[1:]
    return '~' + lit


def is_tautological_clause(clause: Clause) -> bool:
    """
    Return True if the clause is a tautology (contains both l and ¬l).

    Tautological clauses are always satisfied and carry no information;
    they should be dropped early to keep the clause set small.
    """
    for lit in clause:
        if negate_literal(lit) in clause:
            return True
    return False


# ---------------------------------------------------------------------------
# Pass 1 — Eliminate biconditionals
# ---------------------------------------------------------------------------

def _elim_biconditional(f: Formula) -> Formula:
    """φ ↔ ψ  →  (φ → ψ) ∧ (ψ → φ).  Recurse over the full tree."""
    if isinstance(f, Atom):
        return f
    if isinstance(f, Not):
        return Not(_elim_biconditional(f.operand))
    if isinstance(f, And):
        return And(_elim_biconditional(f.left), _elim_biconditional(f.right))
    if isinstance(f, Or):
        return Or(_elim_biconditional(f.left), _elim_biconditional(f.right))
    if isinstance(f, Implies):
        return Implies(_elim_biconditional(f.left), _elim_biconditional(f.right))
    if isinstance(f, Biconditional):
        l = _elim_biconditional(f.left)
        r = _elim_biconditional(f.right)
        return And(Implies(l, r), Implies(r, l))
    raise TypeError(f"Unknown formula node: {type(f).__name__}")


# ---------------------------------------------------------------------------
# Pass 2 — Eliminate implications
# ---------------------------------------------------------------------------

def _elim_implication(f: Formula) -> Formula:
    """
    φ → ψ  →  ¬φ ∨ ψ.
    Must be called AFTER _elim_biconditional, so no Biconditional nodes remain.
    """
    if isinstance(f, Atom):
        return f
    if isinstance(f, Not):
        return Not(_elim_implication(f.operand))
    if isinstance(f, And):
        return And(_elim_implication(f.left), _elim_implication(f.right))
    if isinstance(f, Or):
        return Or(_elim_implication(f.left), _elim_implication(f.right))
    if isinstance(f, Implies):
        l = _elim_implication(f.left)
        r = _elim_implication(f.right)
        return Or(Not(l), r)
    if isinstance(f, Biconditional):
        # Guard: should never reach here after pass 1
        raise AssertionError("Biconditional still present after pass 1 — check pipeline order.")
    raise TypeError(f"Unknown formula node: {type(f).__name__}")


# ---------------------------------------------------------------------------
# Pass 3 — Push negations inward (NNF)
# ---------------------------------------------------------------------------

def _push_negation(f: Formula) -> Formula:
    """
    Drive all negations down to the literal level.

    Rules applied:
      ¬¬φ      →  φ                     (double-negation elimination)
      ¬(φ∧ψ)  →  (¬φ ∨ ¬ψ)             (De Morgan #1)
      ¬(φ∨ψ)  →  (¬φ ∧ ¬ψ)             (De Morgan #2)

    Precondition: no Implies or Biconditional nodes (passes 1 & 2 done).

    Fallback addressed: if a Not wraps another compound after distribution,
    the function recurses on the newly created Or/And to ensure complete NNF.
    """
    if isinstance(f, Atom):
        return f

    if isinstance(f, Not):
        inner = f.operand
        if isinstance(inner, Atom):
            return f                            # ¬p — already a literal
        if isinstance(inner, Not):
            return _push_negation(inner.operand)  # ¬¬φ → φ
        if isinstance(inner, And):
            # ¬(φ∧ψ) → (¬φ∨¬ψ)
            return _push_negation(Or(Not(inner.left), Not(inner.right)))
        if isinstance(inner, Or):
            # ¬(φ∨ψ) → (¬φ∧¬ψ)
            return _push_negation(And(Not(inner.left), Not(inner.right)))
        # Implies / Biconditional should not appear here after passes 1 & 2
        raise AssertionError(
            f"Unexpected node type inside Not after elimination passes: "
            f"{type(inner).__name__}"
        )

    if isinstance(f, And):
        return And(_push_negation(f.left), _push_negation(f.right))
    if isinstance(f, Or):
        return Or(_push_negation(f.left), _push_negation(f.right))

    raise TypeError(
        f"Unexpected formula node in NNF pass: {type(f).__name__}. "
        "Ensure elimination passes ran first."
    )


# ---------------------------------------------------------------------------
# Pass 4 — Distribute OR over AND (→ CNF tree)
# ---------------------------------------------------------------------------

def _distribute_or(f: Formula) -> Formula:
    """
    Distribute OR over AND, converting NNF to CNF.

    Base cases: Atom and Not(Atom) are already literals — return unchanged.
    Recursive cases:
      And(φ,ψ)         →  And(distribute(φ), distribute(ψ))
      Or(φ, And(l,r))  →  And(distribute(Or(φ,l)), distribute(Or(φ,r)))
      Or(And(l,r), ψ)  →  And(distribute(Or(l,ψ)), distribute(Or(r,ψ)))
      Or(φ, ψ)         →  Or(distribute(φ), distribute(ψ))   [no And inside]

    Termination: every recursive call deals with a strictly smaller sub-tree
    because the restructuring only fires when an And appears directly under
    an Or — and each such step reduces the nesting depth of Or/And pairs.
    """
    if isinstance(f, Atom) or isinstance(f, Not):
        return f   # literal — base case

    if isinstance(f, And):
        return And(_distribute_or(f.left), _distribute_or(f.right))

    if isinstance(f, Or):
        left  = _distribute_or(f.left)
        right = _distribute_or(f.right)

        # φ ∨ (ψ ∧ χ)
        if isinstance(right, And):
            return _distribute_or(
                And(Or(left, right.left), Or(left, right.right))
            )
        # (φ ∧ ψ) ∨ χ
        if isinstance(left, And):
            return _distribute_or(
                And(Or(left.left, right), Or(left.right, right))
            )
        # Neither side contains And at top level — already a CNF clause
        return Or(left, right)

    raise TypeError(f"Unexpected node in CNF distribution: {type(f).__name__}")


# ---------------------------------------------------------------------------
# Flatten CNF tree → list of clause sets
# ---------------------------------------------------------------------------

def _extract_clauses(f: Formula) -> List[Clause]:
    """
    Recursively flatten a CNF formula tree into a list of frozenset clauses.
    The tree is either:
      - A conjunction And(…) — split into two sub-lists and concatenate
      - A single clause (Or tree of literals, or a bare literal)
    """
    if isinstance(f, And):
        return _extract_clauses(f.left) + _extract_clauses(f.right)
    # Everything else is a single clause
    return [frozenset(_extract_literals(f))]


def _extract_literals(f: Formula) -> List[Literal]:
    """
    Collect all literals from an Or-tree (a single clause).

    Fallback: if a non-literal appears here (e.g. nested And), it means the
    distribution step was incomplete — raise clearly rather than silently
    producing wrong results.
    """
    if isinstance(f, Or):
        return _extract_literals(f.left) + _extract_literals(f.right)
    if isinstance(f, Atom):
        return [f.name]
    if isinstance(f, Not):
        if isinstance(f.operand, Atom):
            return ['~' + f.operand.name]
        raise ValueError(
            f"Non-literal inside clause after CNF conversion: {f!r}. "
            "The formula may have been passed to _extract_literals before "
            "all four CNF passes completed."
        )
    raise TypeError(
        f"Unexpected node type in clause: {type(f).__name__}. "
        "Expected Or, Atom, or Not(Atom)."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def to_cnf_clauses(formula: Formula) -> List[Clause]:
    """
    Convert a propositional formula to CNF and return its clause list.

    Each clause is a frozenset of literal strings, e.g.:
      frozenset({"p", "~q", "r"})   represents the clause  p ∨ ¬q ∨ r

    Tautological clauses (those containing both l and ¬l) are removed
    because they are trivially true and add no constraint.

    Args:
        formula: Any propositional Formula object.

    Returns:
        A list of frozenset[str] clauses in CNF.
        Returns an empty list only when every clause is tautological
        (i.e., the formula is a tautology — always true).

    Examples:
        >>> to_cnf_clauses(Implies(Atom('p'), Atom('q')))
        [frozenset({'~p', 'q'})]

        >>> to_cnf_clauses(Or(Atom('p'), Not(Atom('p'))))
        []   # tautology — removed
    """
    f = _elim_biconditional(formula)
    f = _elim_implication(f)
    f = _push_negation(f)
    f = _distribute_or(f)

    clauses = _extract_clauses(f)

    # Remove tautologies — they are always satisfied and carry no information
    return [c for c in clauses if not is_tautological_clause(c)]
