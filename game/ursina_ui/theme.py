"""Stardew Valley Inspired Cozy Pixel-Art Theme for Bloxorz 3D.

Central design system providing:
- Authentic warm, earthy, slightly desaturated Stardew Valley color palette
- Procedural pixel-art texture generation (Pillow) with nearest-neighbor filtering
- In-memory texture caching (_PIXEL_TEXTURE_CACHE) ensuring 0 per-frame overhead
- UI styling tokens for parchment boxes, carved wood frames, buttons, and typography
"""
from __future__ import annotations

import math
from pathlib import Path
import random
from typing import Any
from PIL import Image, ImageDraw
from ursina import Texture, color

# ==============================================================================
# 1. STARDEW VALLEY PALETTE CONSTANTS
# ==============================================================================

# Nature & Meadow
GRASS_BASE = "#5C9C3E"
GRASS_LIGHT = "#78B854"
GRASS_DARK = "#42762B"
GRASS_LIP = "#4E8A3A"
DIRT_BASE = "#7A4A28"
DIRT_DARK = "#503018"
DIRT_LIGHT = "#9C6236"
FLOWER_COLORS = ["#F4E242", "#EA7272", "#FFFFFF", "#70A0D0"]

# Handcrafted Farm Timber & Crate
WOOD_BASE = "#9E6438"
WOOD_LIGHT = "#BA7D4C"
WOOD_DARK = "#663C1C"
WOOD_BORDER = "#40240E"
WOOD_NAIL = "#241408"
WOOD_BRACKET = "#52341A"

# Split Blocks (Warm Pine & Cherry Redwood)
SPLIT_CUBE1_BASE = "#B87432"
SPLIT_CUBE1_LIGHT = "#D48E4A"
SPLIT_CUBE1_DARK = "#804A1A"
SPLIT_CUBE1_ACCENT = "#2E8B57"  # Forest green trim

SPLIT_CUBE2_BASE = "#9C4228"
SPLIT_CUBE2_LIGHT = "#B85C40"
SPLIT_CUBE2_DARK = "#6E2A16"
SPLIT_CUBE2_ACCENT = "#3A72A4"  # Mountain blue trim

# Fragile & Bridges
FRAGILE_PLANK = "#8A6546"
FRAGILE_LIGHT = "#A67F5D"
FRAGILE_DARK = "#5C3E28"
FRAGILE_CRACK = "#2E1C10"

BRIDGE_WOOD = "#A06838"
BRIDGE_LIGHT = "#BC824E"
BRIDGE_DARK = "#6E3E1A"
BRIDGE_INACTIVE = "#3E2210"

# Goal Well & Golden Star
GOAL_STONE_RIM = "#6E727A"
GOAL_STONE_DARK = "#4A4D54"
GOAL_STONE_LIGHT = "#8C9098"
GOAL_STONE_MOSS = "#4E7836"
GOAL_PIT_DEEP = "#221A10"
GOAL_STAR = "#F4C430"
GOAL_STAR_LIGHT = "#FFF080"
GOAL_STAR_DARK = "#C49010"

# Switches & Splitters
SWITCH_WOOD_BASE = "#8A562E"
SWITCH_WOOD_BTN = "#D48038"
SWITCH_WOOD_HL = "#F0A858"
SWITCH_WOOD_BORDER = "#482A12"

SWITCH_STONE_BASE = "#666A72"
SWITCH_STONE_RUNE = "#B84030"
SWITCH_STONE_BORDER = "#383A40"

SPLITTER_BASE = "#72767E"
SPLITTER_ACCENT = "#D48038"
SPLITTER_BORDER = "#3A3C42"

# Sky & Atmosphere
SKY_TOP = "#74A4C8"
SKY_MID = "#98C8E2"
SKY_HORIZON = "#F0F4DC"
SKY_HAZE = "#D4EAC0"
CLOUD_WHITE = "#FFFFFF"
CLOUD_SHADOW = "#DCE4EC"

# Stardew Parchment & Dialogue Box UI
PARCHMENT_BG = "#F5E6C8"
PARCHMENT_LIGHT = "#FAF1DE"
PARCHMENT_SHADOW = "#E0CCA4"
PARCHMENT_INSET = "#D4B982"

FRAME_DARK = "#381E0C"
FRAME_BEZEL = "#5C3A1E"
FRAME_LIGHT = "#8B5A2B"
FRAME_CORNER = "#2E180A"

