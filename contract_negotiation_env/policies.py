"""
Reusable policy helpers for demos and benchmarking.
"""

from dataclasses import dataclass, field
from random import Random

from contract_negotiation_env.models import MoveKind, NegotiationAction


@dataclass
class TrapAwarePolicy:
    """
    Stateful heuristic policy tuned for hard negotiation profiles.

    Strategy:
    1) Use all analysis moves for direct risk assessment (max trap coverage).
    2) Prioritize proposals on detected high-risk clauses.
    3) Escalate to counter-offers when rejected.
    4) Walk away when risk remains high and counterparty is uncooperative.
    """

    rng: Random = field(default_factory=Random)
    risky_indices: list[int] = field(default_factory=list)
    scanned_idx: int = 0
    last_assessed_idx: int | None = None
    reject_count: int = 0
    accept_count: int = 0
    proposal_turn: int = 0

    def _record_observation(self, obs) -> None:
        if self.last_assessed_idx is not None and "HIGH RISK" in (obs.risk_report or ""):
            if self.last_assessed_idx not in self.risky_indices:
                self.risky_indices.append(self.last_assessed_idx)

        response = (obs.counterparty_response or "").lower()
        if "rejected" in response or "non-negotiable" in response:
            self.reject_count += 1
        if "accepted" in response or "revised" in response:
            self.accept_count += 1

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

        # Negotiate detected risk first.
        if self.risky_indices and obs.rounds_left > 3:
            target_idx = self.risky_indices[self.proposal_turn % len(self.risky_indices)]
            self.proposal_turn += 1
            return NegotiationAction(
                move_kind=MoveKind.PROPOSE_CHANGE,
                clause_idx=target_idx,
                proposal_text=(
                    "This clause is one-sided and creates asymmetric legal risk. "
                    "Please revise with mutual obligations, bounded liability, and "
                    "balanced termination and renewal language."
                ),
            )

        if self.risky_indices and obs.rounds_left > 1:
            target_idx = self.risky_indices[0]
            return NegotiationAction(
                move_kind=MoveKind.COUNTER_OFFER,
                clause_idx=target_idx,
                proposal_text=(
                    "Counterproposal: bilateral duties, liability cap with "
                    "gross-negligence carve-out, and equal notice rights."
                ),
            )

        # Strategic exit in hard contexts.
        if len(self.risky_indices) >= 2 and self.reject_count >= 2:
            return NegotiationAction(move_kind=MoveKind.WALK_AWAY, clause_idx=0)

        return NegotiationAction(move_kind=MoveKind.ACCEPT_TERMS, clause_idx=0)
