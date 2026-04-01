"""
Procedural contract generator.

Builds a random contract by picking fair clauses from the pool,
injecting a configurable number of trap clauses, shuffling, and
assigning clause indices.  Every generated contract comes with
ground-truth metadata used by the grader.
"""

import random
from typing import List, Dict, Any, Tuple

from contract_negotiation_env.contracts.templates import (
    FAIR_CLAUSES,
    TRAP_CATALOGUE,
    TRAP_TITLES,
)

# how many traps per difficulty band
DIFFICULTY_TRAP_COUNTS = {
    "easy": (1, 2),
    "medium": (2, 3),
    "hard": (3, 5),
}

# counterparty personality weights per difficulty
COUNTERPARTY_WEIGHTS = {
    "easy": ["cooperative", "cooperative", "neutral"],
    "medium": ["cooperative", "neutral", "adversarial"],
    "hard": ["neutral", "adversarial", "adversarial"],
}

CONTRACT_TYPES = ["freelance", "lease", "vendor"]

SCENARIO_PROFILES = {
    # Balanced baseline for quick evaluation runs.
    "baseline": {
        "difficulty": "medium",
        "contract_type": None,
        "counterparty_bias": None,
    },
    # Easy rounds where agent should learn clean analysis behavior.
    "cooperative_bootcamp": {
        "difficulty": "easy",
        "contract_type": None,
        "counterparty_bias": "cooperative",
    },
    # Hard adversarial rounds for finale-level stress tests.
    "adversarial_finals": {
        "difficulty": "hard",
        "contract_type": None,
        "counterparty_bias": "adversarial",
    },
    # Procurement-like vendor context with harder traps.
    "procurement_redteam": {
        "difficulty": "hard",
        "contract_type": "vendor",
        "counterparty_bias": "adversarial",
    },
}


def build_contract(
    contract_type: str | None = None,
    difficulty: str = "medium",
    scenario_profile: str | None = None,
    seed: int | None = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str, str]:
    """
    Generate a contract with embedded traps.

    Returns
    -------
    clauses : list of dicts
        Each has keys: idx, title, body, fairness, is_trap (hidden from agent)
    traps : list of dicts
        Ground-truth trap metadata (clause_idx, trap_type, severity, etc.)
    contract_type : str
    counterparty_style : str
    """
    rng = random.Random(seed)

    if scenario_profile:
        profile = SCENARIO_PROFILES.get(scenario_profile)
        if profile:
            difficulty = profile.get("difficulty", difficulty)
            contract_type = profile.get("contract_type", contract_type)

    if contract_type is None:
        contract_type = rng.choice(CONTRACT_TYPES)

    # pick fair clauses (take 4-5 from the pool)
    fair_pool = FAIR_CLAUSES[contract_type]
    num_fair = rng.randint(4, min(5, len(fair_pool)))
    chosen_fair = rng.sample(fair_pool, num_fair)

    # pick trap clauses
    lo, hi = DIFFICULTY_TRAP_COUNTS.get(difficulty, (2, 3))
    num_traps = rng.randint(lo, hi)
    trap_keys = rng.sample(list(TRAP_CATALOGUE.keys()), min(num_traps, len(TRAP_CATALOGUE)))

    trap_clauses = []
    trap_meta = []
    for tkey in trap_keys:
        trap = TRAP_CATALOGUE[tkey]
        trap_clauses.append({
            "title": TRAP_TITLES[tkey],
            "body": trap["text"],
            "fairness": round(1.0 - trap["severity"], 2),
            "is_trap": True,
            "trap_type": tkey,
        })
        trap_meta.append({
            "clause_idx": -1,  # filled after shuffle
            "trap_type": tkey,
            "severity": trap["severity"],
            "description": trap["why_bad"],
            "fair_version": trap["fair_version"],
            "detected": False,
            "fixed": False,
        })

    # combine and shuffle
    all_clauses = []
    for c in chosen_fair:
        all_clauses.append({
            "title": c["title"],
            "body": c["body"],
            "fairness": c["fairness"],
            "is_trap": False,
            "trap_type": None,
        })
    all_clauses.extend(trap_clauses)
    rng.shuffle(all_clauses)

    # assign indices and backfill trap_meta
    trap_lookup = {}  # trap_type -> clause_idx
    for i, clause in enumerate(all_clauses):
        clause["idx"] = i
        if clause["is_trap"]:
            trap_lookup[clause["trap_type"]] = i

    for tm in trap_meta:
        tm["clause_idx"] = trap_lookup[tm["trap_type"]]

    # pick counterparty style
    style_pool = COUNTERPARTY_WEIGHTS.get(difficulty, ["neutral"])
    counterparty_style = rng.choice(style_pool)
    if scenario_profile:
        profile = SCENARIO_PROFILES.get(scenario_profile)
        if profile and profile.get("counterparty_bias"):
            counterparty_style = profile["counterparty_bias"]

    return all_clauses, trap_meta, contract_type, counterparty_style


def agent_visible_clauses(clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Strip hidden metadata before showing clauses to the agent."""
    visible = []
    for c in clauses:
        visible.append({
            "idx": c["idx"],
            "title": c["title"],
            "body": c["body"],
        })
    return visible
