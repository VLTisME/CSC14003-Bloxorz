"""Màn hình tạm dừng (Pause Menu Screen) cho Bloxorz Ursina UI."""
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


class PauseMenuScreen(Entity):
    """Màn hình tạm dừng ván chơi khi người dùng nhấn ESC."""

    def __init__(
        self,
        on_resume: Callable[[], None],
        on_restart: Callable[[], None],
        on_select_stage: Callable[[], None],
        on_help: Callable[[], None],
        on_main_menu: Callable[[], None],
    ) -> None:
        super().__init__(parent=camera.ui, name="pause_menu_screen", enabled=False)

        self.on_resume = on_resume
        self.on_restart = on_restart
        self.on_select_stage = on_select_stage
        self.on_help = on_help
        self.on_main_menu = on_main_menu

        # Lớp nền mờ dimming ấm áp
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
            scale=(0.552, 0.662),
            color=color.hex(FRAME_DARK),
            z=0.06,
        )

        self.panel = Entity(
            parent=self,
            model="quad",
            scale=(0.54, 0.65),
            texture=get_parchment_panel_texture(140, 170),
            color=color.white,
            z=0.05,
        )

        # Tiêu đề
        self.txt_title = Text(
            parent=self,
            text="TẠM DỪNG",
            font=FONT_NAME,
            scale=2.2,
            origin=(0, 0),
            position=(0, 0.23, 0),
            color=color.hex(TEXT_DARK),
        )

        # Thông tin ván chơi
        self.txt_info = Text(
            parent=self,
            text="Màn 01  •  Số bước: 0",
            font=FONT_NAME,
            scale=1.0,
            origin=(0, 0),
            position=(0, 0.16, 0),
            color=color.hex(TEXT_MUTED),
        )

        # Đường gạch phân cách
        self.divider = Entity(
            parent=self,
            model="quad",
            scale=(0.42, 0.003),
            position=(0, 0.12, 0),
            color=color.hex(FRAME_BEZEL),
        )

        # Danh sách nút bấm
        btn_w, btn_h = 0.38, 0.062
        btn_y_start = 0.05
        btn_spacing = 0.075

        # 1. Nút Tiếp tục
        self.btn_resume = Button(
            parent=self,
            text="TIẾP TỤC (ESC)",
            model="quad",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start, 0),
            color=color.hex("#4E8A3A"),
            highlight_color=color.hex("#62A848"),
            pressed_color=color.hex("#3B682C"),
            text_color=color.white,
            text_origin=(0, 0),
            radius=0.15,
            on_click=self._on_resume_clicked,
        )

        # 2. Nút Chơi lại từ đầu
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

        # 3. Nút Chọn màn khác
        self.btn_stages = Button(
            parent=self,
            text="CHỌN MÀN KHÁC (M)",
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

        # 4. Nút Hướng dẫn
        self.btn_help = Button(
            parent=self,
            text="HƯỚNG DẪN (H)",
            model="quad",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing * 3, 0),
            color=color.hex(BTN_WOOD_BASE),
            highlight_color=color.hex(BTN_HOVER),
            pressed_color=color.hex(BTN_PRESSED),
            text_color=color.hex(TEXT_DARK),
            text_origin=(0, 0),
            radius=0.15,
            on_click=self._on_help_clicked,
        )

        # 5. Nút Menu chính
        self.btn_menu = Button(
            parent=self,
            text="VỀ MENU CHÍNH",
            model="quad",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing * 4, 0),
            color=color.hex("#8A562E"),
            highlight_color=color.hex("#A66B3B"),
            pressed_color=color.hex("#6E3E1A"),
            text_color=color.white,
            text_origin=(0, 0),
            radius=0.15,
            on_click=self._on_main_menu_clicked,
        )


    def _on_resume_clicked(self) -> None:
        self.hide()
        self.on_resume()

    def _on_restart_clicked(self) -> None:
        self.hide()
        self.on_restart()

    def _on_stages_clicked(self) -> None:
        self.hide()
        self.on_select_stage()

    def _on_help_clicked(self) -> None:
        self.on_help()

    def _on_main_menu_clicked(self) -> None:
        self.hide()
        self.on_main_menu()

    def show(self, stage_name: str = "", move_count: int = 0) -> None:
        """Hiển thị menu tạm dừng với thông tin cập nhật."""
        self.txt_info.text = f"{stage_name}  •  Số bước: {move_count}"
        self.enabled = True

    def hide(self) -> None:
        """Ẩn menu tạm dừng."""
        self.enabled = False
