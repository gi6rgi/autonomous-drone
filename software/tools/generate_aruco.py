"""Сгенерировать ArUco-маркер для печати.

  python tools/generate_aruco.py            # id=7, DICT_5X5_50 -> marker_7.png
  python tools/generate_aruco.py --id 3

Печатайте крупно (A3 или плитка из A4, сторона ~30 см) на матовой бумаге,
с белой рамкой вокруг. Размер стороны ЧЁРНОГО квадрата впишите в
config.yaml -> tracker.marker_size_m.
"""
import argparse

import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--id", type=int, default=7)
ap.add_argument("--dict", default="DICT_5X5_50")
ap.add_argument("--px", type=int, default=2000)
args = ap.parse_args()

dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, args.dict))
marker = cv2.aruco.generateImageMarker(dictionary, args.id, args.px)
border = args.px // 10
canvas = np.full((args.px + 2 * border, args.px + 2 * border), 255, np.uint8)
canvas[border:-border, border:-border] = marker
out = f"marker_{args.id}.png"
cv2.imwrite(out, canvas)
print(f"Сохранён {out} ({args.dict}, id={args.id})")
