from .talents import TalentManager

class Spell:
    def __init__(self, abbr, ap_coeff, energy=0, chi_cost=0, chi_gen=0, cd=0, cd_haste=False,
                 cast_time=0, cast_haste=False, is_channeled=False, ticks=1, req_talent=False, gcd_override=None):
        self.abbr = abbr
        self.ap_coeff = ap_coeff
        self.energy_cost = energy
        self.chi_cost = chi_cost
        self.chi_gen = chi_gen
        
        self.base_cd = cd
        self.cd_haste = cd_haste
        self.base_cast_time = cast_time
        self.cast_haste = cast_haste
        
        self.is_channeled = is_channeled
        self.total_ticks = ticks
        self.tick_coeff = ap_coeff / ticks if ticks > 0 else ap_coeff
        
        self.req_talent = req_talent
        self.gcd_override = gcd_override
        self.is_known = not req_talent
        self.current_cd = 0.0
        self.is_combo_strike = True

        # [新增] 机制开关
        self.haste_dmg_scaling = False  # 伤害受急速加成 (Momentum Boost)
        self.tick_dmg_ramp = 0.0        # 每跳伤害递增 (Momentum Boost)
        self.triggers_combat_wisdom = False # 是否触发战斗智慧 (Combat Wisdom)

    def update_tick_coeff(self):
        self.tick_coeff = self.ap_coeff / self.total_ticks if self.total_ticks > 0 else self.ap_coeff

    # ... (get_effective_cd, get_effective_cast_time, get_tick_interval, is_usable 保持不变) ...
    def get_effective_cd(self, player):
        if self.cd_haste: return self.base_cd / (1.0 + player.haste)
        return self.base_cd

    def get_effective_cast_time(self, player):
        if self.cast_haste: return self.base_cast_time / (1.0 + player.haste)
        return self.base_cast_time

    def get_tick_interval(self, player):
        if not self.is_channeled or self.total_ticks <= 0: return 0
        return self.get_effective_cast_time(player) / self.total_ticks

    def is_usable(self, player, other_spells=None):
        if not self.is_known: return False
        if self.current_cd > 0.01: return False
        if player.energy < self.energy_cost: return False
        if player.chi < self.chi_cost: return False
        return True

    def cast(self, player):
        player.energy -= self.energy_cost
        player.chi = max(0, player.chi - self.chi_cost)
        player.chi = min(player.max_chi, player.chi + self.chi_gen)
        self.current_cd = self.get_effective_cd(player)

        if self.gcd_override is not None:
            player.gcd_remaining = self.gcd_override
        else:
            player.gcd_remaining = 1.0

        # [新增] Combat Wisdom 触发逻辑
        extra_damage = 0.0
        if self.triggers_combat_wisdom and getattr(player, 'combat_wisdom_ready', False):
            player.combat_wisdom_ready = False
            player.combat_wisdom_timer = 15.0
            # 模拟移花接木伤害 (系数假设 1.2)
            eh_dmg = 1.2 * (1.0 + player.versatility) 
            extra_damage += eh_dmg

        triggers_mastery = self.is_combo_strike and (player.last_spell_name is not None) and (player.last_spell_name != self.abbr)
        player.last_spell_name = self.abbr

        if self.is_channeled:
            cast_t = self.get_effective_cast_time(player)
            player.is_channeling = True
            player.current_channel_spell = self
            player.channel_time_remaining = cast_t
            player.channel_ticks_remaining = self.total_ticks
            player.channel_tick_interval = self.get_tick_interval(player)
            player.time_until_next_tick = player.channel_tick_interval
            player.channel_mastery_snapshot = triggers_mastery
            return 0.0
        else:
            base_dmg = self.calculate_tick_damage(player, mastery_override=triggers_mastery)
            # Combat Wisdom: 主技能增伤 30%
            if extra_damage > 0: # 说明刚才触发了
                base_dmg *= 1.30
            return base_dmg + extra_damage

    def calculate_tick_damage(self, player, mastery_override=None, tick_idx=0):
        dmg = self.tick_coeff
        
        # [新增] Momentum Boost: 急速加成
        if self.haste_dmg_scaling:
            dmg *= (1.0 + player.haste)
            
        # [新增] Momentum Boost: 叠层增伤
        if self.tick_dmg_ramp > 0:
            dmg *= (1.0 + (tick_idx + 1) * self.tick_dmg_ramp)

        apply_mastery = False
        if mastery_override is not None:
            apply_mastery = mastery_override
        elif self.is_channeled:
            apply_mastery = player.channel_mastery_snapshot
        
        if apply_mastery:
            dmg *= (1.0 + player.mastery)
        dmg *= (1.0 + player.versatility)
        
        return dmg

    def tick_cd(self, dt):
        if self.current_cd > 0:
            self.current_cd = max(0, self.current_cd - dt)

class SpellWDP(Spell):
    def is_usable(self, player, other_spells):
        if not super().is_usable(player): return False
        rsk = other_spells['RSK']
        fof = other_spells['FOF']
        # 即使 FOF 在冷却中也可以用，逻辑是 FOF cd > 0
        return rsk.current_cd > 0 and fof.current_cd > 0

class SpellBook:
    def __init__(self, active_talents=None, talents=None):
        if active_talents is not None and talents is not None:
            merged = list(dict.fromkeys([*active_talents, *talents]))
            active_talents = merged
        elif active_talents is None and talents is not None:
            active_talents = talents

        self.spells = {
            'TP': Spell('TP', 0.88, energy=50, chi_gen=2),
            'BOK': Spell('BOK', 3.56, chi_cost=1),
            'RSK': Spell('RSK', 4.228, chi_cost=2, cd=10.0, cd_haste=True),
            'SCK': Spell('SCK', 3.52, chi_cost=2, is_channeled=True, ticks=4, cast_time=1.5, cast_haste=True),
            
            # [重要] FOF 需要天赋解锁 (1-1)
            'FOF': Spell('FOF', 2.07 * 5, chi_cost=3, cd=24.0, cd_haste=True, is_channeled=True, ticks=5, cast_time=4.0, cast_haste=True, req_talent=True),
            
            'WDP': SpellWDP('WDP', 5.40, cd=30.0, req_talent=True),
            'SOTWL': Spell('SOTWL', 15.12, chi_cost=2, cd=30.0, req_talent=True),
            'SW': Spell('SW', 8.96, cd=30.0, cast_time=0.4, req_talent=True, gcd_override=0.4)
        }
        
        # 标记触发器
        self.spells['TP'].triggers_combat_wisdom = True
        
        self.active_talents = active_talents if active_talents else []
        self.talent_manager = TalentManager()

    def apply_talents(self, player):
        self.talent_manager.apply_talents(self.active_talents, player, self)

    def tick(self, dt):
        for s in self.spells.values():
            s.tick_cd(dt)
