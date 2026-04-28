"""
revision_engine.py — Belief Revision and Contraction
====================================================
Implements operations for expanding, contracting, and revising a belief base,
handling inconsistencies using a priority-based epistemic entrenchment.
"""
from formula import Formula, Not
from belief_base import BeliefBase
from resolution import entails

class RevisionEngine:
    def __init__(self, belief_base: BeliefBase):
        self.bb = belief_base

    def expand(self, formula: Formula, priority: int = 0):
        self.bb.add(formula, priority)
        print(f"Expanded belief base with: {formula} (Priority: {priority})")

    def revise(self, formula: Formula, priority: int = 0):
        negation_phi = Not(formula) 
        self.contract(negation_phi)
        
        self.expand(formula, priority)

    def contract(self, phi):
        if not entails(self.bb.formulas(), phi):
            print(f"Vacuity: '{phi}' is not entailed, no contraction needed.")
            return
            
        sorted_beliefs = sorted(
            self.bb._entries, 
            key=lambda x: (x[1], x[2]), 
            reverse=True
        )
        print(f"DEBUG: Attempting to remove {sorted_beliefs}")
        print(f"Contracting to remove: {phi}")

        for entry in sorted_beliefs:
            formula_to_remove, priority, _ = entry
            
            self.bb.remove(formula_to_remove)
            print(f"  Removed weak belief: {formula_to_remove} (Prio: {priority})")
            
            if not entails(self.bb.formulas(), phi):
                print(f"Success: '{phi}' is no longer entailed.")
                break