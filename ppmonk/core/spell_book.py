# ppmonk/core/spell_book.py

class Spell:
    def __init__(self, abbr, name, ap_coeff,
                 energy_cost=0, chi_cost=0, chi_gen=0,
                 base_cd=0, cd_haste=False,
                 base_cast_time=0, cast_haste=False,
                 is_combo_strike=True, damage_type="Physical",
                 is_channeled=False, total_ticks=1,
                 gcd_override=None,
                 req_talent=False):  # 新增: 标记该技能是否来自天赋

        self.abbr = abbr
        self.name = name
        self.ap_coeff = ap_coeff

        self.energy_cost = energy_cost
        self.chi_cost = chi_cost
        self.chi_gen = chi_gen

        self.base_cd = base_cd
        self.cd_haste = cd_haste

        self.base_cast_time = base_cast_time
        self.cast_haste = cast_haste

        self.is_combo_strike = is_combo_strike
        self.damage_type = damage_type

        self.is_channeled = is_channeled
        self.total_ticks = total_ticks
        self.tick_damage_coeff = ap_coeff / total_ticks if total_ticks > 0 else ap_coeff

        self.gcd_override = gcd_override

        # --- 天赋逻辑 ---
        self.req_talent = req_talent
        # 默认状态：如果不需要天赋，默认为True(学会)；如果需要天赋，默认为False(未学会)
        # 这个状态会在 SpellBook 初始化时被 talent_conf 覆盖
        self.is_known = not req_talent

        self.current_cd = 0.0

    def get_effective_cd(self, player):
        if self.cd_haste:
            return self.base_cd / (1.0 + player.haste)
        return self.base_cd

    def get_effective_cast_time(self, player):
        if self.cast_haste:
            return self.base_cast_time / (1.0 + player.haste)
        return self.base_cast_time

    def get_tick_interval(self, player):
        if not self.is_channeled or self.total_ticks <= 0:
            return 0
        total_time = self.get_effective_cast_time(player)
        return total_time / self.total_ticks

    def is_usable(self, player, other_spells=None):
        # 0. 天赋检查 (最优先)
        if not self.is_known:
            return False

        # 1. CD 检查
        if self.current_cd > 1e-4: return False

        # 2. 资源 检查
        if player.energy < self.energy_cost: return False
        if player.chi < self.chi_cost: return False

        # 3. 状态 检查
        if player.is_channeling: return False

        return True

    def cast(self, player):
        # 双重保险：防止代码直接调用 cast 强行施放未学会的技能
        if not self.is_known:
            return 0.0

        player.energy -= self.energy_cost
        player.chi = max(0, player.chi - self.chi_cost)
        player.chi = min(player.max_chi, player.chi + self.chi_gen)

        self.current_cd = self.get_effective_cd(player)

        # GCD 处理
        if self.gcd_override is not None:
            player.gcd_remaining = self.gcd_override
        else:
            player.gcd_remaining = 1.0

        # 精通触发判定：必须在覆盖 last_spell_name 之前完成
        triggers_mastery = self.is_combo_strike and (player.last_spell_name != self.abbr)

        # 更新上一技能记录
        player.last_spell_name = self.abbr

        if self.is_channeled:
            eff_cast_time = self.get_effective_cast_time(player)
            player.is_channeling = True
            player.channel_time_remaining = eff_cast_time
            player.current_channel_spell = self
            player.channel_ticks_remaining = self.total_ticks
            player.channel_tick_interval = self.get_tick_interval(player)
            player.time_until_next_tick = player.channel_tick_interval

            # 引导技能需要在施放瞬间记录是否触发了精通
            player.channel_mastery_snapshot = triggers_mastery
            return 0.0
        else:
            return self.calculate_tick_damage(player, mastery_override=triggers_mastery)

    def calculate_tick_damage(self, player, mastery_override=None):
        dmg = player.attack_power * self.tick_damage_coeff

        # Mastery: Combo Strikes
        apply_mastery = False

        if mastery_override is not None:
            apply_mastery = mastery_override
        elif self.is_channeled:
            # 引导技能从玩家身上的快照读取判定
            apply_mastery = player.channel_mastery_snapshot

        if apply_mastery:
            dmg *= (1.0 + player.mastery)
        dmg *= (1.0 + player.versatility)
        return dmg

    def tick_cd(self, delta_time):
        if self.current_cd > 0:
            self.current_cd = max(0, self.current_cd - delta_time)


