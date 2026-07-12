"""Главный цикл follow-me.

Запуск на Pi:      python -m follow.main --config config.yaml
Отладка без FC:    python -m follow.main --config config.yaml --dry-run

Логика: команды скорости отправляются ТОЛЬКО когда FC armed и в GUIDED.
Во всех остальных режимах программа лишь наблюдает и печатает телеметрию —
можно безопасно держать её запущенной с момента включения.
"""
from __future__ import annotations

import argparse
import time

import yaml

from .camera import Camera
from .controller import FollowController
from .safety import Safety, TRACK, HOVER, LOITER
from .tracker import make_tracker


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--dry-run", action="store_true",
                    help="без MAVLink: печатать команды вместо отправки")
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    camera = Camera(cfg["camera"])
    tracker = make_tracker(cfg["tracker"])
    controller = FollowController(cfg["follow"], cfg["camera"], cfg["tracker"])
    safety = Safety(cfg["safety"])

    link = None
    if not args.dry_run:
        from .mavlink_link import MavLink
        link = MavLink(cfg["mavlink"]["connection"], cfg["mavlink"]["baud"])
        link.wait_heartbeat()

    period = 1.0 / float(cfg["camera"]["fps"])
    last_log = 0.0
    loiter_sent = False

    try:
        while True:
            t0 = time.monotonic()
            frame = camera.read()
            if frame is None:
                continue
            target = tracker.update(frame)

            if link:
                link.pump()
            voltage = link.voltage if link else None
            engaged = bool(link and link.armed and link.flightmode == "GUIDED")
            act = safety.action(target is not None, voltage)

            vx = yaw = 0.0
            if act == TRACK and target is not None:
                vx, yaw = controller.update(target)
                vx, _, _ = safety.clamp(vx, 0, 0)

            if engaged:
                if act == LOITER:
                    if not loiter_sent:
                        link.set_mode("LOITER")
                        loiter_sent = True
                else:
                    loiter_sent = False
                    if act == TRACK and target is not None:
                        link.send_body_velocity(vx, 0, 0, yaw)
                    else:  # HOVER или цель ещё не появлялась
                        link.stop()
            elif args.dry_run and target is not None:
                pass  # команды считаются, печатаются ниже

            if t0 - last_log > 1.0:
                last_log = t0
                dist = f"{controller.distance_m(target):4.1f}м" if target else " -- "
                mode = link.flightmode if link else "DRY"
                print(f"[{mode}{' ARM' if link and link.armed else ''}] "
                      f"цель={'да' if target else 'НЕТ'} d={dist} "
                      f"vx={vx:+.2f} yaw={yaw:+5.1f} "
                      f"batt={voltage or 0:.1f}V act={act}")

            dt = time.monotonic() - t0
            if dt < period:
                time.sleep(period - dt)
    except KeyboardInterrupt:
        print("\nОстановка.")
    finally:
        if link and link.armed and link.flightmode == "GUIDED":
            link.stop()
        camera.close()


if __name__ == "__main__":
    main()
