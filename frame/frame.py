#!/usr/bin/env python3
"""Параметрическая рама follow-me дрона (deadcat, винты 5.1").

Запуск:   .venv/bin/python frame/frame.py
Выход:    frame/export/*.stl  — на печать
          frame/export/*.step — для доработки во FreeCAD
          frame/export/assembly.step — вся рама в сборе для проверки

Компоновка (снизу вверх):
  АКБ (на ремешке) -> армы -> нижняя плита -> стек 30.5x30.5 ->
  стойки 30 мм -> верхняя плита -> Raspberry Pi 5, камера (нос), GPS (корма).

Все размеры в мм. Ось +X — вперёд (нос).
"""

from pathlib import Path
from build123d import *

# ---------------- Параметры ----------------
MOTOR_R = 125.0                   # радиус осей моторов (база ~250 мм)
ARM_ANGLES = (60, -60, 135, -135) # передние +-60° (deadcat), задние +-135°
PROP_D = 130.0                    # 5.1" — только для проверок зазоров

ARM_T = 6.0                       # толщина арма
BEAM_W = 14.0                     # ширина балки арма
TAB_W = 20.0                      # ширина корневого хвостовика
TAB_R0, TAB_R1 = 30.0, 54.0       # радиальные границы хвостовика
ARM_BOLT_RS = (36.0, 48.0)        # болты M3 крепления арма к плите
PAD_R = 16.0                      # диск под мотор
MOTOR_HOLE_PITCH = 16.0           # 2207: 16x16, M3

PLATE_R = 55.0                    # радиус обеих плит
BOT_T = 6.0                       # нижняя плита
TOP_T = 4.0                       # верхняя плита
POCKET_DEPTH = 1.3                # карман под хвостовик (низ нижней плиты)
CLEAR = 0.25                      # зазор печати на сторону
STANDOFF_H = 30.0                 # стойки M3 между плитами

STACK_PITCH = 30.5                # SpeedyBee F405 V3
STACK_HOLE_D = 4.2                # M4-люверсы стека
STANDOFF_POS = 50.0               # стойки: (+-50,0),(0,+-50)

PI_CENTER = (-5.0, 0.0)           # Raspberry Pi 5 на верхней плите
PI_DX, PI_DY = 58.0, 49.0         # межосевые Pi, M2.5
CAM_MOUNT_X, CAM_MOUNT_Y = 48.0, 8.0    # кронштейн камеры (нос)
GPS_MOUNT_X, GPS_MOUNT_Y = -48.0, 8.0   # мачта GPS (корма)

R_M3, R_M25, R_M2 = 3.2 / 2, 2.7 / 2, 2.2 / 2

EXPORT = Path(__file__).parent / "export"


def hole(x, y, r):
    return Pos(x, y) * Circle(r)


# ---------------- Арм (x4, одинаковые) ----------------
def make_arm():
    sk = (
        Pos((TAB_R0 + TAB_R1) / 2, 0) * Rectangle(TAB_R1 - TAB_R0, TAB_W)
        + Pos((TAB_R0 + MOTOR_R) / 2, 0) * Rectangle(MOTOR_R - TAB_R0, BEAM_W)
        + Pos(MOTOR_R, 0) * Circle(PAD_R)
    )
    for r in ARM_BOLT_RS:
        sk -= hole(r, 0, R_M3)
    p = MOTOR_HOLE_PITCH / 2
    for dx in (-p, p):
        for dy in (-p, p):
            sk -= hole(MOTOR_R + dx, dy, R_M3)
    sk -= hole(MOTOR_R, 0, 4.5)  # вал/провода
    return extrude(sk, ARM_T)


# ---------------- Нижняя плита ----------------
def make_bottom_plate():
    sk = Circle(PLATE_R)
    s = STACK_PITCH / 2
    for dx in (-s, s):
        for dy in (-s, s):
            sk -= hole(dx, dy, STACK_HOLE_D / 2)
    for x, y in ((STANDOFF_POS, 0), (-STANDOFF_POS, 0), (0, STANDOFF_POS), (0, -STANDOFF_POS)):
        sk -= hole(x, y, R_M3)
    for ang in ARM_ANGLES:
        for r in ARM_BOLT_RS:
            sk -= Rot(Z=ang) * hole(r, 0, R_M3)
    # ремешок АКБ (лента до 20 мм) и вывод силового провода
    sk -= Pos(0, 24) * SlotOverall(24, 4)
    sk -= Pos(0, -24) * SlotOverall(24, 4)
    sk -= Pos(-35, 0) * SlotOverall(14, 7)
    plate = extrude(sk, BOT_T)
    # карманы под хвостовики армов (снизу, фиксация от проворота)
    for ang in ARM_ANGLES:
        pocket = Rot(Z=ang) * (
            Pos((TAB_R0 + TAB_R1) / 2, 0)
            * Rectangle(TAB_R1 - TAB_R0 + 2 * CLEAR, TAB_W + 2 * CLEAR)
        )
        plate -= extrude(pocket, POCKET_DEPTH)
    return plate


