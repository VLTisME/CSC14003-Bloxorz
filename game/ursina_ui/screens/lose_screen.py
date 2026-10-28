"""Lose Screen for Bloxorz 3D (Stardew Valley Pixel Art Aesthetic)."""
from __future__ import annotations

from typing import Callable
from ursina import (
    Entity,
    Text,
    camera,
    color,
)

from game.ursina_ui.assets.theme import (
    PALETTE,
    DEFAULT_FONT_NAME,
    LocalizedStr,
    snap,
)
from game.ursina_ui.pixel_widgets import (
    PixelButton,
    get_pixel_panel_texture,
)


class LoseScreen(Entity):
    """Failure modal screen shown when block falls off board or onto fragile tile."""

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

        # 1. Warm night sky / dimmed background overlay
        c_navy = color.hex(PALETTE["navy_1"])
        self.bg_overlay = Entity(
            parent=self,
            model="quad",
            scale=(2.5, 2.5),
            color=color.rgba(c_navy.r, c_navy.g, c_navy.b, 0.88),
            z=0.1,
        )

        # 2. Main Parchment Panel with layered wood bevel
        panel_w = 0.58
        panel_h = 0.66
        w_px = max(64, int(round(panel_w * 864 * (16 / 9))))
        h_px = max(64, int(round(panel_h * 864)))
        panel_tex = get_pixel_panel_texture(w_px, h_px)

        self.panel = Entity(
            parent=self,
            model="quad",
            scale=(panel_w, panel_h),
            texture=panel_tex,
            color=color.white,
            z=0.05,
        )
        self.panel_border = self.panel  # backward compatibility

        # 3. Title ("FALLEN!")
        self.txt_title = Text(
            parent=self,
            text=LocalizedStr("STAGE FAILED!", ["THẤT BẠI!"]),
            font=DEFAULT_FONT_NAME,
            scale=2.3,
            origin=(0, 0),
            position=(0, 0.22, -0.01),
            color=color.hex(PALETTE["red"]),
        )

        # Reason text
        self.txt_reason = Text(
            parent=self,
            text="The block slipped off the edge!",
            font=DEFAULT_FONT_NAME,
            scale=1.0,
            origin=(0, 0),
            position=(0, 0.14, -0.01),
            color=color.hex(PALETTE["ink"]),
            wordwrap=28,
        )

        # Divider line
        self.divider = Entity(
            parent=self,
            model="quad",
            scale=(0.44, 0.004),
            position=(0, 0.095, -0.01),
            color=color.hex(PALETTE["brick"]),
        )

        # 4. Pixel Buttons
        btn_w, btn_h = 0.42, 0.066
        btn_y_start = 0.035
        btn_spacing = 0.080

        # Button 1: Retry (Orange ramp)
        self.btn_retry = PixelButton(
            parent=self,
            text=LocalizedStr("RETRY STAGE", ["THỬ LẠI"]),
            color_ramp="orange",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start, 0),
            on_click=self._on_retry_clicked,
        )

        # Button 2: Undo (Orange ramp)
        self.btn_undo = PixelButton(
            parent=self,
            text=LocalizedStr("UNDO MOVE (U)", ["ĐI LẠI (U)"]),
            color_ramp="orange",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing, 0),
            on_click=self._on_undo_clicked,
        )

        # Button 3: Select Stage (Orange ramp)
        self.btn_stages = PixelButton(
            parent=self,
            text=LocalizedStr("STAGE SELECT", ["CHỌN MÀN CHƠI"]),
            color_ramp="orange",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing * 2, 0),
            on_click=self._on_select_stage_clicked,
        )

        # Button 4: Main Menu (Red ramp)
        self.btn_menu = PixelButton(
            parent=self,
            text=LocalizedStr("MAIN MENU", ["MENU CHÍNH"]),
            color_ramp="red",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing * 3, 0),
            on_click=self._on_main_menu_clicked,
        )

    def set_reason(self, reason: str | None) -> None:
        """Update failure cause description."""
        if not reason:
            self.txt_reason.text = "The block fell off the board!"
        elif "fragile" in reason.lower() or "mỏng" in reason.lower():
            self.txt_reason.text = "Stepped upright on a fragile tile!"
        elif "outside" in reason.lower() or "void" in reason.lower() or "ngoài" in reason.lower():
            self.txt_reason.text = "The block fell into the void!"
        else:
            self.txt_reason.text = reason

    def _on_retry_clicked(self) -> None:
        self.hide()
        if self.on_retry:
            self.on_retry()

    def _on_undo_clicked(self) -> None:
        self.hide()
        if self.on_undo:
            self.on_undo()

    def _on_select_stage_clicked(self) -> None:
        if self.on_select_stage:
            self.on_select_stage()

    def _on_main_menu_clicked(self) -> None:
        self.hide()
        if self.on_main_menu:
            self.on_main_menu()

    def show(self, reason: str | None = None) -> None:
        if reason is not None:
            self.set_reason(reason)
        self.enabled = True

    def hide(self) -> None:
        self.enabled = False
