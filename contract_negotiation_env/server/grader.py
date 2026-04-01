"""
Multi-dimensional programmatic grader for contract negotiation episodes.

Scores the agent across five axes:
  1. Trap detection rate      (did the agent find the hidden problems?)
  2. Amendment quality        (did proposals actually fix things?)
  3. Negotiation efficiency   (fewer rounds = better)
  4. Final contract fairness  (Pareto-optimal outcome analysis)
  5. Walk-away accuracy       (correctly leaving unsalvageable deals)

Each dimension returns a normalised [0, 1] score.  The weighted total
is scaled to a reward in [-1, +1] so it plays nicely with RL training.
"""

from typing import Dict, Any, List


# weight each axis — tweak these to reshape what the agent optimises for
AXIS_WEIGHTS = {
    "trap_detection": 0.30,
    "amendment_quality": 0.25,
    "negotiation_efficiency": 0.15,
    "final_fairness": 0.20,
    "walk_away_accuracy": 0.10,
}

MAX_ANALYSIS_MOVES = 5
MAX_NEGOTIATION_ROUNDS = 8


def score_trap_detection(
    traps: List[Dict[str, Any]],
    detected_indices: List[int],
) -> float:
    """
    Fraction of traps the agent explicitly identified via assess_risk.
    """
    if not traps:
        return 1.0  # no traps to find → perfect by default

    caught = sum(1 for t in traps if t["clause_idx"] in detected_indices)
    return caught / len(traps)


def score_amendment_quality(
    traps: List[Dict[str, Any]],
) -> float:
    """
    Of the traps the agent tried to fix, how many actually got fixed?
    Partial fixes (counterparty partially accepted) count as 0.5.
    """
    if not traps:
        return 1.0

    fixable = [t for t in traps if t.get("detected")]
    if not fixable:
        return 0.0  # didn't even try

    fixed_score = sum(1.0 if t.get("fixed") else 0.0 for t in fixable)
    return fixed_score / len(fixable)


def score_negotiation_efficiency(
    rounds_used: int,
    max_rounds: int = MAX_NEGOTIATION_ROUNDS,
) -> float:
    """
    Reward finishing faster.  Using half the available rounds is ideal;
    past that, efficiency drops linearly.
    """
    if max_rounds == 0:
        return 1.0
    ratio = rounds_used / max_rounds
    # sweet spot around 0.3-0.5 of budget
    if ratio <= 0.5:
        return 1.0
    return max(0.0, 1.0 - (ratio - 0.5) * 2.0)


def score_final_fairness(
    clauses: List[Dict[str, Any]],
) -> float:
    """
    Average fairness of all clauses in the final contract version.
    """
    if not clauses:
        return 0.0
    total = sum(c.get("fairness", 0.5) for c in clauses)
    return total / len(clauses)


def score_walk_away(
    walked_away: bool,
    traps: List[Dict[str, Any]],
    clauses: List[Dict[str, Any]],
) -> float:
    """
    Was walking away the right call?

    Walking away is correct when most traps remain unfixed and no
    concessions were made.  Walking away from a fair contract is penalised.
    """
    unfixed_traps = [t for t in traps if not t.get("fixed")]
    avg_fairness = score_final_fairness(clauses)

    if walked_away:
        if len(unfixed_traps) >= 2 and avg_fairness < 0.65:
            return 1.0   # good call
        elif avg_fairness > 0.80:
            return 0.0   # walked away from a decent deal
        else:
            return 0.4   # debatable
    else:
        # stayed — that's fine as long as the outcome is decent
        if avg_fairness >= 0.75:
            return 1.0
        elif len(unfixed_traps) >= 2:
            return 0.2   # should have left
        else:
            return 0.6


def compute_episode_reward(
    traps: List[Dict[str, Any]],
    detected_indices: List[int],
    clauses: List[Dict[str, Any]],
    rounds_used: int,
    walked_away: bool,
    naive_accept: bool = False,
) -> Dict[str, float]:
    """
    Compute the full score breakdown and a scalar reward.

    Parameters
    ----------
    traps : list
        Ground-truth trap metadata.
    detected_indices : list of int
        Clause indices the agent flagged via assess_risk.
    clauses : list
        Final state of all clauses (may have been rewritten).
    rounds_used : int
        Number of negotiation rounds consumed.
    walked_away : bool
        Whether the agent chose to walk away.
    naive_accept : bool
        True if the agent accepted without investigating anything.

    Returns
    -------
    dict with per-axis scores and a "total_reward" key in [-1, 1].
    """
    # severe penalty for blind acceptance — the cardinal sin
    if naive_accept:
        return {
            "trap_detection": 0.0,
            "amendment_quality": 0.0,
            "negotiation_efficiency": 0.0,
            "final_fairness": score_final_fairness(clauses),
            "walk_away_accuracy": 0.0,
            "total_reward": -1.0,
            "detail": "Accepted contract without any investigation.",
        }

    scores = {
        "trap_detection": score_trap_detection(traps, detected_indices),
        "amendment_quality": score_amendment_quality(traps),
        "negotiation_efficiency": score_negotiation_efficiency(rounds_used),
        "final_fairness": score_final_fairness(clauses),
        "walk_away_accuracy": score_walk_away(walked_away, traps, clauses),
    }

    # weighted sum → [0, 1]
    weighted = sum(scores[k] * AXIS_WEIGHTS[k] for k in AXIS_WEIGHTS)

    # map [0, 1] → [-1, 1] so the RL signal has both positive and negative
    # Penalize unresolved high-severity clauses to prevent reward hacking.
    unresolved_severity = sum(
        t.get("severity", 0.0) for t in traps if not t.get("fixed", False)
    )
    severity_penalty = min(0.35, unresolved_severity * 0.08)

    # Small bonus when all traps are both detected and fixed.
    all_clean_bonus = 0.08 if traps and all(t.get("fixed", False) for t in traps) else 0.0

    raw_reward = (weighted * 2.0) - 1.0
    raw_reward = raw_reward - severity_penalty + all_clean_bonus
    scores["total_reward"] = round(max(-1.0, min(1.0, raw_reward)), 4)
    scores["severity_penalty"] = round(severity_penalty, 4)
    scores["all_clean_bonus"] = round(all_clean_bonus, 4)
    return scores
