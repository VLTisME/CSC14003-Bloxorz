"""Màn hình chính (Main Menu Screen) cho Bloxorz Ursina UI."""
from __future__ import annotations

from typing import Callable
from ursina import (
    Button,
    Entity,
    Text,
    Vec2,
    Vec3,
    application,
    camera,
    color,
    destroy,
)

from game.theme import UI_FONT
from game.ursina_ui.theme import (
    BTN_HOVER,
    BTN_PRESSED,
    BTN_WOOD_BASE,
    FRAME_BEZEL,
    FRAME_DARK,
    SOLVER_ERROR,
    TEXT_DARK,
    TEXT_MUTED,
    get_parchment_panel_texture,
)

FONT_NAME = UI_FONT


class MainMenuScreen(Entity):
    """Màn hình menu chính của trò chơi."""

    def __init__(
        self,
        on_play: Callable[[], None],
        on_select_stage: Callable[[], None],
        on_help: Callable[[], None],
        on_quit: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent=camera.ui, name="main_menu_screen", enabled=False)

        self.on_play = on_play
        self.on_select_stage = on_select_stage
        self.on_help = on_help
        self.on_quit = on_quit or application.quit

        # Lớp nền mờ tối ấm áp
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
            scale=(0.612, 0.732),
            color=color.hex(FRAME_DARK),
            z=0.06,
        )

        self.panel = Entity(
            parent=self,
            model="quad",
            scale=(0.60, 0.72),
            texture=get_parchment_panel_texture(160, 192),
            color=color.white,
            z=0.05,
        )

        # Tiêu đề game
        self.txt_title = Text(
            parent=self,
            text="BLOXORZ 3D",
            font=FONT_NAME,
            scale=2.4,
            origin=(0, 0),
            position=(0, 0.24, 0),
            color=color.hex(TEXT_DARK),
        )

        # Phụ đề
        self.txt_subtitle = Text(
            parent=self,
            text="COZY EDITION • AI FOUNDATIONS",
            font=FONT_NAME,
            scale=1.0,
            origin=(0, 0),
            position=(0, 0.17, 0),
            color=color.hex(TEXT_MUTED),
        )

        # Đường gạch phân cách
        self.divider = Entity(
            parent=self,
            model="quad",
            scale=(0.45, 0.003),
            position=(0, 0.13, 0),
            color=color.hex(FRAME_BEZEL),
        )

        # Danh sách các nút điều hướng
        btn_w, btn_h = 0.42, 0.068
        btn_y_start = 0.05
        btn_spacing = 0.082

        # 1. Nút Chơi ngay
        self.btn_play = Button(
            parent=self,
            text="CHƠI NGAY",
            model="quad",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start, 0),
            color=color.hex("#4E8A3A"),
            highlight_color=color.hex("#62A848"),
            pressed_color=color.hex("#3B682C"),
            text_color=color.white,
            text_origin=(0, 0),
            radius=0.15,
            on_click=self._on_play_clicked,
        )

        # 2. Nút Chọn màn chơi
        self.btn_stages = Button(
            parent=self,
            text="CHỌN MÀN CHƠI",
            model="quad",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing, 0),
            color=color.hex(BTN_WOOD_BASE),
            highlight_color=color.hex(BTN_HOVER),
            pressed_color=color.hex(BTN_PRESSED),
            text_color=color.hex(TEXT_DARK),
            text_origin=(0, 0),
            radius=0.15,
            on_click=self._on_select_stage_clicked,
        )

        # 3. Nút Hướng dẫn
        self.btn_help = Button(
            parent=self,
            text="HƯỚNG DẪN & PHÍM TẮT",
            model="quad",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing * 2, 0),
            color=color.hex(BTN_WOOD_BASE),
            highlight_color=color.hex(BTN_HOVER),
            pressed_color=color.hex(BTN_PRESSED),
            text_color=color.hex(TEXT_DARK),
            text_origin=(0, 0),
            radius=0.15,
            on_click=self._on_help_clicked,
        )

        # 4. Nút Thoát
        self.btn_quit = Button(
            parent=self,
            text="THOÁT TRÒ CHƠI",
            model="quad",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing * 3, 0),
            color=color.hex(SOLVER_ERROR),
            highlight_color=color.hex("#C53030"),
            pressed_color=color.hex("#822020"),
            text_color=color.white,
            text_origin=(0, 0),
            radius=0.15,
            on_click=self._on_quit_clicked,
        )

        # Footer bản quyền / phiên bản
        self.txt_version = Text(
            parent=self,
            text="v2.0 • Ursina 3D Engine",
            font=FONT_NAME,
            scale=0.8,
            origin=(0, 0),
            position=(0, -0.31, 0),
            color=color.hex(TEXT_MUTED),
        )

    def _on_play_clicked(self) -> None:
        self.hide()
        self.on_play()

    def _on_select_stage_clicked(self) -> None:
        self.hide()
        self.on_select_stage()

    def _on_help_clicked(self) -> None:
        self.on_help()

    def _on_quit_clicked(self) -> None:
        self.on_quit()

    def show(self) -> None:
        """Hiển thị menu chính."""
        self.enabled = True

    def hide(self) -> None:
        """Ẩn menu chính."""
        self.enabled = False
