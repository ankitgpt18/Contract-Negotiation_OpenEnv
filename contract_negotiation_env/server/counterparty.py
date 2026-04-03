"""
Simulated counterparty for contract negotiations.

The counterparty has a personality (cooperative / neutral / adversarial)
and a concession budget.  It decides whether to accept, partially accept,
or reject agent proposals — and can inject new traps when adversarial.

With learned adaptation, the counterparty tracks what amendment types work
and adjusts future responses strategically.
"""

import random
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict

from contract_negotiation_env.contracts.templates import TRAP_CATALOGUE, TRAP_TITLES
from contract_negotiation_env.models import Amendment, AmendmentType


class AmendmentTracker:
    """Tracks amendment proposal patterns and success rates."""
    
    def __init__(self):
        self.proposal_history: List[Tuple[AmendmentType, str]] = []  # (type, outcome)
        self.amendment_success_rate: Dict[AmendmentType, Tuple[int, int]] = defaultdict(
            lambda: (0, 0)  # (accepted, total)
        )
        self.agent_strategy_signals: Dict[str, int] = {
            "fairness_focused": 0,
            "liability_focused": 0,
            "duration_focused": 0,
            "payment_focused": 0,
            "aggressive": 0,
        }
    
    def record_proposal(self, amendment: Optional[Amendment], outcome: str) -> None:
        """Record a proposal outcome."""
        if amendment:
            self.proposal_history.append((amendment.amendment_type, outcome))
            
            accepted, total = self.amendment_success_rate[amendment.amendment_type]
            total += 1
            if outcome == "accepted":
                accepted += 1
            self.amendment_success_rate[amendment.amendment_type] = (accepted, total)
            
            # Update strategy signals
            if amendment.amendment_type == AmendmentType.FAIRNESS_IMPROVEMENT:
                self.agent_strategy_signals["fairness_focused"] += 1
            elif amendment.amendment_type == AmendmentType.MODIFY_LIABILITY_CAP:
                self.agent_strategy_signals["liability_focused"] += 1
            elif amendment.amendment_type == AmendmentType.MODIFY_DURATION:
                self.agent_strategy_signals["duration_focused"] += 1
            elif amendment.amendment_type == AmendmentType.MODIFY_PAYMENT_TERMS:
                self.agent_strategy_signals["payment_focused"] += 1
            
            if outcome == "rejected":
                self.agent_strategy_signals["aggressive"] += 1
    
    def get_success_rate(self, amendment_type: AmendmentType) -> float:
        """Get success rate for a specific amendment type (0-1)."""
        accepted, total = self.amendment_success_rate.get(amendment_type, (0, 0))
        if total == 0:
            return 0.5  # Default neutral
        return accepted / total
    
    def get_agent_strategy_profile(self) -> str:
        """Infer agent's negotiation strategy."""
        if not self.agent_strategy_signals:
            return "analytical"
        
        max_signal = max(self.agent_strategy_signals.values())
        if max_signal == 0:
            return "analytical"
        
        dominant_signals = [k for k, v in self.agent_strategy_signals.items() if v == max_signal]
        if "aggressive" in dominant_signals:
            return "aggressive"
        elif "fairness_focused" in dominant_signals:
            return "fairness_conscious"
        elif "liability_focused" in dominant_signals:
            return "risk_averse"
        else:
            return "balanced"


