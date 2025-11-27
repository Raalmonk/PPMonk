
import unittest
from ppmonk.core.spell_book import SpellBook
from ppmonk.core.player import PlayerState

class TestRefactor(unittest.TestCase):
    def test_damage_formula(self):
        player = PlayerState(agility=2000)
        # Should be 2000 AP
        self.assertEqual(player.attack_power, 2000)

        # Test RSK spell
        sb = SpellBook()
        sb.apply_talents(player)
        rsk = sb.spells['RSK']

        # Coeff 4.228
        # Base expected: 4.228 * 2000 = 8456
        # Aura: 1.04
        # Hidden: 1.70
        # Vers: 500 rating -> 500/5400 ~= 0.0926 -> 1.0926
        # Physical DR: 30% -> x0.7
        # Total Mult approx: 1.04 * 1.70 * 1.09 * 0.7 ~= 1.35
        # Total Base Damage approx 11400

        dmg, breakdown = rsk.calculate_tick_damage(player, use_expected_value=True)

        # Breakdown checks
        self.assertIn('coeff', breakdown)
        self.assertIn('ap', breakdown)
        self.assertEqual(int(breakdown['ap']), 2000)

        # Ensure it's not huge (previous bug was * 2000 again -> 22,000,000)
        self.assertTrue(dmg < 100000, f"Damage {dmg} is too high, double multiplication likely persisted.")
        self.assertTrue(dmg > 5000, f"Damage {dmg} seems too low.")

    def test_flurry_strikes_scaling(self):
         player = PlayerState(agility=2000)
         sb = SpellBook()
         fof = sb.spells['FOF']

         # Stacks = 10
         flurry, sob, hi = fof._calculate_flurry_strikes_damage(player, 10, use_expected_value=True)

         # 0.6 * 2000 * 10 = 12000 base
         # plus mods
         self.assertTrue(flurry < 50000)
         self.assertTrue(flurry > 5000)

if __name__ == '__main__':
    unittest.main()
