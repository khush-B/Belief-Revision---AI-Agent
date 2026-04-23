"""
tests/test_entailment.py — Comprehensive Tests for Member B
============================================================
Covers:
  • Formula AST equality and hashing
  • Parser correctness (precedence, associativity, unicode, errors)
  • CNF conversion (each transformation step)
  • Resolution / SAT checker
  • entails() function — including all five AGM-relevant patterns that
    Member C's postulate tests will depend on

Run with:
    cd "Belief-Revision agent"
    python -m pytest tests/ -v
"""

import sys
import os
import pytest

# Make src/ importable regardless of working directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from formula import Atom, Not, And, Or, Implies, Biconditional
from parser import parse, ParseError
from cnf import (
    to_cnf_clauses,
    negate_literal,
    is_tautological_clause,
)
from resolution import entails, is_unsatisfiable


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

p = Atom('p')
q = Atom('q')
r = Atom('r')
s = Atom('s')


# ===========================================================================
# 1.  Formula AST
# ===========================================================================

class TestFormulaEquality:
    def test_atom_equal(self):
        assert Atom('p') == Atom('p')

    def test_atom_not_equal(self):
        assert Atom('p') != Atom('q')

    def test_not_equal(self):
        assert Not(p) == Not(Atom('p'))

    def test_and_equal(self):
        assert And(p, q) == And(Atom('p'), Atom('q'))

    def test_and_order_matters(self):
        # Conjunction is not commutative in the AST (structural equality)
        assert And(p, q) != And(q, p)

    def test_or_equal(self):
        assert Or(p, q) == Or(Atom('p'), Atom('q'))

    def test_implies_equal(self):
        assert Implies(p, q) == Implies(Atom('p'), Atom('q'))

    def test_biconditional_equal(self):
        assert Biconditional(p, q) == Biconditional(Atom('p'), Atom('q'))

    def test_different_types_not_equal(self):
        assert And(p, q) != Or(p, q)

    def test_hashable_in_set(self):
        formulas = {p, q, Not(p), And(p, q)}
        assert len(formulas) == 4
        assert p in formulas

    def test_atoms_method(self):
        assert Implies(And(p, q), Or(r, Not(s))).atoms() == {'p', 'q', 'r', 's'}


# ===========================================================================
# 2.  Parser
# ===========================================================================

class TestParser:
    # --- Basic atoms ---
    def test_single_atom(self):
        assert parse('p') == p

    def test_multichar_atom(self):
        assert parse('rain') == Atom('rain')

    def test_atom_with_digit(self):
        assert parse('x1') == Atom('x1')

    def test_atom_with_underscore(self):
        assert parse('alive_1') == Atom('alive_1')

    # --- Negation ---
    def test_negation_tilde(self):
        assert parse('~p') == Not(p)

    def test_negation_dash(self):
        assert parse('-p') == Not(p)

    def test_double_negation(self):
        assert parse('~~p') == Not(Not(p))

    # --- Conjunction ---
    def test_conjunction(self):
        assert parse('p & q') == And(p, q)

    def test_conjunction_left_assoc(self):
        assert parse('p & q & r') == And(And(p, q), r)

    # --- Disjunction ---
    def test_disjunction(self):
        assert parse('p | q') == Or(p, q)

    def test_disjunction_left_assoc(self):
        assert parse('p | q | r') == Or(Or(p, q), r)

    # --- Implication ---
    def test_implication(self):
        assert parse('p -> q') == Implies(p, q)

    def test_implication_right_assoc(self):
        # p -> q -> r  must be  p -> (q -> r)
        assert parse('p -> q -> r') == Implies(p, Implies(q, r))

    # --- Biconditional ---
    def test_biconditional(self):
        assert parse('p <-> q') == Biconditional(p, q)

    # --- Precedence ---
    def test_negation_binds_tighter_than_and(self):
        # ~p & q  should be  (~p) & q
        assert parse('~p & q') == And(Not(p), q)

    def test_and_binds_tighter_than_or(self):
        # p | q & r  should be  p | (q & r)
        assert parse('p | q & r') == Or(p, And(q, r))

    def test_or_binds_tighter_than_implies(self):
        # p | q -> r  should be  (p | q) -> r
        assert parse('p | q -> r') == Implies(Or(p, q), r)

    def test_implies_binds_tighter_than_bicond(self):
        # p -> q <-> r -> s  =  (p -> q) <-> (r -> s)
        assert parse('p -> q <-> r -> s') == Biconditional(
            Implies(p, q), Implies(r, s)
        )

    # --- Parentheses ---
    def test_parentheses_override_precedence(self):
        assert parse('~(p & q)') == Not(And(p, q))

    def test_nested_parentheses(self):
        assert parse('((p))') == p

    # --- Unicode operators ---
    def test_unicode_negation(self):
        assert parse('¬p') == Not(p)

    def test_unicode_and(self):
        assert parse('p ∧ q') == And(p, q)

    def test_unicode_or(self):
        assert parse('p ∨ q') == Or(p, q)

    def test_unicode_implies(self):
        assert parse('p → q') == Implies(p, q)

    def test_unicode_biconditional(self):
        assert parse('p ↔ q') == Biconditional(p, q)

    # --- Error cases ---
    def test_empty_string_raises(self):
        with pytest.raises(ParseError):
            parse('')

    def test_unmatched_paren_raises(self):
        with pytest.raises(ParseError):
            parse('(p & q')

    def test_unexpected_token_raises(self):
        with pytest.raises(ParseError):
            parse('p @ q')

    def test_missing_operand_raises(self):
        with pytest.raises(ParseError):
            parse('p &')