# --- 具体技能 ---

class SpellTP(Spell):
    def __init__(self):
        super().__init__(
            abbr="TP", name="Tiger Palm", ap_coeff=0.88,
            energy_cost=50, chi_gen=2, base_cd=0,
            req_talent=False  # 基础技能
        )


class SpellBOK(Spell):
    def __init__(self):
        super().__init__(
            abbr="BOK", name="Blackout Kick", ap_coeff=3.56,
            chi_cost=1, base_cd=0,
            req_talent=False
        )


class SpellRSK(Spell):
    def __init__(self):
        super().__init__(
            abbr="RSK", name="Rising Sun Kick", ap_coeff=4.228,
            chi_cost=2, base_cd=10.0, cd_haste=True,
            req_talent=False
        )


class SpellSCK(Spell):
    def __init__(self):
        super().__init__(
            abbr="SCK", name="Spinning Crane Kick", ap_coeff=0.88 * 4,
            chi_cost=2, base_cd=0,
            base_cast_time=1.5, cast_haste=True,
            is_channeled=True, total_ticks=4,
            req_talent=False
        )
        self.tick_damage_coeff = 0.88


class SpellFOF(Spell):
    def __init__(self):
        super().__init__(
            abbr="FOF", name="Fists of Fury", ap_coeff=2.07 * 5,
            chi_cost=3, base_cd=24.0, cd_haste=True,
            base_cast_time=4.0, cast_haste=True,
            is_channeled=True, total_ticks=5,
            req_talent=False  # 虽然是核心技能，但通常视为自带
        )
        self.tick_damage_coeff = 2.07


class SpellWDP(Spell):
    def __init__(self):
        super().__init__(
            abbr="WDP", name="Whirling Dragon Punch", ap_coeff=5.40,
            base_cd=30.0, cd_haste=False,
            req_talent=True  # !!! 天赋技能 !!!
        )

    def is_usable(self, player, other_spells=None):
        # 父类检查 (含 req_talent 检查)
        if not super().is_usable(player): return False

        if other_spells:
            rsk = other_spells.get("RSK")
            fof = other_spells.get("FOF")
            if rsk and fof:
                if rsk.current_cd > 0 and fof.current_cd > 0:
                    return True
        return False


class SpellSOTWL(Spell):
    def __init__(self):
        super().__init__(
            abbr="SOTWL", name="Strike of the Windlord", ap_coeff=15.12,
            chi_cost=2, base_cd=30.0, cd_haste=False,
            req_talent=True  # !!! 天赋技能 !!!
        )


class SpellSW(Spell):
    def __init__(self):
        super().__init__(
            abbr="SW", name="Cut Wind", ap_coeff=8.96,
            base_cd=30.0, cd_haste=False,
            base_cast_time=0.4, cast_haste=False,
            is_channeled=False,
            damage_type="Nature",
            gcd_override=0.4,
            req_talent=True  # !!! 天赋技能 !!!
        )


# --- SpellBook 管理类 (核心改动) ---
class SpellBook:
    def __init__(self, selected_talents=None):
        """
        selected_talents: list of strings, e.g. ["WDP", "SW"]
        如果为 None，则只激活基础技能。
        """
        if selected_talents is None:
            selected_talents = []

        self.spells = {
            "TP": SpellTP(),
            "BOK": SpellBOK(),
            "RSK": SpellRSK(),
            "SCK": SpellSCK(),
            "FOF": SpellFOF(),
            "WDP": SpellWDP(),
            "SOTWL": SpellSOTWL(),
            "SW": SpellSW(),
        }

        # 初始化天赋状态
        for abbr, spell in self.spells.items():
            if spell.req_talent:
                # 如果该技能需要天赋，检查它是否在传入的 selected_talents 列表中
                if abbr in selected_talents:
                    spell.is_known = True
                else:
                    spell.is_known = False  # 没点天赋，设为不可用
            else:
                # 基础技能始终可用
                spell.is_known = True

    def tick(self, delta_time):
        for spell in self.spells.values():
            # 只有学会的技能才需要转CD？
            # 其实不管学没学会，转CD不影响逻辑，但为了性能可以加判断。
            # 这里为了简单，全部转CD。
            spell.tick_cd(delta_time)

    def get_spell(self, abbr):
        return self.spells.get(abbr)