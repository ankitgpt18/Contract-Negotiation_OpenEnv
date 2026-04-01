"""
Typed data models for the Contract Negotiation environment.

Defines what an agent can do (Action), what it sees (Observation),
and the hidden ground truth (State).
"""

from typing import List, Dict, Any
from enum import Enum

from openenv.core.env_server import Action, Observation, State
from pydantic import Field


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
    it targets (clause_idx, zero-based), and optional free-text for
    proposals or counter-offers.
    """

    move_kind: MoveKind
    clause_idx: int = 0
    proposal_text: str = ""


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
