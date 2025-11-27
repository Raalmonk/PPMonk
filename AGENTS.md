# AGENTS.md - PPMonk Simulation Rules & Mechanics

> **Purpose**: This document is the **Single Source of Truth** for the PPMonk simulator.
> **Status**: Updated to match User provided screenshots and specific mechanical adjustments.

---

## 1. Core Attributes & Formulas

### 1.1 Player Stats
* **Agility**: Default `2000.0`. The primary scaler for all damage.
* **Attack Power (AP)**: Base `1.0` in sim formulas. Final Damage = `Coeff * AP * Agility`.
* **Haste**: Reduces GCD, Cooldowns (specific spells), and Channel durations. Increases Energy Regen.
* **Crit**:
    * Chance: `Base (10%) + Rating/4600 + Talents`.
    * Multiplier: `2.0x` (Base). Additive bonuses (e.g., `+20%` makes it `2.2x`).
* **Mastery (Combo Strikes)**: Increases damage when the current spell differs from the previous one.
* **Versatility**: Flat damage multiplier `(1 + Vers%)`.
* **Armor Pen**: Ignores a percentage of target armor. Default `0%`.

### 1.2 Damage Calculation Pipeline
1.  **Raw Base**: `Coefficient * Agility`.
2.  **Multipliers**: Apply all active buffs, talents, and traits (multiplicative).
3.  **Crit**: Roll `Crit%`. If crit, multiply by `(2.0 + BonusCritDmg)`.
4.  **Defense (Armor)**:
    * **Target Physical DR**: `30%` (0.30).
    * **Physical Damage**: `Damage * (1 - 0.30 * (1 - ArmorPen))`.
    * **Nature Damage**: Ignores Armor (True Damage).

---

## 2. Spellbook (Base Skills)

**Note on CD**: "Haste" implies the cooldown is reduced by Haste (`Base / (1+Haste)`).

| Ability | Abbr | Coeff (AP) | Type | Cost | Cooldown | Properties |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Tiger Palm** | TP | **0.88** | Physical | 50 Eng | None | Gens 2 Chi. |
| **Blackout Kick** | BOK | **3.56** | Physical | 1 Chi | **None** | Cooldown removed per user instruction. Limited by GCD/Chi. |
| **Rising Sun Kick** | RSK | **4.228** | Physical | 2 Chi | 10s (Haste)| High priority ST damage. |
| **Fists of Fury** | FOF | **2.07 * 5** | Physical | 3 Chi | 24s (Haste)| **Primary Target**: 100% Dmg.<br>**Secondary**: Soft Cap 5 (Split).<br>Channeled (4s base). |
| **Spinning Crane Kick**| SCK | **3.52** (Total)| Physical | 2 Chi | None | Channeled (1.5s). Soft Cap 5. |
| **Whirling Dragon Punch**| WDP | **5.40** | Physical | 0 | 24s | Usable only if RSK & FOF on CD. Soft Cap 5. |
| **Strike of the Windlord**| SOTWL| **15.12** | Physical | 2 Chi | 30s | Soft Cap 5. |
| **Touch of Death** | ToD | **35% Max HP**| Physical | 0 | 90s | Execute (<15% HP). Ignores Armor in practice, but listed Physical. |
| **Zenith** (Cast) | - | **10.0** | **Nature** | 0 | 90s | Soft Cap 5 AOE. 2 Charges. |
| **Auto Attack** | AA | 2.4(2H)/1.8(DW)| Physical | - | 3.5s/2.6s | Affected by Haste. |

---

## 3. Base Traits (Passive)
*Always enabled.*

1.  **Fast Feet**: RSK dmg `+70%`, SCK dmg `+10%`.
2.  **Ferocity of Xuen**: All damage `+4%`.
3.  **Balanced Stratagem**: Physical damage `+4%` (TP, BOK, RSK, FOF, SCK, WDP, SOTWL, AA).
4.  **Strength of Spirit**: Expel Harm crit chance `+15%`.
5.  **Way of the Cobra**: Auto Attack crit chance `+15%`.

---

## 4. Talent Tree Mechanics

### Row 2: Core Mechanics
* **2-1 Momentum Boost**: FOF dmg scales with Haste. FOF stacks `+10%` dmg per tick. **After FOF ends**, Auto Attack speed `+60%` for 8s.
* **2-2 Combat Wisdom**: Every 15s, next TP resets CD, deals extra **Nature** dmg (`1.2 AP`), buffs TP `+30%`.
* **2-3 Sharp Reflexes**: BOK reduces RSK and FOF cooldowns by `1.0s`.

