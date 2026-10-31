"""Hệ thống điều khiển Camera 3D Isometric cho Bloxorz Ursina UI.

Tính năng:
- Định vị góc nhìn Isometric chuẩn (pitch ~35.26°, yaw ~30°)
- Tự động căn giữa toàn bộ bàn chơi theo kích thước màn (bounding box)
- Chế độ Orthographic (chiếu trục song song chuẩn Bloxorz)
- Zoom bằng con lăn chuột (scroll wheel)
- Phím 'C': Trả camera về vị trí và góc nhìn mặc định
"""
from __future__ import annotations

import math
from ursina import Entity, Vec3, camera, time

from game.theme import get_ursina_config


class CameraRig:
    """Quản lý vị trí, góc xoay và các thao tác tương tác của camera."""

    def __init__(self) -> None:
        cfg = get_ursina_config()
        self.default_yaw = float(cfg.get("cam_yaw", 30.0))
        self.default_pitch = float(cfg.get("cam_pitch", 35.264))
        self.default_fov = float(cfg.get("cam_fov", 16.0))
        self.is_ortho = bool(cfg.get("cam_ortho", True))

        # Pivot điều khiển tại tâm bàn chơi
        self.pivot = Entity(name="camera_pivot", position=(0, 0, 0))
        camera.parent = self.pivot
        camera.orthographic = self.is_ortho

        self.target_position = Vec3(0, 0, 0)
        self.target_yaw = self.default_yaw
        self.target_pitch = self.default_pitch
        self.target_fov = self.default_fov
        self.distance = 32.0

        # Áp dụng thông số ban đầu
        self.reset_view()

    def reset_view(self) -> None:
        """Khôi phục camera về góc nhìn mặc định đã tính toán cho màn hiện tại."""
        self.target_yaw = self.default_yaw
        self.target_pitch = self.default_pitch
        self.target_fov = self.default_fov
        self.pivot.rotation_y = self.target_yaw
        self.pivot.rotation_x = self.target_pitch
        camera.position = (0, 0, -self.distance)
        camera.rotation = (0, 0, 0)
        camera.fov = self.target_fov

    def focus_board(self, min_r: int, max_r: int, min_c: int, max_c: int) -> None:
        """Tính toán tâm và độ thu phóng phù hợp với kích thước bàn cờ."""
        cx = (min_c + max_c) / 2.0
        cz = -(min_r + max_r) / 2.0
        self.target_position = Vec3(cx, 0.0, cz)
        self.pivot.position = self.target_position

        # Điều chỉnh FOV theo chiều dài lớn nhất của bàn
        span_r = max_r - min_r + 1
        span_c = max_c - min_c + 1
        max_span = max(span_r, span_c, 8)

        # Tính toán tầm nhìn tối ưu
        self.default_fov = max(12.0, max_span * 1.35)
        self.target_fov = self.default_fov
        self.distance = max(28.0, max_span * 2.2)
        camera.position = (0, 0, -self.distance)
        camera.fov = self.target_fov

    def input(self, key: str) -> None:
        """Xử lý sự kiện phóng to / thu nhỏ bằng con lăn chuột."""
        if key == "scroll up":
            zoom_delta = 1.2
            self.target_fov = max(6.0, min(45.0, self.target_fov - zoom_delta))
        elif key == "scroll down":
            zoom_delta = 1.2
            self.target_fov = max(6.0, min(45.0, self.target_fov + zoom_delta))

    def update(self, dt: float) -> None:
        """Cập nhật chuyển động mượt mà của camera."""
        # Nội suy mượt mà (lerp)
        lerp_speed = min(1.0, dt * 10.0)
        self.pivot.rotation_y += (self.target_yaw - self.pivot.rotation_y) * lerp_speed
        self.pivot.rotation_x += (self.target_pitch - self.pivot.rotation_x) * lerp_speed
        camera.fov += (self.target_fov - camera.fov) * lerp_speed
