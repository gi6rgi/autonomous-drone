"""Ошибка цели в кадре -> команды скорости.

MVP-логика (высоту держит сам FC по баро):
  - цель левее/правее центра кадра -> yaw_rate, чтобы держать её по центру;
  - видимый размер цели -> оценка дистанции -> vx, чтобы держать дистанцию.

Внимание: 175° линза сильно искажает картинку. Пока цель около центра
кадра, линейное приближение работает; для точности нужна fisheye-калибровка
(tools/, см. README).
"""
from __future__ import annotations

from .tracker import Target


def _clamp(v: float, lim: float) -> float:
    return max(-lim, min(lim, v))


class FollowController:
    def __init__(self, follow_cfg: dict, camera_cfg: dict, tracker_cfg: dict):
        self.kp_yaw = float(follow_cfg["kp_yaw"])
        self.kp_dist = float(follow_cfg["kp_dist"])
        self.max_vx = float(follow_cfg["max_forward_ms"])
        self.max_yaw = float(follow_cfg["max_yaw_rate_dps"])
        self.deadband_px = float(follow_cfg["deadband_px"])
        self.target_dist = float(follow_cfg["target_distance_m"])
        self.frame_w = float(camera_cfg["width"])
        self.fx_px = float(camera_cfg["fx_px"])
        self.marker_size_m = float(tracker_cfg.get("marker_size_m", 0.3))

    def distance_m(self, target: Target) -> float:
        """Пинхол-оценка: d = S_реальный * fx / S_пиксельный."""
        return self.marker_size_m * self.fx_px / max(target.size_px, 1.0)

    def update(self, target: Target) -> tuple[float, float]:
        """-> (vx м/с вперёд, yaw_rate град/с, + вправо)."""
        err_px = target.cx - self.frame_w / 2
        if abs(err_px) < self.deadband_px:
            err_px = 0.0
        yaw_rate = _clamp(self.kp_yaw * err_px / (self.frame_w / 2), self.max_yaw)

        dist_err = self.distance_m(target) - self.target_dist
        vx = _clamp(self.kp_dist * dist_err, self.max_vx)
        return vx, yaw_rate