### Row 3: Stat Buffs
* **3-1 Touch of the Tiger**: TP dmg `+15%`.
* **3-2 Ferociousness**: Crit `+2%/4%`. Doubled while Xuen active (`+4%/8%`).
* **3-3 Hardened Soles**: BOK Crit Chance `+6%/12%`, BOK Crit Dmg `+10%/20%`.
* **3-4 Ascension**: Max Energy `+20` (Total 120 -> 150 w/ Inner Peace). Max Chi `+1` (Total 6). Energy Regen `+10%`.

### Row 4: Proc Engines
* **4-1 Dual Threat**: Auto Attacks have `30%` chance to be replaced by `3.726 AP` **Nature** damage.
* **4-2 Teachings of the Monastery (TotM)**: TP adds stack (Max 4/8). BOK consumes all stacks -> Deals `0.847 AP` extra Physical dmg per stack (multihit). BOK has `12%` chance to reset RSK CD.
* **4-3 Glory of the Dawn**: RSK has `Haste%` chance to trigger again (`1.0 AP` Physical) and generate `1 Chi`.

### Row 5: Enhancements
* **5-1 Crane Vortex**: SCK dmg `+15%`.
* **5-2 Meridian Strikes**: ToD CD `-45s`, Dmg `+15%`.
* **5-3 Rising Star**: RSK dmg `+15%`, Crit Dmg `+12%`.
* **5-5 Hit Combo**: Mastery proc grants 1 stack. `+1%` Dmg per stack (Max 5).
* **5-6 Brawler's Intensity**: RSK CD `-1s`, BOK dmg `+12%`.

### Row 6: AOE & Burst
* **6-1 Jade Ignition**: SCK deals extra `1.8 AP` **Nature** AOE (Soft Cap 5).
* **6-2 Cyclone's Drift**: Haste `+10%`.
* **6-2b Crashing Strikes**: FOF Duration `5.0s`, Ticks `6`.
* **6-4 Obsidian Spiral**: While Zenith active, BOK generates `1 Chi`.
* **6-5 Combo Breaker**: TP has `8%` chance to grant `Blackout Kick!` buff (next BOK free).

### Row 7: Finishers
* **7-1 Dance of Chi-Ji**: Spending Chi grants chance to make next SCK free & buffed.
* **7-2 Shadowboxing Treads**: BOK dmg `+5%`. BOK hits 3 targets total (Cleave).
* **7-4 Energy Burst**: Consuming `Blackout Kick!` generates `1 Chi`.
* **7-5 Inner Peace**: Max Energy `+30` (Base 100 -> 130). TP cost `-5`.

### Row 8 & 9: High Tier
* **8-1 Tiger Eye Brew (TEB)**: Gain stack every 8s. Zenith consumes all -> Crit Buff.
* **8-3 Sunfire Spiral**: RSK Mastery benefit `+20%`.
* **8-4 Communion with Wind**: SOTWL/WDP Dmg `+10%`, CD `-5s`.
* **8-6 Universal Energy**: **Nature** (Magic) damage `+15%`.
* **9-2 Rushing Wind Kick (RWK)**: Consuming `BOK!` has 40% chance to turn RSK into RWK (`1.7975 AP` **Nature** AOE + `6%` dmg per target).
* **9-3 Xuen's Battlegear**: RSK Crit `+20%`. RSK Crit reduces FOF CD `4s`.
* **9-4 Thunderfist**: SOTWL/WDP grant 4 stacks. AA consumes stack -> `1.61 AP` **Nature**.
* **9-8 Jadefire Stomp**: FOF ends -> Stomp (`0.4 AP` **Nature** AOE).

### Row 10: Capstones
* **10-2 Skyfire Heel**: RSK Crit `+4%` per target. 10% Cleave damage (Physical).
* **10-3 Harmonic Combo**: FOF Dmg `-10%`, Cost `2 Chi`.
* **10-4 Flurry of Xuen**: Chance on ability use -> `3.92 AP` **Physical** (AOE).
* **10-5 Martial Agility**: AA Speed `+30%` (Zenith active: `+60%`).
* **10-6 Airborne Rhythm**: SW generates `2 Chi`.
* **10-7 Path of Jade**: Jadefire Dmg `+10%` per target.

