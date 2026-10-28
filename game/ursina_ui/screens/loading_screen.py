"""Pixel Art Loading Screen for Bloxorz 3D."""
from __future__ import annotations

from typing import Callable
from ursina import (
    Entity,
    Text,
    Vec2,
    Vec3,
    application,
    camera,
    color,
    destroy,
)

from game.ursina_ui.assets.theme import (
    PALETTE,
    DEFAULT_FONT_NAME,
)
from game.ursina_ui.pixel_widgets import get_pixel_panel_texture


class LoadingScreen(Entity):
    """Clean retro pixel art loading screen shown during startup asset preparation."""

    def __init__(
        self,
        on_complete: Callable[[], None] | None = None,
        duration: float = 0.65,
    ) -> None:
        super().__init__(parent=camera.ui, name="loading_screen", z=-20)
        self.on_complete = on_complete
        self.duration = duration
        self.elapsed = 0.0
        self._finished = False

        c_navy = color.hex(PALETTE["navy_1"])
        self.bg_overlay = Entity(
            parent=self,
            model="quad",
            scale=(2.5, 2.5),
            color=color.rgba(c_navy.r, c_navy.g, c_navy.b, 0.96),
            z=0.05,
        )

        # Center parchment panel
        panel_w = 0.54
        panel_h = 0.32
        w_px = max(64, int(round(panel_w * 864 * (16 / 9))))
        h_px = max(64, int(round(panel_h * 864)))
        self.panel = Entity(
            parent=self,
            model="quad",
            scale=(panel_w, panel_h),
            texture=get_pixel_panel_texture(w_px, h_px),
            color=color.white,
            z=0.02,
        )

        self.txt_title = Text(
            parent=self,
            text="BLOXORZ 3D",
            font=DEFAULT_FONT_NAME,
            scale=1.8,
            origin=(0, 0),
            position=(0, 0.08, -0.01),
            color=color.hex(PALETTE["ink"]),
        )

        self.txt_status = Text(
            parent=self,
            text="Preparing stages and assets...",
            font=DEFAULT_FONT_NAME,
            scale=0.9,
            origin=(0, 0),
            position=(0, 0.02, -0.01),
            color=color.hex(PALETTE["brick"]),
        )

        # Progress bar frame
        self.bar_bg = Entity(
            parent=self,
            model="quad",
            scale=(0.38, 0.028),
            position=(0, -0.05, -0.01),
            color=color.hex(PALETTE["slate"]),
        )

        # Progress bar fill
        self.bar_fill = Entity(
            parent=self,
            model="quad",
            scale=(0.001, 0.022),
            position=(-0.188, -0.05, -0.02),
            origin=(-0.5, 0),
            color=color.hex(PALETTE["green"]),
        )

        # In headless mode or test environments, finish immediately
        if getattr(application, "headless", False):
            self.finish()

    def update(self) -> None:
        if self._finished:
            return
        from ursina import time
        self.elapsed += getattr(time, "dt", 0.016)
        progress = min(1.0, self.elapsed / max(0.001, self.duration))

        # Smoothly advance progress bar
        self.bar_fill.scale_x = max(0.001, 0.374 * progress)

        if progress >= 1.0:
            self.finish()

    def finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        cb = self.on_complete
        destroy(self)
        if cb:
            cb()