# ===========================================================================
# 3.  Literal helpers
# ===========================================================================

class TestLiteralHelpers:
    def test_negate_positive(self):
        assert negate_literal('p') == '~p'

    def test_negate_negative(self):
        assert negate_literal('~p') == 'p'

    def test_negate_multichar(self):
        assert negate_literal('rain') == '~rain'
        assert negate_literal('~rain') == 'rain'

    def test_tautological_clause(self):
        assert is_tautological_clause(frozenset({'p', '~p'}))

    def test_not_tautological(self):
        assert not is_tautological_clause(frozenset({'p', 'q', '~r'}))

    def test_empty_clause_not_tautological(self):
        assert not is_tautological_clause(frozenset())


# ===========================================================================
# 4.  CNF Conversion
# ===========================================================================

class TestCNFConversion:
    # --- Atoms and negation ---
    def test_atom(self):
        assert to_cnf_clauses(p) == [frozenset({'p'})]

    def test_not_atom(self):
        assert to_cnf_clauses(Not(p)) == [frozenset({'~p'})]

    def test_double_negation_reduces(self):
        # ~~p → p
        assert to_cnf_clauses(Not(Not(p))) == [frozenset({'p'})]

    def test_triple_negation(self):
        # ~~~p → ¬p
        assert to_cnf_clauses(Not(Not(Not(p)))) == [frozenset({'~p'})]

    # --- Conjunction ---
    def test_conjunction(self):
        clauses = to_cnf_clauses(And(p, q))
        assert frozenset({'p'}) in clauses
        assert frozenset({'q'}) in clauses
        assert len(clauses) == 2

    # --- Disjunction ---
    def test_disjunction(self):
        assert to_cnf_clauses(Or(p, q)) == [frozenset({'p', 'q'})]

    # --- Implication ---
    def test_implication_becomes_or(self):
        # p -> q  ≡  ~p | q
        assert to_cnf_clauses(Implies(p, q)) == [frozenset({'~p', 'q'})]

    # --- Biconditional ---
    def test_biconditional_two_clauses(self):
        # p <-> q  ≡  (~p | q) & (~q | p)
        clauses = to_cnf_clauses(Biconditional(p, q))
        assert frozenset({'~p', 'q'}) in clauses
        assert frozenset({'~q', 'p'}) in clauses
        assert len(clauses) == 2

    # --- De Morgan ---
    def test_de_morgan_and(self):
        # ~(p & q)  ≡  ~p | ~q
        assert to_cnf_clauses(Not(And(p, q))) == [frozenset({'~p', '~q'})]

    def test_de_morgan_or(self):
        # ~(p | q)  ≡  ~p & ~q  →  two unit clauses
        clauses = to_cnf_clauses(Not(Or(p, q)))
        assert frozenset({'~p'}) in clauses
        assert frozenset({'~q'}) in clauses
        assert len(clauses) == 2

    # --- Distributivity ---
    def test_distribute_or_over_and(self):
        # p | (q & r)  ≡  (p | q) & (p | r)
        clauses = to_cnf_clauses(Or(p, And(q, r)))
        assert frozenset({'p', 'q'}) in clauses
        assert frozenset({'p', 'r'}) in clauses
        assert len(clauses) == 2

    def test_distribute_and_over_or_left(self):
        # (p & q) | r  ≡  (p | r) & (q | r)
        clauses = to_cnf_clauses(Or(And(p, q), r))
        assert frozenset({'p', 'r'}) in clauses
        assert frozenset({'q', 'r'}) in clauses
        assert len(clauses) == 2

    def test_four_way_distribution(self):
        # (p & q) | (r & s)  ≡  (p|r) & (p|s) & (q|r) & (q|s)
        clauses = to_cnf_clauses(Or(And(p, q), And(r, s)))
        assert frozenset({'p', 'r'}) in clauses
        assert frozenset({'p', 's'}) in clauses
        assert frozenset({'q', 'r'}) in clauses
        assert frozenset({'q', 's'}) in clauses
        assert len(clauses) == 4

    # --- Tautology elimination ---
    def test_tautology_removed(self):
        # p | ~p  is a tautology → empty clause list
        assert to_cnf_clauses(Or(p, Not(p))) == []

    def test_nontrivial_with_tautological_clause_removed(self):
        # (p | ~p) & q  →  only {q}  (the tautological clause is dropped)
        clauses = to_cnf_clauses(And(Or(p, Not(p)), q))
        assert clauses == [frozenset({'q'})]

    # --- Complex formula roundtrip ---
    def test_complex_implies_chain(self):
        # (p -> q) & (q -> r) should give two clauses:  {~p,q}  {~q,r}
        clauses = to_cnf_clauses(And(Implies(p, q), Implies(q, r)))
        assert frozenset({'~p', 'q'}) in clauses
        assert frozenset({'~q', 'r'}) in clauses

    def test_modus_ponens_cnf(self):
        # p & (p -> q)  →  {p}  {~p, q}
        clauses = to_cnf_clauses(And(p, Implies(p, q)))
        assert frozenset({'p'}) in clauses
        assert frozenset({'~p', 'q'}) in clauses


