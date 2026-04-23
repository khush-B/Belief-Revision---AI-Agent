"""
resolution.py — Resolution-Based SAT Checking and Logical Entailment
====================================================================
Implements propositional-logic entailment using the resolution refutation
procedure, with no external logic packages.

Core principle
--------------
  B ⊨ φ   (B entails φ)
  iff
  B ∪ {¬φ}  is unsatisfiable (no model satisfies all beliefs AND ¬φ).

  We check unsatisfiability by the *resolution* rule:

      C₁ ∪ {l}   C₂ ∪ {¬l}
      ─────────────────────────
           C₁ ∪ C₂              (resolvent)

  If the *empty clause* □ can be derived, the clause set is unsatisfiable.
  If no new clause can be added (fixpoint), the set is satisfiable.

Algorithm — full propositional resolution
------------------------------------------
  1.  Convert every formula to CNF; collect into one clause set S.
  2.  Remove tautological clauses (p ∨ ¬p type).
  3.  If □ ∈ S already, return UNSAT immediately.
  4.  Repeat until fixpoint or □ found:
        a.  For every unprocessed pair (C₁, C₂) ∈ S × S:
              For every complementary literal pair (l, ¬l):
                  Compute resolvent R = (C₁ - {l}) ∪ (C₂ - {¬l})
                  If R = □  → return UNSAT
                  If R is tautological  → discard
                  If ∃ existing E ⊆ R  → discard (forward subsumption)
                  Else add R to new_clauses
        b.  If new_clauses ∩ (S_complement) = ∅  → return SAT (fixpoint)
        c.  S ← S ∪ new_clauses

Termination guarantee
---------------------
  Over a finite set of propositional variables, there are finitely many
  distinct subsets of literals, hence finitely many possible clauses.
  Because we only add new (non-subsumed) clauses to S, the algorithm
  terminates.

Known fallback — performance
-----------------------------
  Full resolution is PSPACE-complete in the worst case.  For the small
  belief bases used in this assignment it is fast enough.  If performance
  becomes an issue, adding unit propagation or the DPLL procedure would
  be the right extension point.
"""

from __future__ import annotations

from typing import List, Set, FrozenSet

from formula import Formula, Not
from cnf import to_cnf_clauses, Clause, Literal, negate_literal, is_tautological_clause


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

def _resolve_all(c1: Clause, c2: Clause) -> List[Clause]:
    """
    Compute ALL binary resolvents of two clauses.

    For each literal l ∈ C₁ such that ¬l ∈ C₂, produce:
        R = (C₁ − {l}) ∪ (C₂ − {¬l})

    Fallback addressed: returning only the *first* complementary literal per
    pair (as a naïve implementation would do) is incomplete — multiple
    resolution steps may be possible between the same pair.  We iterate
    all literals in c1 to find every applicable l.

    Tautological resolvents are discarded immediately to keep the clause set
    lean.  A resolvent is tautological iff some atom appears both positive
    and negative in R.
    """
    resolvents: List[Clause] = []
    for lit in c1:
        neg = negate_literal(lit)
        if neg in c2:
            resolvent = frozenset((c1 - {lit}) | (c2 - {neg}))
            if not is_tautological_clause(resolvent):
                resolvents.append(resolvent)
    return resolvents


# ---------------------------------------------------------------------------
# Public: satisfiability check
# ---------------------------------------------------------------------------

def is_unsatisfiable(clauses: List[Clause]) -> bool:
    """
    Determine whether a set of CNF clauses is unsatisfiable using full
    propositional resolution.

    Args:
        clauses: A list of Clause objects (frozenset of literals).

    Returns:
        True  if the clause set is unsatisfiable (contradiction derivable).
        False if the clause set is satisfiable (no contradiction exists).

    Optimisations applied:
      • Tautological clauses removed on entry.
      • Visited-pair set prevents re-resolving the same (C₁, C₂) pair.
      • Forward subsumption: a new resolvent R is discarded if ∃ E ∈ S
        with E ⊆ R (E already subsumes R, making R weaker/redundant).
    """
    # De-duplicate and strip tautologies
    clause_set: Set[Clause] = set()
    for c in clauses:
        if not is_tautological_clause(c):
            clause_set.add(c)

    # Immediate empty-clause check (e.g. formula is literally ⊥ = False)
    if frozenset() in clause_set:
        return True

    # Track which (unordered) pairs we have already resolved so we never
    # redo work.  Using frozenset({c1, c2}) as the key is safe because
    # clause_set elements are unique frozensets (themselves hashable).
    resolved_pairs: Set[FrozenSet] = set()

    while True:
        new_clauses: Set[Clause] = set()
        clause_list = list(clause_set)

        for i in range(len(clause_list)):
            for j in range(i + 1, len(clause_list)):
                c1, c2 = clause_list[i], clause_list[j]

                # frozenset({c1, c2}) is order-independent pair identifier.
                # Because clause_set has unique elements, c1 != c2 always.
                pair_key: FrozenSet = frozenset({c1, c2})
                if pair_key in resolved_pairs:
                    continue
                resolved_pairs.add(pair_key)

                for resolvent in _resolve_all(c1, c2):
                    # Empty clause → contradiction
                    if len(resolvent) == 0:
                        return True

                    # Forward subsumption: skip if an existing clause E ⊆ R
                    # (E is "stronger" than R; R adds nothing new)
                    if any(existing <= resolvent for existing in clause_set):
                        continue

                    new_clauses.add(resolvent)

        # Fixpoint: no clause was added that was not already known → SAT
        truly_new = new_clauses - clause_set
        if not truly_new:
            return False

        clause_set |= truly_new


# ---------------------------------------------------------------------------
# Public: entailment check  (the function every teammate calls)
# ---------------------------------------------------------------------------

def entails(belief_base: List[Formula], phi: Formula) -> bool:
    """
    Check whether a belief base B logically entails a formula φ.

    Implements:  B ⊨ φ   iff   B ∪ {¬φ}  is unsatisfiable.

    Args:
        belief_base: Iterable of Formula objects representing the agent's
                     current beliefs.  May be an empty list (empty belief
                     base), a plain Python list, or any iterable of Formula.
        phi:         The formula whose entailment is to be tested.

    Returns:
        True   if every model of B also satisfies φ.
        False  if there exists a model of B that falsifies φ.

    Special cases handled correctly:
      • Empty belief base: entails([], tautology) → True
                           entails([], non-tautology) → False
      • Contradictory belief base: entails([p, ¬p], anything) → True
        (ex falso quodlibet — a contradictory base entails everything)
      • φ is a tautology: always True regardless of belief base.

    Examples:
        >>> p, q = Atom('p'), Atom('q')
        >>> entails([p, Implies(p, q)], q)      # modus ponens
        True
        >>> entails([p], q)                     # not entailed
        False
        >>> entails([p, Not(p)], q)             # ex falso quodlibet
        True
    """
    # Build B ∪ {¬φ} as a flat list of CNF clauses
    all_clauses: List[Clause] = []

    for formula in belief_base:
        all_clauses.extend(to_cnf_clauses(formula))

    # Add ¬φ  — if B ∪ {¬φ} is unsat, then B ⊨ φ
    all_clauses.extend(to_cnf_clauses(Not(phi)))

    return is_unsatisfiable(all_clauses)
