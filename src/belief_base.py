"""
belief_base.py — Belief Base with Priority Order
=================================================
Implements an ordered belief base where formulas carry explicit priorities.

Designed by Member A.  Member B exposes this interface here as a documented
stub so that Members C and the main demo can import it regardless of
Member A's final implementation state.

Priority convention
-------------------
  Lower numeric priority = more entrenched (less likely to be contracted).
  Higher numeric priority = less entrenched (first candidate for removal).

  Example:  background knowledge might receive priority 0 (most entrenched),
            recent observations priority 10 (first to be dropped).

  When two formulas have equal priority, the one added *earlier* (lower
  insertion index) is considered more entrenched.

Public interface used by Member C (contraction / revision)
----------------------------------------------------------
  bb = BeliefBase()
  bb.add(formula, priority=5)       # add with explicit priority
  bb.add(formula)                   # add with default/auto priority
  bb.remove(formula)
  bb.formulas()        → List[Formula]  ordered highest-priority first
  bb.least_entrenched_subset(phi)   → subset to remove for contraction
  formula in bb        → bool
  len(bb)              → int
  iter(bb)             → iterate over Formula objects

Public interface used by Member B (entailment)
----------------------------------------------
  entails(bb.formulas(), phi)   — pass the formula list directly

Nothing in belief_base.py imports from resolution.py to avoid cycles.
"""

from __future__ import annotations

from typing import List, Iterator, Optional, Tuple
from formula import Formula


class BeliefBase:
    """
    An ordered belief base with explicit formula priorities.

    Internally stores (formula, priority, insertion_order) triples so that
    iteration order is well-defined and contraction can identify the least
    entrenched formulas deterministically.
    """

    def __init__(self) -> None:
        # Each entry: (formula, priority, insertion_index)
        self._entries: List[Tuple[Formula, int, int]] = []
        self._insertion_counter: int = 0

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add(self, formula: Formula, priority: int = 0) -> None:
        """
        Add *formula* to the belief base with the given *priority*.

        If the identical formula is already present (by structural equality),
        the existing entry is updated to the NEW priority value.  This
        matches the AGM intuition that asserting something more strongly can
        change its entrenchment.

        Args:
            formula:  A Formula object.
            priority: Non-negative integer.  Higher value = less entrenched.
                      Default 0 = most entrenched.
        """
        if priority < 0:
            raise ValueError(f"Priority must be non-negative, got {priority}.")

        # Replace existing entry if same formula already known
        for idx, (f, p, ins) in enumerate(self._entries):
            if f == formula:
                self._entries[idx] = (formula, priority, ins)
                return

        self._entries.append((formula, priority, self._insertion_counter))
        self._insertion_counter += 1

    def remove(self, formula: Formula) -> None:
        """
        Remove *formula* from the belief base.

        Raises:
            KeyError if the formula is not present.
        """
        for idx, (f, _, _) in enumerate(self._entries):
            if f == formula:
                del self._entries[idx]
                return
        raise KeyError(f"Formula not found in belief base: {formula!r}")

    def clear(self) -> None:
        """Remove all formulas."""
        self._entries.clear()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def formulas(self) -> List[Formula]:
        """
        Return all formulas as a plain Python list (no priority metadata).

        This is the list passed to  entails(belief_base.formulas(), phi)
        in resolution.py.
        """
        return [f for f, _p, _i in self._entries]

    def formulas_with_priority(self) -> List[Tuple[Formula, int]]:
        """Return list of (formula, priority) pairs, sorted most→least entrenched."""
        sorted_entries = sorted(self._entries, key=lambda e: (e[1], e[2]))
        return [(f, p) for f, p, _ in sorted_entries]

    def least_entrenched(self) -> Optional[Formula]:
        """
        Return the single least-entrenched formula (highest priority value,
        latest insertion if tied), or None if the base is empty.

        Used by Member C's partial-meet contraction.
        """
        if not self._entries:
            return None
        # Sort by (priority desc, insertion_index desc) → last element is least entrenched
        worst = max(self._entries, key=lambda e: (e[1], e[2]))
        return worst[0]

    def least_entrenched_implying(self, phi: Formula) -> List[Formula]:
        """
        Return the least-entrenched formulas that (together with the rest)
        contribute to entailment of phi.

        Simple implementation: remove formulas in ascending entrenchment order
        (least entrenched first) until the truncated base no longer entails phi.
        Returns the removed formulas — these form the 'contraction kernel'.

        NOTE: Full partial-meet contraction is implemented by Member C.
        This helper is provided for convenience.
        """
        from resolution import entails as _entails   # local import avoids cycle

        sorted_entries = sorted(self._entries, key=lambda e: (-e[1], -e[2]))
        remaining = list(self._entries)
        removed: List[Formula] = []

        for entry in sorted_entries:
            candidate_remaining = [e for e in remaining if e is not entry]
            candidate_formulas = [f for f, _, _ in candidate_remaining]
            if not _entails(candidate_formulas, phi):
                remaining = candidate_remaining
                removed.append(entry[0])
                if not _entails([f for f, _, _ in remaining], phi):
                    break

        return removed

    # ------------------------------------------------------------------
    # Python special methods
    # ------------------------------------------------------------------

    def __contains__(self, formula: Formula) -> bool:
        return any(f == formula for f, _, _ in self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[Formula]:
        for f, _, _ in self._entries:
            yield f

    def __repr__(self) -> str:
        items = ", ".join(repr(f) for f, _, _ in self._entries)
        return f"BeliefBase([{items}])"
