from contract_negotiation_env.client import NegotiationEnv
from contract_negotiation_env.policies import TrapAwarePolicy


def run_showcase(seed: int = 21, profile: str = "adversarial_finals"):
    env = NegotiationEnv()
    policy = TrapAwarePolicy()
    obs = env.reset(seed=seed, scenario_profile=profile)
    print("START:", obs.message)
    done = False

    while not done:
        action = policy.act(obs)
        obs = env.step(action)
        print(f"ACTION={action.move_kind.value} cidx={action.clause_idx}")
        if obs.risk_report:
            print("RISK:", obs.risk_report)
        if obs.counterparty_response:
            print("COUNTERPARTY:", obs.counterparty_response)
        if obs.done:
            done = True
            print("\nFINAL MESSAGE:", obs.message)
            print("FINAL REWARD:", obs.reward)
            print("SCORE BREAKDOWN:", obs.score_breakdown)


if __name__ == "__main__":
    run_showcase()
