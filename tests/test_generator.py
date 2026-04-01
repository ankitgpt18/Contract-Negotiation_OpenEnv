import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contract_negotiation_env.contracts.generator import build_contract


class TestGenerator(unittest.TestCase):
    def test_seed_reproducibility(self):
        a = build_contract(seed=11)
        b = build_contract(seed=11)
        self.assertEqual(a[0], b[0])  # clauses
        self.assertEqual(a[1], b[1])  # traps
        self.assertEqual(a[2], b[2])  # contract_type
        self.assertEqual(a[3], b[3])  # counterparty_style

    def test_profile_bias_applies(self):
        _, _, _, style = build_contract(seed=5, scenario_profile="adversarial_finals")
        self.assertEqual(style, "adversarial")


if __name__ == "__main__":
    unittest.main()
