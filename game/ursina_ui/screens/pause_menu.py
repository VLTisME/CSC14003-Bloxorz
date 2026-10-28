"""Pause Menu Screen for Bloxorz 3D (Stardew Valley Pixel Art Aesthetic)."""
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


class PauseMenuScreen(Entity):
    """Pause modal screen triggered via ESC or pause button."""

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
        panel_w = 0.56
        panel_h = 0.68
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

        # 3. Title
        self.txt_title = Text(
            parent=self,
            text=LocalizedStr("PAUSED", ["TẠM DỪNG"]),
            font=DEFAULT_FONT_NAME,
            scale=2.2,
            origin=(0, 0),
            position=(0, 0.23, -0.01),
            color=color.hex(PALETTE["ink"]),
        )

        # Stage info
        self.txt_info = Text(
            parent=self,
            text="Stage 01  •  Moves: 0",
            font=DEFAULT_FONT_NAME,
            scale=1.0,
            origin=(0, 0),
            position=(0, 0.16, -0.01),
            color=color.hex(PALETTE["brick"]),
        )

        # Divider line
        self.divider = Entity(
            parent=self,
            model="quad",
            scale=(0.44, 0.004),
            position=(0, 0.12, -0.01),
            color=color.hex(PALETTE["brick"]),
        )

        # 4. Pixel Buttons
        btn_w, btn_h = 0.40, 0.066
        btn_y_start = 0.05
        btn_spacing = 0.080

        # Button 1: Resume (Green ramp)
        self.btn_resume = PixelButton(
            parent=self,
            text=LocalizedStr("RESUME", ["TIẾP TỤC"]),
            color_ramp="green",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start, 0),
            on_click=self._on_resume_clicked,
        )

        # Button 2: Restart (Orange ramp)
        self.btn_restart = PixelButton(
            parent=self,
            text=LocalizedStr("RESTART", ["CHƠI LẠI"]),
            color_ramp="orange",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing, 0),
            on_click=self._on_restart_clicked,
        )

        # Button 3: Select Stage (Orange ramp)
        self.btn_stages = PixelButton(
            parent=self,
            text=LocalizedStr("STAGE SELECT", ["CHỌN MÀN"]),
            color_ramp="orange",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing * 2, 0),
            on_click=self._on_select_stage_clicked,
        )

        # Button 4: Help (Orange ramp)
        self.btn_help = PixelButton(
            parent=self,
            text=LocalizedStr("HOW TO PLAY", ["TRỢ GIÚP"]),
            color_ramp="orange",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing * 3, 0),
            on_click=self._on_help_clicked,
        )

        # Button 5: Main Menu (Red ramp)
        self.btn_menu = PixelButton(
            parent=self,
            text=LocalizedStr("MAIN MENU", ["MENU CHÍNH"]),
            color_ramp="red",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing * 4, 0),
            on_click=self._on_main_menu_clicked,
        )

    def update_info(self, stage_name: str, moves: int) -> None:
        """Update stage name and move count in header."""
        self.txt_info.text = f"{stage_name}  •  Moves: {moves}"

    def _on_resume_clicked(self) -> None:
        self.hide()
        if self.on_resume:
            self.on_resume()

    def _on_restart_clicked(self) -> None:
        self.hide()
        if self.on_restart:
            self.on_restart()

    def _on_select_stage_clicked(self) -> None:
        if self.on_select_stage:
            self.on_select_stage()

    def _on_help_clicked(self) -> None:
        if self.on_help:
            self.on_help()

    def _on_main_menu_clicked(self) -> None:
        self.hide()
        if self.on_main_menu:
            self.on_main_menu()

    def show(self, stage_name: str = "", move_count: int = 0) -> None:
        if stage_name or move_count:
            self.txt_info.text = f"{stage_name}  •  Moves: {move_count}"
        self.enabled = True

    def hide(self) -> None:
        self.enabled = False
