
import sys
import os
sys.path.append(os.getcwd())

from ppmonk.core.player import PlayerState
from ppmonk.core.spell_book import SpellBook

def verify_changes():
    print("--- Verifying Updates ---")

    # 1. Ascension
    p = PlayerState()
    sb = SpellBook(talents=['Ascension'])
    sb.apply_talents(p)
    print(f"Ascension Check: Max Energy {p.max_energy} (Exp 150), Current Energy {p.energy} (Exp 150)")
    assert p.max_energy == 150
    assert p.energy == 150

    # 2. Touch of Death & Meridian Strikes
    p = PlayerState(max_health=100000.0)
    # Apply Meridian Strikes (5-2)
    sb = SpellBook(talents=['5-2'])
    sb.apply_talents(p) # This should apply talent to spell IF spell exists. But ToD is in init.

    tod = sb.spells.get('ToD')
    if not tod:
        print("ERROR: ToD not in SpellBook")
        return

    print(f"ToD Check: Base CD {tod.base_cd} (Exp 45 with Meridian Strikes)")
    assert tod.base_cd == 45.0 # 90 -> 45

    # Check Usage
    p.target_health_pct = 0.20
    assert not tod.is_usable(p, sb.spells), "ToD should not be usable at 20%"
    p.target_health_pct = 0.10
    assert tod.is_usable(p, sb.spells), "ToD should be usable at 10%"

    # Check Damage
    # Dmg = 100k * 0.35 * 1.15 (Meridian) = 40250.
    # Player also has Versatility (default 500 rating -> 500/5400 = 0.0925 -> 1.0925)
    # Player Vers = 500 / 5400 = 0.0925925
    dmg, bd = tod.cast(p, sb.spells)
    expected_base = 35000 * 1.15
    print(f"ToD Damage: {dmg:.2f}, Breakdown: {bd}")
    assert dmg > 35000, "Damage should be boosted by Meridian and Vers"

    # 3. Hit Combo
    p = PlayerState()
    sb = SpellBook(talents=['5-5']) # Hit Combo
    sb.apply_talents(p)

    # Cast TP
    tp = sb.spells['TP']
    tp.cast(p, sb.spells)
    print(f"Hit Combo Stack (After TP): {p.hit_combo_stacks} (Exp 1)")
    assert p.hit_combo_stacks == 1

    # Cast RSK (Trigger Mastery)
    rsk = sb.spells['RSK']
    rsk.cast(p, sb.spells)
    print(f"Hit Combo Stack (After RSK): {p.hit_combo_stacks} (Exp 2)")
    assert p.hit_combo_stacks == 2

    # Cast RSK again (Fail Mastery)
    rsk.charges = 1 # Reset charge
    rsk.current_cd = 0
    p.energy = 100
    p.chi = 2
    rsk.cast(p, sb.spells)
    print(f"Hit Combo Stack (After RSK Repeat): {p.hit_combo_stacks} (Exp 0 or same?)")
    # Current implementation: "if not triggers_mastery... reset to 0".
    assert p.hit_combo_stacks == 0

    # 4. Momentum Boost
    p = PlayerState(rating_haste=0)
    sb = SpellBook(talents=['2-1']) # Momentum Boost
    sb.apply_talents(p)

    fof = sb.spells['FOF']
    p.chi = 3
    p.energy = 100
    fof.cast(p, sb.spells) # Starts Channel

    # Advance time to finish channel (4s)
    p.advance_time(4.1)

    print(f"Momentum Buff Active: {p.momentum_buff_active} (Exp True)")
    assert p.momentum_buff_active == True

    # Check Attack Speed
    # Base Swing 2.6 (dw). Haste 0.
    # With buff: 2.6 / 1.6 = 1.625
    # We can check via next swing timer or just logic.
    # Logic in advance_time: "if momentum_buff_active: swing_speed_mod *= 1.6"
    # Verify via property if possible or dry run.
    # Dry run swing logic:
    p.swing_timer = 0.1
    p.advance_time(0.2)
    # Swing timer should reset to Base / 1.6
    print(f"Swing Timer after attack: {p.swing_timer:.2f}")
    # Should be approx 2.6/1.6 = 1.625 minus elapsed remainder
    assert p.swing_timer < 2.0, "Swing timer should be reduced significantly"

    print("--- ALL CHECKS PASSED ---")

if __name__ == "__main__":
    verify_changes()
