"""Проверка камеры и трекера без полёта.

  python tools/test_camera.py                  # 1 кадр -> frame.jpg
  python tools/test_camera.py --live           # окно с трекингом (нужен дисплей)

Запускать из каталога software/: python tools/test_camera.py
"""
import argparse
import sys
from pathlib import Path

import cv2
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from follow.camera import Camera            # noqa: E402
from follow.controller import FollowController  # noqa: E402
from follow.tracker import make_tracker     # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="config.yaml")
ap.add_argument("--live", action="store_true")
args = ap.parse_args()

cfg = yaml.safe_load(open(args.config))
cam = Camera(cfg["camera"])
tracker = make_tracker(cfg["tracker"])
ctrl = FollowController(cfg["follow"], cfg["camera"], cfg["tracker"])


def annotate(frame):
    target = tracker.update(frame)
    if target:
        cv2.circle(frame, (int(target.cx), int(target.cy)), 12, (0, 255, 0), 3)
        vx, yaw = ctrl.update(target)
        txt = f"d={ctrl.distance_m(target):.1f}m vx={vx:+.2f} yaw={yaw:+.0f}"
        cv2.putText(frame, txt, (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, (0, 255, 0), 2)
    else:
        cv2.putText(frame, "no target", (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, (0, 0, 255), 2)
    return frame


try:
    if args.live:
        while True:
            frame = cam.read()
            if frame is None:
                continue
            cv2.imshow("follow", annotate(frame))
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    else:
        frame = annotate(cam.read())
        cv2.imwrite("frame.jpg", frame)
        print("Сохранён frame.jpg")
finally:
    cam.close()
