"""
mastermind.py — Mastermind AI via Belief Revision  (Optional 2)
================================================================
Implements a Mastermind-playing AI agent that uses the belief revision
engine as its reasoning core.

Game rules (standard 4-peg, 6-colour Mastermind)
--------------------------------------------------
  • The codemaker picks a secret code: an ordered sequence of 4 pegs,
    each a colour from {1, 2, 3, 4, 5, 6}.
  • After each guess, the codebreaker receives feedback:
      - black_pegs: number of positions with the correct colour
      - white_pegs: number of correct colours in wrong positions
  • The codebreaker wins by guessing the exact code.

Belief revision approach
------------------------
  The agent maintains a set of *candidate* codes — all codes that are
  consistent with the observations so far.  Each feedback act as a revision:

    revise(B, "guess G gave feedback (b, w)")
    ⟹  remove from candidates any code inconsistent with that feedback

  This is exactly belief revision under new evidence:
    • *Expansion*: no candidates are added (we only learn constraints).
    • *Contraction*: inconsistent candidates are eliminated.
    • The remaining candidates form the agent's current belief state.

  Propositional encoding (optional, demoed in demo_mastermind)
  -----------------------------------------------------------
  Each candidate code is encoded as a propositional atom `code_<i>` where
  i is an index into the full list of 1296 possible codes.  Feedback
  eliminates codes by asserting ¬code_i for each ruled-out candidate.
  The agent then selects its next guess from the remaining believed codes.

  This bridges the abstract belief revision framework with a concrete game,
  illustrating how to use entailment as a filter on hypotheses.

Strategy
--------
  The agent uses a *minimax* strategy: at each step it picks the guess
  that minimises the maximum number of remaining candidates regardless
  of the feedback received (Knuth's 5-guess algorithm principle).
  For efficiency it picks from the current candidate set only.

Usage
-----
  from mastermind import MastermindAgent, play_mastermind

  agent = MastermindAgent()
  agent.make_guess()          # get first guess
  agent.receive_feedback(1, 2)
  agent.make_guess()          # get refined guess
  ...
  play_mastermind(secret=(1, 2, 3, 4))  # full auto game
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from itertools import product
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from formula import Atom, Not, And
from belief_base import BeliefBase
from resolution import entails


# ---------------------------------------------------------------------------
# Game constants
# ---------------------------------------------------------------------------

COLOURS = (1, 2, 3, 4, 5, 6)
PEGS    = 4

# All possible codes: 6^4 = 1296 tuples
ALL_CODES: List[Tuple[int, ...]] = list(product(COLOURS, repeat=PEGS))


# ---------------------------------------------------------------------------
# Feedback helper
# ---------------------------------------------------------------------------

def score(guess: Tuple[int, ...], secret: Tuple[int, ...]) -> Tuple[int, int]:
    """
    Compute (black_pegs, white_pegs) for a guess against a secret.

    black_pegs = number of positions where colour is exactly correct.
    white_pegs = number of correct colours in wrong positions.

    Args:
        guess:  Tuple of PEGS colour integers.
        secret: The secret code tuple.

    Returns:
        (black_pegs, white_pegs)  — the standard Mastermind feedback.

    Algorithm
    ---------
    1. Count exact matches (black pegs).
    2. For each colour c, count min(occurrences in guess, occurrences in secret).
       Sum gives total correct colours (including exact matches).
    3. white_pegs = total_correct - black_pegs.
    """
    black = sum(g == s for g, s in zip(guess, secret))

    colour_counts_guess   = [guess.count(c)  for c in COLOURS]
    colour_counts_secret  = [secret.count(c) for c in COLOURS]
    total_correct = sum(min(cg, cs) for cg, cs in
                        zip(colour_counts_guess, colour_counts_secret))

    white = total_correct - black
    return black, white


# ---------------------------------------------------------------------------
# MastermindAgent
# ---------------------------------------------------------------------------

class MastermindAgent:
    """
    A Mastermind codebreaker agent that uses belief revision semantics.

    The agent maintains a `BeliefBase` whose formulas are atoms of the form
    `code_<i>` (one per candidate code index).  Initially all 1296 atoms are
    *implicitly believed* (all codes are candidates).

    When feedback is received, the agent calls `revise()` on the belief
    base: it adds ¬code_i for every candidate that is inconsistent with
    the feedback.  Candidates are those code_i atoms NOT negated.

    Attributes:
        candidates: Current list of remaining possible codes.
        history:    List of (guess, (black, white)) tuples — game history.
        bb:         BeliefBase tracking which codes remain possible.
    """

    def __init__(self) -> None:
        self.candidates: List[Tuple[int, ...]] = list(ALL_CODES)
        self.history:    List[Tuple[Tuple[int, ...], Tuple[int, int]]] = []
        self.bb:         BeliefBase = BeliefBase()

        # Each candidate code gets an atom  code_i  in the belief base
        self._atoms: Dict[int, Atom] = {
            i: Atom(f"code_{i}") for i in range(len(ALL_CODES))
        }
        # Assert all codes as possible (priority 0 = highly entrenched)
        for atom in self._atoms.values():
            self.bb.add(atom, priority=0)

    # ------------------------------------------------------------------
    # Core belief-revision interface
    # ------------------------------------------------------------------

    def receive_feedback(self, guess: Tuple[int, ...],
                         black: int, white: int) -> None:
        """
        Update the agent's beliefs given feedback for *guess*.

        Steps:
        1. For each candidate code c, compute score(guess, c).
        2. If score != (black, white), then c is impossible: add ¬code_i
           to the belief base (high-priority, i.e. easy to be removed if
           needed, but here it's the core evidence).
        3. Remove eliminated codes from the candidates list.
        4. Record history.

        This implements the AGM revision step: the agent revises its
        belief state with the new evidence.
        """
        eliminated = []
        for i, code in enumerate(ALL_CODES):
            atom = self._atoms[i]
            if atom not in self.bb:
                continue    # already eliminated in a previous step

            if score(guess, code) != (black, white):
                # This code is impossible: add its negation to the base
                neg = Not(atom)
                self.bb.add(neg, priority=len(self.history) + 1)
                # Remove the positive atom (it is now contradicted)
                if atom in self.bb:
                    self.bb.remove(atom)
                eliminated.append(code)

        # Sync candidates list
        eliminated_set = set(eliminated)
        self.candidates = [c for c in self.candidates
                           if c not in eliminated_set]
        self.history.append((guess, (black, white)))

    def make_guess(self) -> Tuple[int, ...]:
        """
        Return the agent's next guess using a minimax strategy.

        Strategy:
        - On the first move, return the hardcoded optimal first guess (1,1,2,2)
          which Knuth proved minimises the worst-case number of remaining
          candidates.
        - On subsequent moves: for each candidate c, compute the maximum
          number of candidates that would remain for any possible feedback.
          Pick the candidate that minimises this maximum (minimax).

        Falls back to the first candidate if no better choice is found.

        Returns:
            A code tuple (c1, c2, c3, c4) to guess.
        """
        if not self.history:
            return (1, 1, 2, 2)   # Knuth's optimal first guess

        if len(self.candidates) == 1:
            return self.candidates[0]

        if len(self.candidates) <= 2:
            return self.candidates[0]

        # Minimax over candidates only (fast enough for <= 1296 codes)
        best_guess  = self.candidates[0]
        best_max    = len(self.candidates) + 1

        for candidate in self.candidates:
            # Partition remaining candidates by feedback
            partition: Dict[Tuple[int, int], int] = {}
            for other in self.candidates:
                fb = score(candidate, other)
                partition[fb] = partition.get(fb, 0) + 1
            worst_case = max(partition.values())
            if worst_case < best_max:
                best_max   = worst_case
                best_guess = candidate

        return best_guess

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def is_solved(self) -> bool:
        """Return True iff the agent has zeroed in on the secret code."""
        return len(self.candidates) == 1

    def remaining(self) -> int:
        """Return the number of candidate codes remaining."""
        return len(self.candidates)

    def __repr__(self) -> str:
        return (f"MastermindAgent("
                f"remaining={self.remaining()}, "
                f"moves={len(self.history)})")


# ---------------------------------------------------------------------------
# play_mastermind — full automated game
# ---------------------------------------------------------------------------

def play_mastermind(
    secret: Tuple[int, ...],
    verbose: bool = True,
    max_guesses: int = 10,
) -> int:
    """
    Run a complete automated Mastermind game against the given *secret*.

    Args:
        secret:      The secret code as a 4-tuple of colour ints (1–6).
        verbose:     If True, print each guess and feedback.
        max_guesses: Safety limit to prevent infinite loops.

    Returns:
        The number of guesses taken to solve the code.
        Returns -1 if the code was not cracked within *max_guesses*.

    Example output (verbose=True):
        Mastermind: secret is hidden.  Agent is guessing...
        Guess 1: (1, 1, 2, 2)  →  black=0, white=1  (1294 candidates left)
        Guess 2: (3, 3, 4, 5)  →  black=0, white=0  (294 candidates left)
        ...
        Guess N: (x, y, z, w)  →  black=4, white=0  ← SOLVED in N guesses!
    """
    if verbose:
        print("  Mastermind: secret is hidden.  Agent is guessing...")

    agent = MastermindAgent()

    for turn in range(1, max_guesses + 1):
        guess = agent.make_guess()
        black, white = score(guess, secret)

        if verbose:
            print(
                f"  Guess {turn}: {guess}  →  "
                f"black={black}, white={white}  "
                f"({agent.remaining()} candidates before feedback)"
            )

        agent.receive_feedback(guess, black, white)

        if black == PEGS:
            if verbose:
                print(f"  ← SOLVED in {turn} guess{'es' if turn > 1 else ''}!")
            return turn

    if verbose:
        print(f"  ← Could not solve within {max_guesses} guesses.")
    return -1


# ---------------------------------------------------------------------------
# Benchmark: test agent on all 1296 possible codes
# ---------------------------------------------------------------------------

def benchmark(verbose: bool = False) -> Dict[str, object]:
    """
    Run the agent on every one of the 1296 possible codes and collect stats.

    Returns a dict with keys:
      max_guesses    — worst-case number of guesses across all codes
      avg_guesses    — average number of guesses
      solved_within  — dict mapping  n_guesses → count of codes solved in n
      unsolved       — list of codes not solved (should be empty)
    """
    results: Dict[int, int] = {}
    unsolved: List[Tuple[int, ...]] = []

    for secret in ALL_CODES:
        n = play_mastermind(secret, verbose=verbose)
        if n == -1:
            unsolved.append(secret)
        else:
            results[n] = results.get(n, 0) + 1

    total = sum(results.values())
    avg   = sum(k * v for k, v in results.items()) / total if total > 0 else 0

    return {
        "max_guesses":   max(results.keys(), default=0),
        "avg_guesses":   round(avg, 3),
        "solved_within": results,
        "unsolved":      unsolved,
    }
