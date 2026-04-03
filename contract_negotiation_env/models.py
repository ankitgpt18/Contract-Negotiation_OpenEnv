"""
Typed data models for the Contract Negotiation environment.

Defines what an agent can do (Action), what it sees (Observation),
and the hidden ground truth (State).
"""

from typing import List, Dict, Any, Optional
from enum import Enum

from openenv.core.env_server import Action, Observation, State
from pydantic import Field


# ── amendment types ──────────────────────────────────────────────────

class AmendmentType(str, Enum):
    """Structured amendment categories for contract negotiation."""

    FAIRNESS_IMPROVEMENT = "fairness_improvement"  # Make clause more balanced
    MODIFY_PAYMENT_TERMS = "modify_payment_terms"  # Change payment schedule/amount
    MODIFY_LIABILITY_CAP = "modify_liability_cap"  # Set liability ceiling
    MODIFY_DURATION = "modify_duration"  # Change term length
    ADD_PROTECTIVE_CLAUSE = "add_protective_clause"  # Insert new safeguard
    REMOVE_CLAUSE = "remove_clause"  # Delete problematic clause
    MODIFY_TERMINATION = "modify_termination"  # Change exit terms
    MODIFY_NON_COMPETE = "modify_non_compete"  # Narrow non-compete scope
    MODIFY_IP_RIGHTS = "modify_ip_rights"  # Clarify IP ownership
    LIMIT_AUTO_RENEWAL = "limit_auto_renewal"  # Add exit window for auto-renew


class Amendment(Action):
    """
    Structured amendment to a contract clause.
    
    Replaces free-text proposals with semantically meaningful changes.
    """

    amendment_type: AmendmentType
    clause_idx: int
    parameters: Dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""  # Brief explanation for clarity
    
    def validate(self) -> bool:
        """Basic semantic validation of the amendment."""
        # Validate parameters based on amendment type
        params = self.parameters
        
        if self.amendment_type == AmendmentType.MODIFY_PAYMENT_TERMS:
            # Must have payment_days or payment_amount
            return "payment_days" in params or "payment_amount" in params
        
        elif self.amendment_type == AmendmentType.MODIFY_LIABILITY_CAP:
            # Must specify cap amount or percentage
            return "cap_amount" in params or "cap_percentage" in params
        
        elif self.amendment_type == AmendmentType.MODIFY_DURATION:
            # Must specify duration in months/years
            return "duration_months" in params or "duration_years" in params
        
        elif self.amendment_type == AmendmentType.MODIFY_NON_COMPETE:
            # Must specify duration and/or scope
            return ("duration_months" in params or "scope" in params)
        
        elif self.amendment_type == AmendmentType.LIMIT_AUTO_RENEWAL:
            # Must specify notice period
            return "advance_notice_days" in params
        
        # Other amendment types don't require strict validation
        return True
    
    def to_brief_text(self) -> str:
        """Convert amendment to brief natural language for counterparty."""
        base = f"{self.amendment_type.value.replace('_', ' ').title()}"
        
        if self.parameters:
            params_str = ", ".join(f"{k}={v}" for k, v in self.parameters.items())
            return f"{base} ({params_str})"
        
        return base


# ── action types the agent can pick ──────────────────────────────────

class MoveKind(str, Enum):
    """Every possible move an agent can take during a negotiation."""

    READ_CLAUSE = "read_clause"
    ASSESS_RISK = "assess_risk"
    PROPOSE_CHANGE = "propose_change"
    ACCEPT_TERMS = "accept_terms"
    REJECT_TERMS = "reject_terms"
    COUNTER_OFFER = "counter_offer"
    WALK_AWAY = "walk_away"


class NegotiationAction(Action):
    """
    A single move in the negotiation episode.

    The agent specifies *what* it wants to do (move_kind), which clause
    it targets (clause_idx, zero-based), and optionally a structured
    amendment or free-text proposal for backward compatibility.
    """

    move_kind: MoveKind
    clause_idx: int = 0
    proposal_text: str = ""  # Legacy: free-text proposals (still supported)
    amendment: Optional[Amendment] = None  # New: structured amendments



# ── what the agent sees back ─────────────────────────────────────────

class ClauseView(Action):
    """
    Lightweight view of one contract clause shown to the agent.
    Inheriting from Action is fine — it's just a Pydantic model for nesting.
    Using a plain BaseModel would also work but we keep it in the openenv family.
    """

    idx: int
    title: str
    body: str


class NegotiationObservation(Observation):
    """
    Everything the agent can see after taking a step.
    """

    phase: str = "analysis"  # analysis | negotiation | resolution
    contract_type: str = ""
    clauses: List[Dict[str, Any]] = Field(default_factory=list)
    risk_report: str = ""
    counterparty_response: str = ""
    rounds_left: int = 0
    analysis_moves_left: int = 0
    negotiation_summary: str = ""
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""


# ── hidden state (ground truth) ──────────────────────────────────────

class TrapInfo(Action):
    """Metadata for a hidden trap baked into a clause."""

    clause_idx: int
    trap_type: str  # e.g. unfair_termination, liability_shift …
    severity: float = 1.0
    description: str = ""
    detected: bool = False
    fixed: bool = False


class NegotiationState(State):
    """
    Full internal state including hidden info the agent must *discover*.
    """

    contract_type: str = ""
    difficulty: str = "medium"
    counterparty_style: str = "neutral"
    traps: List[Dict[str, Any]] = Field(default_factory=list)
    clauses_raw: List[Dict[str, Any]] = Field(default_factory=list)
    fairness_floor: float = 0.0  # min fairness the counterparty will accept
    concession_budget: float = 0.0
    agent_detected_traps: List[int] = Field(default_factory=list)
    resolved: bool = False
    walked_away: bool = False
    final_fairness: float = 0.0
    phase: str = "analysis"
    analysis_moves_used: int = 0
    negotiation_rounds_used: int = 0
