"""Pixel Art UI Widgets for Bloxorz 3D (Stardew Valley Aesthetic).

Includes:
1. PixelPanel: Parchment modal container with layered wood frame, click-outside/ESC dismissal.
2. PixelButton: Reactive 9-sliced tactile button supporting 4 ramps (Green, Orange, Red, Disabled).
3. PixelTab: Category tab switcher with active/inactive visual states.
4. PixelLevelTile: Stage selector grid card with current, completed, and locked state rendering.
5. PixelCloseButton: Square red pixel art close button ('X').

All widgets:
- Adhere strictly to the 29-color PALETTE.
- Snap positions and dimensions using PIXEL_SCALE = 3.
- Enforce Nearest-Neighbor texture sampling (no mipmaps, no blur).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
from PIL import Image
from ursina import (
    Button,
    Entity,
    Text,
    Texture,
    Vec2,
    Vec3,
    camera,
    color,
    destroy,
    mouse,
)

from game.ursina_ui.assets.theme import (
    PALETTE,
    BUTTON_RAMPS,
    DEFAULT_FONT_NAME,
    DEFAULT_FONT_PATH,
    PIXEL_SCALE,
    px,
    snap,
)
from tools.gen_buttons import (
    generate_button_base_sprite,
    slice_9,
    hex_to_rgba,
    validate_image_palette,
)

# Base directories
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
BUTTONS_DIR = ASSETS_DIR / "ui" / "buttons"

# In-memory texture caches
_BUTTON_TEXTURE_CACHE: dict[tuple[str, str, int, int], Texture] = {}
_PANEL_TEXTURE_CACHE: dict[tuple[int, int], Texture] = {}
_BASE_SPRITE_CACHE: dict[tuple[str, str], Image.Image] = {}


# ==============================================================================
# TEXTURE GENERATION & CACHING HELPERS
# ==============================================================================

def get_base_button_sprite(color_ramp: str, state: str) -> Image.Image:
    """Retrieve or generate 24x24 base button sprite for a given ramp and state."""
    ramp_key = color_ramp.upper()
    state_key = "normal" if state == "idle" else ("selected" if state == "active" else state)
    cache_key = (ramp_key, state_key)

    if cache_key in _BASE_SPRITE_CACHE:
        return _BASE_SPRITE_CACHE[cache_key]

    # Try loading pre-rendered sprite file first
    file_path = BUTTONS_DIR / f"btn_{color_ramp.lower()}_{state_key}.png"
    if file_path.exists():
        with Image.open(file_path) as img:
            sprite = img.copy()
    else:
        ramp = BUTTON_RAMPS.get(ramp_key, BUTTON_RAMPS["ORANGE"])
        sprite = generate_button_base_sprite(ramp, state_key, 24)

    _BASE_SPRITE_CACHE[cache_key] = sprite
    return sprite


def get_pixel_button_texture(
    color_ramp: str,
    state: str,
    width_px: int,
    height_px: int,
) -> Texture:
    """Get or create a 9-sliced nearest-neighbor Ursina Texture for a button."""
    ramp_key = color_ramp.upper()
    state_key = "normal" if state == "idle" else ("selected" if state == "active" else state)

    # Quantize dimensions to PIXEL_SCALE multiples to ensure pixel snapping
    w = max(18, int(round(width_px / PIXEL_SCALE)) * PIXEL_SCALE)
    h = max(18, int(round(height_px / PIXEL_SCALE)) * PIXEL_SCALE)
    cache_key = (ramp_key, state_key, w, h)

    if cache_key in _BUTTON_TEXTURE_CACHE:
        return _BUTTON_TEXTURE_CACHE[cache_key]

    base_sprite = get_base_button_sprite(ramp_key, state_key)
    sliced_img = slice_9(base_sprite, w, h, c=6)
    validate_image_palette(sliced_img, f"btn_{ramp_key}_{state_key}_{w}x{h}")

    tex = Texture(sliced_img)
    tex.filtering = False
    _BUTTON_TEXTURE_CACHE[cache_key] = tex
    return tex


def generate_panel_base_sprite(s: int = 48, c: int = 10) -> Image.Image:
    """Generate base 9-slice sprite for Stardew parchment modal panel."""
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    pix = img.load()
    c_cream = hex_to_rgba(PALETTE["cream"])
    c_brick = hex_to_rgba(PALETTE["brick"])
    c_wood = hex_to_rgba(PALETTE["wood"])
    c_tan = hex_to_rgba(PALETTE["tan"])
    c_ivory = hex_to_rgba(PALETTE["ivory"])

    for y in range(c, s - c):
        for x in range(c, s - c):
            pix[x, y] = c_cream

    # Outer border (brick)
    for x in range(1, s - 1):
        pix[x, 0] = c_brick
        pix[x, s - 1] = c_brick
    for y in range(1, s - 1):
        pix[0, y] = c_brick
        pix[w_edge := s - 1, y] = c_brick

    # Mid frame (wood)
    for x in range(2, s - 2):
        pix[x, 1] = c_wood
        pix[x, s - 2] = c_wood
    for y in range(2, s - 2):
        pix[1, y] = c_wood
        pix[s - 2, y] = c_wood

    # Inner bevel (tan highlight top/left, brick shadow bottom/right)
    for x in range(3, s - 3):
        pix[x, 2] = c_tan
        pix[x, s - 3] = c_brick
    for y in range(3, s - 3):
        pix[2, y] = c_tan
        pix[s - 3, y] = c_brick

    # Inner highlight line (ivory)
    for x in range(4, s - 4):
        pix[x, 3] = c_ivory
        pix[x, s - 4] = c_cream
    for y in range(4, s - 4):
        pix[3, y] = c_ivory
        pix[s - 4, y] = c_cream

    validate_image_palette(img, "panel_base")
    return img


_PANEL_BASE_SPRITE: Image.Image | None = None


def get_pixel_panel_texture(width_px: int, height_px: int) -> Texture:
    """Get or create a 9-sliced parchment panel Texture with layered wood border."""
    global _PANEL_BASE_SPRITE
    if _PANEL_BASE_SPRITE is None:
        _PANEL_BASE_SPRITE = generate_panel_base_sprite(48, 10)

    w = max(32, int(round(width_px / PIXEL_SCALE)) * PIXEL_SCALE)
    h = max(32, int(round(height_px / PIXEL_SCALE)) * PIXEL_SCALE)
    cache_key = (w, h)

    if cache_key in _PANEL_TEXTURE_CACHE:
        return _PANEL_TEXTURE_CACHE[cache_key]

    sliced_panel = slice_9(_PANEL_BASE_SPRITE, w, h, c=10)
    validate_image_palette(sliced_panel, f"panel_{w}x{h}")

    tex = Texture(sliced_panel)
    tex.filtering = False
    _PANEL_TEXTURE_CACHE[cache_key] = tex
    return tex


# ==============================================================================
# 1. PIXEL BUTTON
# ==============================================================================

class PixelButton(Button):
    """Tactile pixel art button using Stardew Valley 4-step color ramps.

    Features:
    - 9-slice textures maintaining 1px border and crisp corner geometry.
    - Automatic state transitions: normal, hover, pressed, selected.
    - 1px physical text depression animation when pressed.
    - Snapped positions and dimensions to PIXEL_SCALE.
    """

    def __init__(
        self,
        text: str = "",
        color_ramp: str = "orange",
        scale: tuple[float, float] | Vec2 = (0.12, 0.05),
        position: tuple[float, float, float] | Vec3 = (0, 0, 0),
        on_click: Callable[[], None] | None = None,
        font: str = DEFAULT_FONT_NAME,
        text_color: color.Color | None = None,
        text_size: float = 1.0,
        disabled: bool = False,
        parent: Entity | None = None,
        **kwargs: Any,
    ) -> None:
        # Pre-calculate pixel dimensions for 9-slice generation
        # Reference height of Ursina UI is 1.0 (864px standard), width is 1.7777 (1536px)
        self.raw_scale = Vec2(scale[0], scale[1]) if isinstance(scale, (tuple, list)) else Vec2(scale)
        self.w_px = max(24, int(round(self.raw_scale.x * 864 * (16 / 9))))
        self.h_px = max(24, int(round(self.raw_scale.y * 864)))

        self._color_ramp = color_ramp.lower()
        self._state = "normal"
        self._is_selected = False
        self._disabled = disabled
        self._custom_text_size = text_size

        # Default text color based on ramp
        if text_color is None:
            text_color = color.hex(PALETTE["ivory"]) if self._color_ramp == "red" else color.hex(PALETTE["ink"])

        # Retrieve normal texture
        current_ramp = "disabled" if self._disabled else self._color_ramp
        tex = get_pixel_button_texture(current_ramp, "normal", self.w_px, self.h_px)

        btn_kwargs = dict(kwargs)
        if on_click is not None:
            btn_kwargs["on_click"] = on_click

        super().__init__(
            parent=parent,
            text=text,
            model="quad",
            texture=tex,
            color=color.white,
            highlight_color=color.white,
            pressed_color=color.white,
            scale=self.raw_scale,
            position=position,
            **btn_kwargs,
        )

        # Configure pixel text
        if hasattr(self, "text_entity") and self.text_entity:
            self.text_entity.font = font
            self.text_entity.color = text_color
            self.text_entity.origin = (0, 0)
            self._fit_text()
            self.text_entity.position = (0, 0, -0.01)

        self._text_offset_y = 0.003  # 1-2px visual depression

    def _fit_text(self) -> None:
        """Scale text entity to safely fit within button boundaries without overflowing."""
        if not hasattr(self, "text_entity") or not self.text_entity:
            return
        t_str = str(getattr(self, "_stored_text", "") or getattr(self.text_entity, "text", "") or "")
        base_size = getattr(self, "_custom_text_size", 1.0)
        lines = t_str.split("\n")
        max_len = max((len(l) for l in lines), default=0)
        if max_len > 0:
            # At world_scale=20, each character width in UI space is ~0.011 to 0.0125
            est_width = max_len * 0.0118 * base_size
            max_allowed = max(0.04, self.raw_scale.x - 0.018)
            if est_width > max_allowed:
                base_size *= (max_allowed / est_width)
        self.text_entity.world_scale = Vec3(20 * base_size)

    @property
    def text(self) -> str:
        if hasattr(self, "_stored_text") and self._stored_text is not None:
            return self._stored_text
        return getattr(self.text_entity, "text", "") if hasattr(self, "text_entity") and self.text_entity else ""

    @text.setter
    def text(self, value: Any) -> None:
        self._stored_text = value
        Button.text.fset(self, value)
        self._fit_text()

    @property
    def color_ramp(self) -> str:
        return self._color_ramp

    @color_ramp.setter
    def color_ramp(self, value: str) -> None:
        self._color_ramp = value.lower()
        self._update_texture()

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    @is_selected.setter
    def is_selected(self, value: bool) -> None:
        self._is_selected = value
        self._state = "selected" if value else "normal"
        self._update_texture()

    @property
    def disabled(self) -> bool:
        return self._disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        self._disabled = value
        self._update_texture()

    def set_state(self, state: str) -> None:
        """Update button visual state ('normal', 'hover', 'pressed', 'selected')."""
        self._state = state
        self._update_texture()

    def _update_texture(self) -> None:
        """Update active texture from current state and ramp."""
        active_ramp = "disabled" if self._disabled else self._color_ramp
        active_state = self._state
        if self._disabled:
            active_state = "normal"
        elif self._is_selected and active_state == "normal":
            active_state = "selected"

        self.texture = get_pixel_button_texture(active_ramp, active_state, self.w_px, self.h_px)

    def on_mouse_enter(self) -> None:
        if self._disabled:
            return
        if not self._is_selected:
            self._state = "hover"
            self._update_texture()

    def on_mouse_exit(self) -> None:
        if self._disabled:
            return
        self._state = "selected" if self._is_selected else "normal"
        self._update_texture()

    def input(self, key: str) -> None:
        if self._disabled:
            return

        if key == "left mouse down" and self.hovered:
            self._state = "pressed"
            self._update_texture()
            if hasattr(self, "text_entity") and self.text_entity:
                self.text_entity.y = -self._text_offset_y

        elif key == "left mouse up":
            if hasattr(self, "text_entity") and self.text_entity:
                self.text_entity.y = 0.0
            if self.hovered and not self._is_selected:
                self._state = "hover"
            else:
                self._state = "selected" if self._is_selected else "normal"
            self._update_texture()

        super().input(key)


# ==============================================================================
# 2. PIXEL CLOSE BUTTON ('X')
# ==============================================================================

class PixelCloseButton(PixelButton):
    """Square red pixel art close button with 'X' label."""

    def __init__(
        self,
        position: tuple[float, float, float] | Vec3 = (0, 0, 0),
        scale: tuple[float, float] | Vec2 = (0.046, 0.046),
        on_click: Callable[[], None] | None = None,
        parent: Entity | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            text="X",
            color_ramp="red",
            scale=scale,
            position=position,
            on_click=on_click,
            parent=parent,
            text_color=color.hex(PALETTE["ivory"]),
            **kwargs,
        )
        if hasattr(self, "text_entity") and self.text_entity:
            self.text_entity.world_scale = Vec3(20)


# ==============================================================================
# 3. PIXEL TAB
# ==============================================================================

class PixelTab(PixelButton):
    """Category tab button supporting active (elevated) and inactive (recessed) states."""

    def __init__(
        self,
        text: str = "",
        tab_id: str = "",
        is_active: bool = False,
        scale: tuple[float, float] | Vec2 = (0.52, 0.054),
        position: tuple[float, float, float] | Vec3 = (0, 0, 0),
        on_click: Callable[[], None] | None = None,
        parent: Entity | None = None,
        **kwargs: Any,
    ) -> None:
        self.tab_id = tab_id
        super().__init__(
            text=text,
            color_ramp="orange" if is_active else "disabled",
            scale=scale,
            position=position,
            on_click=on_click,
            parent=parent,
            **kwargs,
        )
        self.set_active(is_active)

    def set_active(self, active: bool) -> None:
        """Switch active tab state."""
        self.is_selected = active
        if active:
            self.color_ramp = "orange"
            if hasattr(self, "text_entity") and self.text_entity:
                self.text_entity.color = color.hex(PALETTE["ink"])
                self.text_entity.world_scale = Vec3(18)
        else:
            self.color_ramp = "disabled"
            if hasattr(self, "text_entity") and self.text_entity:
                self.text_entity.color = color.hex(PALETTE["ivory"])
                self.text_entity.world_scale = Vec3(18)


# ==============================================================================
# 4. PIXEL LEVEL TILE
# ==============================================================================

class PixelLevelTile(PixelButton):
    """Stage selection grid card displaying stage number, best record, and play status."""

    def __init__(
        self,
        stage_id: str,
        is_current: bool = False,
        is_won: bool = False,
        best_moves: int | None = None,
        ref_len: int | None = None,
        scale: tuple[float, float] | Vec2 = (0.192, 0.092),
        position: tuple[float, float, float] | Vec3 = (0, 0, 0),
        on_click: Callable[[], None] | None = None,
        parent: Entity | None = None,
        **kwargs: Any,
    ) -> None:
        self.stage_id = stage_id
        self.is_current = is_current
        self.is_won = is_won
        self.best_moves = best_moves
        self.ref_len = ref_len

        # Format English labels
        if stage_id.startswith("sample"):
            num_part = stage_id.replace("sample", "").lstrip("0")
            title_str = f"SAMPLE {num_part or '0'}"
        else:
            num_part = stage_id.replace("stage", "")
            title_str = f"STAGE {num_part}"

        if is_current:
            status_str = "PLAYING"
            ramp = "orange"
        elif is_won:
            status_str = f"{best_moves} steps" if best_moves else "CLEARED"
            ramp = "green"
        else:
            status_str = f"{ref_len}b opt" if ref_len else "Unplayed"
            ramp = "disabled"

        full_label = f"{title_str}\n{status_str}"

        super().__init__(
            text=full_label,
            color_ramp=ramp,
            scale=scale,
            position=position,
            on_click=on_click,
            parent=parent,
            **kwargs,
        )

        if hasattr(self, "text_entity") and self.text_entity:
            self.text_entity.world_scale = Vec3(17)
            if is_won:
                self.text_entity.color = color.hex(PALETTE["ivory"])
            elif is_current:
                self.text_entity.color = color.hex(PALETTE["ink"])
            else:
                self.text_entity.color = color.hex(PALETTE["ivory"])


# ==============================================================================
# 5. PIXEL PANEL (MODAL CONTAINER)
# ==============================================================================

class PixelPanel(Entity):
    """Parchment modal container with layered wood frame, click-outside/ESC dismissal."""

    def __init__(
        self,
        scale: tuple[float, float] | Vec2 = (1.20, 0.80),
        position: tuple[float, float, float] | Vec3 = (0, 0, -0.05),
        title: str | None = None,
        subtitle: str | None = None,
        close_button: bool = True,
        on_close: Callable[[], None] | None = None,
        click_outside_to_close: bool = True,
        parent: Entity | None = None,
        **kwargs: Any,
    ) -> None:
        target_parent = parent if parent is not None else camera.ui
        super().__init__(parent=target_parent, z=position[2] if len(position) > 2 else -0.05, **kwargs)

        self.on_close = on_close
        self.modal_scale = Vec2(scale[0], scale[1]) if isinstance(scale, (tuple, list)) else Vec2(scale)

        # 1. Background modal click blocker
        if click_outside_to_close:
            self.blocker = Entity(
                parent=self,
                model="quad",
                scale=(camera.aspect_ratio * 2.2, 2.2),
                z=0.04,
                color=color.rgba(0, 0, 0, 0.45),
                collider="box",
            )
            self.blocker.on_click = self._handle_click_outside

        # 2. Main Parchment Panel Entity
        w_px = max(64, int(round(self.modal_scale.x * 864 * (16 / 9))))
        h_px = max(64, int(round(self.modal_scale.y * 864)))
        panel_texture = get_pixel_panel_texture(w_px, h_px)

        self.panel_body = Entity(
            parent=self,
            model="quad",
            texture=panel_texture,
            color=color.white,
            scale=self.modal_scale,
            position=(0, 0, 0.02),
        )

        # 3. Header Title & Subtitle
        if title:
            self.txt_title = Text(
                parent=self,
                text=title,
                font=DEFAULT_FONT_NAME,
                scale=1.65,
                origin=(0, 0),
                position=(0, self.modal_scale.y / 2 - 0.045, -0.02),
                color=color.hex(PALETTE["ink"]),
            )

        if subtitle:
            self.txt_subtitle = Text(
                parent=self,
                text=subtitle,
                font=DEFAULT_FONT_NAME,
                scale=0.88,
                origin=(0, 0),
                position=(0, self.modal_scale.y / 2 - 0.090, -0.02),
                color=color.hex(PALETTE["brick"]),
            )

        # 4. Close Button (top-right)
        if close_button:
            close_x = self.modal_scale.x / 2 - 0.045
            close_y = self.modal_scale.y / 2 - 0.045
            self.btn_close = PixelCloseButton(
                parent=self,
                position=(close_x, close_y, -0.03),
                scale=(0.046, 0.046),
                on_click=self.close,
            )

        # 5. Content Area for child elements
        self.content_area = Entity(parent=self, position=(0, 0, -0.02), name="content_area")

    def _handle_click_outside(self) -> None:
        """Close modal when clicking the dimmed background outside panel."""
        self.close()

    def close(self) -> None:
        """Trigger on_close callback and destroy modal entity."""
        if self.on_close:
            self.on_close()
        destroy(self)

    def input(self, key: str) -> None:
        if key == "escape":
            self.close()