# ===========================================================================
# 5.  Resolution / SAT checker
# ===========================================================================

class TestIsUnsatisfiable:
    def test_empty_clause_set_is_sat(self):
        assert not is_unsatisfiable([])

    def test_unit_clause_is_sat(self):
        assert not is_unsatisfiable([frozenset({'p'})])

    def test_direct_contradiction(self):
        # {p} and {~p} → empty clause immediately
        assert is_unsatisfiable([frozenset({'p'}), frozenset({'~p'})])

    def test_longer_contradiction(self):
        # {p, q}, {~p, q}, {~q}  →  unsatisfiable
        assert is_unsatisfiable([
            frozenset({'p', 'q'}),
            frozenset({'~p', 'q'}),
            frozenset({'~q'}),
        ])

    def test_satisfiable_two_clauses(self):
        # {p} and {q} → p=T, q=T satisfies both
        assert not is_unsatisfiable([frozenset({'p'}), frozenset({'q'})])

    def test_tautological_clause_ignored(self):
        # {p, ~p} is a tautology — does not make the set unsat
        assert not is_unsatisfiable([frozenset({'p', '~p'})])

    def test_formula_contradiction_full(self):
        # p & (p -> q) & ~q  →  unsat
        clauses = (
            to_cnf_clauses(p)
            + to_cnf_clauses(Implies(p, q))
            + to_cnf_clauses(Not(q))
        )
        assert is_unsatisfiable(clauses)

    def test_no_contradiction(self):
        # p | q  →  sat (p=T, q=F works)
        clauses = to_cnf_clauses(Or(p, q))
        assert not is_unsatisfiable(clauses)

    def test_resolution_chain(self):
        # Unit-resolving chain: {p}, {~p, q}, {~q, r}, {~r}  → unsat
        assert is_unsatisfiable([
            frozenset({'p'}),
            frozenset({'~p', 'q'}),
            frozenset({'~q', 'r'}),
            frozenset({'~r'}),
        ])


# ===========================================================================
# 6.  entails() — core entailment function
# ===========================================================================

