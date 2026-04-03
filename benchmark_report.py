from datetime import datetime, UTC
from pathlib import Path
from statistics import mean
from random import Random

from contract_negotiation_env.client import NegotiationEnv
from contract_negotiation_env.models import MoveKind, NegotiationAction
from contract_negotiation_env.policies import TrapAwarePolicy


PROFILES = [
    "baseline",
    "cooperative_bootcamp",
    "adversarial_finals",
    "procurement_redteam",
    "saas_moderate",
    "saas_hardened",
    "ma_complex",
    "ip_licensing_strict",
    "employment_fair",
    "employment_hostile",
]
POLICIES = ["random", "no_analysis", "targeted_heuristic"]


def random_policy(obs, rng: Random):
    if obs.done:
        return NegotiationAction(move_kind=MoveKind.ACCEPT_TERMS, clause_idx=0)

    valid_idx = 0 if not obs.clauses else rng.randint(0, len(obs.clauses) - 1)
    choices = [
        MoveKind.READ_CLAUSE,
        MoveKind.ASSESS_RISK,
        MoveKind.PROPOSE_CHANGE,
        MoveKind.COUNTER_OFFER,
        MoveKind.ACCEPT_TERMS,
        MoveKind.WALK_AWAY,
    ]
    move = rng.choice(choices)
    text = (
        "Please revise this clause to reduce one-sided obligations and improve clarity."
        if move in (MoveKind.PROPOSE_CHANGE, MoveKind.COUNTER_OFFER)
        else ""
    )
    return NegotiationAction(move_kind=move, clause_idx=valid_idx, proposal_text=text)


def no_analysis_policy(obs):
    if obs.rounds_left > 6:
        return NegotiationAction(
            move_kind=MoveKind.PROPOSE_CHANGE,
            clause_idx=0,
            proposal_text="Please improve this clause to be more balanced.",
        )
    return NegotiationAction(move_kind=MoveKind.ACCEPT_TERMS, clause_idx=0)


def run_policy(obs, policy_name: str, rng: Random, policy_state: dict):
    if policy_name == "random":
        return random_policy(obs, rng)
    if policy_name == "no_analysis":
        return no_analysis_policy(obs)
    policy = policy_state.get("policy")
    if policy is None:
        policy = TrapAwarePolicy(rng=rng)
        policy_state["policy"] = policy
    return policy.act(obs)


def evaluate_profile(profile: str, policy_name: str, episodes: int = 20):
    results = []
    for seed in range(episodes):
        rng = Random(seed + 991)
        policy_state = {}
        env = NegotiationEnv()
        obs = env.reset(seed=seed, scenario_profile=profile)
        while not obs.done:
            action = run_policy(obs, policy_name, rng, policy_state)
            obs = env.step(action)
        results.append(obs.score_breakdown)
    return results


def aggregate(results):
    keys = [
        "total_reward",
        "trap_detection",
        "amendment_quality",
        "negotiation_efficiency",
        "final_fairness",
        "walk_away_accuracy",
    ]
    return {k: round(mean(r.get(k, 0.0) for r in results), 4) for k in keys}


def write_report(output_path: Path, episodes_per_profile: int = 20):
    lines = []
    lines.append("# Benchmark Report")
    lines.append("")
    lines.append(f"- generated_at: {datetime.now(UTC).isoformat()}")
    lines.append(f"- episodes_per_profile: {episodes_per_profile}")
    lines.append("")
    lines.append("| policy | profile | total_reward | trap_detection | amendment_quality | negotiation_efficiency | final_fairness | walk_away_accuracy |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")

    for policy_name in POLICIES:
        for profile in PROFILES:
            agg = aggregate(evaluate_profile(profile, policy_name, episodes_per_profile))
            lines.append(
                f"| {policy_name} | {profile} | {agg['total_reward']:.4f} | "
                f"{agg['trap_detection']:.4f} | {agg['amendment_quality']:.4f} | "
                f"{agg['negotiation_efficiency']:.4f} | {agg['final_fairness']:.4f} | "
                f"{agg['walk_away_accuracy']:.4f} |"
            )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote benchmark report to {output_path}")


if __name__ == "__main__":
    report_path = Path("artifacts/benchmark_report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_report(report_path, episodes_per_profile=20)
