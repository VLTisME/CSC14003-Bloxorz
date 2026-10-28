"""Win Screen for Bloxorz 3D (Stardew Valley Pixel Art Aesthetic)."""
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


class WinScreen(Entity):
    """Victory screen shown upon successfully dropping the block into the goal hole."""

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

        # 3. Title ("STAGE CLEARED!")
        self.txt_title = Text(
            parent=self,
            text=LocalizedStr("STAGE CLEARED!", ["CHIẾN THẮNG!"]),
            font=DEFAULT_FONT_NAME,
            scale=2.3,
            origin=(0, 0),
            position=(0, 0.23, -0.01),
            color=color.hex(PALETTE["brick"]),
        )

        # Gold Stars container
        self.stars_container = Entity(parent=self)
        for offset_x in (-0.05, 0.0, 0.05):
            Entity(
                parent=self.stars_container,
                model="diamond",
                position=(offset_x, 0.165, -0.01),
                scale=(0.026, 0.038, 0.01),
                color=color.hex(PALETTE["butter"]),
            )

        # Stats text
        self.txt_stats = Text(
            parent=self,
            text="Moves: 0  |  Record: 0",
            font=DEFAULT_FONT_NAME,
            scale=1.1,
            origin=(0, 0),
            position=(0, 0.11, -0.01),
            color=color.hex(PALETTE["ink"]),
        )

        # Subtitle badge
        self.txt_message = Text(
            parent=self,
            text="* New Best Record! *",
            font=DEFAULT_FONT_NAME,
            scale=0.9,
            origin=(0, 0),
            position=(0, 0.065, -0.01),
            color=color.hex(PALETTE["green"]),
        )

        # 4. Pixel Buttons
        btn_w, btn_h = 0.42, 0.066
        btn_y_start = 0.005
        btn_spacing = 0.080

        # Button 1: Next Stage (Green ramp)
        self.btn_next = PixelButton(
            parent=self,
            text=LocalizedStr("NEXT STAGE", ["MÀN TIẾP THEO"]),
            color_ramp="green",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start, 0),
            on_click=self._on_next_clicked,
        )

        # Button 2: Replay Stage (Orange ramp)
        self.btn_restart = PixelButton(
            parent=self,
            text=LocalizedStr("REPLAY STAGE", ["CHƠI LẠI MÀN NÀY"]),
            color_ramp="orange",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing, 0),
            on_click=self._on_restart_clicked,
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

    def set_stats(self, moves: int, best_moves: int, is_new_record: bool = False) -> None:
        """Update move statistics and victory badge."""
        self.txt_stats.text = f"Moves: {moves}  |  Record: {best_moves}"
        if is_new_record:
            self.txt_message.text = "* NEW BEST RECORD! *"
            self.txt_message.color = color.hex(PALETTE["butter"])
        else:
            self.txt_message.text = "Stage Completed Successfully!"
            self.txt_message.color = color.hex(PALETTE["green"])

    def _on_next_clicked(self) -> None:
        self.hide()
        if self.on_next_stage:
            self.on_next_stage()

    def _on_restart_clicked(self) -> None:
        self.hide()
        if self.on_restart:
            self.on_restart()

    def _on_select_stage_clicked(self) -> None:
        if self.on_select_stage:
            self.on_select_stage()

    def _on_main_menu_clicked(self) -> None:
        self.hide()
        if self.on_main_menu:
            self.on_main_menu()

    def show(self, stage_name: str = "", moves: int = 0, best_moves: int | None = None, is_new_record: bool = False) -> None:
        best_str = f"Record: {best_moves}" if best_moves is not None else "New Record!"
        stage_prefix = f"{stage_name}  •  " if stage_name else ""
        self.txt_stats.text = f"{stage_prefix}Moves: {moves}  •  {best_str}"
        if is_new_record:
            self.txt_message.text = "* NEW BEST RECORD! *"
            self.txt_message.color = color.hex(PALETTE["butter"])
        else:
            self.txt_message.text = "Stage Completed Successfully!"
            self.txt_message.color = color.hex(PALETTE["green"])
        self.enabled = True

    def hide(self) -> None:
        self.enabled = False
