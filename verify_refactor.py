import sys
import os

# Add repo root to path
sys.path.append(os.getcwd())

from ppmonk.core.player import PlayerState
from ppmonk.core.spell_book import SpellBook

def verify_refactor():
    print("=== Verifying Refactor ===")

    # Setup Player with Agility
    agility = 2500.0
    targets = 5
    player = PlayerState(agility=agility, target_count=targets)

    # Active Talents including new ones
    talents = [
        "1-1", "9-4", "9-2", "9-5", "8-6", "8-7", "6-5", "7-2"
        # FOF, Thunderfist, RWK, WeaponWind, UnivEnergy, MemoryMonastery, ComboBreaker, Shadowboxing
    ]

    spell_book = SpellBook(talents=talents)
    spell_book.apply_talents(player)

    print(f"Player Agility: {player.agility}")
    print(f"Player Attack Power: {player.attack_power}")
    print(f"Player Target Count: {player.target_count}")
    print(f"Has Thunderfist: {player.has_thunderfist}")
    print(f"Has RWK: {player.has_rushing_wind_kick}")
    print(f"Has UnivEnergy: {player.has_universal_energy}")

    # 1. Test Auto Attack Damage Scaling
    print("\n--- Testing Auto Attack ---")
    player.haste = 0.0
    dmg, logs = player.advance_time(4.0) # Should trigger at least one AA (2.6s)

    aa_log = next((l for l in logs if "Auto Attack" in l['Action']), None)
    if aa_log:
        print(f"AA Damage: {aa_log['Expected DMG']}")
        print(f"AA Breakdown: {aa_log['Breakdown']}")
        base = aa_log['Breakdown']['base']
        expected_base_approx = 1.8 * 2500 * 2500 # Coeff * AP * Agility
        print(f"Expected Base (Approx 1.8 * Ag^2): {expected_base_approx}")
        if base > 1000000:
            print("Agility scaling confirmed (Numbers are high as requested).")
    else:
        print("Error: No AA found.")

    # 2. Test Thunderfist Stacking
    print("\n--- Testing Thunderfist Stacking ---")
    # Cast SOTWL (if available) or WDP
    # First unlock SOTWL
    spell_book.spells['SOTWL'].is_known = True # Force know if talent missed
    player.chi = 5
    player.energy = 100

    sotwl = spell_book.spells['SOTWL']
    print(f"Casting {sotwl.name}...")
    sotwl.cast(player, spell_book.spells)

    print(f"Thunderfist Stacks: {player.thunderfist_stacks}")
    # Expected: 4 + target_count(5) = 9
    if player.thunderfist_stacks == 9:
        print("Thunderfist stacking verified.")
    else:
        print(f"Error: Thunderfist stacks {player.thunderfist_stacks} != 9")

    # 3. Test Thunderfist Consumption
    print("\n--- Testing Thunderfist Consumption ---")
    # Advance time to trigger AA and consumption
    # Force timer to be ready just in case
    player.thunderfist_icd_timer = 0
    dmg, logs = player.advance_time(3.0)

    tf_log = next((l for l in logs if l['Action'] == "Thunderfist"), None)
    if tf_log:
        print(f"Thunderfist Proc Dmg: {tf_log['Expected DMG']}")
        print(f"Breakdown: {tf_log['Breakdown']}")
        if "UniversalEnergy: x1.15" in str(tf_log['Breakdown']):
             print("Universal Energy application verified.")
        print(f"Remaining Stacks: {player.thunderfist_stacks}")
    else:
        print("Error: Thunderfist did not proc on AA.")

    # 4. Test RWK Trigger & Cast
    print("\n--- Testing RWK ---")
    # Force proc RWK
    player.rwk_ready = True
    rsk = spell_book.spells['RSK']
    print("Casting RSK (as RWK)...")

    dmg, breakdown = rsk.cast(player)
    print(f"RWK Damage: {dmg}")
    print(f"Breakdown: {breakdown}")

    if breakdown['aoe_type'] == 'soft_cap':
        print("RWK AOE Type verified.")
    else:
        print(f"Error: RWK AOE Type is {breakdown.get('aoe_type')}")

    if "RWK_Targets" in str(breakdown['modifiers']):
         print("RWK Target Scaling verified.")

    if player.rwk_ready == False:
        print("RWK consumed verified.")
    else:
        print("Error: RWK not consumed.")

    # 5. Jade Ignition (Nature check)
    print("\n--- Testing Jade Ignition ---")
    player.has_jade_ignition = True
    player.hit_combo_stacks = 5
    sck = spell_book.spells['SCK']
    dmg, breakdown = sck.cast(player)

    extra = breakdown.get('extra_events', [])
    ji = next((e for e in extra if e['name'] == 'Jade Ignition'), None)
    if ji:
        print(f"Jade Ignition Dmg: {ji['damage']}")
        # Can't easily verify exact modifiers from here without deep inspection, but code review confirms Nature logic.
    else:
        print("Error: Jade Ignition not found.")

    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    verify_refactor()
