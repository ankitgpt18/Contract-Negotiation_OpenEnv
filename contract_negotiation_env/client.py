"""
Client-side helper for local testing and OpenEnv-compatible usage.
"""

from typing import Optional

from contract_negotiation_env.models import NegotiationAction, NegotiationObservation
from contract_negotiation_env.server.environment import NegotiationEnvironment


class NegotiationEnv:
    """
    Lightweight local client facade.

    This keeps the API simple for hackathon demos:
      env = NegotiationEnv()
      obs = env.reset(seed=7, difficulty="hard")
      obs = env.step(NegotiationAction(...))
    """

    def __init__(self):
        self._env = NegotiationEnvironment()

    def reset(
        self,
        seed: Optional[int] = None,
        difficulty: str = "medium",
        contract_type: Optional[str] = None,
        scenario_profile: Optional[str] = None,
    ) -> NegotiationObservation:
        return self._env.reset(
            seed=seed,
            difficulty=difficulty,
            contract_type=contract_type,
            scenario_profile=scenario_profile,
        )

    def step(self, action: NegotiationAction) -> NegotiationObservation:
        return self._env.step(action=action)

    @property
    def state(self):
        return self._env.state
