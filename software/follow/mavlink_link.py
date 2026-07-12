"""Связь с ArduPilot по MAVLink (pymavlink).

Дрон управляется командами скорости в системе координат корпуса
(SET_POSITION_TARGET_LOCAL_NED, MAV_FRAME_BODY_OFFSET_NED). ArduPilot
принимает их ТОЛЬКО в режиме GUIDED — это и есть главный предохранитель:
пилот тумблером переводит FC в GUIDED («передал управление Pi») и в любой
момент выдёргивает обратно в LOITER/RTL.
"""
from __future__ import annotations

import math
import time

from pymavlink import mavutil

# ignore position + acceleration + yaw; использовать velocity + yaw_rate
_TYPE_MASK = (
    mavutil.mavlink.POSITION_TARGET_TYPEMASK_X_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_Y_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_Z_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AX_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AY_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AZ_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_YAW_IGNORE
)


class MavLink:
    def __init__(self, connection: str, baud: int = 921600):
        self.m = mavutil.mavlink_connection(connection, baud=baud)
        self.voltage: float | None = None
        self.gps_fix: int = 0
        self.satellites: int = 0

    def wait_heartbeat(self, timeout: float = 30.0):
        print(f"Жду heartbeat от FC ({self.m.address})...")
        hb = self.m.wait_heartbeat(timeout=timeout)
        if hb is None:
            raise TimeoutError("Нет heartbeat: проверьте UART/провода/SERIALx_PROTOCOL")
        print(f"OK: system {self.m.target_system}, режим {self.flightmode}")

    def pump(self):
        """Вычитать входящие сообщения (звать каждый цикл)."""
        while True:
            msg = self.m.recv_match(blocking=False)
            if msg is None:
                return
            t = msg.get_type()
            if t == "SYS_STATUS":
                self.voltage = msg.voltage_battery / 1000.0
            elif t == "GPS_RAW_INT":
                self.gps_fix = msg.fix_type
                self.satellites = msg.satellites_visible

    @property
    def flightmode(self) -> str:
        return self.m.flightmode

    @property
    def armed(self) -> bool:
        return bool(self.m.motors_armed())

    def set_mode(self, name: str):
        self.m.set_mode_apm(self.m.mode_mapping()[name])
        print(f"-> режим {name}")

    def send_body_velocity(self, vx: float, vy: float, vz: float,
                           yaw_rate_dps: float):
        """Скорости в СК корпуса: vx вперёд, vy вправо, vz ВНИЗ (NED), м/с."""
        self.m.mav.set_position_target_local_ned_send(
            0,
            self.m.target_system, self.m.target_component,
            mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED,
            _TYPE_MASK,
            0, 0, 0,
            vx, vy, vz,
            0, 0, 0,
            0, math.radians(yaw_rate_dps),
        )

    def stop(self):
        """Нулевые скорости — зависнуть."""
        self.send_body_velocity(0, 0, 0, 0)
