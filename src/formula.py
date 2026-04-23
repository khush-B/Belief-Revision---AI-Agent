"""
formula.py — Propositional Logic Formula AST
=============================================
Defines the immutable, hashable data structures that represent propositional
formulas as an Abstract Syntax Tree (AST).

All formula objects are immutable and hashable so they can be placed in
sets / used as dict keys (needed by the resolution engine and belief base).

Node types
----------
  Atom           — propositional variable, e.g. p, rain, alive
  Not(φ)         — negation  ¬φ
  And(φ, ψ)      — conjunction  φ ∧ ψ
  Or(φ, ψ)       — disjunction  φ ∨ ψ
  Implies(φ, ψ)  — implication  φ → ψ
  Biconditional(φ, ψ) — biconditional  φ ↔ ψ

Used by:  parser.py, cnf.py, resolution.py, belief_base.py (Member A),
          contraction.py (Member C)
"""

from __future__ import annotations
from typing import Set


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class Formula:
    """Abstract base class for propositional logic formulas."""

    # Convenience Python operator overloads so formulas can be composed
    # naturally in tests and scripts without importing connective classes.
    def __neg__(self) -> Not:           # -phi  →  Not(phi)
        return Not(self)

    def __and__(self, other: Formula) -> And:   # phi & psi  →  And(phi, psi)
        return And(self, other)

    def __or__(self, other: Formula) -> Or:     # phi | psi  →  Or(phi, psi)
        return Or(self, other)

    def atoms(self) -> Set[str]:
        """Return the set of propositional variable names in this formula."""
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError

    def __repr__(self) -> str:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Concrete formula nodes
# ---------------------------------------------------------------------------

class Atom(Formula):
    """A propositional variable (leaf node).

    Examples: Atom('p'), Atom('rain'), Atom('x1')
    """

    __slots__ = ('name',)

    def __init__(self, name: str) -> None:
        if not name:
            raise ValueError("Atom name must be a non-empty string.")
        self.name = name

    def atoms(self) -> Set[str]:
        return {self.name}

    def __repr__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Atom) and self.name == other.name

    def __hash__(self) -> int:
        return hash(('Atom', self.name))


class Not(Formula):
    """Negation: ¬φ"""

    __slots__ = ('operand',)

    def __init__(self, operand: Formula) -> None:
        self.operand = operand

    def atoms(self) -> Set[str]:
        return self.operand.atoms()

    def __repr__(self) -> str:
        if isinstance(self.operand, Atom):
            return f'¬{self.operand}'
        return f'¬({self.operand})'

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Not) and self.operand == other.operand

    def __hash__(self) -> int:
        return hash(('Not', self.operand))


class And(Formula):
    """Conjunction: φ ∧ ψ"""

    __slots__ = ('left', 'right')

    def __init__(self, left: Formula, right: Formula) -> None:
        self.left = left
        self.right = right

    def atoms(self) -> Set[str]:
        return self.left.atoms() | self.right.atoms()

    def __repr__(self) -> str:
        return f'({self.left} ∧ {self.right})'

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, And)
                and self.left == other.left
                and self.right == other.right)

    def __hash__(self) -> int:
        return hash(('And', self.left, self.right))


class Or(Formula):
    """Disjunction: φ ∨ ψ"""

    __slots__ = ('left', 'right')

    def __init__(self, left: Formula, right: Formula) -> None:
        self.left = left
        self.right = right

    def atoms(self) -> Set[str]:
        return self.left.atoms() | self.right.atoms()

    def __repr__(self) -> str:
        return f'({self.left} ∨ {self.right})'

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, Or)
                and self.left == other.left
                and self.right == other.right)

    def __hash__(self) -> int:
        return hash(('Or', self.left, self.right))


class Implies(Formula):
    """Material implication: φ → ψ  (right-associative)"""

    __slots__ = ('left', 'right')

    def __init__(self, left: Formula, right: Formula) -> None:
        self.left = left
        self.right = right

    def atoms(self) -> Set[str]:
        return self.left.atoms() | self.right.atoms()

    def __repr__(self) -> str:
        return f'({self.left} → {self.right})'

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, Implies)
                and self.left == other.left
                and self.right == other.right)

    def __hash__(self) -> int:
        return hash(('Implies', self.left, self.right))


class Biconditional(Formula):
    """Biconditional (if and only if): φ ↔ ψ"""

    __slots__ = ('left', 'right')

    def __init__(self, left: Formula, right: Formula) -> None:
        self.left = left
        self.right = right

    def atoms(self) -> Set[str]:
        return self.left.atoms() | self.right.atoms()

    def __repr__(self) -> str:
        return f'({self.left} ↔ {self.right})'

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, Biconditional)
                and self.left == other.left
                and self.right == other.right)

    def __hash__(self) -> int:
        return hash(('Biconditional', self.left, self.right))
