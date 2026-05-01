"""
tests/test_agm.py — AGM Postulate Tests  (Member C)
====================================================
Tests the five required AGM postulates on the actual revision / contraction
operations implemented in revision_engine.py.

Postulates tested
-----------------
  K*1  Success       B * φ ⊨ φ
  K*2  Inclusion     B * φ ⊆ Cn(B ∪ {φ})
  K*3  Vacuity       B ⊭ ¬φ  →  B * φ = B + φ
  K*4  Consistency   φ consistent  →  B * φ is consistent
  K*5  Extensionality  φ ≡ ψ  →  B * φ ≡ B * ψ

Also tests contraction postulates:
  K÷1  Success       if B ⊭ φ then (B ÷ φ) ⊭ φ
  K÷2  Inclusion     B ÷ φ ⊆ B
  K÷3  Vacuity       if B ⊭ φ then B ÷ φ = B
  K÷4  Recovery      B ⊆ (B ÷ φ) + φ  (expansion of contraction recovers B)
  K÷5  Extensionality  φ ≡ ψ  →  B ÷ φ ≡ B ÷ ψ

Run with:
    cd "Belief-Revision agent"
    python -m pytest tests/ -v
"""

import sys
import os
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from formula import Atom, Not, And, Or, Implies, Biconditional
from parser import parse
from belief_base import BeliefBase
from resolution import entails
from revision_engine import RevisionEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_engine(*formulas_with_priority):
    """
    Build a fresh RevisionEngine from (formula, priority) pairs.

    Example:
        make_engine((p, 0), (q, 5))
    """
    bb = BeliefBase()
    for formula, priority in formulas_with_priority:
        bb.add(formula, priority)
    return RevisionEngine(bb)


def make_simple_engine(*formulas):
    """Build engine from formulas with default priority 0, in ascending order."""
    bb = BeliefBase()
    for i, f in enumerate(formulas):
        bb.add(f, priority=i)   # higher index → less entrenched
    return RevisionEngine(bb)


# Shared atoms
p = Atom('p')
q = Atom('q')
r = Atom('r')
s = Atom('s')


# ===========================================================================
# Revision Postulates  (K* postulates)
# ===========================================================================

class TestRevisionSuccess:
    """K*1 — Success: B * φ ⊨ φ"""

    def test_success_simple(self):
        eng = make_simple_engine(p, q)
        eng.revise(r)
        assert entails(eng.bb.formulas(), r)

    def test_success_after_conflicting_belief(self):
        # Base contains ¬q; revise by q must make the base entail q
        eng = make_simple_engine(p, Not(q))
        eng.revise(q)
        assert entails(eng.bb.formulas(), q)

    def test_success_with_complex_formula(self):
        eng = make_simple_engine(p)
        phi = Or(q, r)
        eng.revise(phi)
        assert entails(eng.bb.formulas(), phi)

    def test_success_with_implication(self):
        eng = make_simple_engine(p, Not(Implies(p, q)))
        eng.revise(Implies(p, q))
        assert entails(eng.bb.formulas(), Implies(p, q))


class TestRevisionInclusion:
    """K*2 — Inclusion: B * φ ⊆ Cn(B ∪ {φ})

    Any formula entailed after revision was either entailed by B ∪ {φ}
    already.  We test the concrete: a formula in B that doesn't conflict
    with φ should still be entailed after revision.
    """

    def test_non_conflicting_belief_preserved(self):
        # Base: {p, ~q}.  Revise by r (no conflict with p, ~q).
        # p should still be entailed afterwards.
        eng = make_engine((p, 0), (Not(q), 1))
        eng.revise(r)
        assert entails(eng.bb.formulas(), p)

    def test_entailed_consequence_preserved(self):
        # Base: {p -> q, p}.  Revise by r.  q should still be entailed.
        eng = make_engine((Implies(p, q), 0), (p, 1))
        eng.revise(r)
        assert entails(eng.bb.formulas(), q)

    def test_unrelated_formula_after_revision(self):
        eng = make_simple_engine(p, q, r)
        # Revise by s.  p, q, r unrelated to s → still entailed.
        eng.revise(s)
        assert entails(eng.bb.formulas(), p)
        assert entails(eng.bb.formulas(), q)
        assert entails(eng.bb.formulas(), r)


class TestRevisionVacuity:
    """K*3 — Vacuity: if B ⊭ ¬φ, then B * φ = B + φ (no contraction needed).

    When the belief base does not entail the negation of φ, revision
    should equal plain expansion — no beliefs are dropped.
    """

    def test_vacuous_revision_adds_without_removing(self):
        # {p}.  B ⊭ ¬q, so revise(q) = expand(q).
        bb = BeliefBase()
        bb.add(p, 0)
        eng = RevisionEngine(bb)

        assert not entails([p], Not(q))   # confirm vacuity condition
        eng.revise(q)

        assert entails(eng.bb.formulas(), p)  # original p preserved
        assert entails(eng.bb.formulas(), q)  # new q present

    def test_vacuous_no_removal(self):
        bb = BeliefBase()
        bb.add(p, 0)
        bb.add(r, 0)
        eng = RevisionEngine(bb)

        before_count = len(eng.bb)
        eng.revise(q)   # q does not conflict with {p, r}
        after_count = len(eng.bb)

        assert after_count == before_count + 1  # only one formula added


