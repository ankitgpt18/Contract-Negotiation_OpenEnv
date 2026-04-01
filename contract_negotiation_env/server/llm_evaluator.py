"""
LLM-based episode evaluator for negotiation reasoning quality.

In production this would call an LLM API (Llama 3 / Hugging Face endpoint)
to judge the agent's step-by-step reasoning.  For the hackathon demo we
implement a heuristic mock that analyses the transcript the same way an
LLM rubric would.

The rubric checks four dimensions:
  1. Reasoning quality — did the agent explain *why* a clause is risky?
  2. Strategic coherence — was there a logical plan (investigate → propose → resolve)?
  3. Information usage — did the agent act on what it learned from tools?
  4. Professional tone — are proposals written like actual amendments?
"""

from typing import Dict, List, Any


# ── keywords the heuristic looks for in the transcript ───────────────

INVESTIGATION_SIGNALS = ["read_clause", "assess_risk"]
PROPOSAL_SIGNALS = ["propose_change", "counter_offer"]
RESOLUTION_SIGNALS = ["accept_terms", "reject_terms", "walk_away"]

# phrases that suggest the agent explained its reasoning
REASONING_PHRASES = [
    "unfair", "one-sided", "asymmetric", "vague", "ambiguous",
    "risky", "problematic", "concern", "issue", "trap",
    "liability", "termination", "renewal", "penalty",
    "overreach", "overbroad", "unilateral",
]


def evaluate_episode(
    action_log: List[Dict[str, Any]],
    traps: List[Dict[str, Any]],
    detected_indices: List[int],
) -> Dict[str, Any]:
    """
    Analyse a completed episode transcript and return LLM-style scores.

    Parameters
    ----------
    action_log : list of dict
        Each entry has: step, move_kind, clause_idx, proposal_text, result
    traps : list of dict
        Ground-truth trap metadata.
    detected_indices : list of int
        Which clauses the agent flagged.

    Returns
    -------
    dict with dimension scores (0-100), overall score, and feedback text.
    """
    reasoning_score = _score_reasoning(action_log, traps)
    strategy_score = _score_strategy(action_log)
    info_usage_score = _score_information_usage(action_log, detected_indices, traps)
    tone_score = _score_professional_tone(action_log)

    overall = (
        reasoning_score * 0.35
        + strategy_score * 0.25
        + info_usage_score * 0.25
        + tone_score * 0.15
    )

    feedback_parts = []
    if reasoning_score >= 70:
        feedback_parts.append(
            "Strong analytical reasoning — the agent explained why "
            "specific clauses were problematic."
        )
    elif reasoning_score >= 40:
        feedback_parts.append(
            "Some analytical reasoning present, but the agent could "
            "provide deeper explanations for flagged issues."
        )
    else:
        feedback_parts.append(
            "Weak reasoning — the agent acted without articulating "
            "why clauses were risky."
        )

    if strategy_score >= 70:
        feedback_parts.append(
            "Coherent negotiation strategy: investigated before proposing."
        )
    else:
        feedback_parts.append(
            "Strategy was fragmented — proposals came before sufficient "
            "investigation."
        )

    if info_usage_score >= 70:
        feedback_parts.append(
            "Good use of gathered information in proposals."
        )
    else:
        feedback_parts.append(
            "Agent didn't fully leverage the information it gathered."
        )

    return {
        "reasoning_quality": round(reasoning_score, 1),
        "strategic_coherence": round(strategy_score, 1),
        "information_usage": round(info_usage_score, 1),
        "professional_tone": round(tone_score, 1),
        "overall_llm_score": round(overall, 1),
        "feedback": "  ".join(feedback_parts),
    }


# ── dimension scorers ────────────────────────────────────────────────

