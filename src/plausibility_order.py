"""
plausibility_order.py — Plausibility-Order Belief Representation  (Optional 1)
================================================================================
Implements the *possible-worlds* variant of belief revision described in
the assignment's Optional Task 1:

  "Represent possible worlds and a plausibility ordering, define entailment
   as 'true in all most plausible worlds', and implement a lexicographic or
   minimal revision method."

Overview
--------
A **plausibility order** is a total pre-order (≼) on possible worlds, where
world w₁ ≼ w₂ means "w₁ is at least as plausible as w₂".  The *most
plausible* worlds are those minimal under ≼.

For a set of propositional atoms {a₁, …, aₙ}, a *possible world* is a
complete truth-value assignment (a frozenset of true atoms).

Entailment
----------
  B ⊨_κ φ   iff   φ is true in every world of minimum rank

Revision — Lexicographic / Minimal Change
------------------------------------------
Revising by φ is done via *conditional beliefs*: the new ordering ranks φ-
worlds first (by their original rank) and ¬φ-worlds after.  This is the
**lexicographic revision** (also called Spohn conditioning) and satisfies
all AGM postulates.

  rank_φ(w) = (0, rank(w))   if  w ⊨ φ
  rank_φ(w) = (1, rank(w))   if  w ⊭ φ

Usage
-----
  from plausibility_order import PlausibilityOrder
  from formula import Atom, Implies, Not

  atoms = ['p', 'q']
  po = PlausibilityOrder(atoms)
  po.assert_belief(Implies(Atom('p'), Atom('q')))
  po.assert_belief(Atom('p'))

  print(po.entails(Atom('q')))      # True
  po.revise(Not(Atom('p')))
  print(po.entails(Not(Atom('p')))  # True
"""

from __future__ import annotations

from itertools import product
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from formula import Formula, Atom, Not, And, Or, Implies, Biconditional


# ---------------------------------------------------------------------------
# World type
# ---------------------------------------------------------------------------

World = FrozenSet[str]  # frozenset of atom names that are TRUE in this world


def _eval_formula(formula: Formula, world: World) -> bool:
    """
    Evaluate *formula* in *world* using a recursive descent.

    Args:
        formula: A Formula AST node.
        world:   A frozenset of atom names that are TRUE.
                 Any atom NOT in the frozenset is FALSE.

    Returns:
        The truth value of the formula in this world.
    """
    if isinstance(formula, Atom):
        return formula.name in world
    if isinstance(formula, Not):
        return not _eval_formula(formula.operand, world)
    if isinstance(formula, And):
        return _eval_formula(formula.left, world) and _eval_formula(formula.right, world)
    if isinstance(formula, Or):
        return _eval_formula(formula.left, world) or _eval_formula(formula.right, world)
    if isinstance(formula, Implies):
        return (not _eval_formula(formula.left, world)) or _eval_formula(formula.right, world)
    if isinstance(formula, Biconditional):
        return _eval_formula(formula.left, world) == _eval_formula(formula.right, world)
    raise TypeError(f"Unknown formula node: {type(formula).__name__}")


def _generate_all_worlds(atoms: List[str]) -> List[World]:
    """
    Generate all 2^n possible worlds over a set of atom names.

    A world is represented as a frozenset of the TRUE atoms.

    Args:
        atoms: List of propositional variable names.

    Returns:
        A list of 2^n worlds (frozensets).
    """
    worlds = []
    for truth_values in product([False, True], repeat=len(atoms)):
        world = frozenset(name for name, tv in zip(atoms, truth_values) if tv)
        worlds.append(world)
    return worlds


# ---------------------------------------------------------------------------
# PlausibilityOrder class
# ---------------------------------------------------------------------------

