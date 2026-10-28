"""Hệ thống bóng đổ mềm (Blob Shadow) siêu nhẹ cho Bloxorz Ursina UI.

Tính năng:
- Tạo bóng đổ phẳng ngay sát trên mặt sàn (y = 0.005) không tốn chi phí render GPU
- Tự động thay đổi kích thước và xoay theo tư thế khối (UPRIGHT: 1x1, HORIZONTAL: 2x1, VERTICAL: 1x2)
- Hiệu ứng thị giác chân thực: Khi khối lăn nhấc lên cao, bóng tự động to ra (wider) và mờ đi (lighter),
  khi khối tiếp đất bóng co lại và đậm nét trở lại.
- Hỗ trợ 2 bóng độc lập khi khối bị phân tách thành 2 khối nhỏ.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from ursina import Entity, Vec2, Vec3, color, destroy

from game.engine import Posture
from game.ursina_ui.materials import get_blob_shadow_texture


class BlobShadow:
    """Quản lý các Entity bóng phẳng (blob shadow) bên dưới khối người chơi."""

    def __init__(self) -> None:
        self.tex = get_blob_shadow_texture(size=128)
        self.shadow_main: Entity | None = None
        self.shadow_cube_2: Entity | None = None
        self.is_suppressed: bool = False
        self.create_shadows()

    def create_shadows(self) -> None:
        """Tạo đối tượng shadow quad."""
        self.destroy_all()
        # Bóng khối chính / khối 1
        self.shadow_main = Entity(
            name="blob_shadow_main",
            model="quad",
            rotation_x=90,
            position=Vec3(0, 0.008, 0),
            scale=Vec2(1.2, 1.2),
            texture=self.tex,
            color=color.rgba(0.0, 0.0, 0.0, 0.85),
            always_on_top=False,
        )
        # Bóng cho khối 2 khi split
        self.shadow_cube_2 = Entity(
            name="blob_shadow_cube2",
            model="quad",
            rotation_x=90,
            position=Vec3(0, 0.008, 0),
            scale=Vec2(1.15, 1.15),
            texture=self.tex,
            color=color.rgba(0.0, 0.0, 0.0, 0.85),
            enabled=False,
        )

    def destroy_all(self) -> None:
        """Dọn dẹp bóng khi reset hoặc đổi màn."""
        if self.shadow_main is not None:
            destroy(self.shadow_main)
            self.shadow_main = None
        if self.shadow_cube_2 is not None:
            destroy(self.shadow_cube_2)
            self.shadow_cube_2 = None

    def update_transform(
        self,
        world_x: float,
        world_z: float,
        block_y: float,
        posture: Posture,
        is_split: bool = False,
        cube_2_pos: tuple[float, float, float] | None = None,
    ) -> None:
        """Cập nhật vị trí, kích thước và độ đậm nhạt của bóng theo khối."""
        if self.is_suppressed or self.shadow_main is None:
            return

        # Tính toán độ nâng (lift) của khối so với sàn
        base_y = 1.0 if posture == Posture.UPRIGHT else 0.5
        lift = max(0.0, block_y - base_y)

        # 1. Kích thước bóng cơ bản theo tư thế
        if is_split:
            base_sx, base_sz = 1.15, 1.15
        elif posture == Posture.UPRIGHT:
            base_sx, base_sz = 1.18, 1.18
        elif posture == Posture.HORIZONTAL:
            base_sx, base_sz = 2.18, 1.18
        else:  # VERTICAL
            base_sx, base_sz = 1.18, 2.18

        # Khối càng nâng cao -> bóng càng to và càng nhạt
        scale_mult = 1.0 + lift * 0.35
        alpha_mult = max(0.2, 1.0 - lift * 0.6)

        self.shadow_main.enabled = True
        self.shadow_main.position = Vec3(world_x, 0.008, world_z)
        self.shadow_main.scale = Vec2(base_sx * scale_mult, base_sz * scale_mult)
        self.shadow_main.color = color.rgba(0.0, 0.0, 0.0, 0.85 * alpha_mult)

        # 2. Xử lý bóng thứ 2 nếu đang ở trạng thái phân tách (split)
        if is_split and cube_2_pos is not None and self.shadow_cube_2 is not None:
            self.shadow_cube_2.enabled = True
            c2_x, c2_y, c2_z = cube_2_pos
            c2_lift = max(0.0, c2_y - 0.5)
            c2_scale = 1.15 * (1.0 + c2_lift * 0.35)
            c2_alpha = max(0.2, 1.0 - c2_lift * 0.6)
            self.shadow_cube_2.position = Vec3(c2_x, 0.008, c2_z)
            self.shadow_cube_2.scale = Vec2(c2_scale, c2_scale)
            self.shadow_cube_2.color = color.rgba(0.0, 0.0, 0.0, 0.85 * c2_alpha)
        elif self.shadow_cube_2 is not None:
            self.shadow_cube_2.enabled = False

    def suppress(self) -> None:
        """Ngăn chặn hoàn toàn việc vẽ bóng (dùng khi khối rơi hoặc bước đi thua)."""
        self.is_suppressed = True
        self.hide()

    def unsuppress(self) -> None:
        """Cho phép vẽ bóng trở lại khi chơi bình thường."""
        self.is_suppressed = False

    def hide(self) -> None:
        """Ẩn bóng (ví dụ khi khối đã rơi hoàn toàn vào vực sâu)."""
        if self.shadow_main:
            self.shadow_main.enabled = False
        if self.shadow_cube_2:
            self.shadow_cube_2.enabled = False