def _score_reasoning(
    action_log: List[Dict[str, Any]],
    traps: List[Dict[str, Any]],
) -> float:
    """Did the agent explain *why* things are problematic?"""
    if not action_log:
        return 0.0

    # check proposal texts and risk assessment actions for reasoning keywords
    reasoning_hits = 0
    total_proposals = 0

    for entry in action_log:
        text = entry.get("proposal_text", "").lower()
        kind = entry.get("move_kind", "")

        if kind in ("propose_change", "counter_offer", "assess_risk"):
            total_proposals += 1
            if any(phrase in text for phrase in REASONING_PHRASES):
                reasoning_hits += 1

    if total_proposals == 0:
        return 10.0  # did nothing meaningful

    base = (reasoning_hits / total_proposals) * 80.0

    # bonus for targeting actual trap clauses
    trap_indices = {t["clause_idx"] for t in traps}
    targeted_traps = sum(
        1 for e in action_log
        if e.get("move_kind") in ("assess_risk", "propose_change")
        and e.get("clause_idx") in trap_indices
    )
    bonus = min(20.0, targeted_traps * 8.0)

    return min(100.0, base + bonus)


def _score_strategy(action_log: List[Dict[str, Any]]) -> float:
    """Was there a logical investigate-then-propose-then-resolve flow?"""
    if not action_log:
        return 0.0

    kinds = [e.get("move_kind", "") for e in action_log]

    # ideal: investigation actions appear before proposal actions
    first_investigation = _first_index(kinds, INVESTIGATION_SIGNALS)
    first_proposal = _first_index(kinds, PROPOSAL_SIGNALS)
    first_resolution = _first_index(kinds, RESOLUTION_SIGNALS)

    score = 50.0  # baseline

    # reward investigation before proposal
    if first_investigation is not None and first_proposal is not None:
        if first_investigation < first_proposal:
            score += 25.0
        else:
            score -= 20.0

    # reward proposal before resolution
    if first_proposal is not None and first_resolution is not None:
        if first_proposal < first_resolution:
            score += 15.0

    # penalty for jumping straight to resolution
    if first_investigation is None and first_resolution is not None:
        score -= 30.0

    # bonus for multiple investigation steps
    inv_count = sum(1 for k in kinds if k in INVESTIGATION_SIGNALS)
    if inv_count >= 2:
        score += 10.0

    return max(0.0, min(100.0, score))


def _score_information_usage(
    action_log: List[Dict[str, Any]],
    detected_indices: List[int],
    traps: List[Dict[str, Any]],
) -> float:
    """Did the agent proposals target the clauses it investigated?"""
    if not action_log:
        return 0.0

    investigated_clauses = set()
    proposal_clauses = set()

    for entry in action_log:
        kind = entry.get("move_kind", "")
        idx = entry.get("clause_idx", -1)

        if kind in INVESTIGATION_SIGNALS:
            investigated_clauses.add(idx)
        elif kind in PROPOSAL_SIGNALS:
            proposal_clauses.add(idx)

    if not proposal_clauses:
        return 20.0  # made no proposals at all

    # how many proposals targeted previously investigated clauses?
    informed_proposals = proposal_clauses & investigated_clauses
    ratio = len(informed_proposals) / len(proposal_clauses) if proposal_clauses else 0

    # bonus for targeting actual traps
    trap_indices = {t["clause_idx"] for t in traps}
    trap_hits = proposal_clauses & trap_indices
    trap_bonus = min(30.0, len(trap_hits) * 12.0)

    return min(100.0, ratio * 60.0 + trap_bonus + 10.0)


def _score_professional_tone(action_log: List[Dict[str, Any]]) -> float:
    """Are proposals written in professional language?"""
    if not action_log:
        return 50.0

    proposal_texts = [
        e.get("proposal_text", "")
        for e in action_log
        if e.get("move_kind") in ("propose_change", "counter_offer")
        and e.get("proposal_text")
    ]

    if not proposal_texts:
        return 50.0  # no proposals to judge

    score = 60.0  # baseline for having proposals

    for text in proposal_texts:
        words = text.split()
        # reward longer, more detailed proposals
        if len(words) >= 15:
            score += 8.0
        elif len(words) >= 8:
            score += 4.0
        else:
            score -= 5.0  # too terse

    return max(0.0, min(100.0, score))


# ── util ─────────────────────────────────────────────────────────────

def _first_index(kinds: List[str], targets: List[str]) -> int | None:
    """Find the first occurrence of any target in the kinds list."""
    for i, k in enumerate(kinds):
        if k in targets:
            return i
    return None
