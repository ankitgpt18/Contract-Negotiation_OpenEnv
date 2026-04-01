import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from contract_negotiation_env.client import NegotiationEnv
    from contract_negotiation_env.models import MoveKind, NegotiationAction
except ModuleNotFoundError as exc:
    if "openenv" in str(exc):
        NegotiationEnv = None
        MoveKind = None
        NegotiationAction = None
    else:
        raise


@unittest.skipIf(NegotiationEnv is None, "openenv-core not installed in this runtime")
class TestEnvironment(unittest.TestCase):
    def test_reset_with_profile(self):
        env = NegotiationEnv()
        obs = env.reset(seed=1, scenario_profile="cooperative_bootcamp")
        self.assertFalse(obs.done)
        self.assertIn("Active scenario profile", obs.message)

    def test_accept_ends_episode(self):
        env = NegotiationEnv()
        env.reset(seed=2, scenario_profile="baseline")
        obs = env.step(NegotiationAction(move_kind=MoveKind.ACCEPT_TERMS, clause_idx=0))
        self.assertTrue(obs.done)
        self.assertIsNotNone(obs.reward)


if __name__ == "__main__":
    unittest.main()