BTN_WOOD_BASE = "#D49A50"
BTN_WOOD_LIGHT = "#E8B870"
BTN_WOOD_SHADOW = "#9C6A28"
BTN_WOOD_BORDER = "#5C3A1E"

BTN_HOVER = "#E8B870"
BTN_PRESSED = "#A87030"

TEXT_DARK = "#3B2314"
TEXT_MUTED = "#6B492B"
TEXT_GOLD = "#C47B14"
TEXT_SHADOW = "#FFF2DC"

# Solver Dynamic Colors (Keeping exact state semantics)
SOLVER_IDLE = "#C47B14"       # Warm Oak Amber
SOLVER_RUNNING = "#D96E20"    # Autumn Pumpkin
SOLVER_PAUSED = "#4E8A3A"     # Farm Green
SOLVER_COMPLETED = "#3A8A6E"  # Harvest Teal
SOLVER_ERROR = "#A83226"      # Barnyard Red

# Font configuration
FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
UI_FONT = "BeVietnamPro-Bold.ttf"

# ==============================================================================
# 2. HELPER FUNCTIONS
# ==============================================================================

def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Convert hex string '#RRGGBB' to tuple (r, g, b)."""
    s = hex_str.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    val = int(s, 16)
    return ((val >> 16) & 255, (val >> 8) & 255, val & 255)


def hex_to_rgba(hex_str: str, alpha: int = 255) -> tuple[int, int, int, int]:
    """Convert hex string with alpha to tuple (r, g, b, a)."""
    r, g, b = hex_to_rgb(hex_str)
    return (r, g, b, alpha)


def hex_to_ursina_color(hex_str: str, alpha: float = 1.0) -> color.Color:
    """Convert hex string to Ursina color.Color."""
    c = color.hex(hex_str)
    return color.Color(c[0], c[1], c[2], float(alpha))


def blend_rgb(c1: tuple[int, int, int], c2: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Linearly blend two RGB colors without alpha transparency."""
    f = max(0.0, min(1.0, factor))
    return (
        int(c1[0] * (1.0 - f) + c2[0] * f),
        int(c1[1] * (1.0 - f) + c2[1] * f),
        int(c1[2] * (1.0 - f) + c2[2] * f),
    )


# Texture cache to ensure each procedural pixel texture is generated only once
_PIXEL_TEXTURE_CACHE: dict[str, Texture] = {}


def _create_and_cache(key: str, img: Image.Image) -> Texture:
    tex = Texture(img)
    tex.filtering = False
    _PIXEL_TEXTURE_CACHE[key] = tex
    return tex


# ==============================================================================
# 3. PROCEDURAL PIXEL-ART TEXTURE GENERATORS
# ==============================================================================

def get_grass_tile_texture(is_alt: bool = False, size: int = 32) -> Texture:
    """Generate crisp Stardew Valley meadow grass texture with dirt-lip bevel."""
    key = f"stardew_grass_{is_alt}_{size}"
    if key in _PIXEL_TEXTURE_CACHE:
        return _PIXEL_TEXTURE_CACHE[key]

    rng = random.Random(1337 if not is_alt else 4242)
    base_rgb = hex_to_rgb(GRASS_BASE)
    light_rgb = hex_to_rgb(GRASS_LIGHT)
    dark_rgb = hex_to_rgb(GRASS_DARK)

    img = Image.new("RGB", (size, size), base_rgb)
    pixels = img.load()
    assert pixels is not None

    # Base stippling for natural meadow texture
    for y in range(size):
        for x in range(size):
            r = rng.random()
            if r < 0.22:
                pixels[x, y] = light_rgb
            elif r < 0.38:
                pixels[x, y] = dark_rgb

    # Tiny grass blade tufts
    num_tufts = size // 5
    for _ in range(num_tufts):
        tx = rng.randint(2, size - 4)
        ty = rng.randint(2, size - 4)
        pixels[tx, ty] = light_rgb
        pixels[tx, ty - 1] = light_rgb
        pixels[tx + 1, ty] = dark_rgb

    # Occasional tiny 1-pixel meadow flowers (yellow, pink, white)
    num_flowers = 3 if is_alt else 2
    for _ in range(num_flowers):
        fx = rng.randint(3, size - 4)
        fy = rng.randint(3, size - 4)
        flower_col = hex_to_rgb(rng.choice(FLOWER_COLORS))
        pixels[fx, fy] = flower_col
        pixels[fx, fy + 1] = dark_rgb

    # Outer 1-pixel dark grass edge rim
    draw = ImageDraw.Draw(img)
    edge_rgb = blend_rgb(base_rgb, dark_rgb, 0.7)
    draw.rectangle([(0, 0), (size - 1, size - 1)], outline=edge_rgb, width=1)

    return _create_and_cache(key, img)