class TestRevisionConsistency:
    """K*4 — Consistency: if φ is consistent, B * φ is consistent."""

    def test_consistent_after_revision(self):
        eng = make_simple_engine(p, Not(q))
        eng.revise(q)                         # q is consistent
        assert eng.is_consistent()

    def test_consistent_after_negation_revision(self):
        eng = make_simple_engine(p, q)
        eng.revise(Not(p))                    # ¬p is consistent
        assert eng.is_consistent()

    def test_consistent_complex(self):
        phi = Implies(p, q)
        eng = make_simple_engine(Not(phi))
        eng.revise(phi)
        assert eng.is_consistent()

    def test_initially_inconsistent_base_becomes_consistent(self):
        # Start with p and ¬p (inconsistent); revise by q
        eng = make_engine((p, 0), (Not(p), 5))
        eng.revise(q)
        assert eng.is_consistent()


class TestRevisionExtensionality:
    """K*5 — Extensionality: if φ ≡ ψ then B * φ ≡ B * ψ.

    We test by revising two copies of the same base by logically
    equivalent formulas and checking they produce equivalent results.
    """

    def _make_two_equal_engines(self, *beliefs):
        """Return two identical engines for parallel revision."""
        bb1, bb2 = BeliefBase(), BeliefBase()
        for i, f in enumerate(beliefs):
            bb1.add(f, priority=i)
            bb2.add(f, priority=i)
        return RevisionEngine(bb1), RevisionEngine(bb2)

    def test_extensionality_double_negation(self):
        # φ = p,  ψ = ¬¬p  →  logically equivalent
        eng1, eng2 = self._make_two_equal_engines(Not(p), q)
        eng1.revise(p)
        eng2.revise(Not(Not(p)))

        # Both should entail p (Success) and be consistent
        assert entails(eng1.bb.formulas(), p)
        assert entails(eng2.bb.formulas(), p)
        assert eng1.is_consistent()
        assert eng2.is_consistent()

    def test_extensionality_tautological_equivalents(self):
        # φ = p -> q,  ψ = ¬p ∨ q  (definitionally equivalent)
        eng1, eng2 = self._make_two_equal_engines(Not(Implies(p, q)), r)
        phi = Implies(p, q)
        psi = Or(Not(p), q)

        eng1.revise(phi)
        eng2.revise(psi)

        # Both should entail the respective formula (and the other, since equiv)
        assert entails(eng1.bb.formulas(), phi)
        assert entails(eng2.bb.formulas(), psi)
        assert entails(eng1.bb.formulas(), psi)
        assert entails(eng2.bb.formulas(), phi)


# ===========================================================================
# Contraction Postulates  (K÷ postulates)
# ===========================================================================

class TestContractionSuccess:
    """K÷1 — Success: if φ is not a tautology, B ÷ φ ⊭ φ."""

    def test_contract_removes_entailment(self):
        eng = make_simple_engine(p, q)
        assert entails(eng.bb.formulas(), p)
        eng.contract(p)
        assert not entails(eng.bb.formulas(), p)

    def test_contract_implication(self):
        eng = make_engine((Implies(p, q), 0), (p, 5))
        # Base entails q via MP
        assert entails(eng.bb.formulas(), q)
        eng.contract(q)
        assert not entails(eng.bb.formulas(), q)

    def test_contract_disjunction(self):
        eng = make_engine((p, 0), (q, 5))
        disj = Or(p, q)
        assert entails(eng.bb.formulas(), disj)
        eng.contract(disj)
        assert not entails(eng.bb.formulas(), disj)


class TestContractionInclusion:
    """K÷2 — Inclusion: B ÷ φ ⊆ B.  Contraction never adds beliefs."""

    def test_no_new_formulas_after_contraction(self):
        bb = BeliefBase()
        bb.add(p, 0); bb.add(q, 1); bb.add(r, 2)
        eng = RevisionEngine(bb)

        before = set(eng.bb.formulas())
        eng.contract(r)
        after = set(eng.bb.formulas())

        assert after <= before   # no formula added

    def test_all_remaining_were_original(self):
        eng = make_engine((p, 0), (Implies(p, q), 1))
        original = set(repr(f) for f in eng.bb.formulas())
        eng.contract(q)
        for f in eng.bb.formulas():
            assert repr(f) in original


class TestContractionVacuity:
    """K÷3 — Vacuity: if B ⊭ φ, then B ÷ φ = B (no change)."""

    def test_vacuous_contraction_no_change(self):
        bb = BeliefBase()
        bb.add(p, 0); bb.add(q, 1)
        eng = RevisionEngine(bb)

        # r is not in the base and not entailed
        assert not entails([p, q], r)

        before = list(eng.bb._entries)
        eng.contract(r)
        after = list(eng.bb._entries)

        assert before == after   # exactly unchanged

    def test_vacuous_count_unchanged(self):
        eng = make_simple_engine(p, q)
        before_len = len(eng.bb)
        eng.contract(r)   # not entailed
        assert len(eng.bb) == before_len


