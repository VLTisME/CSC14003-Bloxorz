"""Main Menu Screen for Bloxorz 3D (Stardew Valley Pixel Art Aesthetic)."""
from __future__ import annotations

from pathlib import Path
from typing import Callable
from ursina import (
    Entity,
    Text,
    Texture,
    Vec2,
    camera,
    color,
    load_texture,
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

LOGO_DIR = Path(__file__).resolve().parent.parent / "assets" / "ui" / "logo"


class MainMenuScreen(Entity):
    """Main start menu screen for Bloxorz 3D with authentic pixel art styling."""

    def __init__(
        self,
        on_play: Callable[[], None],
        on_select_stage: Callable[[], None],
        on_help: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        super().__init__(parent=camera.ui, name="main_menu_screen", enabled=False)

        self.on_play = on_play
        self.on_select_stage = on_select_stage
        self.on_help = on_help
        self.on_quit = on_quit

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
        panel_w = 0.62
        panel_h = 0.74
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

        # 3. Logo Title ("BLOXORZ") & Subtitle ("3D PUZZLE")
        title_tex_path = LOGO_DIR / "logo_title.png"
        sub_tex_path = LOGO_DIR / "logo_sub.png"

        title_tex = Texture(title_tex_path) if title_tex_path.exists() else None
        if title_tex:
            title_tex.filtering = False
            aspect = title_tex.width / max(1, title_tex.height)
            title_h = 0.088
            title_w = title_h * aspect
            self.txt_title = Entity(
                parent=self,
                model="quad",
                texture=title_tex,
                color=color.white,
                scale=(title_w, title_h),
                position=(0, 0.23, -0.01),
            )
        else:
            self.txt_title = Text(
                parent=self,
                text="BLOXORZ",
                font=DEFAULT_FONT_NAME,
                scale=2.4,
                origin=(0, 0),
                position=(0, 0.23, -0.01),
                color=color.hex(PALETTE["ink"]),
            )

        sub_tex = Texture(sub_tex_path) if sub_tex_path.exists() else None
        if sub_tex:
            sub_tex.filtering = False
            aspect = sub_tex.width / max(1, sub_tex.height)
            sub_h = 0.038
            sub_w = sub_h * aspect
            self.txt_subtitle = Entity(
                parent=self,
                model="quad",
                texture=sub_tex,
                color=color.white,
                scale=(sub_w, sub_h),
                position=(0, 0.155, -0.01),
            )
        else:
            self.txt_subtitle = Text(
                parent=self,
                text="3D PUZZLE",
                font=DEFAULT_FONT_NAME,
                scale=1.0,
                origin=(0, 0),
                position=(0, 0.155, -0.01),
                color=color.hex(PALETTE["brick"]),
            )

        # Decorative divider line in brick/tan
        self.divider = Entity(
            parent=self,
            model="quad",
            scale=(0.46, 0.004),
            position=(0, 0.115, -0.01),
            color=color.hex(PALETTE["brick"]),
        )

        # 4. Pixel Navigation Buttons
        btn_w, btn_h = 0.42, 0.068
        btn_y_start = 0.045
        btn_spacing = 0.082

        # Button 1: Play Now (Green ramp)
        self.btn_play = PixelButton(
            parent=self,
            text=LocalizedStr("PLAY NOW", ["CHƠI NGAY"]),
            color_ramp="green",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start, 0),
            on_click=self._on_play_clicked,
        )

        # Button 2: Select Stage (Orange ramp)
        self.btn_stages = PixelButton(
            parent=self,
            text=LocalizedStr("STAGE SELECT", ["CHỌN MÀN CHƠI"]),
            color_ramp="orange",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing, 0),
            on_click=self._on_select_stage_clicked,
        )

        # Button 3: How to Play (Orange ramp)
        self.btn_help = PixelButton(
            parent=self,
            text=LocalizedStr("HOW TO PLAY", ["HƯỚNG DẪN & PHÍM TẮT"]),
            color_ramp="orange",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing * 2, 0),
            on_click=self._on_help_clicked,
        )

        # Button 4: Quit (Red ramp)
        self.btn_quit = PixelButton(
            parent=self,
            text=LocalizedStr("QUIT GAME", ["THOÁT TRÒ CHƠI"]),
            color_ramp="red",
            scale=(btn_w, btn_h),
            position=(0, btn_y_start - btn_spacing * 3, 0),
            on_click=self._on_quit_clicked,
        )

        # Footer version label
        self.txt_version = Text(
            parent=self,
            text="v2.0 • AI Foundations • Bloxorz 3D",
            font=DEFAULT_FONT_NAME,
            scale=0.75,
            origin=(0, 0),
            position=(0, -0.315, -0.01),
            color=color.hex(PALETTE["brick"]),
        )

    def _on_play_clicked(self) -> None:
        self.hide()
        if self.on_play:
            self.on_play()

    def _on_select_stage_clicked(self) -> None:
        if self.on_select_stage:
            self.on_select_stage()

    def _on_help_clicked(self) -> None:
        if self.on_help:
            self.on_help()

    def _on_quit_clicked(self) -> None:
        if self.on_quit:
            self.on_quit()

    def show(self) -> None:
        self.enabled = True

    def hide(self) -> None:
        self.enabled = False
