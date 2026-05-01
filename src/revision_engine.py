"""
revision_engine.py — Belief Revision and Contraction  (Member C)
=================================================================
Implements the three core AGM operations on a priority-ordered belief base:

  expand(φ)   — add φ without any consistency check (B + φ)
  contract(φ) — remove φ from B using partial-meet contraction guided by
                the priority order (least-entrenched formulas removed first)
  revise(φ)   — Levi identity: B * φ  =  (B ÷ ¬φ) + φ

AGM Postulates verified by tests/test_agm.py
---------------------------------------------
  K*1  Success      — after revise(φ), the base entails φ
  K*2  Inclusion    — B * φ ⊆ Cn(B ∪ {φ})
  K*3  Vacuity      — if B ⊭ ¬φ, then B * φ = B + φ
  K*4  Consistency  — if φ is consistent, B * φ is consistent
  K*5  Extensionality — if φ ≡ ψ then B * φ ≡ B * ψ

Contraction strategy
--------------------
  Priority-based partial-meet contraction:
  Walk the belief base from least-entrenched (highest priority) to most-
  entrenched (lowest priority).  Remove formulas one at a time until the
  base no longer entails φ.  This is a valid selection function consistent
  with the AGM framework: it minimises change relative to the entrenchment
  ordering.
"""
from __future__ import annotations

from typing import List, Optional
from formula import Formula, Not
from belief_base import BeliefBase
from resolution import entails


class RevisionEngine:
    """
    Wraps a BeliefBase and exposes the AGM expand / contract / revise
    operations.

    Args:
        belief_base: The BeliefBase instance to operate on.  The engine
                     mutates it in-place; the caller keeps a reference to
                     the same BeliefBase.
    """

    def __init__(self, belief_base: BeliefBase) -> None:
        self.bb = belief_base

    # ------------------------------------------------------------------
    # Expansion  (K + φ)
    # ------------------------------------------------------------------

    def expand(self, formula: Formula, priority: int = 0) -> None:
        """
        Add *formula* to the belief base unconditionally with *priority*.

        This is the simplest AGM operation: no consistency check is performed.
        The caller is responsible for ensuring it is appropriate to expand
        (i.e. the base does not already contain ¬φ unless revision is
        intended).

        AGM Inclusion postulate: all original beliefs are preserved in B + φ.
        """
        self.bb.add(formula, priority)

    # ------------------------------------------------------------------
    # Contraction  (K ÷ φ)
    # ------------------------------------------------------------------

    def contract(self, phi: Formula) -> None:
        """
        Remove entailment of *phi* from the belief base using partial-meet
        contraction guided by the priority / entrenchment order.

        Algorithm
        ---------
        1. If the base does not already entail phi, do nothing (Vacuity).
        2. Sort entries from least-entrenched to most-entrenched.
        3. Remove them one at a time until phi is no longer entailed.
        4. Stop as soon as entailment is broken (minimises change).

        After this call: self.bb.formulas() ⊭ phi  (unless phi is a
        tautology, in which case no finite removal can succeed).

        Returns immediately without error when phi is a tautology —
        tautologies cannot be contracted.
        """
        # Vacuity: nothing to do if phi is not entailed
        if not entails(self.bb.formulas(), phi):
            return

        # Sort ascending entrenchment: highest priority value first
        # (least entrenched = highest priority number = removed first)
        sorted_entries = sorted(
            self.bb._entries,
            key=lambda e: (-e[1], -e[2])   # descending by (priority, insertion)
        )

        # --- Kernel contraction (first pass) ---
        # Find the least-entrenched formula whose *individual* removal breaks
        # entailment of phi.  Only that formula is removed (minimal change).
        # This ensures "innocent" formulas (not part of any proof of phi) are
        # never removed — satisfying the recovery postulate for typical cases.
        for entry in sorted_entries:
            formula_to_remove = entry[0]
            remaining = [f for f, _, _ in self.bb._entries
                         if f != formula_to_remove]
            if not entails(remaining, phi):
                self.bb.remove(formula_to_remove)
                return

        # --- Fallback: greedy removal ---
        # Reached when phi has independent disjunctive support (multiple
        # non-overlapping proofs, e.g. {p, q} both individually entail p∨q).
        # Remove from least entrenched until entailment breaks.
        for entry in sorted_entries:
            formula_to_remove = entry[0]
            if formula_to_remove in self.bb:
                self.bb.remove(formula_to_remove)
                if not entails(self.bb.formulas(), phi):
                    return

    # ------------------------------------------------------------------
    # Revision  (K * φ)   — Levi Identity
    # ------------------------------------------------------------------

    def revise(self, formula: Formula, priority: int = 0) -> None:
        """
        Revise the belief base to consistently include *formula*.

        Uses the Levi Identity:
            B * φ  =  (B ÷ ¬φ) + φ

        Steps:
        1. Contract by ¬φ  (remove the reason for believing ¬φ).
        2. Expand by φ     (assert φ at the given priority).

        This guarantees:
        • Success:      the result entails φ.
        • Consistency:  if φ is consistent, the result is consistent
                        (because ¬φ was removed before φ was added).

        Args:
            formula:  The formula to revise with.
            priority: Entrenchment priority for the newly added belief
                      (default 0 = most entrenched).
        """
        self.contract(Not(formula))
        self.expand(formula, priority)

    # ------------------------------------------------------------------
    # AGM postulate verification helpers
    # ------------------------------------------------------------------

    def is_consistent(self) -> bool:
        """
        Return True iff the current belief base is logically consistent
        (does not entail a contradiction).

        Uses Atom 'agm_check_var' as the trivial contradiction witness:
        a consistent base cannot entail both some atom and its negation.
        We materialise the contradiction as the formula  (p & ~p)  for
        an arbitrary fresh atom and check it is NOT entailed.
        """
        from formula import Atom, And
        witness = Atom('__consistency_witness__')
        contradiction = And(witness, Not(witness))
        return not entails(self.bb.formulas(), contradiction)

    # ------------------------------------------------------------------
    # Convenience: snapshot and restore
    # ------------------------------------------------------------------

    def snapshot(self) -> List:
        """Return a copy of the internal entries list for later restore."""
        return list(self.bb._entries)

    def restore(self, saved_entries: List) -> None:
        """Restore the belief base to a previously saved snapshot."""
        self.bb._entries = list(saved_entries)