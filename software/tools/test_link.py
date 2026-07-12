"""Проверка связи Pi <-> FC: heartbeat, режим, батарея, GPS.

  python tools/test_link.py                          # порт из config.yaml
  python tools/test_link.py --conn udp:127.0.0.1:14550   # SITL
"""
import argparse
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from follow.mavlink_link import MavLink  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="config.yaml")
ap.add_argument("--conn", default=None)
ap.add_argument("--baud", type=int, default=None)
args = ap.parse_args()

cfg = yaml.safe_load(open(args.config))["mavlink"]
link = MavLink(args.conn or cfg["connection"], args.baud or cfg.get("baud", 921600))
link.wait_heartbeat()

print("10 секунд телеметрии:")
for _ in range(10):
    link.pump()
    print(f"  режим={link.flightmode:10s} armed={link.armed} "
          f"batt={link.voltage or 0:.2f}V gps_fix={link.gps_fix} "
          f"sats={link.satellites}")
    time.sleep(1)
print("Связь работает.")
