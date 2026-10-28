"""Màn hình chiến thắng (Win Screen) cho Bloxorz Ursina UI."""
from __future__ import annotations

from typing import Callable
from ursina import (
    Button,
    Entity,
    Text,
    camera,
    color,
)

from game.theme import UI_FONT
from game.ursina_ui.theme import (
    BTN_HOVER,
    BTN_PRESSED,
    BTN_WOOD_BASE,
    FRAME_BEZEL,
    FRAME_DARK,
    TEXT_DARK,
    TEXT_MUTED,
    get_parchment_panel_texture,
)

FONT_NAME = UI_FONT


class WinScreen(Entity):
    """Màn hình vinh danh khi hoàn thành màn chơi."""

    def __init__(
        self,
        on_next_stage: Callable[[], None],
        on_restart: Callable[[], None],
        on_select_stage: Callable[[], None],
        on_main_menu: Callable[[], None],
    ) -> None:
        super().__init__(parent=camera.ui, name="win_screen", enabled=False)

        self.on_next_stage = on_next_stage
        self.on_restart = on_restart
        self.on_select_stage = on_select_stage
        self.on_main_menu = on_main_menu

        # Nền mờ ấm áp
        self.bg_overlay = Entity(
            parent=self,
            model="quad",
            scale=(2.5, 2.5),
            color=color.rgba(24 / 255.0, 16 / 255.0, 10 / 255.0, 0.85),
            z=0.1,
        )

        # Panel trung tâm kiểu bảng gỗ thông báo & giấy da parchment
        self.panel_border = Entity(
            parent=self,
            model="quad",
            scale=(0.572, 0.652),
            color=color.hex("#C47B14"),
            z=0.06,
        )

        self.panel = Entity(
            parent=self,
            model="quad",
            scale=(0.56, 0.64),
            texture=get_parchment_panel_texture(150, 170),
            color=color.white,
            z=0.05,
        )

        # Tiêu đề chiến thắng
        self.txt_title = Text(
            parent=self,
            text="CHIẾN THẮNG!",
            font=FONT_NAME,
            scale=2.3,
            origin=(0, 0),
            position=(0, 0.23, 0),
            color=color.hex("#C47B14"),
        )

        # Biểu tượng sao vàng / kim cương vinh danh
        self.stars_container = Entity(parent=self)
        for offset_x in (-0.05, 0.0, 0.05):
            Entity(
                parent=self.stars_container,
                model="diamond",
                position=(offset_x, 0.165, -0.01),
                scale=(0.026, 0.038, 0.01),
                color=color.hex("#F4C430"),
            )

        # Thống kê thành tích
        self.txt_stats = Text(
            parent=self,
            text="Số bước: 0  |  Kỷ lục: 0",
            font=FONT_NAME,
            scale=1.1,
            origin=(0, 0),
            position=(0, 0.09, 0),
            color=color.hex(TEXT_DARK),
        )

        # Đường gạch phân cách
        self.divider = Entity(
            parent=self,
            model="quad",
            scale=(0.44, 0.003),
            position=(0, 0.04, 0),
            color=color.hex(FRAME_BEZEL),
        )

        # Danh sách nút bấm
        btn_w, btn_h = 0.40, 0.065
        btn_y_start = -0.03
        btn_spacing = 0.078

        # 1. Nút Màn tiếp theo
        self.btn_next = Button(
            parent=self,
            text="MÀN TIẾP THEO (ENTER)",
            model="quad",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start, 0),
            color=color.hex("#4E8A3A"),
            highlight_color=color.hex("#62A848"),
            pressed_color=color.hex("#3B682C"),
            text_color=color.white,
            text_origin=(0, 0),
            radius=0.15,
            on_click=self._on_next_clicked,
        )

        # 2. Nút Chơi lại màn này
        self.btn_restart = Button(
            parent=self,
            text="CHƠI LẠI MÀN (R)",
            model="quad",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing, 0),
            color=color.hex(BTN_WOOD_BASE),
            highlight_color=color.hex(BTN_HOVER),
            pressed_color=color.hex(BTN_PRESSED),
            text_color=color.hex(TEXT_DARK),
            text_origin=(0, 0),
            radius=0.15,
            on_click=self._on_restart_clicked,
        )

        # 3. Nút Danh sách màn
        self.btn_stages = Button(
            parent=self,
            text="DANH SÁCH MÀN (M)",
            model="quad",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing * 2, 0),
            color=color.hex(BTN_WOOD_BASE),
            highlight_color=color.hex(BTN_HOVER),
            pressed_color=color.hex(BTN_PRESSED),
            text_color=color.hex(TEXT_DARK),
            text_origin=(0, 0),
            radius=0.15,
            on_click=self._on_stages_clicked,
        )

        # 4. Nút Menu chính
        self.btn_menu = Button(
            parent=self,
            text="MENU CHÍNH",
            model="quad",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing * 3, 0),
            color=color.hex("#8A562E"),
            highlight_color=color.hex("#A66B3B"),
            pressed_color=color.hex("#6E3E1A"),
            text_color=color.white,
            text_origin=(0, 0),
            radius=0.15,
            on_click=self._on_main_menu_clicked,
        )


    def _on_next_clicked(self) -> None:
        self.hide()
        self.on_next_stage()

    def _on_restart_clicked(self) -> None:
        self.hide()
        self.on_restart()

    def _on_stages_clicked(self) -> None:
        self.hide()
        self.on_select_stage()

    def _on_main_menu_clicked(self) -> None:
        self.hide()
        self.on_main_menu()

    def show(self, stage_name: str = "", moves: int = 0, best_moves: int | None = None) -> None:
        """Hiển thị màn hình chiến thắng với điểm số."""
        best_str = f"Kỷ lục: {best_moves}" if best_moves is not None else "Kỷ lục mới!"
        self.txt_stats.text = f"{stage_name}  •  Số bước: {moves}  •  {best_str}"
        self.enabled = True

    def hide(self) -> None:
        """Ẩn màn hình chiến thắng."""
        self.enabled = False
