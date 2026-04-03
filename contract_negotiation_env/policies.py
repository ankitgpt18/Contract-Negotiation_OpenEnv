"""
Reusable policy helpers for demos and benchmarking.
"""

from dataclasses import dataclass, field
from random import Random

from contract_negotiation_env.models import (
    MoveKind,
    NegotiationAction,
    Amendment,
    AmendmentType,
)


def infer_amendment_type(clause_title: str, fairness: float) -> AmendmentType:
    """Infer an appropriate amendment type from clause title and fairness."""
    title_lower = clause_title.lower()
    
    if "termination" in title_lower:
        return AmendmentType.MODIFY_TERMINATION
    elif "payment" in title_lower or "fee" in title_lower:
        return AmendmentType.MODIFY_PAYMENT_TERMS
    elif "liability" in title_lower or "indemnif" in title_lower:
        return AmendmentType.MODIFY_LIABILITY_CAP
    elif "non-compet" in title_lower or "non-compete" in title_lower:
        return AmendmentType.MODIFY_NON_COMPETE
    elif "renewal" in title_lower or "auto-renew" in title_lower:
        return AmendmentType.LIMIT_AUTO_RENEWAL
    elif "intellectual property" in title_lower or "ip" in title_lower:
        return AmendmentType.MODIFY_IP_RIGHTS
    else:
        return AmendmentType.FAIRNESS_IMPROVEMENT


@dataclass
class TrapAwarePolicy:
    """
    Stateful heuristic policy tuned for hard negotiation profiles.

    Strategy:
    1) Use all analysis moves for direct risk assessment (max trap coverage).
    2) Prioritize proposals on detected high-risk clauses.
    3) Escalate to counter-offers when rejected.
    4) Walk away when risk remains high and counterparty is uncooperative.
    
    Generates structured amendments when possible.
    """

    rng: Random = field(default_factory=Random)
    risky_indices: list[int] = field(default_factory=list)
    scanned_idx: int = 0
    last_assessed_idx: int | None = None
    reject_count: int = 0
    accept_count: int = 0
    proposal_turn: int = 0
    clause_titles: dict[int, str] = field(default_factory=dict)

    def _record_observation(self, obs) -> None:
        if self.last_assessed_idx is not None and "HIGH RISK" in (obs.risk_report or ""):
            if self.last_assessed_idx not in self.risky_indices:
                self.risky_indices.append(self.last_assessed_idx)

        response = (obs.counterparty_response or "").lower()
        if "rejected" in response or "non-negotiable" in response:
            self.reject_count += 1
        if "accepted" in response or "revised" in response:
            self.accept_count += 1
        
        # Store clause titles for amendment generation
        if obs.clauses:
            for clause in obs.clauses:
                cidx = clause.get("idx", 0)
                self.clause_titles[cidx] = clause.get("title", "")

    def _create_structured_amendment(self, clause_idx: int, clause_data: dict) -> Amendment:
        """Generate a structured amendment based on clause data."""
        title = self.clause_titles.get(clause_idx, clause_data.get("title", ""))
        fairness = clause_data.get("fairness", 0.5)
        
        amendment_type = infer_amendment_type(title, fairness)
        
        # Create type-specific parameters
        parameters = {}
        if amendment_type == AmendmentType.MODIFY_PAYMENT_TERMS:
            parameters = {"payment_days": 30, "late_fee_cap": 0.015}
        elif amendment_type == AmendmentType.MODIFY_LIABILITY_CAP:
            parameters = {"cap_percentage": 1.0}  # Cap at 1x annual fees
        elif amendment_type == AmendmentType.MODIFY_DURATION:
            parameters = {"duration_months": 12}
        elif amendment_type == AmendmentType.MODIFY_NON_COMPETE:
            parameters = {"duration_months": 6, "scope": "direct_solicitation"}
        elif amendment_type == AmendmentType.LIMIT_AUTO_RENEWAL:
            parameters = {"advance_notice_days": 30}
        
        return Amendment(
            amendment_type=amendment_type,
            clause_idx=clause_idx,
            parameters=parameters,
            rationale="Proposed modification to improve fairness.",
        )

    def act(self, obs) -> NegotiationAction:
        self._record_observation(obs)

        if obs.done:
            return NegotiationAction(move_kind=MoveKind.ACCEPT_TERMS, clause_idx=0)

        # Highest-value analysis move: assess risk directly.
        if obs.analysis_moves_left > 0:
            idx = self.scanned_idx % max(1, len(obs.clauses))
            self.scanned_idx += 1
            self.last_assessed_idx = idx
            return NegotiationAction(move_kind=MoveKind.ASSESS_RISK, clause_idx=idx)

        # Negotiate detected risk first with structured amendments.
        if self.risky_indices and obs.rounds_left > 3:
            target_idx = self.risky_indices[self.proposal_turn % len(self.risky_indices)]
            self.proposal_turn += 1
            
            # Find the clause data
            clause_data = {}
            if obs.clauses:
                for c in obs.clauses:
                    if c.get("idx") == target_idx:
                        clause_data = c
                        break
            
            amendment = self._create_structured_amendment(target_idx, clause_data)
            
            return NegotiationAction(
                move_kind=MoveKind.PROPOSE_CHANGE,
                clause_idx=target_idx,
                amendment=amendment,
                proposal_text=(
                    "This clause is one-sided and creates asymmetric legal risk. "
                    "Please revise with mutual obligations, bounded liability, and "
                    "balanced termination and renewal language."
                ),
            )

        if self.risky_indices and obs.rounds_left > 1:
            target_idx = self.risky_indices[0]
            
            # Find the clause data
            clause_data = {}
            if obs.clauses:
                for c in obs.clauses:
                    if c.get("idx") == target_idx:
                        clause_data = c
                        break
            
            amendment = self._create_structured_amendment(target_idx, clause_data)
            
            return NegotiationAction(
                move_kind=MoveKind.COUNTER_OFFER,
                clause_idx=target_idx,
                amendment=amendment,
                proposal_text=(
                    "Counterproposal: bilateral duties, liability cap with "
                    "gross-negligence carve-out, and equal notice rights."
                ),
            )

        # Strategic exit in hard contexts.
        if len(self.risky_indices) >= 2 and self.reject_count >= 2:
            return NegotiationAction(move_kind=MoveKind.WALK_AWAY, clause_idx=0)

        return NegotiationAction(move_kind=MoveKind.ACCEPT_TERMS, clause_idx=0)