def get_fragile_wood_texture(size: int = 32) -> Texture:
    """Generate cracked weathered cedar planks texture for fragile tiles."""
    key = f"stardew_fragile_{size}"
    if key in _PIXEL_TEXTURE_CACHE:
        return _PIXEL_TEXTURE_CACHE[key]

    base_rgb = hex_to_rgb(FRAGILE_PLANK)
    light_rgb = hex_to_rgb(FRAGILE_LIGHT)
    dark_rgb = hex_to_rgb(FRAGILE_DARK)
    crack_rgb = hex_to_rgb(FRAGILE_CRACK)

    img = Image.new("RGB", (size, size), base_rgb)
    draw = ImageDraw.Draw(img)

    # 4 distinct horizontal wooden planks
    plank_h = size // 4
    for p in range(4):
        py = p * plank_h
        draw.line([(0, py), (size - 1, py)], fill=dark_rgb, width=1)
        draw.line([(0, py + 1), (size - 1, py + 1)], fill=light_rgb, width=1)

    # Weathered grain and prominent jagged cracks
    cracks = [
        [(size // 4, 3), (size // 3, size // 2), (size // 2, size - 4)],
        [(size * 3 // 4, 4), (size * 2 // 3, size // 3), (size * 3 // 4, size * 3 // 4)],
        [(size // 2, size // 2), (size * 3 // 4, size * 2 // 3)],
    ]
    for c in cracks:
        draw.line(c, fill=crack_rgb, width=2)

    # Outer plank outline
    draw.rectangle([(0, 0), (size - 1, size - 1)], outline=dark_rgb, width=1)
    return _create_and_cache(key, img)


def get_bridge_wood_texture(is_active: bool = True, size: int = 32) -> Texture:
    """Generate rustic suspension bridge wooden planks texture."""
    key = f"stardew_bridge_{is_active}_{size}"
    if key in _PIXEL_TEXTURE_CACHE:
        return _PIXEL_TEXTURE_CACHE[key]

    base_rgb = hex_to_rgb(BRIDGE_WOOD if is_active else BRIDGE_INACTIVE)
    light_rgb = hex_to_rgb(BRIDGE_LIGHT if is_active else DIRT_DARK)
    dark_rgb = hex_to_rgb(BRIDGE_DARK if is_active else FRAME_DARK)

    img = Image.new("RGB", (size, size), base_rgb)
    draw = ImageDraw.Draw(img)

    # Vertical bridge planks with nail studs on borders
    num_planks = 4
    pw = size // num_planks
    for i in range(num_planks):
        x = i * pw
        draw.line([(x, 0), (x, size - 1)], fill=dark_rgb, width=1)
        draw.line([(x + 1, 0), (x + 1, size - 1)], fill=light_rgb, width=1)
        # 1-pixel nail rivets top and bottom
        if is_active:
            draw.point((x + pw // 2, 2), fill=dark_rgb)
            draw.point((x + pw // 2, size - 3), fill=dark_rgb)

    draw.rectangle([(0, 0), (size - 1, size - 1)], outline=dark_rgb, width=1)
    return _create_and_cache(key, img)


def get_goal_well_texture(size: int = 32) -> Texture:
    """Generate cobblestone well rim with dark center opening."""
    key = f"stardew_goal_well_{size}"
    if key in _PIXEL_TEXTURE_CACHE:
        return _PIXEL_TEXTURE_CACHE[key]

    img = Image.new("RGB", (size, size), hex_to_rgb(GOAL_STONE_RIM))
    draw = ImageDraw.Draw(img)

    dark_stone = hex_to_rgb(GOAL_STONE_DARK)
    light_stone = hex_to_rgb(GOAL_STONE_LIGHT)
    moss = hex_to_rgb(GOAL_STONE_MOSS)
    pit = hex_to_rgb(GOAL_PIT_DEEP)

    # Cobblestone pattern around the perimeter
    rim = size // 5
    for y in range(0, size, 4):
        for x in range(0, size, 4):
            if x < rim or x >= size - rim or y < rim or y >= size - rim:
                draw.rectangle([(x, y), (x + 3, y + 3)], outline=dark_stone)
                if (x + y) % 7 == 0:
                    draw.point((x + 1, y + 1), fill=moss)
                else:
                    draw.point((x + 1, y + 1), fill=light_stone)

    # Deep well pit in the middle
    draw.rectangle([(rim, rim), (size - 1 - rim, size - 1 - rim)], fill=pit)
    draw.rectangle([(rim, rim), (size - 1 - rim, size - 1 - rim)], outline=dark_stone, width=1)

    return _create_and_cache(key, img)


def get_soft_switch_wood_texture(size: int = 32) -> Texture:
    """Generate carved round wooden pressure plate."""
    key = f"stardew_sw_soft_{size}"
    if key in _PIXEL_TEXTURE_CACHE:
        return _PIXEL_TEXTURE_CACHE[key]

    img = Image.new("RGB", (size, size), hex_to_rgb(GRASS_BASE))
    draw = ImageDraw.Draw(img)

    border_rgb = hex_to_rgb(SWITCH_WOOD_BORDER)
    base_rgb = hex_to_rgb(SWITCH_WOOD_BASE)
    btn_rgb = hex_to_rgb(SWITCH_WOOD_BTN)
    hl_rgb = hex_to_rgb(SWITCH_WOOD_HL)

    pad = size // 6
    # Wooden pressure ring
    draw.ellipse([pad - 1, pad - 1, size - pad, size - pad], fill=border_rgb)
    draw.ellipse([pad, pad, size - 1 - pad, size - 1 - pad], fill=base_rgb)
    # Raised center button
    inner_pad = pad + 3
    draw.ellipse([inner_pad, inner_pad, size - 1 - inner_pad, size - 1 - inner_pad], fill=btn_rgb)
    # Top-left highlight pixel curve
    draw.arc([inner_pad, inner_pad, size - 1 - inner_pad, size - 1 - inner_pad], 180, 270, fill=hl_rgb, width=1)

    return _create_and_cache(key, img)


def get_hard_switch_stone_texture(size: int = 32) -> Texture:
    """Generate heavy carved stone rune plate."""
    key = f"stardew_sw_hard_{size}"
    if key in _PIXEL_TEXTURE_CACHE:
        return _PIXEL_TEXTURE_CACHE[key]

    img = Image.new("RGB", (size, size), hex_to_rgb(GRASS_BASE))
    draw = ImageDraw.Draw(img)

    border_rgb = hex_to_rgb(SWITCH_STONE_BORDER)
    base_rgb = hex_to_rgb(SWITCH_STONE_BASE)
    rune_rgb = hex_to_rgb(SWITCH_STONE_RUNE)
    hl_rgb = blend_rgb(base_rgb, (255, 255, 255), 0.25)

    pad = size // 6
    draw.rectangle([(pad - 1, pad - 1), (size - pad, size - pad)], fill=border_rgb)
    draw.rectangle([(pad, pad), (size - 1 - pad, size - 1 - pad)], fill=base_rgb)
    draw.line([(pad, pad), (size - 1 - pad, pad)], fill=hl_rgb, width=1)

    # Carved cross rune in the center
    cx, cy = size // 2, size // 2
    arm = size // 4
    w = max(2, size // 10)
    draw.rectangle([(cx - w // 2, cy - arm), (cx + w // 2, cy + arm)], fill=rune_rgb)
    draw.rectangle([(cx - arm, cy - w // 2), (cx + arm, cy + w // 2)], fill=rune_rgb)

    return _create_and_cache(key, img)


def get_splitter_stone_texture(size: int = 32) -> Texture:
    """Generate twin stepped plates splitter texture."""
    key = f"stardew_splitter_{size}"
    if key in _PIXEL_TEXTURE_CACHE:
        return _PIXEL_TEXTURE_CACHE[key]

    img = Image.new("RGB", (size, size), hex_to_rgb(GRASS_BASE))
    draw = ImageDraw.Draw(img)

    base_rgb = hex_to_rgb(SPLITTER_BASE)
    border_rgb = hex_to_rgb(SPLITTER_BORDER)
    accent_rgb = hex_to_rgb(SPLITTER_ACCENT)

    pad = 3
    mid = size // 2
    # Two separated wooden/stone slabs
    draw.rectangle([(pad, pad), (mid - 2, size - 1 - pad)], fill=base_rgb, outline=border_rgb)
    draw.rectangle([(mid + 1, pad), (size - 1 - pad, size - 1 - pad)], fill=base_rgb, outline=border_rgb)

    # Accent rune dots on each slab
    draw.rectangle([(pad + 3, mid - 2), (mid - 5, mid + 2)], fill=accent_rgb)
    draw.rectangle([(mid + 4, mid - 2), (size - 1 - pad - 3, mid + 2)], fill=accent_rgb)

    return _create_and_cache(key, img)


def get_crate_block_texture(cube_index: int = 0, is_active: bool = True, size: int = 32) -> Texture:
    """Generate Stardew Valley timber crate block texture with corner brackets and iron nails."""
    key = f"stardew_crate_{cube_index}_{is_active}_{size}"
    if key in _PIXEL_TEXTURE_CACHE:
        return _PIXEL_TEXTURE_CACHE[key]

    if cube_index == 1:
        base_hex = SPLIT_CUBE1_BASE if is_active else SPLIT_CUBE1_DARK
        light_hex = SPLIT_CUBE1_LIGHT if is_active else SPLIT_CUBE1_BASE
        dark_hex = SPLIT_CUBE1_DARK
        bracket_hex = SPLIT_CUBE1_ACCENT
    elif cube_index == 2:
        base_hex = SPLIT_CUBE2_BASE if is_active else SPLIT_CUBE2_DARK
        light_hex = SPLIT_CUBE2_LIGHT if is_active else SPLIT_CUBE2_BASE
        dark_hex = SPLIT_CUBE2_DARK
        bracket_hex = SPLIT_CUBE2_ACCENT
    else:
        base_hex = WOOD_BASE
        light_hex = WOOD_LIGHT
        dark_hex = WOOD_DARK
        bracket_hex = WOOD_BRACKET

    base_rgb = hex_to_rgb(base_hex)
    light_rgb = hex_to_rgb(light_hex)
    dark_rgb = hex_to_rgb(dark_hex)
    border_rgb = hex_to_rgb(WOOD_BORDER)
    bracket_rgb = hex_to_rgb(bracket_hex)
    nail_rgb = hex_to_rgb(WOOD_NAIL)

    img = Image.new("RGB", (size, size), base_rgb)
    draw = ImageDraw.Draw(img)

    # Horizontal wooden plank seams
    plank_h = size // 3
    for p in range(1, 3):
        y = p * plank_h
        draw.line([(0, y), (size - 1, y)], fill=dark_rgb, width=1)
        draw.line([(0, y + 1), (size - 1, y + 1)], fill=light_rgb, width=1)

    # Outer dark timber bevel
    draw.rectangle([(0, 0), (size - 1, size - 1)], outline=border_rgb, width=1)
    draw.line([(1, 1), (size - 2, 1)], fill=light_rgb, width=1)
    draw.line([(1, 1), (1, size - 2)], fill=light_rgb, width=1)

    # 4 Iron corner reinforcement brackets with center nail stud
    corner_size = max(4, size // 6)
    corners = [
        (0, 0, corner_size, corner_size),
        (size - corner_size, 0, size - 1, corner_size),
        (0, size - corner_size, corner_size, size - 1),
        (size - corner_size, size - corner_size, size - 1, size - 1),
    ]
    for c in corners:
        draw.rectangle([(c[0], c[1]), (c[2], c[3])], fill=bracket_rgb, outline=border_rgb)
        # Nail in the middle of each corner
        nx = (c[0] + c[2]) // 2
        ny = (c[1] + c[3]) // 2
        draw.point((nx, ny), fill=nail_rgb)

    return _create_and_cache(key, img)


def get_stardew_sky_texture(width: int = 64, height: int = 64) -> Texture:
    """Generate 4-band flat retro pixel meadow sky with drifting clouds."""
    key = f"stardew_sky_{width}_{height}"
    if key in _PIXEL_TEXTURE_CACHE:
        return _PIXEL_TEXTURE_CACHE[key]

    img = Image.new("RGB", (width, height), hex_to_rgb(SKY_TOP))
    draw = ImageDraw.Draw(img)

    # 4 clean bands (no gradient blur)
    band_h = height // 4
    bands = [
        (0, hex_to_rgb(SKY_TOP)),
        (band_h, hex_to_rgb(SKY_MID)),
        (band_h * 2, hex_to_rgb(SKY_HORIZON)),
        (band_h * 3, hex_to_rgb(SKY_HAZE)),
    ]
    for i, (y_start, col) in enumerate(bands):
        y_end = height if i == len(bands) - 1 else bands[i + 1][0]
        draw.rectangle([(0, y_start), (width - 1, y_end)], fill=col)

    # Procedural pixel cloud shapes on upper bands
    cloud_col = hex_to_rgb(CLOUD_WHITE)
    cloud_shadow = hex_to_rgb(CLOUD_SHADOW)
    cloud_stamps = [
        (8, 10, 16, 6),
        (38, 14, 20, 7),
        (22, 22, 14, 5),
    ]
    for cx, cy, cw, ch in cloud_stamps:
        draw.ellipse([(cx, cy), (cx + cw, cy + ch)], fill=cloud_shadow)
        draw.ellipse([(cx, cy - 1), (cx + cw - 1, cy + ch - 2)], fill=cloud_col)

    return _create_and_cache(key, img)


def get_parchment_panel_texture(width: int = 64, height: int = 64) -> Texture:
    """Generate Stardew Valley menu dialogue box texture with dark wood border and parchment center."""
    key = f"stardew_parchment_{width}_{height}"
    if key in _PIXEL_TEXTURE_CACHE:
        return _PIXEL_TEXTURE_CACHE[key]

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    f_dark = hex_to_rgba(FRAME_DARK)
    f_bezel = hex_to_rgba(FRAME_BEZEL)
    f_light = hex_to_rgba(FRAME_LIGHT)
    f_inset = hex_to_rgba(PARCHMENT_INSET)
    p_bg = hex_to_rgba(PARCHMENT_BG)
    p_light = hex_to_rgba(PARCHMENT_LIGHT)

    # Outer dark wood outline with stepped corners (pixel-bracket corner feel)
    draw.rectangle([(2, 0), (width - 3, height - 1)], fill=f_dark)
    draw.rectangle([(0, 2), (width - 1, height - 3)], fill=f_dark)

    # Warm wood frame bezel
    draw.rectangle([(3, 1), (width - 4, height - 2)], fill=f_bezel)
    draw.rectangle([(1, 3), (width - 2, height - 4)], fill=f_bezel)

    # Top & Left wood highlight
    draw.line([(3, 2), (width - 4, 2)], fill=f_light, width=1)
    draw.line([(2, 3), (2, height - 4)], fill=f_light, width=1)

    # Inset ridge
    draw.rectangle([(4, 4), (width - 5, height - 5)], fill=f_inset)

    # Parchment body
    draw.rectangle([(5, 5), (width - 6, height - 6)], fill=p_bg)
    draw.line([(5, 5), (width - 6, 5)], fill=p_light, width=1)
    draw.line([(5, 5), (5, height - 6)], fill=p_light, width=1)

    return _create_and_cache(key, img)


def get_wooden_button_texture(width: int = 64, height: int = 32, state: str = "normal") -> Texture:
    """Generate carved wooden item/button texture for normal, hover, pressed states."""
    key = f"stardew_btn_{width}_{height}_{state}"
    if key in _PIXEL_TEXTURE_CACHE:
        return _PIXEL_TEXTURE_CACHE[key]

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    border_rgb = hex_to_rgba(BTN_WOOD_BORDER)
    if state == "hover":
        fill_rgb = hex_to_rgba(BTN_HOVER)
        top_hl = hex_to_rgba("#FFF0A0")
        bot_sh = hex_to_rgba(BTN_WOOD_BASE)
    elif state == "pressed":
        fill_rgb = hex_to_rgba(BTN_PRESSED)
        top_hl = hex_to_rgba(BTN_WOOD_SHADOW)
        bot_sh = hex_to_rgba(BTN_WOOD_LIGHT)
    else:
        fill_rgb = hex_to_rgba(BTN_WOOD_BASE)
        top_hl = hex_to_rgba(BTN_WOOD_LIGHT)
        bot_sh = hex_to_rgba(BTN_WOOD_SHADOW)

    # Stepped rounded pixel corners
    draw.rectangle([(1, 0), (width - 2, height - 1)], fill=border_rgb)
    draw.rectangle([(0, 1), (width - 1, height - 2)], fill=border_rgb)

    # Fill
    draw.rectangle([(1, 1), (width - 2, height - 2)], fill=fill_rgb)

    # Bevel lines
    draw.line([(2, 1), (width - 3, 1)], fill=top_hl, width=1)
    draw.line([(1, 2), (1, height - 3)], fill=top_hl, width=1)
    draw.line([(2, height - 2), (width - 3, height - 2)], fill=bot_sh, width=1)
    draw.line([(width - 2, 2), (width - 2, height - 3)], fill=bot_sh, width=1)

    return _create_and_cache(key, img)


def get_blob_shadow_texture(size: int = 32) -> Texture:
    """Generate subtle pixel-quantized soft shadow for cozy lighting."""
    key = f"stardew_shadow_{size}"
    if key in _PIXEL_TEXTURE_CACHE:
        return _PIXEL_TEXTURE_CACHE[key]

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size / 2.0, size / 2.0
    # Gentle warm dirt shadow
    shadow_col = hex_to_rgb(DIRT_DARK)
    steps = 4
    for i in range(steps, 0, -1):
        r = (size * 0.44) * (i / float(steps))
        alpha = int(140 * (1.0 - (i / float(steps)) ** 1.5))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(shadow_col[0], shadow_col[1], shadow_col[2], alpha))

    return _create_and_cache(key, img)


# ==============================================================================
# 4. BACKWARD COMPATIBILITY ADAPTERS
# ==============================================================================

def get_theme(theme_name: str = "toy") -> dict[str, Any]:
    """Provide structured compatibility dictionary matching the Stardew Valley theme."""
    return {
        "name": "Stardew Valley Meadow (Cozy Pixel Art)",
        "bg_top": SKY_TOP,
        "bg_bottom": SKY_HAZE,
        "bg_glow": SKY_MID,
        "panel_bg": PARCHMENT_BG,
        "text_primary": TEXT_DARK,
        "text_secondary": TEXT_MUTED,
        "regular": {
            "top": GRASS_BASE,
            "top_alt": GRASS_LIGHT,
            "outline": GRASS_DARK,
        },
        "start": {
            "top": GRASS_LIGHT,
            "outline": GRASS_DARK,
        },
        "fragile": {
            "top": FRAGILE_PLANK,
            "crack": FRAGILE_CRACK,
            "outline": FRAGILE_DARK,
        },
        "bridge_active": {
            "top": BRIDGE_WOOD,
            "outline": BRIDGE_DARK,
        },
        "bridge_inactive": {
            "top": BRIDGE_INACTIVE,
            "outline": FRAME_DARK,
        },
        "switch_soft": {
            "top": SWITCH_WOOD_BASE,
            "circle": SWITCH_WOOD_BTN,
            "outline": SWITCH_WOOD_BORDER,
        },
        "switch_hard": {
            "top": SWITCH_STONE_BASE,
            "cross": SWITCH_STONE_RUNE,
            "outline": SWITCH_STONE_BORDER,
        },
        "splitter": {
            "top": SPLITTER_BASE,
            "icon": SPLITTER_ACCENT,
            "outline": SPLITTER_BORDER,
        },
        "goal": {
            "top": GOAL_PIT_DEEP,
            "star": GOAL_STAR,
            "star_border": GOAL_STAR_DARK,
            "glow": GOAL_STAR_LIGHT,
        },
        "block_main": {
            "color": WOOD_BASE,
            "outline": WOOD_BORDER,
        },
    }


def get_ursina_config() -> dict[str, Any]:
    """Return physics and animation timing tuned for Stardew's cozy, chunky feel."""
    return {
        "floor_thickness": 0.35,
        "tile_gap": 0.04,
        "roll_duration": 0.18,      # Calm, eased rolls
        "fall_duration": 0.85,
        "victory_duration": 1.4,
        "cam_yaw": 30.0,
        "cam_pitch": 35.264,
        "cam_fov": 16.0,
        "cam_ortho": True,
        "bg_blur_radius": 0,        # No blur to preserve crisp pixel look
    }


def setup_ui_font() -> str:
    """Setup UI font from assets folder."""
    from panda3d.core import getModelPath
    from ursina import Text, application

    if FONT_DIR.exists():
        _model_path = getModelPath()
        font_dir_str = str(FONT_DIR.resolve())
        if font_dir_str not in [str(p) for p in _model_path.directories]:
            _model_path.append_path(font_dir_str)
        if hasattr(application, "fonts_folder"):
            application.fonts_folder = FONT_DIR

    Text.default_font = UI_FONT
    return UI_FONT
