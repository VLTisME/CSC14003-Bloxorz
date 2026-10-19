"""Hiển thị bàn chơi 3D (BoardView) cho Bloxorz Ursina UI.

Quản lý tất cả các ô sàn:
- Ô sàn thông thường (.) và ô xuất phát (S) với texture xanh chanh sắc nét
- Ô gạch cam nứt vỡ (F - Fragile)
- Ô cầu chuyển đổi (B - Bridge) có hoạt ảnh nâng lên/hạ xuống
- Công tắc tròn mềm (O - Soft switch) có nút đỏ nảy
- Công tắc chữ X cứng (X - Hard switch)
- Ô phân tách (T - Splitter)
- Hố đích 3D (G - Goal) với ngôi sao vàng xoay và bập bênh lơ lửng
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING
from ursina import Entity, Vec3, color, destroy, time

from game.theme import get_theme, get_ursina_config
from game.ursina_ui.materials import (
    get_fragile_texture,
    get_hard_switch_texture,
    get_soft_switch_texture,
    get_splitter_texture,
    get_tile_texture,
    hex_to_ursina_color,
)

if TYPE_CHECKING:
    from game.engine import BloxorzEngine


class BoardView:
    """Quản lý các Entity 3D đại diện cho sàn cờ và các đối tượng tĩnh/động trên bàn."""

    def __init__(self, theme_name: str = "toy") -> None:
        self.theme_name = theme_name
        self.theme = get_theme(theme_name)
        cfg = get_ursina_config()
        self.thickness = float(cfg.get("floor_thickness", 0.35))
        self.gap = float(cfg.get("tile_gap", 0.04))
        self.tile_size = 1.0 - self.gap

        # Gốc chứa toàn bộ các entity sàn để dễ xóa khi đổi màn
        self.root: Entity | None = None

        # Quản lý các nhóm ô đặc biệt
        self.tile_entities: dict[tuple[int, int], Entity] = {}
        self.bridge_entities: dict[int, list[Entity]] = {}
        self.switch_button_entities: dict[tuple[int, int], Entity] = {}
        self.fragile_entities: dict[tuple[int, int], Entity] = {}
        self.goal_star: Entity | None = None
        self.goal_pit: Entity | None = None

        # Bounding box của sàn
        self.min_r = 0
        self.max_r = 0
        self.min_c = 0
        self.max_c = 0

    def destroy_all(self) -> None:
        """Dọn dẹp hoàn toàn các Entity sàn hiện tại."""
        if self.root is not None:
            destroy(self.root)
            self.root = None
        self.tile_entities.clear()
        self.bridge_entities.clear()
        self.switch_button_entities.clear()
        self.fragile_entities.clear()
        self.goal_star = None
        self.goal_pit = None

    def load_stage(self, engine: BloxorzEngine) -> None:
        """Xây dựng lại toàn bộ bàn cờ từ dữ liệu engine."""
        self.destroy_all()
        self.root = Entity(name="board_root", position=(0, 0, 0))

        cells = engine.cells
        if not cells:
            return

        active_cells = [(r, c) for (r, c), char in cells.items() if char != "#"]
        if not active_cells:
            return

        rows = [r for r, c in active_cells]
        cols = [c for r, c in active_cells]
        self.min_r, self.max_r = min(rows), max(rows)
        self.min_c, self.max_c = min(cols), max(cols)

        # 1. Tạo các ô sàn (bỏ qua ô vực sâu #)
        for (r, c), char in cells.items():
            if char == "#":
                continue

            world_x = float(c)
            world_z = -float(r)
            pos_y = -self.thickness / 2.0

            if char == "G":
                # Ô đích (Goal) là một hố rỗng vuông vức khoét sâu xuống sàn
                self.goal_pit = Entity(
                    parent=self.root,
                    model="cube",
                    position=Vec3(world_x, -self.thickness * 1.2, world_z),
                    scale=Vec3(self.tile_size, self.thickness * 1.5, self.tile_size),
                    color=hex_to_ursina_color(self.theme["goal"].get("top", "#17202A")),
                    transparent=False,
                )
                # Ngôi sao 3D vàng lơ lửng trên hố đích
                star_color = hex_to_ursina_color(self.theme["goal"].get("star", "#FFD700"))
                self.goal_star = Entity(
                    parent=self.root,
                    model="diamond",
                    position=Vec3(world_x, 0.45, world_z),
                    scale=Vec3(0.42, 0.52, 0.42),
                    color=star_color,
                )
                continue

            # Các loại ô còn lại đều có một khối sàn cơ bản
            is_alt = ((r + c) % 2 == 1)
            tile_tex = get_tile_texture(self.theme_name, is_alt=is_alt)
            tile_color = color.white

            if char == "F":
                # Ô gạch cam mỏng nứt
                tile_tex = get_fragile_texture(self.theme_name)
            elif char == "B":
                # Ô cầu chuyển đổi (Bridge)
                bridge_idx = engine.replay.bridge_cells.get((r, c), 0) if engine.replay else 0
                is_active = engine.is_bridge_active(bridge_idx)
                b_color = hex_to_ursina_color(self.theme["bridge_active"]["top"] if is_active else self.theme["bridge_inactive"]["top"])

                tile_entity = Entity(
                    parent=self.root,
                    model="cube",
                    position=Vec3(world_x, pos_y if is_active else -self.thickness * 1.8, world_z),
                    scale=Vec3(self.tile_size, self.thickness, self.tile_size),
                    color=b_color,
                    transparent=False,
                )
                if bridge_idx not in self.bridge_entities:
                    self.bridge_entities[bridge_idx] = []
                self.bridge_entities[bridge_idx].append(tile_entity)
                self.tile_entities[(r, c)] = tile_entity
                continue

            elif char == "T":
                # Ô phân tách (Splitter)
                tile_tex = get_splitter_texture(self.theme_name)

            tile_entity = Entity(
                parent=self.root,
                model="cube",
                position=Vec3(world_x, pos_y, world_z),
                scale=Vec3(self.tile_size, self.thickness, self.tile_size),
                texture=tile_tex,
                color=tile_color,
                transparent=False,
            )
            self.tile_entities[(r, c)] = tile_entity

            if char == "F":
                self.fragile_entities[(r, c)] = tile_entity

            elif char in ("O", "X"):
                # Nút công tắc nổi lên trên mặt sàn
                btn_tex = get_soft_switch_texture(self.theme_name) if char == "O" else get_hard_switch_texture(self.theme_name)
                btn_entity = Entity(
                    parent=self.root,
                    model="cube",
                    position=Vec3(world_x, 0.04, world_z),
                    scale=Vec3(0.55, 0.08, 0.55),
                    texture=btn_tex,
                    color=color.white,
                    transparent=False,
                )
                self.switch_button_entities[(r, c)] = btn_entity

    def reset_fragile_tiles(self) -> None:
        """Khôi phục vị trí của các ô gạch mỏng sau khi bị vỡ rơi."""
        pos_y = -self.thickness / 2.0
        for ent in self.fragile_entities.values():
            if ent:
                ent.y = pos_y
                ent.rotation = Vec3(0, 0, 0)

    def update_bridges(self, engine: BloxorzEngine, dt: float = 0.016) -> None:
        """Cập nhật trạng thái nâng lên/hạ xuống của các nhóm cầu."""
        for bridge_idx, entities in self.bridge_entities.items():
            active = engine.is_bridge_active(bridge_idx)
            target_y = -self.thickness / 2.0 if active else -self.thickness * 1.8
            target_col = hex_to_ursina_color(self.theme["bridge_active"]["top"] if active else self.theme["bridge_inactive"]["top"])

            for ent in entities:
                ent.y += (target_y - ent.y) * min(1.0, dt * 14.0)
                ent.color = target_col

    def update_switches(self, engine: BloxorzEngine, dt: float = 0.016) -> None:
        """Nén nút công tắc xuống khi khối đứng lên trên."""
        occupied = set(engine.block_cells)
        for (r, c), btn in self.switch_button_entities.items():
            is_stepped = (r, c) in occupied
            target_y = 0.01 if is_stepped else 0.04
            btn.y += (target_y - btn.y) * min(1.0, dt * 16.0)

    def update(self, dt: float) -> None:
        """Cập nhật các hoạt ảnh nhàn rỗi (idle) của bàn chơi."""
        if self.goal_star is not None:
            # Ngôi sao đích tự xoay quanh trục thẳng đứng
            self.goal_star.rotation_y += dt * 80.0
            # Dao động nhẹ bập bênh theo hình sin
            t = time.time() * 3.5
            self.goal_star.y = 0.45 + 0.07 * math.sin(t)
