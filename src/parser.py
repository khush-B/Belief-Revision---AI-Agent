"""
parser.py — Recursive-Descent Parser for Propositional Logic
=============================================================
Converts a string like "p -> (q | ~r)" into a Formula AST.

Supported syntax
----------------
  Atoms          — any sequence of letters, digits, underscores starting
                   with a letter, e.g.  p, q1, rain, alive_1
  Negation       — ~φ   or  -φ   or  ¬φ
  Conjunction    — φ & ψ   or  φ ∧ ψ
  Disjunction    — φ | ψ   or  φ ∨ ψ
  Implication    — φ -> ψ  or  φ → ψ   (right-associative)
  Biconditional  — φ <-> ψ or  φ ↔ ψ
  Parentheses    — (φ)

Operator precedence (highest to lowest)
-----------------------------------------
  ~   negation
  &   conjunction
  |   disjunction
  ->  implication  (right-associative: a->b->c  ≡  a->(b->c))
  <-> biconditional

Usage
-----
  from parser import parse
  f = parse("p -> (q | ~r)")
"""

from formula import Formula, Atom, Not, And, Or, Implies, Biconditional


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ParseError(Exception):
    """Raised when the input string cannot be parsed as a propositional formula."""


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

# Token types
_TT_ATOM    = 'ATOM'
_TT_NOT     = 'NOT'
_TT_AND     = 'AND'
_TT_OR      = 'OR'
_TT_IMPLIES = 'IMPLIES'
_TT_BICOND  = 'BICOND'
_TT_LPAREN  = 'LPAREN'
_TT_RPAREN  = 'RPAREN'
_TT_EOF     = 'EOF'


def _tokenize(text: str) -> list:
    """
    Convert a formula string into a flat list of (token_type, value) tuples.

    Potential fallback: multi-character operators (<->, ->) require look-ahead.
    We scan left-to-right and check longer patterns first to avoid partial
    matches (e.g., '<->' must be checked before '<' alone).
    """
    tokens = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        # --- Whitespace ---
        if ch.isspace():
            i += 1
            continue

        # --- Multi-character operators (must come before single-char checks) ---
        if text[i:i+3] == '<->':
            tokens.append((_TT_BICOND, '<->'))
            i += 3
            continue
        if text[i:i+2] == '->':
            tokens.append((_TT_IMPLIES, '->'))
            i += 2
            continue

        # --- Single-character ASCII operators ---
        if ch == '&':
            tokens.append((_TT_AND, '&'))
        elif ch == '|':
            tokens.append((_TT_OR, '|'))
        elif ch in ('~', '-'):
            tokens.append((_TT_NOT, ch))
        elif ch == '(':
            tokens.append((_TT_LPAREN, '('))
        elif ch == ')':
            tokens.append((_TT_RPAREN, ')'))

        # --- Unicode operators ---
        elif ch == '¬':
            tokens.append((_TT_NOT, '¬'))
        elif ch == '∧':
            tokens.append((_TT_AND, '∧'))
        elif ch == '∨':
            tokens.append((_TT_OR, '∨'))
        elif ch == '→':
            tokens.append((_TT_IMPLIES, '→'))
        elif ch == '↔':
            tokens.append((_TT_BICOND, '↔'))

        # --- Atom: letter followed by letters/digits/underscores ---
        elif ch.isalpha() or ch == '_':
            j = i
            while j < n and (text[j].isalnum() or text[j] == '_'):
                j += 1
            tokens.append((_TT_ATOM, text[i:j]))
            i = j
            continue

        else:
            raise ParseError(
                f"Unexpected character '{ch}' at position {i} in: {text!r}"
            )

        i += 1

    tokens.append((_TT_EOF, None))
    return tokens


# ---------------------------------------------------------------------------
# Recursive-Descent Parser
# ---------------------------------------------------------------------------

class _Parser:
    """
    Internal parser class.  Do not use directly — call parse() instead.

    Grammar (in pseudo-BNF, precedence encoded by nesting):

        formula       ::= biconditional
        biconditional ::= implication ('<->' implication)*
        implication   ::= disjunction ('->' implication)?   ← right-assoc
        disjunction   ::= conjunction ('|' conjunction)*
        conjunction   ::= negation ('&' negation)*
        negation      ::= '~' negation | atom
        atom          ::= IDENTIFIER | '(' formula ')'
    """

    def __init__(self, tokens: list) -> None:
        self._tokens = tokens
        self._pos = 0

    # --- Token helpers ---

    def _peek(self) -> tuple:
        return self._tokens[self._pos]

    def _consume(self, expected_type: str | None = None) -> tuple:
        tok = self._tokens[self._pos]
        if expected_type is not None and tok[0] != expected_type:
            raise ParseError(
                f"Expected token type '{expected_type}' "
                f"but got '{tok[0]}' (value={tok[1]!r})"
            )
        self._pos += 1
        return tok

    # --- Grammar rules ---

    def parse(self) -> Formula:
        result = self._biconditional()
        if self._peek()[0] != _TT_EOF:
            raise ParseError(
                f"Unexpected token {self._peek()} after end of formula"
            )
        return result

    def _biconditional(self) -> Formula:
        # Left-associative: p <-> q <-> r  ≡  (p <-> q) <-> r
        left = self._implication()
        while self._peek()[0] == _TT_BICOND:
            self._consume(_TT_BICOND)
            right = self._implication()
            left = Biconditional(left, right)
        return left

    def _implication(self) -> Formula:
        # RIGHT-associative: p -> q -> r  ≡  p -> (q -> r)
        # Fallback: if this were left-associative, chained implications would
        # have wrong semantics.  We recurse on the right-hand side.
        left = self._disjunction()
        if self._peek()[0] == _TT_IMPLIES:
            self._consume(_TT_IMPLIES)
            right = self._implication()   # <-- recursion gives right-assoc
            return Implies(left, right)
        return left

    def _disjunction(self) -> Formula:
        left = self._conjunction()
        while self._peek()[0] == _TT_OR:
            self._consume(_TT_OR)
            right = self._conjunction()
            left = Or(left, right)
        return left

    def _conjunction(self) -> Formula:
        left = self._negation()
        while self._peek()[0] == _TT_AND:
            self._consume(_TT_AND)
            right = self._negation()
            left = And(left, right)
        return left

    def _negation(self) -> Formula:
        if self._peek()[0] == _TT_NOT:
            self._consume(_TT_NOT)
            operand = self._negation()   # allows ~~p correctly
            return Not(operand)
        return self._atom()

    def _atom(self) -> Formula:
        tok = self._peek()
        if tok[0] == _TT_ATOM:
            self._consume(_TT_ATOM)
            return Atom(tok[1])
        elif tok[0] == _TT_LPAREN:
            self._consume(_TT_LPAREN)
            formula = self._biconditional()   # full sub-formula inside parens
            self._consume(_TT_RPAREN)
            return formula
        else:
            raise ParseError(
                f"Expected an atom or '(' but got '{tok[0]}' (value={tok[1]!r})"
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(text: str) -> Formula:
    """
    Parse a propositional formula string and return a Formula AST.

    Args:
        text: A string representing a propositional formula.

    Returns:
        A Formula object (Atom, Not, And, Or, Implies, or Biconditional).

    Raises:
        ParseError: if the string is syntactically invalid.

    Examples:
        >>> parse("p -> q")
        (p → q)
        >>> parse("~p | (q & r)")
        (¬p ∨ (q ∧ r))
        >>> parse("p <-> q")
        (p ↔ q)
    """
    tokens = _tokenize(text)
    return _Parser(tokens).parse()
