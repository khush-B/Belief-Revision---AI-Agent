"""
tests/test_belief_base.py — Tests for BeliefBase (Member A)
===========================================================
Covers:
  1. Basic mutation: add, remove, clear
  2. Priority order and epistemic entrenchment
  3. Duplicate-formula handling
  4. least_entrenched() — correct identification of weakest belief
  5. formulas_with_priority() — correct sort order
  6. least_entrenched_implying() — contraction kernel helper
  7. AGM postulate foundations that depend on BeliefBase structure
  8. Alice vs Bob — belief base vs belief set distinction (Lecture 11)

Priority convention (current implementation)
--------------------------------------------
  Lower numeric priority  =  more entrenched  (harder to remove)
  Higher numeric priority =  less entrenched  (first candidate for removal)
  Default priority = 0  (most entrenched)

  Example: background axioms use priority=0; recent observations use priority>0.

Run with:
    cd "Belief-Revision---AI-Agent"
    python -m pytest tests/test_belief_base.py -v
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from formula import Atom, Not, And, Or, Implies, Biconditional
from belief_base import BeliefBase

# ---------------------------------------------------------------------------
# Shared atoms
# ---------------------------------------------------------------------------

p = Atom('p')
q = Atom('q')
r = Atom('r')
s = Atom('s')


# ===========================================================================
# 1.  Basic mutation — add / remove / clear
# ===========================================================================

class TestBeliefBaseBasic:

    def test_empty_base_has_zero_length(self):
        bb = BeliefBase()
        assert len(bb) == 0

    def test_add_single_formula(self):
        bb = BeliefBase()
        bb.add(p)
        assert len(bb) == 1

    def test_add_multiple_formulas(self):
        bb = BeliefBase()
        bb.add(p)
        bb.add(q)
        bb.add(Implies(p, q))
        assert len(bb) == 3

    def test_contains_added_formula(self):
        bb = BeliefBase()
        bb.add(p)
        assert p in bb

    def test_does_not_contain_unadded_formula(self):
        bb = BeliefBase()
        bb.add(p)
        assert q not in bb

    def test_contains_is_syntactic_not_logical(self):
        # p→q is explicitly in base; q is a consequence but NOT explicit
        bb = BeliefBase()
        bb.add(p)
        bb.add(Implies(p, q))
        assert q not in bb          # not explicitly stored
        assert Implies(p, q) in bb  # explicitly stored

    def test_remove_existing_formula(self):
        bb = BeliefBase()
        bb.add(p)
        bb.remove(p)
        assert p not in bb
        assert len(bb) == 0

    def test_remove_missing_formula_raises_key_error(self):
        bb = BeliefBase()
        bb.add(p)
        with pytest.raises(KeyError):
            bb.remove(q)

    def test_remove_from_empty_base_raises_key_error(self):
        bb = BeliefBase()
        with pytest.raises(KeyError):
            bb.remove(p)

    def test_clear_empties_base(self):
        bb = BeliefBase()
        bb.add(p)
        bb.add(q)
        bb.add(r)
        bb.clear()
        assert len(bb) == 0
        assert p not in bb

    def test_clear_on_empty_base_is_safe(self):
        bb = BeliefBase()
        bb.clear()
        assert len(bb) == 0

    def test_iteration_yields_all_formulas(self):
        bb = BeliefBase()
        bb.add(p)
        bb.add(q)
        bb.add(r)
        result = set(bb)
        assert result == {p, q, r}

    def test_formulas_returns_list_of_formula_objects(self):
        bb = BeliefBase()
        bb.add(p)
        bb.add(Implies(p, q))
        fs = bb.formulas()
        assert isinstance(fs, list)
        assert p in fs
        assert Implies(p, q) in fs

    def test_invalid_priority_raises_value_error(self):
        bb = BeliefBase()
        with pytest.raises(ValueError):
            bb.add(p, priority=-1)


# ===========================================================================
# 2.  Duplicate-formula handling
# ===========================================================================

class TestBeliefBaseDuplicates:

    def test_adding_same_formula_twice_keeps_one_entry(self):
        bb = BeliefBase()
        bb.add(p)
        bb.add(p)
        assert len(bb) == 1

    def test_adding_same_formula_updates_priority(self):
        bb = BeliefBase()
        bb.add(p, priority=0)
        bb.add(p, priority=5)  # re-assert with new priority
        assert len(bb) == 1
        pairs = bb.formulas_with_priority()
        priority_of_p = next(pr for f, pr in pairs if f == p)
        assert priority_of_p == 5

    def test_structurally_equal_formulas_are_deduplicated(self):
        bb = BeliefBase()
        bb.add(And(p, q))
        bb.add(And(p, q))
        assert len(bb) == 1

    def test_structurally_different_formulas_are_not_deduplicated(self):
        # And(p,q) and And(q,p) are structurally distinct in this AST
        bb = BeliefBase()
        bb.add(And(p, q))
        bb.add(And(q, p))
        assert len(bb) == 2


# ===========================================================================
# 3.  Priority order — epistemic entrenchment
# ===========================================================================

class TestBeliefBasePriority:

    def test_default_priority_is_zero(self):
        bb = BeliefBase()
        bb.add(p)
        pairs = bb.formulas_with_priority()
        assert pairs[0] == (p, 0)

    def test_formulas_with_priority_returns_all_pairs(self):
        bb = BeliefBase()
        bb.add(p, priority=0)
        bb.add(q, priority=3)
        pairs = dict(bb.formulas_with_priority())
        assert pairs[p] == 0
        assert pairs[q] == 3

    def test_formulas_with_priority_sorted_most_to_least_entrenched(self):
        # Lower priority number = more entrenched → comes first in sorted output
        bb = BeliefBase()
        bb.add(p, priority=0)   # most entrenched
        bb.add(q, priority=5)   # less entrenched
        bb.add(r, priority=10)  # least entrenched
        pairs = bb.formulas_with_priority()
        priorities = [pr for _, pr in pairs]
        assert priorities == sorted(priorities)  # ascending = most entrenched first

    def test_formulas_with_priority_tiebreak_by_insertion_order(self):
        # Same priority: earlier insertion = more entrenched = lower in ascending sort
        bb = BeliefBase()
        bb.add(p, priority=1)  # inserted first → more entrenched
        bb.add(q, priority=1)  # inserted second → less entrenched
        pairs = bb.formulas_with_priority()
        formulas = [f for f, _ in pairs]
        assert formulas[0] == p   # p inserted first, so it is more entrenched
        assert formulas[1] == q


# ===========================================================================
# 4.  least_entrenched()
# ===========================================================================

class TestLeastEntrenched:

    def test_empty_base_returns_none(self):
        bb = BeliefBase()
        assert bb.least_entrenched() is None

    def test_single_formula_is_least_entrenched(self):
        bb = BeliefBase()
        bb.add(p)
        assert bb.least_entrenched() == p

    def test_highest_priority_is_least_entrenched(self):
        bb = BeliefBase()
        bb.add(p, priority=0)   # most entrenched (background)
        bb.add(q, priority=5)   # less entrenched (observation)
        assert bb.least_entrenched() == q

    def test_least_entrenched_among_three(self):
        bb = BeliefBase()
        bb.add(p, priority=0)
        bb.add(q, priority=3)
        bb.add(r, priority=7)
        assert bb.least_entrenched() == r

    def test_tiebreak_by_insertion_later_is_less_entrenched(self):
        # Equal priority: most recently added is less entrenched
        bb = BeliefBase()
        bb.add(p, priority=5)  # added first
        bb.add(q, priority=5)  # added second → less entrenched on tie
        assert bb.least_entrenched() == q

    def test_least_entrenched_after_remove(self):
        bb = BeliefBase()
        bb.add(p, priority=0)
        bb.add(q, priority=5)
        bb.remove(q)
        assert bb.least_entrenched() == p

    def test_least_entrenched_after_priority_update(self):
        bb = BeliefBase()
        bb.add(p, priority=0)
        bb.add(q, priority=3)
        # Demote p to be even less entrenched
        bb.add(p, priority=10)
        assert bb.least_entrenched() == p


# ===========================================================================
# 5.  least_entrenched_implying()
# ===========================================================================

class TestLeastEntrenchedImplying:

    def test_base_not_entailing_phi_returns_empty(self):
        # {p} does not entail q → no removal needed
        bb = BeliefBase()
        bb.add(p, priority=0)
        result = bb.least_entrenched_implying(q)
        assert result == []

    def test_empty_base_returns_empty(self):
        bb = BeliefBase()
        result = bb.least_entrenched_implying(p)
        assert result == []

    def test_single_formula_entailing_itself(self):
        # {p} ⊨ p → remove p
        bb = BeliefBase()
        bb.add(p, priority=0)
        result = bb.least_entrenched_implying(p)
        assert result == [p]

    def test_removes_least_entrenched_sufficient_formula(self):
        # B = {p(priority=5), p→q(priority=0)} ⊨ q
        # p is less entrenched (priority=5).
        # Removing p alone stops entailment → p is in the kernel.
        bb = BeliefBase()
        bb.add(p, priority=5)           # less entrenched
        bb.add(Implies(p, q), priority=0)  # more entrenched
        result = bb.least_entrenched_implying(q)
        assert p in result

    def test_respects_priority_order(self):
        # B = {p(priority=0), p→q(priority=5)} ⊨ q
        # p→q is less entrenched (priority=5).
        # Removing p→q alone stops entailment.
        bb = BeliefBase()
        bb.add(p, priority=0)              # more entrenched
        bb.add(Implies(p, q), priority=5)  # less entrenched
        result = bb.least_entrenched_implying(q)
        assert Implies(p, q) in result

    def test_returned_formulas_are_formula_objects(self):
        bb = BeliefBase()
        bb.add(p, priority=0)
        result = bb.least_entrenched_implying(p)
        for f in result:
            from formula import Formula
            assert isinstance(f, Formula)

    def test_removal_stops_entailment(self):
        # After removing the returned formulas, base should no longer entail phi
        from resolution import entails as _entails

        bb = BeliefBase()
        bb.add(p, priority=5)
        bb.add(Implies(p, q), priority=0)

        phi = q
        to_remove = bb.least_entrenched_implying(phi)
        for f in to_remove:
            bb.remove(f)

        assert not _entails(bb.formulas(), phi)


# ===========================================================================
# 6.  AGM postulate foundations
# ===========================================================================

class TestAGMFoundations:
    """
    Structural tests that confirm the BeliefBase supports the AGM postulate
    checks Member C will implement.  These do not test contraction/revision
    directly — they verify the belief base provides the necessary operations.

    References: AGM postulates for contraction (Lecture 11):
      Success:       if φ ∉ Cn(∅), then φ ∉ Cn(B ÷ φ)
      Inclusion:     B ÷ φ ⊆ B
      Vacuity:       if φ ∉ Cn(B), then B ÷ φ = B
      Consistency:   if B is consistent and φ ∉ Cn(∅), then B ÷ φ is consistent
      Extensionality: if φ ↔ ψ is a tautology, then B ÷ φ = B ÷ ψ
    """

    def test_explicit_membership_distinct_from_entailment(self):
        # __contains__ tests explicit membership (not Cn membership)
        bb = BeliefBase()
        bb.add(p)
        bb.add(Implies(p, q))
        # q is entailed but NOT explicitly in the base
        assert q not in bb
        assert p in bb
        assert Implies(p, q) in bb

    def test_inclusion_subset_after_removal(self):
        # Any subset produced by contraction must be ⊆ original base.
        # Here we simulate by removing the result of least_entrenched_implying.
        bb_original = BeliefBase()
        bb_original.add(p, priority=5)
        bb_original.add(Implies(p, q), priority=0)
        bb_original.add(r, priority=0)

        original_formulas = set(bb_original.formulas())

        bb_contracted = BeliefBase()
        for f, pri in bb_original.formulas_with_priority():
            bb_contracted.add(f, pri)

        to_remove = bb_contracted.least_entrenched_implying(q)
        for f in to_remove:
            bb_contracted.remove(f)

        # Inclusion: contracted ⊆ original
        for f in bb_contracted.formulas():
            assert f in original_formulas

    def test_vacuity_no_removal_when_phi_not_entailed(self):
        # If B does not entail φ, contraction by φ leaves B unchanged.
        # least_entrenched_implying returns [] when phi is not entailed.
        bb = BeliefBase()
        bb.add(p, priority=0)
        bb.add(r, priority=0)
        # B = {p, r} does not entail q
        result = bb.least_entrenched_implying(q)
        assert result == []  # vacuity: nothing to remove

    def test_base_can_represent_consistent_knowledge(self):
        # {p, q} is consistent — both can be true simultaneously
        from resolution import entails as _entails
        bb = BeliefBase()
        bb.add(p)
        bb.add(q)
        contradiction = And(r, Not(r))
        assert not _entails(bb.formulas(), contradiction)

    def test_base_detects_inconsistency(self):
        # {p, ¬p} is inconsistent — entails everything
        from resolution import entails as _entails
        bb = BeliefBase()
        bb.add(p)
        bb.add(Not(p))
        assert _entails(bb.formulas(), q)  # ex falso quodlibet


# ===========================================================================
# 7.  Alice vs Bob — belief base vs belief set (Lecture 11)
# ===========================================================================

class TestAliceVsBob:
    """
    Illustrates why belief *bases* (not belief *sets*) matter for dynamics.

    Alice's base: {p, q}         — Cn(Alice) contains p and q
    Bob's   base: {p, p↔q}      — Cn(Bob)   also contains p and q

    Both agents have the same belief set.  However, contracting by p yields
    different results because their bases have different structure.

    After contracting p from Alice: {q} remains         → q still believed
    After contracting p from Bob:   {p↔q} or {} remains → q no longer follows

    This test verifies that the BeliefBase correctly captures this structural
    difference.
    """

    def test_alice_and_bob_have_same_belief_set(self):
        from resolution import entails as _entails

        alice = BeliefBase()
        alice.add(p)
        alice.add(q)

        bob = BeliefBase()
        bob.add(p)
        bob.add(Biconditional(p, q))

        # Both believe p
        assert _entails(alice.formulas(), p)
        assert _entails(bob.formulas(), p)

        # Both believe q
        assert _entails(alice.formulas(), q)
        assert _entails(bob.formulas(), q)

    def test_alice_retains_q_after_contracting_p(self):
        from resolution import entails as _entails

        alice = BeliefBase()
        alice.add(p, priority=5)   # p is less entrenched (can be removed)
        alice.add(q, priority=0)   # q is independently held

        to_remove = alice.least_entrenched_implying(p)
        for f in to_remove:
            alice.remove(f)

        # After removing p, Alice still explicitly holds q
        assert q in alice
        assert _entails(alice.formulas(), q)

    def test_bob_loses_q_after_contracting_p(self):
        from resolution import entails as _entails

        bob = BeliefBase()
        bob.add(p, priority=5)              # p is less entrenched
        bob.add(Biconditional(p, q), priority=0)  # p↔q is background

        to_remove = bob.least_entrenched_implying(p)
        for f in to_remove:
            bob.remove(f)

        # After removing p, Bob's base is {p↔q}.
        # {p↔q} alone does NOT entail q (both p=F,q=F and p=T,q=T satisfy it)
        assert not _entails(bob.formulas(), q)

    def test_alice_bob_bases_are_structurally_different(self):
        # Despite identical belief sets, the bases have different formulas
        alice = BeliefBase()
        alice.add(p)
        alice.add(q)

        bob = BeliefBase()
        bob.add(p)
        bob.add(Biconditional(p, q))

        assert set(alice.formulas()) != set(bob.formulas())
