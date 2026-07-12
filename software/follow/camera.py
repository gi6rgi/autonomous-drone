"""Захват кадров: picamera2 (IMX219 на Pi) или OpenCV (веб-камера для отладки)."""
from __future__ import annotations


class Camera:
    def __init__(self, cfg: dict):
        self.w, self.h = int(cfg["width"]), int(cfg["height"])
        self.backend = cfg.get("backend", "picamera2")
        self._picam = None
        self._cap = None

        if self.backend == "picamera2":
            from picamera2 import Picamera2  # ставится через apt на Pi
            import libcamera
            self._picam = Picamera2()
            transform = libcamera.Transform(
                hflip=bool(cfg.get("hflip")), vflip=bool(cfg.get("vflip")))
            video_cfg = self._picam.create_video_configuration(
                main={"size": (self.w, self.h), "format": "RGB888"},  # RGB888 = BGR в памяти
                transform=transform,
            )
            self._picam.configure(video_cfg)
            self._picam.start()
        elif self.backend == "opencv":
            import cv2
            self._cap = cv2.VideoCapture(int(cfg.get("device", 0)))
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.w)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.h)
            if not self._cap.isOpened():
                raise RuntimeError(f"Камера opencv:{cfg.get('device', 0)} не открылась")
        else:
            raise ValueError(f"Неизвестный backend камеры: {self.backend}")

    def read(self):
        """BGR-кадр (numpy) или None."""
        if self._picam is not None:
            return self._picam.capture_array("main")
        ok, frame = self._cap.read()
        return frame if ok else None

    def close(self):
        if self._picam is not None:
            self._picam.stop()
        if self._cap is not None:
            self._cap.release()
