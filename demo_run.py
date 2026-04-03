from contract_negotiation_env.client import NegotiationEnv
from contract_negotiation_env.policies import TrapAwarePolicy


def run_demo():
    """
    Demo: Agent uses TrapAwarePolicy to autonomously:
    1. Analyze clauses for traps
    2. Target detected traps with structured amendments
    3. Learn from counterparty responses
    
    """
    env = NegotiationEnv()
    policy = TrapAwarePolicy()
    obs = env.reset(seed=42, scenario_profile="hard")
    print("START:", obs.message)
    done = False

    while not done:
        # Policy intelligently chooses next action (analyze, propose, etc.)
        action = policy.act(obs)
        obs = env.step(action)
        print(f"ACTION={action.move_kind.value} cidx={action.clause_idx}")
        # Show amendment details if present
        if action.amendment:
            print(f"  → Amendment: type={action.amendment.amendment_type.value}, params={action.amendment.parameters}")
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
    run_demo()
