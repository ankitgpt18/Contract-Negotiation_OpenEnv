"""
Simulated counterparty for contract negotiations.

The counterparty has a personality (cooperative / neutral / adversarial)
and a concession budget.  It decides whether to accept, partially accept,
or reject agent proposals — and can inject new traps when adversarial.
"""

import random
from typing import Dict, Any, List, Tuple

from contract_negotiation_env.contracts.templates import TRAP_CATALOGUE, TRAP_TITLES


class Counterparty:
    """
    Stateful opponent that reacts to the agent's proposals.

    concession_budget starts at 1.0 and decreases as the counterparty
    makes concessions.  Once it hits 0 the counterparty won't budge.
    """

    def __init__(
        self,
        style: str = "neutral",
        concession_budget: float = 1.0,
        seed: int | None = None,
    ):
        self.style = style
        self.budget = concession_budget
        self.rng = random.Random(seed)
        self.concessions_made: List[int] = []  # clause indices conceded
        self.new_traps_injected = 0

        # base acceptance thresholds per style
        self._accept_thresh = {
            "cooperative": 0.35,
            "neutral": 0.55,
            "adversarial": 0.75,
        }

    # ── public interface ─────────────────────────────────────────────

    def respond_to_proposal(
        self,
        clause_idx: int,
        proposal_text: str,
        clause_data: Dict[str, Any],
        all_clauses: List[Dict[str, Any]],
        trap_meta: List[Dict[str, Any]],
    ) -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Evaluate a proposed amendment and return a response.

        Returns
        -------
        outcome : str
            "accepted" | "partial" | "rejected" | "counter"
        message : str
            Natural-language response from the counterparty.
        updated_clauses : list
            Clauses after any accepted changes.
        updated_traps : list
            Trap metadata after any fixes.
        """
        is_trap = clause_data.get("is_trap", False)
        threshold = self._accept_thresh.get(self.style, 0.55)

        # roll the dice, weighted by remaining budget
        roll = self.rng.random()
        effective_threshold = threshold * (1.0 - self.budget * 0.3)

        # cooperative counterparty almost always accepts legitimate fixes
        if is_trap and self.style == "cooperative" and self.budget > 0.2:
            return self._accept(clause_idx, clause_data, all_clauses, trap_meta)

        if roll > effective_threshold and self.budget > 0.1:
            return self._accept(clause_idx, clause_data, all_clauses, trap_meta)

        # adversarial counterparty may counter with a new trap swap
        if self.style == "adversarial" and self.rng.random() < 0.4:
            return self._inject_counter_trap(
                clause_idx, all_clauses, trap_meta
            )

        # partial concession — fix the wording but keep some edge
        if self.budget > 0.3 and self.rng.random() < 0.5:
            return self._partial_accept(clause_idx, clause_data, all_clauses, trap_meta)

        # flat rejection
        return self._reject(clause_idx)

    def respond_to_counter_offer(
        self,
        clause_idx: int,
        counter_text: str,
        clause_data: Dict[str, Any],
        all_clauses: List[Dict[str, Any]],
        trap_meta: List[Dict[str, Any]],
    ) -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Handle agent's counter-offer — similar logic but slightly more lenient."""
        # counter-offers show persistence so slightly lower threshold
        self.budget = max(0, self.budget - 0.05)
        return self.respond_to_proposal(
            clause_idx, counter_text, clause_data, all_clauses, trap_meta
        )

    # ── internal helpers ──────────────────────────────────────────────

    def _accept(
        self,
        clause_idx: int,
        clause_data: Dict[str, Any],
        all_clauses: List[Dict[str, Any]],
        trap_meta: List[Dict[str, Any]],
    ) -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        self.budget -= 0.15
        self.concessions_made.append(clause_idx)

        # if this was a trap, mark it fixed
        for tm in trap_meta:
            if tm["clause_idx"] == clause_idx:
                tm["fixed"] = True
                # rewrite the clause body with the fair version
                fair_text = tm.get("fair_version", clause_data["body"])
                for c in all_clauses:
                    if c["idx"] == clause_idx:
                        c["body"] = fair_text
                        c["fairness"] = 0.90
                        break

        msg = (
            f"We agree to revise Clause {clause_idx + 1} "
            f"({clause_data.get('title', '')}).  The updated language "
            f"has been incorporated."
        )
        return "accepted", msg, all_clauses, trap_meta

    def _partial_accept(
        self,
        clause_idx: int,
        clause_data: Dict[str, Any],
        all_clauses: List[Dict[str, Any]],
        trap_meta: List[Dict[str, Any]],
    ) -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        self.budget -= 0.08

        # soften the clause slightly but don't fully fix it
        for c in all_clauses:
            if c["idx"] == clause_idx:
                c["fairness"] = min(0.75, c.get("fairness", 0.5) + 0.2)
                break

        msg = (
            f"We can partially accommodate your concern about "
            f"Clause {clause_idx + 1}.  We've softened the language but "
            f"some protective provisions must remain.  Please review the "
            f"revised text."
        )
        return "partial", msg, all_clauses, trap_meta

    def _reject(
        self, clause_idx: int
    ) -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        msg = (
            f"We appreciate the feedback on Clause {clause_idx + 1}, "
            f"but this provision is standard in our agreements and "
            f"non-negotiable at this time."
        )
        return "rejected", msg, [], []  # no changes

    def _inject_counter_trap(
        self,
        original_idx: int,
        all_clauses: List[Dict[str, Any]],
        trap_meta: List[Dict[str, Any]],
    ) -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Adversarial move: accept the change but sneak in a new trap elsewhere.
        """
        existing_types = {tm["trap_type"] for tm in trap_meta}
        available = [k for k in TRAP_CATALOGUE if k not in existing_types]

        if not available:
            return self._reject(original_idx)

        new_key = self.rng.choice(available)
        new_trap = TRAP_CATALOGUE[new_key]

        # find a fair clause to replace with the new trap
        fair_indices = [c["idx"] for c in all_clauses if not c.get("is_trap")]
        if not fair_indices:
            return self._reject(original_idx)

        target_idx = self.rng.choice(fair_indices)

        for c in all_clauses:
            if c["idx"] == target_idx:
                c["title"] = TRAP_TITLES[new_key]
                c["body"] = new_trap["text"]
                c["fairness"] = round(1.0 - new_trap["severity"], 2)
                c["is_trap"] = True
                c["trap_type"] = new_key
                break

        trap_meta.append({
            "clause_idx": target_idx,
            "trap_type": new_key,
            "severity": new_trap["severity"],
            "description": new_trap["why_bad"],
            "fair_version": new_trap["fair_version"],
            "detected": False,
            "fixed": False,
        })

        self.new_traps_injected += 1
        self.budget -= 0.10

        msg = (
            f"We've agreed to revise Clause {original_idx + 1} as requested.  "
            f"We've also updated some other provisions to align with our "
            f"revised internal policies.  Please review the latest draft."
        )
        return "counter", msg, all_clauses, trap_meta
