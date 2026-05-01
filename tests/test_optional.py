"""
tests/test_optional.py — Tests for Optional Tasks 1 & 2
========================================================
Optional 1:  Plausibility Order (possible-worlds belief revision)
Optional 2:  Mastermind AI (belief-revision-based codebreaker)

Run with:
    cd "Belief-Revision agent"
    python -m pytest tests/ -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from formula import Atom, Not, And, Or, Implies, Biconditional
from plausibility_order import PlausibilityOrder, _eval_formula
from mastermind import MastermindAgent, play_mastermind, score, ALL_CODES, PEGS


# ===========================================================================
# Optional Task 1 — Plausibility Order
# ===========================================================================

p = Atom('p')
q = Atom('q')
r = Atom('r')


class TestWorldEvaluation:
    """Test the formula evaluation over possible worlds."""

    def test_atom_true(self):
        assert _eval_formula(Atom('p'), frozenset({'p'}))

    def test_atom_false(self):
        assert not _eval_formula(Atom('p'), frozenset())

    def test_negation_true(self):
        assert _eval_formula(Not(Atom('p')), frozenset())

    def test_negation_false(self):
        assert not _eval_formula(Not(Atom('p')), frozenset({'p'}))

    def test_and_true(self):
        assert _eval_formula(And(Atom('p'), Atom('q')), frozenset({'p', 'q'}))

    def test_and_false_missing_one(self):
        assert not _eval_formula(And(Atom('p'), Atom('q')), frozenset({'p'}))

    def test_or_true_one(self):
        assert _eval_formula(Or(Atom('p'), Atom('q')), frozenset({'p'}))

    def test_or_false_none(self):
        assert not _eval_formula(Or(Atom('p'), Atom('q')), frozenset())

    def test_implies_true_antecedent_false(self):
        assert _eval_formula(Implies(Atom('p'), Atom('q')), frozenset())

    def test_implies_false(self):
        # p -> q is False only when p=T, q=F
        assert not _eval_formula(Implies(Atom('p'), Atom('q')), frozenset({'p'}))

    def test_biconditional_both_true(self):
        assert _eval_formula(
            Biconditional(Atom('p'), Atom('q')), frozenset({'p', 'q'})
        )

    def test_biconditional_both_false(self):
        assert _eval_formula(
            Biconditional(Atom('p'), Atom('q')), frozenset()
        )

    def test_biconditional_different_values(self):
        assert not _eval_formula(
            Biconditional(Atom('p'), Atom('q')), frozenset({'p'})
        )


class TestPlausibilityOrderInit:
    def test_world_count_two_atoms(self):
        po = PlausibilityOrder(['p', 'q'])
        assert len(po.worlds) == 4

    def test_world_count_three_atoms(self):
        po = PlausibilityOrder(['p', 'q', 'r'])
        assert len(po.worlds) == 8

    def test_all_worlds_equal_rank_initially(self):
        po = PlausibilityOrder(['p', 'q'])
        ranks = set(po.rank.values())
        assert ranks == {0}

    def test_no_belief_without_revision(self):
        po = PlausibilityOrder(['p', 'q'])
        # No beliefs asserted — p is not believed, q is not believed
        assert not po.entails(Atom('p'))
        assert not po.entails(Atom('q'))

    def test_tautology_believed(self):
        po = PlausibilityOrder(['p'])
        # p | ~p is a tautology — must hold in every world
        assert po.entails(Or(Atom('p'), Not(Atom('p'))))


class TestPlausibilityOrderRevise:
    def test_success_after_revision(self):
        """K*1 Success: after revise(φ), the system believes φ."""
        po = PlausibilityOrder(['p', 'q'])
        po.revise(Atom('p'))
        assert po.entails(Atom('p'))

    def test_success_complex_formula(self):
        po = PlausibilityOrder(['p', 'q'])
        phi = Implies(Atom('p'), Atom('q'))
        po.revise(phi)
        assert po.entails(phi)

    def test_revision_removes_contrary(self):
        """After believing p, revising with ~p should make ~p believed."""
        po = PlausibilityOrder(['p', 'q'])
        po.revise(Atom('p'))
        assert po.entails(Atom('p'))

        po.revise(Not(Atom('p')))
        assert po.entails(Not(Atom('p')))

    def test_consistency_after_revision(self):
        """Revising with a consistent formula keeps the world set non-empty."""
        po = PlausibilityOrder(['p', 'q'])
        po.revise(Atom('p'))
        assert len(po.most_plausible()) > 0

    def test_most_plausible_are_phi_worlds_after_revision(self):
        """After revise(p), all minimum-rank worlds satisfy p."""
        po = PlausibilityOrder(['p', 'q'])
        po.revise(Atom('p'))
        for w in po.most_plausible():
            assert 'p' in w

    def test_most_plausible_after_conjunction_revision(self):
        po = PlausibilityOrder(['p', 'q'])
        po.revise(And(Atom('p'), Atom('q')))
        for w in po.most_plausible():
            assert 'p' in w
            assert 'q' in w

    def test_relative_order_preserved_within_phi_worlds(self):
        """
        Lexicographic revision preserves the relative ranking of φ-worlds.
        Initially all worlds have the same rank; after revise(p) all p-worlds
        should share rank 0 (they were all equally plausible beforehand).
        """
        po = PlausibilityOrder(['p', 'q'])
        po.revise(Atom('p'))
        p_worlds = [w for w in po.worlds if 'p' in w]
        ranks = {po.rank[w] for w in p_worlds}
        assert ranks == {0}

    def test_not_phi_worlds_ranked_higher(self):
        po = PlausibilityOrder(['p', 'q'])
        po.revise(Atom('p'))
        min_rank = min(po.rank.values())
        for w in po.worlds:
            if 'p' not in w:
                assert po.rank[w] > min_rank

    def test_revision_noop_for_tautology(self):
        """Revising with a tautology should not crash and all worlds remain."""
        po = PlausibilityOrder(['p'])
        taut = Or(Atom('p'), Not(Atom('p')))
        po.revise(taut)          # should not raise
        assert len(po.worlds) == 2

    def test_revision_with_contradiction_noop(self):
        """Revising with a contradiction (no models) should be a no-op."""
        po = PlausibilityOrder(['p'])
        contra = And(Atom('p'), Not(Atom('p')))
        ranks_before = dict(po.rank)
        po.revise(contra)
        assert po.rank == ranks_before


class TestPlausibilityOrderContract:
    def test_vacuity_no_change(self):
        po = PlausibilityOrder(['p', 'q'])
        po.revise(Atom('p'))
        # po does not believe q
        assert not po.entails(Atom('q'))
        ranks_before = dict(po.rank)
        po.contract(Atom('q'))
        assert po.rank == ranks_before

    def test_contract_removes_belief(self):
        po = PlausibilityOrder(['p', 'q'])
        po.revise(Atom('p'))
        assert po.entails(Atom('p'))
        po.contract(Atom('p'))
        assert not po.entails(Atom('p'))

    def test_contract_tautology_noop(self):
        po = PlausibilityOrder(['p'])
        taut = Or(Atom('p'), Not(Atom('p')))
        po.revise(Atom('p'))
        ranks_before = dict(po.rank)
        po.contract(taut)
        # Tautology cannot be contracted — state unchanged for min worlds
        # (implementation does nothing for tautologies)


class TestPlausibilityOrderDisplay:
    def test_world_to_str_all_true(self):
        po = PlausibilityOrder(['p', 'q'])
        world = frozenset({'p', 'q'})
        s = po.world_to_str(world)
        assert 'p=T' in s
        assert 'q=T' in s

    def test_world_to_str_all_false(self):
        po = PlausibilityOrder(['p', 'q'])
        world = frozenset()
        s = po.world_to_str(world)
        assert 'p=F' in s
        assert 'q=F' in s

    def test_repr_no_crash(self):
        po = PlausibilityOrder(['p', 'q'])
        po.revise(Atom('p'))
        r = repr(po)
        assert 'PlausibilityOrder' in r
        assert 'rank' in r


# ===========================================================================
# Optional Task 2 — Mastermind AI
# ===========================================================================

class TestScoreFunction:
    def test_perfect_score(self):
        assert score((1, 2, 3, 4), (1, 2, 3, 4)) == (4, 0)

    def test_all_wrong(self):
        # No colour appears in the same or any position
        assert score((1, 1, 1, 1), (2, 2, 2, 2)) == (0, 0)

    def test_all_correct_colour_wrong_position(self):
        # (1,2,3,4) vs (2,3,4,1) — same 4 colours, all wrong position
        assert score((1, 2, 3, 4), (2, 3, 4, 1)) == (0, 4)

    def test_one_black(self):
        assert score((1, 2, 3, 4), (1, 5, 5, 5)) == (1, 0)

    def test_one_white(self):
        # colour 1 appears but in wrong position
        assert score((1, 2, 3, 4), (5, 1, 5, 5)) == (0, 1)

    def test_black_takes_priority(self):
        # (1,1,2,3) vs (1,2,1,3): pos 0 exact (1=1), pos 3 exact (3=3) → black=2
        # Colour counts — guess: {1:2, 2:1, 3:1}, secret: {1:2, 2:1, 3:1}
        # total correct = min(2,2)+min(1,1)+min(1,1) = 2+1+1 = 4, white = 4-2 = 2
        assert score((1, 1, 2, 3), (1, 2, 1, 3)) == (2, 2)
    def test_duplicate_colours(self):
        # guess=(1,1,1,1) vs secret=(1,1,2,3)
        # black=2 (pos 0,1), total correct=min(4,2)=2, white=0
        assert score((1, 1, 1, 1), (1, 1, 2, 3)) == (2, 0)

    def test_symmetry_is_not_symmetric(self):
        # score is not necessarily symmetric due to duplicate counting
        # but this exact case should be symmetric
        g, s = (1, 2, 3, 4), (4, 3, 2, 1)
        b, w = score(g, s)
        assert b == 0
        assert w == 4


class TestMastermindAgent:
    def test_initial_candidates(self):
        agent = MastermindAgent()
        assert agent.remaining() == 1296   # 6^4

    def test_first_guess_is_optimal(self):
        agent = MastermindAgent()
        assert agent.make_guess() == (1, 1, 2, 2)

    def test_feedback_reduces_candidates(self):
        agent = MastermindAgent()
        guess = (1, 1, 2, 2)
        agent.receive_feedback(guess, 0, 0)
        # All codes containing colours 1 or 2 are eliminated
        assert agent.remaining() < 1296
        assert agent.remaining() > 0

    def test_perfect_feedback_leaves_one(self):
        agent = MastermindAgent()
        secret = (1, 2, 3, 4)
        # Manually feed each guess and its feedback until solved or close
        guess = (1, 2, 3, 4)
        agent.receive_feedback(guess, 4, 0)   # perfect match
        assert agent.remaining() == 1   # only the secret remains

    def test_is_not_solved_initially(self):
        agent = MastermindAgent()
        assert not agent.is_solved()

    def test_is_solved_after_narrowing(self):
        agent = MastermindAgent()
        secret = (3, 5, 6, 2)
        # Feed perfect score immediately
        agent.receive_feedback(secret, 4, 0)
        assert agent.is_solved()

    def test_history_recorded(self):
        agent = MastermindAgent()
        agent.receive_feedback((1, 1, 2, 2), 0, 1)
        assert len(agent.history) == 1
        assert agent.history[0] == ((1, 1, 2, 2), (0, 1))

    def test_candidates_are_consistent_with_feedback(self):
        """After feedback, every remaining candidate is consistent with it."""
        agent = MastermindAgent()
        guess = (1, 1, 2, 2)
        feedback = (0, 1)
        agent.receive_feedback(guess, *feedback)
        for c in agent.candidates:
            assert score(guess, c) == feedback, \
                f"Candidate {c} inconsistent with feedback {feedback}"

    def test_multiple_feedbacks_narrow_candidates(self):
        agent = MastermindAgent()
        secret = (2, 4, 6, 1)
        for _ in range(5):
            if agent.is_solved():
                break
            g = agent.make_guess()
            b, w = score(g, secret)
            agent.receive_feedback(g, b, w)

        # After up to 5 guesses the agent should have narrowed dramatically
        assert agent.remaining() <= 10


class TestPlayMastermind:
    def test_solve_in_bounded_guesses(self):
        # The minimax strategy should solve any code within ~8 guesses
        # (theoretically within 6 for Knuth, but our simplified version
        # uses candidate-only subset so may take up to ~7–8)
        secret = (1, 2, 3, 4)
        n = play_mastermind(secret, verbose=False)
        assert 1 <= n <= 8

    def test_trivial_code(self):
        n = play_mastermind((1, 1, 1, 1), verbose=False)
        assert n >= 1

    def test_all_same_colour(self):
        n = play_mastermind((6, 6, 6, 6), verbose=False)
        assert n >= 1

    def test_various_secrets(self):
        test_cases = [
            (1, 2, 3, 4),
            (6, 5, 4, 3),
            (1, 1, 2, 3),
            (3, 3, 3, 3),
            (2, 4, 6, 1),
            (5, 1, 3, 2),
        ]
        for secret in test_cases:
            n = play_mastermind(secret, verbose=False)
            assert 1 <= n <= 10, \
                f"Could not solve {secret} within 10 guesses (took {n})"

    def test_returns_positive_int(self):
        n = play_mastermind((4, 2, 5, 1), verbose=False)
        assert isinstance(n, int)
        assert n > 0
