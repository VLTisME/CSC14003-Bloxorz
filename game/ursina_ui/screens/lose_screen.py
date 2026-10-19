"""Màn hình thất bại (Lose Screen) cho Bloxorz Ursina UI."""
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

FONT_NAME = UI_FONT


class LoseScreen(Entity):
    """Màn hình thông báo khi khối rơi khỏi sàn hoặc phạm quy."""

    def __init__(
        self,
        on_retry: Callable[[], None],
        on_undo: Callable[[], None],
        on_select_stage: Callable[[], None],
        on_main_menu: Callable[[], None],
    ) -> None:
        super().__init__(parent=camera.ui, name="lose_screen", enabled=False)

        self.on_retry = on_retry
        self.on_undo = on_undo
        self.on_select_stage = on_select_stage
        self.on_main_menu = on_main_menu

        # Nền mờ đỏ trầm cảnh báo
        self.bg_overlay = Entity(
            parent=self,
            model="quad",
            scale=(2.5, 2.5),
            color=color.rgba(20 / 255.0, 8 / 255.0, 10 / 255.0, 0.88),
            z=0.1,
        )

        # Panel trung tâm
        self.panel = Entity(
            parent=self,
            model="quad",
            scale=(0.56, 0.62),
            color=color.rgba(36 / 255.0, 20 / 255.0, 26 / 255.0, 0.95),
            z=0.05,
        )

        self.panel_border = Entity(
            parent=self,
            model="quad",
            scale=(0.565, 0.625),
            color=color.hex("#E53E3E"),
            z=0.06,
        )

        # Tiêu đề thất bại
        self.txt_title = Text(
            parent=self,
            text="THẤT BẠI!",
            font=FONT_NAME,
            scale=2.3,
            origin=(0, 0),
            position=(0, 0.22, 0),
            color=color.hex("#FC8181"),
        )

        # Lý do thua
        self.txt_reason = Text(
            parent=self,
            text="Khối đã bị rơi khỏi sàn đấu!",
            font=FONT_NAME,
            scale=1.0,
            origin=(0, 0),
            position=(0, 0.14, 0),
            color=color.hex("#FEB2B2"),
            wordwrap=28,
        )

        # Đường gạch phân cách
        self.divider = Entity(
            parent=self,
            model="quad",
            scale=(0.44, 0.003),
            position=(0, 0.09, 0),
            color=color.hex("#742A2A"),
        )

        # Danh sách nút bấm
        btn_w, btn_h = 0.40, 0.065
        btn_y_start = 0.02
        btn_spacing = 0.078

        # 1. Nút Thử lại
        self.btn_retry = Button(
            parent=self,
            text="THỬ LẠI (R)",
            model="quad",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start, 0),
            color=color.hex("#C53030"),
            highlight_color=color.hex("#E53E3E"),
            text_color=color.white,
            text_origin=(0, 0),
            radius=0.15,
            on_click=self._on_retry_clicked,
        )

        # 2. Nút Hoàn tác bước vừa đi
        self.btn_undo = Button(
            parent=self,
            text="HOÀN TÁC BƯỚC CUỐI (U)",
            model="quad",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing, 0),
            color=color.hex("#2D3748"),
            highlight_color=color.hex("#4A5568"),
            text_color=color.hex("#E2E8F0"),
            text_origin=(0, 0),
            radius=0.15,
            on_click=self._on_undo_clicked,
        )

        # 3. Nút Chọn màn khác
        self.btn_stages = Button(
            parent=self,
            text="CHỌN MÀN KHÁC (M)",
            model="quad",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing * 2, 0),
            color=color.hex("#2D3748"),
            highlight_color=color.hex("#4A5568"),
            text_color=color.hex("#E2E8F0"),
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
            color=color.hex("#4A5568"),
            highlight_color=color.hex("#718096"),
            text_color=color.hex("#F7FAFC"),
            text_origin=(0, 0),
            radius=0.15,
            on_click=self._on_main_menu_clicked,
        )


    def _on_retry_clicked(self) -> None:
        self.hide()
        self.on_retry()

    def _on_undo_clicked(self) -> None:
        self.hide()
        self.on_undo()

    def _on_stages_clicked(self) -> None:
        self.hide()
        self.on_select_stage()

    def _on_main_menu_clicked(self) -> None:
        self.hide()
        self.on_main_menu()

    def show(self, reason: str = "") -> None:
        """Hiển thị màn hình thất bại với lý do."""
        display_reason = "Khối đã bị rơi khỏi sàn đấu!"
        r_lower = reason.lower()
        if "fragile" in r_lower:
            display_reason = "Gạch mỏng bị vỡ do khối đứng thẳng!"
        elif "void" in r_lower or "outside" in r_lower:
            display_reason = "Khối lăn chệch mép rơi xuống vực!"
        elif "split" in r_lower:
            display_reason = "Khối bị rơi khi đang tách đôi!"
        elif reason:
            display_reason = reason
        self.txt_reason.text = display_reason
        self.enabled = True

    def hide(self) -> None:
        """Ẩn màn hình thất bại."""
        self.enabled = False
