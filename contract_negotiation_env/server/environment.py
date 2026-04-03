"""
Core RL environment for contract negotiation.

Implements the OpenEnv Environment interface: reset(), step(), state.
The game has three phases:
  Analysis    → agent reads clauses and assesses risks (up to 5 moves)
  Negotiation → agent proposes changes, handles counterparty responses (up to 8 rounds)
  Resolution  → agent accepts, rejects, or walks away

Observations are text-heavy by design — this environment is built for
LLM agents that reason in natural language.
"""

import uuid
import random
import copy
from typing import Optional, Any

from openenv.core.env_server import Environment

from contract_negotiation_env.models import (
    NegotiationAction,
    NegotiationObservation,
    NegotiationState,
    MoveKind,
)
from contract_negotiation_env.contracts.generator import (
    build_contract,
    agent_visible_clauses,
    SCENARIO_PROFILES,
)
from contract_negotiation_env.server.counterparty import Counterparty
from contract_negotiation_env.server.grader import compute_episode_reward
from contract_negotiation_env.server.llm_evaluator import evaluate_episode


# phase budgets
MAX_ANALYSIS_MOVES = 5
MAX_NEGOTIATION_ROUNDS = 8


class NegotiationEnvironment(Environment):
    """
    OpenEnv-compatible environment for multi-party contract negotiation.
    """

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._state = NegotiationState()
        self._clauses = []
        self._traps = []
        self._counterparty = None
        self._action_log = []
        self._detected = []          # clause indices the agent flagged
        self._proposals_made = []     # clause indices the agent proposed changes for
        self._contract_type = ""
        self._negotiation_rounds = 0
        self._analysis_moves = 0
        self._phase = "analysis"
        self._done = False
        self._naive_accept = False
        self._walked_away = False
        self._final_scores = {}

    # ── reset ────────────────────────────────────────────────────────

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        difficulty: str = "medium",
        contract_type: Optional[str] = None,
        scenario_profile: Optional[str] = None,
        **kwargs: Any,
    ) -> NegotiationObservation:
        """Generate a fresh contract and return the opening observation."""

        eid = episode_id or str(uuid.uuid4())[:12]

        clauses, traps, ctype, cpstyle = build_contract(
            contract_type=contract_type,
            difficulty=difficulty,
            scenario_profile=scenario_profile,
            seed=seed,
        )

        self._clauses = clauses
        self._traps = traps
        self._contract_type = ctype
        self._counterparty = Counterparty(
            style=cpstyle,
            concession_budget=1.0,
            seed=seed,
            learning_enabled=True,  # Enable learning/adaptation
        )
        self._action_log = []
        self._detected = []
        self._proposals_made = []
        self._negotiation_rounds = 0
        self._analysis_moves = 0
        self._phase = "analysis"
        self._done = False
        self._naive_accept = False
        self._walked_away = False
        self._final_scores = {}

        self._state = NegotiationState(
            episode_id=eid,
            step_count=0,
            contract_type=ctype,
            difficulty=difficulty,
            counterparty_style=cpstyle,
            traps=[copy.deepcopy(t) for t in traps],
            clauses_raw=[copy.deepcopy(c) for c in clauses],
            fairness_floor=0.4,
            concession_budget=1.0,
            phase="analysis",
        )

        return NegotiationObservation(
            done=False,
            reward=None,
            phase="analysis",
            contract_type=ctype,
            clauses=agent_visible_clauses(clauses),
            risk_report="",
            counterparty_response="",
            rounds_left=MAX_NEGOTIATION_ROUNDS,
            analysis_moves_left=MAX_ANALYSIS_MOVES,
            negotiation_summary="",
            score_breakdown={},
            message=(
                f"You are reviewing a {ctype} contract with "
                f"{len(clauses)} clauses.  Some clauses may contain "
                f"unfair terms.  Use your analysis moves to investigate, "
                f"then negotiate amendments.  You have {MAX_ANALYSIS_MOVES} "
                f"analysis moves and {MAX_NEGOTIATION_ROUNDS} negotiation rounds."
                + (
                    f"  Active scenario profile: {scenario_profile}."
                    if scenario_profile in SCENARIO_PROFILES
                    else ""
                )
            ),
        )

    # ── step ─────────────────────────────────────────────────────────

    def step(
        self,
        action: NegotiationAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> NegotiationObservation:
        """Process one agent action and return the resulting observation."""

        if self._done:
            return self._terminal_observation("Episode already finished.")

        self._state.step_count += 1
        move = action.move_kind
        cidx = action.clause_idx
        proposal = action.proposal_text
        amendment = action.amendment

        # log it
        log_entry = {
            "step": self._state.step_count,
            "move_kind": move.value if isinstance(move, MoveKind) else move,
            "clause_idx": cidx,
            "proposal_text": proposal,
            "amendment": amendment.to_brief_text() if amendment else None,
            "result": "",
        }

        # route to the right handler
        if move == MoveKind.READ_CLAUSE:
            obs = self._handle_read_clause(cidx, log_entry)
        elif move == MoveKind.ASSESS_RISK:
            obs = self._handle_assess_risk(cidx, log_entry)
        elif move == MoveKind.PROPOSE_CHANGE:
            obs = self._handle_propose_change(cidx, proposal, amendment, log_entry)
        elif move == MoveKind.COUNTER_OFFER:
            obs = self._handle_counter_offer(cidx, proposal, amendment, log_entry)
        elif move == MoveKind.ACCEPT_TERMS:
            obs = self._handle_accept(log_entry)
        elif move == MoveKind.REJECT_TERMS:
            obs = self._handle_reject(log_entry)
        elif move == MoveKind.WALK_AWAY:
            obs = self._handle_walk_away(log_entry)
        else:
            log_entry["result"] = "Unknown action."
            obs = self._build_observation("Invalid move_kind.")

        self._action_log.append(log_entry)

        # auto-transition from analysis to negotiation when budget exhausted
        if (
            self._phase == "analysis"
            and self._analysis_moves >= MAX_ANALYSIS_MOVES
            and not self._done
        ):
            self._phase = "negotiation"
            obs.phase = "negotiation"
            obs.message += (
                "  Analysis phase complete — you are now in the negotiation phase."
            )

        return obs

    # ── state property ───────────────────────────────────────────────

    @property
    def state(self) -> NegotiationState:
        self._state.phase = self._phase
        self._state.analysis_moves_used = self._analysis_moves
        self._state.negotiation_rounds_used = self._negotiation_rounds
        self._state.agent_detected_traps = list(self._detected)
        self._state.resolved = self._done
        self._state.walked_away = self._walked_away
        return self._state

    # ── action handlers ──────────────────────────────────────────────

    def _handle_read_clause(self, cidx, log_entry):
        if cidx < 0 or cidx >= len(self._clauses):
            log_entry["result"] = "Invalid clause index."
            return self._build_observation("Clause index out of range.")

        self._analysis_moves += 1
        clause = self._clauses[cidx]

        detail = (
            f"Clause {cidx + 1}: {clause['title']}\n"
            f"{clause['body']}"
        )
        log_entry["result"] = detail

        return self._build_observation(
            f"Read clause {cidx + 1} ({clause['title']}).",
            risk_report=detail,
        )

    def _handle_assess_risk(self, cidx, log_entry):
        if cidx < 0 or cidx >= len(self._clauses):
            log_entry["result"] = "Invalid clause index."
            return self._build_observation("Clause index out of range.")

        self._analysis_moves += 1
        clause = self._clauses[cidx]

        # build a risk assessment based on ground truth
        if clause.get("is_trap"):
            # find the matching trap info
            trap_info = next(
                (t for t in self._traps if t["clause_idx"] == cidx), None
            )
            if trap_info and cidx not in self._detected:
                self._detected.append(cidx)
                trap_info["detected"] = True

            risk_text = (
                f"HIGH RISK — Clause {cidx + 1} ({clause['title']}) contains "
                f"potentially unfair terms.  Fairness rating: "
                f"{clause.get('fairness', 0.5):.0%}.  "
                f"Recommendation: propose amendments before accepting."
            )
        else:
            risk_text = (
                f"LOW RISK — Clause {cidx + 1} ({clause['title']}) appears "
                f"standard and fair.  Fairness rating: "
                f"{clause.get('fairness', 0.9):.0%}."
            )

        log_entry["result"] = risk_text

        return self._build_observation(
            f"Risk assessment for clause {cidx + 1} complete.",
            risk_report=risk_text,
        )

    def _handle_propose_change(self, cidx, proposal, amendment, log_entry):
        if self._phase == "analysis":
            self._phase = "negotiation"

        if self._negotiation_rounds >= MAX_NEGOTIATION_ROUNDS:
            log_entry["result"] = "No negotiation rounds remaining."
            return self._build_observation(
                "You have used all negotiation rounds.  "
                "You must accept, reject, or walk away."
            )

        if cidx < 0 or cidx >= len(self._clauses):
            log_entry["result"] = "Invalid clause index."
            return self._build_observation("Clause index out of range.")

        self._negotiation_rounds += 1
        self._proposals_made.append(cidx)
        clause = self._clauses[cidx]

        outcome, msg, updated_clauses, updated_traps = (
            self._counterparty.respond_to_proposal(
                cidx, proposal, amendment, clause, self._clauses, self._traps
            )
        )

        if updated_clauses:
            self._clauses = updated_clauses
        if updated_traps:
            self._traps = updated_traps

        log_entry["result"] = f"{outcome}: {msg}"

        return self._build_observation(
            f"Proposal for clause {cidx + 1}: {outcome}.",
            counterparty_response=msg,
        )

    def _handle_counter_offer(self, cidx, proposal, amendment, log_entry):
        if self._phase == "analysis":
            self._phase = "negotiation"

        if self._negotiation_rounds >= MAX_NEGOTIATION_ROUNDS:
            log_entry["result"] = "No negotiation rounds remaining."
            return self._build_observation(
                "You have used all negotiation rounds."
            )

        if cidx < 0 or cidx >= len(self._clauses):
            log_entry["result"] = "Invalid clause index."
            return self._build_observation("Clause index out of range.")

        self._negotiation_rounds += 1
        clause = self._clauses[cidx]

        outcome, msg, updated_clauses, updated_traps = (
            self._counterparty.respond_to_counter_offer(
                cidx, proposal, amendment, clause, self._clauses, self._traps
            )
        )

        if updated_clauses:
            self._clauses = updated_clauses
        if updated_traps:
            self._traps = updated_traps

        log_entry["result"] = f"{outcome}: {msg}"

        return self._build_observation(
            f"Counter-offer on clause {cidx + 1}: {outcome}.",
            counterparty_response=msg,
        )

    def _handle_accept(self, log_entry):
        self._done = True

        # check if this was a naive accept (no investigation at all)
        investigation_count = sum(
            1 for e in self._action_log
            if e.get("move_kind") in ("read_clause", "assess_risk")
        )
        self._naive_accept = investigation_count == 0

        scores = compute_episode_reward(
            traps=self._traps,
            detected_indices=self._detected,
            clauses=self._clauses,
            rounds_used=self._negotiation_rounds,
            walked_away=False,
            naive_accept=self._naive_accept,
        )

        llm_eval = evaluate_episode(
            self._action_log, self._traps, self._detected
        )
        
        # Include what the counterparty learned about the agent
        counterparty_insights = self._counterparty.get_learned_insights()

        self._final_scores = {**scores, "llm_evaluation": llm_eval, "counterparty_learned": counterparty_insights}

        log_entry["result"] = f"Accepted.  Reward: {scores['total_reward']}"

        return self._terminal_observation(
            "Contract accepted.  Episode complete.",
            reward=scores["total_reward"],
            scores=self._final_scores,
        )

    def _handle_reject(self, log_entry):
        self._done = True

        scores = compute_episode_reward(
            traps=self._traps,
            detected_indices=self._detected,
            clauses=self._clauses,
            rounds_used=self._negotiation_rounds,
            walked_away=False,
            naive_accept=False,
        )

        # small penalty for rejecting (vs walking away which is a strategic choice)
        scores["total_reward"] = round(scores.get("total_reward", 0) - 0.15, 4)

        llm_eval = evaluate_episode(
            self._action_log, self._traps, self._detected
        )
        counterparty_insights = self._counterparty.get_learned_insights()
        self._final_scores = {**scores, "llm_evaluation": llm_eval, "counterparty_learned": counterparty_insights}

        log_entry["result"] = f"Rejected.  Reward: {scores['total_reward']}"

        return self._terminal_observation(
            "Contract rejected.  Episode complete.",
            reward=scores["total_reward"],
            scores=self._final_scores,
        )

    def _handle_walk_away(self, log_entry):
        self._done = True
        self._walked_away = True

        scores = compute_episode_reward(
            traps=self._traps,
            detected_indices=self._detected,
            clauses=self._clauses,
            rounds_used=self._negotiation_rounds,
            walked_away=True,
            naive_accept=False,
        )

        llm_eval = evaluate_episode(
            self._action_log, self._traps, self._detected
        )
        counterparty_insights = self._counterparty.get_learned_insights()
        self._final_scores = {**scores, "llm_evaluation": llm_eval, "counterparty_learned": counterparty_insights}

        log_entry["result"] = f"Walked away.  Reward: {scores['total_reward']}"

        return self._terminal_observation(
            "Agent walked away from the deal.  Episode complete.",
            reward=scores["total_reward"],
            scores=self._final_scores,
        )

    # ── observation builders ─────────────────────────────────────────

    def _build_observation(
        self,
        message: str,
        risk_report: str = "",
        counterparty_response: str = "",
    ) -> NegotiationObservation:
        return NegotiationObservation(
            done=False,
            reward=None,
            phase=self._phase,
            contract_type=self._contract_type,
            clauses=agent_visible_clauses(self._clauses),
            risk_report=risk_report,
            counterparty_response=counterparty_response,
            rounds_left=MAX_NEGOTIATION_ROUNDS - self._negotiation_rounds,
            analysis_moves_left=MAX_ANALYSIS_MOVES - self._analysis_moves,
            negotiation_summary=(
                f"Detected risks: {len(self._detected)}.  "
                f"Proposals made: {len(self._proposals_made)}.  "
                f"Rounds remaining: {MAX_NEGOTIATION_ROUNDS - self._negotiation_rounds}."
            ),
            score_breakdown={},
            message=message,
        )

    def _terminal_observation(
        self,
        message: str,
        reward: float = 0.0,
        scores: dict = None,
    ) -> NegotiationObservation:
        return NegotiationObservation(
            done=True,
            reward=reward,
            phase="resolution",
            contract_type=self._contract_type,
            clauses=agent_visible_clauses(self._clauses),
            risk_report="",
            counterparty_response="",
            rounds_left=0,
            analysis_moves_left=0,
            negotiation_summary=(
                f"Episode finished.  "
                f"Traps detected: {len(self._detected)}/{len(self._traps)}.  "
                f"Negotiation rounds used: {self._negotiation_rounds}."
            ),
            score_breakdown=scores or {},
            message=message,
        )