# ---------------- Верхняя плита ----------------
def make_top_plate():
    sk = Circle(PLATE_R)
    for x, y in ((STANDOFF_POS, 0), (-STANDOFF_POS, 0), (0, STANDOFF_POS), (0, -STANDOFF_POS)):
        sk -= hole(x, y, R_M3)
    for dx in (-PI_DX / 2, PI_DX / 2):
        for dy in (-PI_DY / 2, PI_DY / 2):
            sk -= hole(PI_CENTER[0] + dx, PI_CENTER[1] + dy, R_M25)
    for y in (CAM_MOUNT_Y, -CAM_MOUNT_Y):
        sk -= hole(CAM_MOUNT_X, y, R_M3)
    for y in (GPS_MOUNT_Y, -GPS_MOUNT_Y):
        sk -= hole(GPS_MOUNT_X, y, R_M3)
    sk -= Pos(34, 0) * SlotOverall(18, 4)   # шлейф камеры
    sk -= Pos(-30, 0) * SlotOverall(14, 6)  # провода GPS/UART вниз к стеку
    return extrude(sk, TOP_T)


# ---------------- Кронштейн камеры (IMX219, наклон 10° вниз) ----------------
def make_camera_bracket():
    base_sk = Rectangle(20, 28) - hole(0, CAM_MOUNT_Y, R_M3) - hole(0, -CAM_MOUNT_Y, R_M3)
    base = extrude(base_sk, 3)

    up_sk = Rectangle(28, 34, align=(Align.CENTER, Align.MIN))
    up_sk -= Pos(0, 16) * Circle(7)  # окно объектива
    for dy in (-10.5, 10.5):         # отверстия платы IMX219: 21 x 12.5, M2
        for dz in (-6.25, 6.25):
            up_sk -= Pos(dy, 16 + dz) * Circle(R_M2)
    upright = extrude(Plane.YZ * up_sk, 3)          # стенка толщиной 3, x: 0..3
    upright = Pos(7, 0, 3) * Rot(0, 10, 0) * upright  # наклон 10° вперёд-вниз
    return base + upright


# ---------------- Мачта GPS ----------------
def make_gps_mast():
    base = extrude(Rectangle(20, 28) - hole(0, GPS_MOUNT_Y, R_M3) - hole(0, -GPS_MOUNT_Y, R_M3), 3)
    post = Pos(0, 0, 3) * extrude(Rectangle(10, 10), 40)
    top_sk = Rectangle(28, 28)
    top_sk -= Pos(0, 11) * SlotOverall(10, 3)
    top_sk -= Pos(0, -11) * SlotOverall(10, 3)
    top_sk -= Pos(11, 0) * SlotOverall(10, 3, rotation=90)
    top_sk -= Pos(-11, 0) * SlotOverall(10, 3, rotation=90)
    top = Pos(0, 0, 43) * extrude(top_sk, 2)
    return base + post + top


# ---------------- Сборка и экспорт ----------------
def main():
    EXPORT.mkdir(exist_ok=True)
    arm = make_arm()
    bottom = make_bottom_plate()
    top = make_top_plate()
    cam = make_camera_bracket()
    gps = make_gps_mast()

    parts = {"arm": arm, "bottom_plate": bottom, "top_plate": top,
             "camera_bracket": cam, "gps_mast": gps}
    for name, part in parts.items():
        assert part.volume > 1, f"{name}: пустая геометрия"
        export_stl(part, str(EXPORT / f"{name}.stl"))
        export_step(part, str(EXPORT / f"{name}.step"))
        bb = part.bounding_box()
        print(f"{name:16s} V={part.volume/1000:7.1f} см3  "
              f"габарит {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} мм")

    top_z = BOT_T + STANDOFF_H
    assembly = Compound(children=[
        bottom,
        *[Pos(0, 0, POCKET_DEPTH - ARM_T) * Rot(Z=a) * arm for a in ARM_ANGLES],
        Pos(0, 0, top_z) * top,
        Pos(CAM_MOUNT_X, 0, top_z + TOP_T) * cam,
        Pos(GPS_MOUNT_X, 0, top_z + TOP_T) * gps,
    ])
    export_step(assembly, str(EXPORT / "assembly.step"))
    print(f"\nСборка: {EXPORT / 'assembly.step'}")

    # Проверка зазора винтов: ближняя точка диска винта к центру
    clearance = (MOTOR_R - PROP_D / 2) - PLATE_R
    print(f"Зазор винт-плита: {clearance:.1f} мм (должен быть > 3)")
    assert clearance > 3


if __name__ == "__main__":
    main()