class TestEntails:
    # --- Basic propositional patterns ---
    def test_modus_ponens(self):
        assert entails([p, Implies(p, q)], q)

    def test_modus_tollens(self):
        # {p -> q, ~q} |= ~p
        assert entails([Implies(p, q), Not(q)], Not(p))

    def test_hypothetical_syllogism(self):
        assert entails([Implies(p, q), Implies(q, r)], Implies(p, r))

    def test_disjunctive_syllogism(self):
        # {p | q, ~p} |= q
        assert entails([Or(p, q), Not(p)], q)

    def test_and_introduction(self):
        assert entails([p, q], And(p, q))

    def test_and_elimination_left(self):
        assert entails([And(p, q)], p)

    def test_and_elimination_right(self):
        assert entails([And(p, q)], q)

    def test_or_introduction(self):
        # {p} |= p | q
        assert entails([p], Or(p, q))

    # --- Non-entailment cases ---
    def test_does_not_entail_unrelated(self):
        assert not entails([p], q)

    def test_does_not_entail_converse(self):
        # {p -> q} does NOT entail q -> p
        assert not entails([Implies(p, q)], Implies(q, p))

    def test_empty_base_does_not_entail_non_tautology(self):
        assert not entails([], p)

    def test_empty_base_entails_tautology(self):
        # [] |= p | ~p   (tautology)
        assert entails([], Or(p, Not(p)))

    def test_empty_base_entails_biconditional_tautology(self):
        # [] |= p -> p
        assert entails([], Implies(p, p))

    # --- Special cases ---
    def test_ex_falso_quodlibet(self):
        # Contradictory base entails everything
        assert entails([p, Not(p)], q)

    def test_ex_falso_non_trivial(self):
        assert entails([And(p, Not(p))], Implies(q, r))

    def test_belief_entails_itself(self):
        assert entails([p], p)

    def test_complex_formula_entails(self):
        # Classic detective: "(rain | fog) -> bus_taken", "rain"  |=  "bus_taken"
        rain = Atom('rain')
        fog  = Atom('fog')
        bus  = Atom('bus_taken')
        assert entails([Implies(Or(rain, fog), bus), rain], bus)

    def test_biconditional_entailment(self):
        # {p <-> q, p} |= q
        assert entails([Biconditional(p, q), p], q)

    def test_biconditional_reverse_entailment(self):
        # {p <-> q, q} |= p
        assert entails([Biconditional(p, q), q], p)

    def test_chain_of_implications(self):
        # {p->q, q->r, r->s, p} |= s
        assert entails([
            Implies(p, q), Implies(q, r), Implies(r, s), p
        ], s)

    def test_does_not_entail_when_missing_premise(self):
        # {p->q, q->r}  does NOT entail  s
        assert not entails([Implies(p, q), Implies(q, r)], s)

    # --- Formulae built from parse() ---
    def test_entails_from_parsed_formulas(self):
        f1 = parse('p -> q')
        f2 = parse('p')
        goal = parse('q')
        assert entails([f1, f2], goal)

    def test_not_entails_from_parsed_formulas(self):
        f1 = parse('p | q')
        goal = parse('p & q')
        assert not entails([f1], goal)


# ===========================================================================
# 7.  AGM Postulate patterns (used by Member C)
# ===========================================================================

class TestAGMPatterns:
    """
    These tests confirm that entails() behaves correctly for the patterns
    underlying the five required AGM postulates.

    They do NOT test contraction/revision themselves (that is Member C's
    job) but validate the logical foundation those tests will rely on.
    """

    def test_consistency_of_consistent_base(self):
        # {p, q} is consistent: there exists a model (p=T, q=T)
        # ⇒ it does NOT entail ⊥ (a contradiction).
        # We approximate ⊥ as p & ~p.
        contradiction = And(r, Not(r))
        assert not entails([p, q], contradiction)

    def test_consistency_violated_by_contradiction(self):
        # {p, ~p} IS inconsistent: entails everything
        assert entails([p, Not(p)], And(q, Not(q)))

    def test_success_pattern(self):
        # After revision by φ, the result should entail φ.
        # Here we just confirm {φ} |= φ (trivially supports success).
        assert entails([p], p)

    def test_inclusion_pattern(self):
        # If {p, q} |= r, then any superset also entails r.
        assert entails([p, q, r], r)

    def test_vacuity_pattern(self):
        # If belief base does NOT entail ~φ, expansion by φ preserves base.
        # {p} does not entail ~q, so expanding by q keeps p.
        assert not entails([p], Not(q))
        assert entails([p, q], p)   # after expansion, p is still entailed

    def test_extensionality_pattern(self):
        # If φ ≡ ψ (i.e., each entails the other), revising by either
        # should give logically equivalent results.
        # Confirm equivalence: p <-> (~~p)
        assert entails([p], Not(Not(p)))
        assert entails([Not(Not(p))], p)