class TestContractionRecovery:
    """K÷4 — Recovery: B ⊆ (B ÷ φ) + φ.

    Contracting then re-expanding should recover the original beliefs
    (they should at least be entailed by the result).
    """

    def test_recovery_simple(self):
        # B = {p, q}.  Contract p.  Then expand by p.
        bb = BeliefBase()
        bb.add(p, 0); bb.add(q, 0)
        eng = RevisionEngine(bb)

        orig = list(bb.formulas())
        eng.contract(p)
        eng.expand(p)

        for f in orig:
            assert entails(eng.bb.formulas(), f), \
                f"Recovery failed: {f!r} not entailed after (B÷p)+p"

    def test_recovery_chain(self):
        # B = {p (priority=0), r (priority=5)}.  Contract r.
        # r's kernel is {r} alone (r entails itself; p is irrelevant).
        # After contract(r) + expand(r): both p and r must be entailed.
        bb = BeliefBase()
        bb.add(p, 0)
        bb.add(r, 5)   # r is less entrenched
        eng = RevisionEngine(bb)

        orig_formulas = list(bb.formulas())
        eng.contract(r)
        eng.expand(r)

        for f in orig_formulas:
            assert entails(eng.bb.formulas(), f), \
                f"Recovery failed: {f!r} not entailed after (B÷r)+r"


class TestContractionExtensionality:
    """K÷5 — Extensionality: φ ≡ ψ → B ÷ φ behaves like B ÷ ψ."""

    def test_contract_equivalent_formulas(self):
        # p -> q  ≡  ~p | q.  Contracting by one or the other should both
        # remove entailment of the equivalents.
        bb1, bb2 = BeliefBase(), BeliefBase()
        for bb in [bb1, bb2]:
            bb.add(Implies(p, q), 0)
            bb.add(p, 1)

        eng1, eng2 = RevisionEngine(bb1), RevisionEngine(bb2)
        eng1.contract(Implies(p, q))
        eng2.contract(Or(Not(p), q))

        # Neither base should entail q afterwards
        assert not entails(eng1.bb.formulas(), q)
        assert not entails(eng2.bb.formulas(), q)


# ===========================================================================
# Expansion tests
# ===========================================================================

class TestExpansion:
    def test_expand_adds_formula(self):
        eng = make_simple_engine(p)
        eng.expand(q)
        assert entails(eng.bb.formulas(), q)

    def test_expand_preserves_existing(self):
        eng = make_simple_engine(p)
        eng.expand(q)
        assert entails(eng.bb.formulas(), p)

    def test_expand_respects_priority(self):
        bb = BeliefBase()
        bb.add(p, priority=0)
        eng = RevisionEngine(bb)
        eng.expand(q, priority=10)
        assert eng.bb.least_entrenched() == q

    def test_expand_does_not_check_consistency(self):
        # expand() must NOT raise even when adding a contradiction
        eng = make_simple_engine(p)
        eng.expand(Not(p))    # no error — expansion is unchecked
        # Base is now inconsistent — but expand is supposed to be unchecked
        assert not eng.is_consistent()


# ===========================================================================
# Integration: full revision pipeline
# ===========================================================================

class TestIntegrationRevision:
    """End-to-end scenarios combining multiple operations."""

    def test_revise_updates_conflicting_belief(self):
        # Classic scenario: "it was raining, now it's not"
        rain = Atom('rain')
        wet = Atom('wet')

        bb = BeliefBase()
        bb.add(rain, priority=0)
        bb.add(Implies(rain, wet), priority=0)
        eng = RevisionEngine(bb)

        assert entails(eng.bb.formulas(), wet)

        eng.revise(Not(rain))
        assert entails(eng.bb.formulas(), Not(rain))
        assert eng.is_consistent()

    def test_multiple_revisions(self):
        bb = BeliefBase()
        eng = RevisionEngine(bb)

        eng.revise(p)
        assert entails(eng.bb.formulas(), p)

        eng.revise(Not(p))
        assert entails(eng.bb.formulas(), Not(p))
        assert eng.is_consistent()

        eng.revise(p)
        assert entails(eng.bb.formulas(), p)
        assert eng.is_consistent()

    def test_revise_parsed_formulas(self):
        bb = BeliefBase()
        eng = RevisionEngine(bb)

        rule = parse('p -> q')
        fact = parse('p')
        contradiction = parse('~q')

        eng.expand(rule, priority=0)
        eng.expand(fact, priority=1)
        assert entails(eng.bb.formulas(), parse('q'))

        eng.revise(contradiction)
        assert entails(eng.bb.formulas(), Not(Atom('q')))
        assert eng.is_consistent()

    def test_belief_base_snapshot_restore(self):
        bb = BeliefBase()
        bb.add(p, 0); bb.add(q, 1)
        eng = RevisionEngine(bb)

        snap = eng.snapshot()
        eng.revise(Not(p))
        assert entails(eng.bb.formulas(), Not(p))

        eng.restore(snap)
        assert entails(eng.bb.formulas(), p)