class PlausibilityOrder:
    """
    A plausibility-ordered belief state over propositional variables.

    Internally keeps a *rank* mapping  rank: World → int  where a lower
    rank means *more plausible*.  All worlds start with rank 0 (equally
    most plausible).  Asserting a belief, or revising, adjusts ranks.

    The *most plausible worlds* are those with the minimum rank value.

    Attributes:
        atoms:  Sorted list of propositional atom names the model covers.
        worlds: All 2^n possible worlds (frozensets of true atom names).
        rank:   dict mapping each World to its non-negative integer rank.
    """

    def __init__(self, atoms: List[str]) -> None:
        """
        Initialise the plausibility order over the given propositional atoms.

        All worlds start with rank 0 (equally most plausible — no beliefs yet).

        Args:
            atoms: List of propositional variable names, e.g. ['p', 'q', 'r'].
        """
        self.atoms: List[str] = sorted(atoms)
        self.worlds: List[World] = _generate_all_worlds(self.atoms)
        # Every world equally plausible at start
        self.rank: Dict[World, int] = {w: 0 for w in self.worlds}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _min_rank(self) -> int:
        """Return the minimum rank value currently in use."""
        return min(self.rank.values())

    def _most_plausible_worlds(self) -> List[World]:
        """Return all worlds with the minimum (most plausible) rank."""
        min_r = self._min_rank()
        return [w for w in self.worlds if self.rank[w] == min_r]

    def _phi_worlds(self, phi: Formula) -> List[World]:
        """Return all worlds in which formula *phi* is true."""
        return [w for w in self.worlds if _eval_formula(phi, w)]

    def _not_phi_worlds(self, phi: Formula) -> List[World]:
        """Return all worlds in which formula *phi* is false."""
        return [w for w in self.worlds if not _eval_formula(phi, w)]

    # ------------------------------------------------------------------
    # Entailment
    # ------------------------------------------------------------------

    def entails(self, phi: Formula) -> bool:
        """
        Return True iff *phi* holds in every most-plausible world.

        Formally:  B ⊨_κ φ   iff   ∀ w ∈ min(≼): w ⊨ φ

        This corresponds to the agent *believing* φ given its current
        plausibility ordering.

        Args:
            phi: The formula whose entailment to test.

        Returns:
            True if phi is believed; False otherwise.
        """
        return all(_eval_formula(phi, w) for w in self._most_plausible_worlds())

    # ------------------------------------------------------------------
    # Revision — lexicographic / minimal-rank update
    # ------------------------------------------------------------------

    def revise(self, phi: Formula) -> None:
        """
        Revise the plausibility order to incorporate *phi* as a new belief.

        Uses *lexicographic revision* (Spohn conditioning):

          new_rank(w) = (0, rank(w))  if  w ⊨ φ
                        (1, rank(w))  if  w ⊭ φ

        Concretely: φ-worlds retain their relative order among themselves
        and are all ranked strictly more plausible than any ¬φ-world.

        This satisfies all AGM revision postulates:
          • Success:          ⊨_κ' φ  after revision (all min worlds satisfy φ)
          • Minimality:       relative order among φ-worlds is unchanged
          • Consistency:      if φ has a model, result is consistent

        Algorithm:
          1. Collect current ranks.
          2. Among φ-worlds: compact ranks to 0, 1, 2, … preserving order.
          3. Among ¬φ-worlds: offset ranks above all φ-world ranks.
        """
        phi_worlds = self._phi_worlds(phi)

        if not phi_worlds:
            # φ has no model — cannot revise with a contradiction.
            # By convention: leave the ordering unchanged (no-op).
            return

        not_phi_worlds = self._not_phi_worlds(phi)

        # ------ Step 1: compact φ-world ranks  ------
        phi_ranks_sorted = sorted(set(self.rank[w] for w in phi_worlds))
        phi_rank_map = {old: new for new, old in enumerate(phi_ranks_sorted)}

        # ------ Step 2: offset ¬φ-world ranks  ------
        max_phi_rank = len(phi_ranks_sorted)   # first available rank after φ-worlds
        not_phi_ranks_sorted = sorted(set(self.rank[w] for w in not_phi_worlds))
        not_phi_rank_map = {
            old: max_phi_rank + new
            for new, old in enumerate(not_phi_ranks_sorted)
        }

        # ------ Apply ------
        for w in phi_worlds:
            self.rank[w] = phi_rank_map[self.rank[w]]
        for w in not_phi_worlds:
            self.rank[w] = not_phi_rank_map[self.rank[w]]

    # ------------------------------------------------------------------
    # Assert / contract (convenience wrappers)
    # ------------------------------------------------------------------

    def assert_belief(self, phi: Formula) -> None:
        """
        Assert *phi* as a new belief, revising if necessary.

        Equivalent to revise(phi) — uses the same lexicographic update.
        Provided as a friendlier name for the 'belief assertion' scenario.
        """
        self.revise(phi)

    def contract(self, phi: Formula) -> None:
        """
        Contract the plausibility order to stop believing *phi*.

        Implemented by promoting some ¬φ-worlds to share the minimum rank,
        so that the minimum set contains at least one ¬φ-world.

        If the agent already does not believe phi, this is a no-op.
        If phi is a tautology, this is a no-op (cannot contract tautologies).
        """
        if not self.entails(phi):
            return   # Vacuity: nothing to do

        # The most plausible ¬φ-worlds should be promoted to the min rank
        not_phi_worlds = self._not_phi_worlds(phi)
        if not not_phi_worlds:
            # phi is a tautology — cannot contract
            return

        min_r = self._min_rank()
        # Find the most plausible ¬φ-worlds (lowest rank among non-phi)
        min_not_phi_rank = min(self.rank[w] for w in not_phi_worlds)
        # Promote them to min_r so they tie with the current minimum
        for w in not_phi_worlds:
            if self.rank[w] == min_not_phi_rank:
                self.rank[w] = min_r

    # ------------------------------------------------------------------
    # Introspection / display helpers
    # ------------------------------------------------------------------

    def ranked_worlds(self) -> List[Tuple[int, World]]:
        """Return list of (rank, world) sorted by ascending rank."""
        return sorted(
            [(r, w) for w, r in self.rank.items()],
            key=lambda x: (x[0], sorted(x[1]))
        )

    def most_plausible(self) -> List[World]:
        """Return the most-plausible worlds (those with the minimum rank)."""
        return self._most_plausible_worlds()

    def world_to_str(self, world: World) -> str:
        """Format a world as a human-readable assignment string."""
        parts = []
        for a in self.atoms:
            parts.append(f"{a}=T" if a in world else f"{a}=F")
        return "{" + ", ".join(parts) + "}"

    def __repr__(self) -> str:
        lines = [f"PlausibilityOrder(atoms={self.atoms})"]
        prev_rank = None
        for rank, world in self.ranked_worlds():
            if rank != prev_rank:
                lines.append(f"  rank {rank}:")
                prev_rank = rank
            lines.append(f"    {self.world_to_str(world)}")
        return "\n".join(lines)
