from contract_negotiation_env.client import NegotiationEnv
from contract_negotiation_env.models import NegotiationAction, MoveKind


def run_demo():
    env = NegotiationEnv()
    obs = env.reset(seed=42, difficulty="hard")
    print("START:", obs.message)

    # Investigate first three clauses.
    for i in range(min(3, len(obs.clauses))):
        obs = env.step(NegotiationAction(move_kind=MoveKind.READ_CLAUSE, clause_idx=i))
        print(f"\nREAD {i}:", obs.risk_report or obs.message)
        obs = env.step(NegotiationAction(move_kind=MoveKind.ASSESS_RISK, clause_idx=i))
        print(f"ASSESS {i}:", obs.risk_report or obs.message)

    # Attempt one concrete amendment.
    obs = env.step(
        NegotiationAction(
            move_kind=MoveKind.PROPOSE_CHANGE,
            clause_idx=0,
            proposal_text=(
                "This clause appears one-sided and creates asymmetric risk. "
                "Please revise with mutual obligations, capped liability, and "
                "explicit notice requirements."
            ),
        )
    )
    print("\nNEGOTIATION:", obs.counterparty_response or obs.message)

    # Close episode.
    obs = env.step(NegotiationAction(move_kind=MoveKind.ACCEPT_TERMS, clause_idx=0))
    print("\nFINAL MESSAGE:", obs.message)
    print("FINAL REWARD:", obs.reward)
    print("SCORE BREAKDOWN:", obs.score_breakdown)


if __name__ == "__main__":
    run_demo()
