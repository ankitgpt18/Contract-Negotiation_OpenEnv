import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contract_negotiation_env.server.grader import compute_episode_reward


class TestGrader(unittest.TestCase):
    def test_naive_accept_penalty(self):
        result = compute_episode_reward(
            traps=[{"clause_idx": 0, "fixed": False, "severity": 0.9}],
            detected_indices=[],
            clauses=[{"fairness": 0.3}],
            rounds_used=0,
            walked_away=False,
            naive_accept=True,
        )
        self.assertEqual(result["total_reward"], -1.0)

    def test_all_clean_bonus_applies(self):
        result = compute_episode_reward(
            traps=[{"clause_idx": 0, "fixed": True, "severity": 0.8}],
            detected_indices=[0],
            clauses=[{"fairness": 0.9}],
            rounds_used=2,
            walked_away=False,
            naive_accept=False,
        )
        self.assertGreaterEqual(result["all_clean_bonus"], 0.08)


if __name__ == "__main__":
    unittest.main()