---

## 5. Hero Talents: Shado-Pan (Physical Focus)
*Choice Node: Select this tree OR Conduit of the Celestials.*

### Core Mechanics
* **Flurry Strikes**:
    * **Trigger**: Casting Fists of Fury consumes ALL charges.
    * **Effect**: Deals `0.6 AP` **Physical** damage per charge.
* **Flurry Charges**: Max 30 (Uncapped in sim logic).
    * **Generation**: Auto Attacks.
        * **2H Weapon**: 100% chance per hit.
        * **Dual Wield**: Scaled to match 2H PPM (~74% chance).

### Talents
* **Must Pick**:
    * **Veteran's Eye**: Haste `+5%`.
    * **Martial Precision**: Armor Penetration `12%`.
    * **Shado Over the Battlefield**: Flurry Strikes deal `0.52 AP` **Nature** damage to all enemies within 6 yds (**Reduced beyond 8 targets**).
    * **One Versus Many**: AA Crits generate **2** charges (Double). FOF damage `+20%`.
    * **Stand Ready**: Casting Zenith grants **10** Flurry Charges. Your **next attack** triggers Flurry Strikes at **70%** effectiveness.
    * **Against All Odds**: Agility `+4%`.
    * **Efficient Training**: Energy Spenders (TP) damage `+20%`. Zenith CD `-10s`.
    * **Vigilant Watch**: BOK Crit Damage `+30%`.
    * **Weapons of the Wall**: Zenith Stomp damage `+20%`.
    * **Wisdom of the Wall**: While Zenith active, RSK and SCK launch **3** Flurry Strikes.

* **Choice Node 1**:
    * **Pride of Pandaria**: Flurry Strikes have `+15%` Crit Chance.
    * **High Impact**: Enemies dying within 10s of Flurry Strike explode for `1.0 AP` Physical (8 yds).

---

## 6. Hero Talents: Conduit of the Celestials (Nature Focus)
*Choice Node: Select this tree OR Shado-Pan.*

### Core Mechanics
* **Invoke Xuen (Base)**:
    * Strikes 3 enemies every 1s for `0.257 AP` **Nature** damage (Tiger Lightning).
    * **Empowered Tiger Lightning**: Every 4s, strikes enemies for **8%** of the damage you dealt in the last 4s.
* **Heart of the Jade Serpent**:
    * Trigger: Casting SOTWL or WDP.
    * Effect: **Cooldown Recovery Rate +75%** for 8s (FOF, SOTWL, RSK, WDP). FOF channel time reduced by **50%**.
* **Inner Compass**:
    * Mechanic: Rotates alignment (Crane -> Tiger -> Ox -> Serpent) when a Celestial assists you.
    * Bonus: Increases corresponding stat by **2%** (Haste/Crit/Vers/Mastery).

### Talents
* **Choice Node 1**:
    * **Xuen's Guidance**: TotM has `15%` chance to refund a charge. TP damage `+10%`.
    * **Temple Training**: FOF and SCK damage `+10%`.

* **Must Pick**:
    * **Courage of the White Tiger**: TP has chance (~4 PPM) to cause Xuen to claw for `3.375 AP` **Physical**. Invoke Xuen guarantees next TP triggers this.
    * **Strength of the Black Ox**: After Xuen assists, next BOK refunds 2 TotM stacks and causes Niuzao Stomp (`2.0 AP` AOE, Soft Cap 5).
    * **Path of the Falling Star**: Celestial Conduit damage `+100%` vs Single Target (Reduces 20% per add. target).
    * **Celestial Conduit**: Castable within 1 min of Xuen. Channel 4s. Radiates `5 * 2.75 AP` **Nature** damage (Soft Cap 5).
    * **Flowing Wisdom**: Heart of the Jade Serpent grants `+10%` Haste.
    * **Unity Within**: Celestial Conduit can be recast once for 200% effectiveness. Automatically casts at end if unused.
    * **Yu'lon's Avatar**: ~1.5 PPM. Casting Zenith triggers Heart of the Jade Serpent (4s duration, 100% effectiveness).

* **Choice Node 2**:
    * **Restore Balance**: Damage `+5%` while Xuen is active.
    * **Xuen's Bond**: Xuen damage `+30%`, CD `-30s`.