class Counterparty:
    """
    Stateful opponent that reacts to the agent's proposals.

    concession_budget starts at 1.0 and decreases as the counterparty
    makes concessions.  Once it hits 0 the counterparty won't budge.
    
    With learning: tracks amendment types, success patterns, and agent
    strategies to provide adaptive responses.
    """

    def __init__(
        self,
        style: str = "neutral",
        concession_budget: float = 1.0,
        seed: int | None = None,
        learning_enabled: bool = True,
    ):
        self.style = style
        self.budget = concession_budget
        self.rng = random.Random(seed)
        self.concessions_made: List[int] = []  # clause indices conceded
        self.new_traps_injected = 0
        self.learning_enabled = learning_enabled
        self.tracker = AmendmentTracker() if learning_enabled else None

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
        proposal_text: str = "",
        amendment: Optional[Amendment] = None,
        clause_data: Dict[str, Any] = None,
        all_clauses: List[Dict[str, Any]] = None,
        trap_meta: List[Dict[str, Any]] = None,
    ) -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Evaluate a proposed amendment and return a response.
        
        Supports both structured amendments and legacy text proposals.

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
        if clause_data is None:
            clause_data = {}
        if all_clauses is None:
            all_clauses = []
        if trap_meta is None:
            trap_meta = []
            
        # Handle structured amendments with enhanced logic
        if amendment:
            return self._respond_to_amendment(
                amendment, clause_data, all_clauses, trap_meta
            )
        
        # Fall back to legacy text proposal handling
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
        return self._reject(clause_idx, all_clauses, trap_meta)
    
    def _respond_to_amendment(
        self,
        amendment: Amendment,
        clause_data: Dict[str, Any],
        all_clauses: List[Dict[str, Any]],
        trap_meta: List[Dict[str, Any]],
    ) -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Evaluate a structured amendment with type-aware and learned logic."""
        
        # Validate the amendment structure
        if not amendment.validate():
            outcome = "rejected"
            msg = self._reject(amendment.clause_idx, all_clauses, trap_meta)[1]
            if self.learning_enabled:
                self.tracker.record_proposal(amendment, outcome)
            return outcome, msg, all_clauses, trap_meta
        
        # Calculate acceptance likelihood
        acceptance_score = self._calculate_amendment_score(amendment, clause_data)
        
        # Incorporate learning: boost score if agent has successfully used this type
        if self.learning_enabled and self.tracker:
            success_rate = self.tracker.get_success_rate(amendment.amendment_type)
            # Cooperative counterparty learns faster
            learning_boost = success_rate * (0.5 if self.style == "cooperative" else 0.15)
            acceptance_score += learning_boost
            acceptance_score = min(0.95, acceptance_score)  # Cap at 0.95
        
        threshold = self._accept_thresh.get(self.style, 0.55)
        effective_threshold = threshold * (1.0 - self.budget * 0.3)
        
        # Cooperative counterparty: more likely to accept fixing amendments, learns quickly
        if self.style == "cooperative" and acceptance_score > 0.4:
            outcome, msg, updated_clauses, updated_traps = self._accept(
                amendment.clause_idx, clause_data, all_clauses, trap_meta
            )
            if self.learning_enabled:
                self.tracker.record_proposal(amendment, outcome)
            return outcome, msg, updated_clauses, updated_traps
        
        # Generic roll with learned adjustment
        roll = self.rng.random()
        if roll > effective_threshold and self.budget > 0.1:
            outcome, msg, updated_clauses, updated_traps = self._accept(
                amendment.clause_idx, clause_data, all_clauses, trap_meta
            )
            if self.learning_enabled:
                self.tracker.record_proposal(amendment, outcome)
            return outcome, msg, updated_clauses, updated_traps
        
        # Adversarial: inject counter trap (but less if agent has been strategic)
        if self.style == "adversarial" and self.rng.random() < 0.3:
            outcome, msg, updated_clauses, updated_traps = self._inject_counter_trap(
                amendment.clause_idx, all_clauses, trap_meta
            )
            if self.learning_enabled:
                self.tracker.record_proposal(amendment, outcome)
            return outcome, msg, updated_clauses, updated_traps
        
        # Partial concession (more likely if agent strategy is balanced)
        if self.budget > 0.3 and self.rng.random() < 0.55:
            outcome, msg, updated_clauses, updated_traps = self._partial_accept(
                amendment.clause_idx, clause_data, all_clauses, trap_meta
            )
            if self.learning_enabled:
                self.tracker.record_proposal(amendment, outcome)
            return outcome, msg, updated_clauses, updated_traps
        
        outcome = "rejected"
        msg = self._reject(amendment.clause_idx, all_clauses, trap_meta)[1]
        if self.learning_enabled:
            self.tracker.record_proposal(amendment, outcome)
        return outcome, msg, all_clauses, trap_meta
    
    def _calculate_amendment_score(
        self, amendment: Amendment, clause_data: Dict[str, Any]
    ) -> float:
        """Score how favorable an amendment is (0-1, higher = more favorable)."""
        
        score = 0.5  # baseline
        
        # Fairness-improving amendments are always viewed positively
        if amendment.amendment_type == AmendmentType.FAIRNESS_IMPROVEMENT:
            score = 0.75
        
        # Liability caps are viewed favorably by cooperative/neutral
        elif amendment.amendment_type == AmendmentType.MODIFY_LIABILITY_CAP:
            if self.style != "adversarial":
                score = 0.70
            else:
                score = 0.35
        
        # Narrowing non-competes is favorable
        elif amendment.amendment_type == AmendmentType.MODIFY_NON_COMPETE:
            score = 0.65
        
        # Protective clauses are viewed as reasonable
        elif amendment.amendment_type == AmendmentType.ADD_PROTECTIVE_CLAUSE:
            score = 0.60
        
        # Limit auto-renewal is reasonable
        elif amendment.amendment_type == AmendmentType.LIMIT_AUTO_RENEWAL:
            if self.style != "adversarial":
                score = 0.65
            else:
                score = 0.40
        
        # Payment term modifications depend on parameters
        elif amendment.amendment_type == AmendmentType.MODIFY_PAYMENT_TERMS:
            # Extend payment terms slightly improves score
            if amendment.parameters.get("payment_days", 0) > 30:
                score = 0.65
            else:
                score = 0.50
        
        # Remove clause is contentious
        elif amendment.amendment_type == AmendmentType.REMOVE_CLAUSE:
            score = 0.30
        
        return score

    def respond_to_counter_offer(
        self,
        clause_idx: int,
        counter_text: str = "",
        amendment: Optional[Amendment] = None,
        clause_data: Dict[str, Any] = None,
        all_clauses: List[Dict[str, Any]] = None,
        trap_meta: List[Dict[str, Any]] = None,
    ) -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Handle agent's counter-offer — similar logic but slightly more lenient."""
        # counter-offers show persistence so slightly lower threshold
        self.budget = max(0, self.budget - 0.05)
        return self.respond_to_proposal(
            clause_idx, counter_text, amendment, clause_data, all_clauses, trap_meta
        )
    
    def get_learned_insights(self) -> Dict[str, Any]:
        """
        Extract what the counterparty has learned about the agent.
        
        Returns info about detected agent strategy, amendment effectiveness, etc.
        """
        if not self.learning_enabled or not self.tracker:
            return {}
        
        insights = {
            "agent_strategy": self.tracker.get_agent_strategy_profile(),
            "proposals_made": len(self.tracker.proposal_history),
            "amendment_success_rates": {},
        }
        
        # Add success rates for each amendment type
        for amendment_type, (accepted, total) in self.tracker.amendment_success_rate.items():
            success_rate = accepted / total if total > 0 else 0
            insights["amendment_success_rates"][amendment_type.value] = {
                "accepted": accepted,
                "total": total,
                "success_rate": round(success_rate, 2),
            }
        
        return insights

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
        self, clause_idx: int, all_clauses: List[Dict[str, Any]] = None, trap_meta: List[Dict[str, Any]] = None
    ) -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        msg = (
            f"We appreciate the feedback on Clause {clause_idx + 1}, "
            f"but this provision is standard in our agreements and "
            f"non-negotiable at this time."
        )
        return "rejected", msg, all_clauses or [], trap_meta or []

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
            return self._reject(original_idx, all_clauses, trap_meta)

        new_key = self.rng.choice(available)
        new_trap = TRAP_CATALOGUE[new_key]

        # find a fair clause to replace with the new trap
        fair_indices = [c["idx"] for c in all_clauses if not c.get("is_trap")]
        if not fair_indices:
            return self._reject(original_idx, all_clauses, trap_meta)

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
