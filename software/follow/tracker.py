"""Трекеры цели.

ArucoTracker — рекомендуемый старт: детектирует напечатанный ArUco-маркер.
Детерминированный, лёгкий, даёт размер маркера в пикселях (оценка дистанции).

CsrtTracker — следит за произвольным объектом по начальному ROI
(выделяется мышью в tools/test_camera.py --select). Дрейфует, дистанцию
оценивает грубо по высоте рамки. Следующий шаг после ArUco.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Target:
    cx: float        # центр цели в пикселях
    cy: float
    size_px: float   # характерный размер (сторона маркера / высота рамки)


class ArucoTracker:
    def __init__(self, cfg: dict):
        dict_id = getattr(cv2.aruco, cfg.get("aruco_dict", "DICT_5X5_50"))
        self.dictionary = cv2.aruco.getPredefinedDictionary(dict_id)
        self.detector = cv2.aruco.ArucoDetector(self.dictionary)
        self.marker_id = int(cfg.get("aruco_id", 7))

    def update(self, frame) -> Target | None:
        corners, ids, _ = self.detector.detectMarkers(frame)
        if ids is None:
            return None
        for marker_corners, marker_id in zip(corners, ids.flatten()):
            if marker_id != self.marker_id:
                continue
            pts = marker_corners.reshape(4, 2)
            cx, cy = pts.mean(axis=0)
            side = float(np.mean([np.linalg.norm(pts[i] - pts[(i + 1) % 4])
                                  for i in range(4)]))
            return Target(float(cx), float(cy), side)
        return None


class CsrtTracker:
    def __init__(self, cfg: dict):
        self._tracker = None

    def init_roi(self, frame, bbox: tuple[int, int, int, int]):
        self._tracker = cv2.TrackerCSRT_create()
        self._tracker.init(frame, bbox)

    def update(self, frame) -> Target | None:
        if self._tracker is None:
            return None
        ok, (x, y, w, h) = self._tracker.update(frame)
        if not ok:
            return None
        return Target(x + w / 2, y + h / 2, float(h))


def make_tracker(cfg: dict):
    mode = cfg.get("mode", "aruco")
    if mode == "aruco":
        return ArucoTracker(cfg)
    if mode == "csrt":
        return CsrtTracker(cfg)
    raise ValueError(f"Неизвестный трекер: {mode}")
