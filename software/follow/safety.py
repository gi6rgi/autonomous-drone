"""Предохранители на стороне Pi.

Главный предохранитель — на стороне пилота: FC слушает Pi только в GUIDED,
тумблер RC мгновенно возвращает LOITER/RTL. Здесь — второй эшелон.
"""
from __future__ import annotations

import time

TRACK, HOVER, LOITER = "track", "hover", "loiter"


class Safety:
    def __init__(self, cfg: dict):
        self.hover_after = float(cfg["target_lost_hover_s"])
        self.loiter_after = float(cfg["target_lost_loiter_s"])
        self.min_battery_v = float(cfg["min_battery_v"])
        self.max_speed = float(cfg["max_speed_ms"])
        self._last_seen: float | None = None

    def action(self, has_target: bool, voltage: float | None) -> str:
        now = time.monotonic()
        if voltage is not None and voltage < self.min_battery_v:
            return LOITER
        if has_target:
            self._last_seen = now
            return TRACK
        if self._last_seen is None:
            return HOVER
        lost_for = now - self._last_seen
        if lost_for > self.loiter_after:
            return LOITER
        if lost_for > self.hover_after:
            return HOVER
        return TRACK  # короткий пропуск кадра — продолжаем по последней команде

    def clamp(self, vx: float, vy: float, vz: float) -> tuple[float, float, float]:
        lim = self.max_speed
        return (max(-lim, min(lim, vx)),
                max(-lim, min(lim, vy)),
                max(-lim, min(lim, vz)))
