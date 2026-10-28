"""Khối người chơi 3D (BlockView) cho Bloxorz Ursina UI.

Kiến trúc Dual-Cube Solid Assembly:
- Khối 1x1x2 được cấu thành từ 2 nửa lập phương 1x1x1 đối xứng chuẩn xác.
- Mỗi nửa giữ tỉ lệ UV vuông vức 1:1 bất biến trên cả 6 mặt, triệt tiêu hoàn toàn lỗi co dãn texture khi đổi tư thế.
- Texture gỗ gụ sẫm RGB đặc 100% có thớ vân tự nhiên và viền vát cạnh 3D (chamfered bevel edge) nổi khối sắc sảo.
- Có đường rãnh ghép chìm tự nhiên giữa 2 nửa, tạo cảm giác nguyên khối cơ học đầm tay.
- Hỗ trợ hoàn hảo chế độ Split tách đôi sang 2 khối ngọc lam và sapphire.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from ursina import Entity, Vec3, color, destroy, scene

from game.engine import Posture
from game.theme import get_theme
from game.ursina_ui.materials import (
    get_posture_block_texture,
    get_solid_wood_texture,
    get_split_wood_texture,
    hex_to_ursina_color,
)

if TYPE_CHECKING:
    from game.engine import BloxorzEngine


class BlockView:
    """Quản lý các Entity 3D đại diện cho khối Bloxorz của người chơi."""

    def __init__(self, theme_name: str = "toy") -> None:
        self.theme_name = theme_name
        self.theme = get_theme(theme_name)

        # Cấu hình vật liệu gỗ tối giản thanh lịch viền vát cạnh nổi khối
        bm = self.theme.get("block_main", {})
        self.base_wood_color = bm.get("color", bm.get("top", "#8B5A2B"))
        self.wood_texture = get_posture_block_texture(Posture.UPRIGHT, part=1, base_hex=self.base_wood_color)

        # Root container của khối chính
        self.block_entity = Entity(
            name="bloxorz_block_root",
            position=Vec3(0, 0, 0),
        )

        # Nửa 1 của khối
        self.cube_1 = Entity(
            parent=self.block_entity,
            name="block_part1",
            model="cube",
            position=Vec3(0, 0.5, 0),
            scale=Vec3(0.98, 0.98, 0.98),
            texture=self.wood_texture,
            color=color.white,
            transparent=False,
        )

        # Nửa 2 của khối
        self.cube_2 = Entity(
            parent=self.block_entity,
            name="block_part2",
            model="cube",
            position=Vec3(0, 1.5, 0),
            scale=Vec3(0.98, 0.98, 0.98),
            texture=self.wood_texture,
            color=color.white,
            transparent=False,
        )

        # Alias để tương thích với chế độ split
        self.cube_2_entity = self.cube_2

    def destroy_all(self) -> None:
        """Dọn dẹp các entity của khối."""
        if self.cube_1:
            destroy(self.cube_1)
            self.cube_1 = None
        if self.cube_2:
            destroy(self.cube_2)
            self.cube_2 = None
        if self.block_entity:
            destroy(self.block_entity)
            self.block_entity = None
        self.cube_2_entity = None

    def sync_from_engine(self, engine: BloxorzEngine) -> None:
        """Đồng bộ trạng thái hiển thị của khối từ BloxorzEngine."""
        if self.block_entity is None or self.cube_1 is None or self.cube_2 is None:
            return

        if engine.is_split:
            # Chế độ tách 2 khối nhỏ 1x1x1
            r1, c1 = engine.state.first
            r2, c2 = engine.state.second

            # Khối 1 (Gỗ Hổ Phách viền Ngọc Lục Bảo)
            is_c1_active = (engine.selected_cube == 1)
            self.cube_1.enabled = True
            self.cube_1.parent = scene
            self.cube_1.position = Vec3(float(c1), 0.5, -float(r1))
            self.cube_1.scale = Vec3(0.98, 0.98, 0.98)
            self.cube_1.rotation = Vec3(0, 0, 0)
            self.cube_1.texture = get_split_wood_texture(1, is_active=is_c1_active)
            self.cube_1.color = color.white
            self.cube_1.transparent = False

            # Khối 2 (Gỗ Anh Đào viền Lam Ngọc)
            is_c2_active = (engine.selected_cube == 2)
            self.cube_2.enabled = True
            self.cube_2.parent = scene
            self.cube_2.position = Vec3(float(c2), 0.5, -float(r2))
            self.cube_2.scale = Vec3(0.98, 0.98, 0.98)
            self.cube_2.rotation = Vec3(0, 0, 0)
            self.cube_2.texture = get_split_wood_texture(2, is_active=is_c2_active)
            self.cube_2.color = color.white
            self.cube_2.transparent = False

            self.block_entity.enabled = False

        else:
            # Chế độ khối đơn 1x1x2 nguyên vẹn
            self.block_entity.enabled = True
            self.block_entity.parent = scene
            self.block_entity.rotation = Vec3(0, 0, 0)
            self.block_entity.scale = Vec3(1, 1, 1)

            self.cube_1.parent = self.block_entity
            self.cube_2.parent = self.block_entity
            self.cube_1.enabled = True
            self.cube_2.enabled = True
            self.cube_1.scale = Vec3(0.98, 0.98, 0.98)
            self.cube_2.scale = Vec3(0.98, 0.98, 0.98)
            self.cube_1.rotation = Vec3(0, 0, 0)
            self.cube_2.rotation = Vec3(0, 0, 0)
            if self.cube_1.texture is not self.wood_texture:
                self.cube_1.texture = self.wood_texture
            if self.cube_2.texture is not self.wood_texture:
                self.cube_2.texture = self.wood_texture
            self.cube_1.color = color.white
            self.cube_2.color = color.white
            self.cube_1.transparent = False
            self.cube_2.transparent = False

            cells = engine.block_cells
            if not cells:
                return

            posture = engine.posture
            if posture == Posture.UPRIGHT:
                r, c = cells[0]
                self.block_entity.position = Vec3(float(c), 0.0, -float(r))
                self.cube_1.position = Vec3(0.0, 0.5, 0.0)
                self.cube_2.position = Vec3(0.0, 1.5, 0.0)

            elif posture == Posture.HORIZONTAL:
                cols = [c for r, c in cells]
                r = cells[0][0]
                c_min = min(cols)
                self.block_entity.position = Vec3(float(c_min), 0.0, -float(r))
                self.cube_1.position = Vec3(0.0, 0.5, 0.0)
                self.cube_2.position = Vec3(1.0, 0.5, 0.0)

            else:  # VERTICAL
                rows = [r for r, c in cells]
                c = cells[0][1]
                r_min = min(rows)
                self.block_entity.position = Vec3(float(c), 0.0, -float(r_min))
                self.cube_1.position = Vec3(0.0, 0.5, 0.0)
                self.cube_2.position = Vec3(0.0, 0.5, -1.0)

    def setup_cells(self, cells: list[tuple[int, int]]) -> None:
        """Thiết lập vị trí và hình học chuẩn của khối theo danh sách ô (chuẩn bị cho hoạt ảnh rơi)."""
        if not cells or self.block_entity is None or self.cube_1 is None or self.cube_2 is None:
            return

        self.block_entity.enabled = True
        self.block_entity.parent = scene
        self.block_entity.rotation = Vec3(0, 0, 0)
        self.block_entity.scale = Vec3(1, 1, 1)

        self.cube_1.parent = self.block_entity
        self.cube_2.parent = self.block_entity
        self.cube_1.enabled = True
        self.cube_2.enabled = True
        self.cube_1.scale = Vec3(0.98, 0.98, 0.98)
        self.cube_2.scale = Vec3(0.98, 0.98, 0.98)
        self.cube_1.rotation = Vec3(0, 0, 0)
        self.cube_2.rotation = Vec3(0, 0, 0)

        if len(cells) == 1:
            r, c = cells[0]
            self.block_entity.position = Vec3(float(c), 0.0, -float(r))
            self.cube_1.position = Vec3(0.0, 0.5, 0.0)
            self.cube_2.position = Vec3(0.0, 1.5, 0.0)
        elif cells[0][0] == cells[1][0]:  # HORIZONTAL
            r = cells[0][0]
            c_min = min(cells[0][1], cells[1][1])
            self.block_entity.position = Vec3(float(c_min), 0.0, -float(r))
            self.cube_1.position = Vec3(0.0, 0.5, 0.0)
            self.cube_2.position = Vec3(1.0, 0.5, 0.0)
        else:  # VERTICAL
            c = cells[0][1]
            r_min = min(cells[0][0], cells[1][0])
            self.block_entity.position = Vec3(float(c), 0.0, -float(r_min))
            self.cube_1.position = Vec3(0.0, 0.5, 0.0)
            self.cube_2.position = Vec3(0.0, 0.5, -1.0)

    def get_world_bounds(self, engine: BloxorzEngine) -> tuple[float, float, float, Posture]:
        """Trả về (x, y, z, posture) của tâm khối trong không gian thế giới."""
        if engine.is_split and engine.state is not None:
            r1, c1 = engine.state.first
            return (float(c1), 0.5, -float(r1), Posture.SPLIT)

        cells = engine.block_cells
        if cells:
            cs = [c for r, c in cells]
            rs = [r for r, c in cells]
            cx = sum(cs) / float(len(cs))
            cz = -sum(rs) / float(len(rs))
            by = 1.0 if engine.posture == Posture.UPRIGHT else 0.5
            return (cx, by, cz, engine.posture)
        if self.cube_1 and self.cube_2 and not engine.is_split:
            center = (self.cube_1.world_position + self.cube_2.world_position) * 0.5
            return (center.x, center.y, center.z, engine.posture)
        pos = self.block_entity.world_position if self.block_entity else Vec3(0, 0, 0)
        return (pos.x, 0.5, pos.z, engine.posture)

