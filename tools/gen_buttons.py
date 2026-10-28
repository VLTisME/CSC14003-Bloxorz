#!/usr/bin/env python3
"""Pixel Button Sprite Generator for Bloxorz 3D (Stardew Valley Aesthetic).

Generates 16 button state sprites from the 4-step color ramps (GREEN, ORANGE, RED, DISABLED)
and 4 states (normal, hover, pressed, selected).
Ensures all pixels strictly adhere to the 29-color PALETTE.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Import theme definitions
import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from game.ursina_ui.assets.theme import PALETTE, BUTTON_RAMPS, DEFAULT_FONT_PATH


def hex_to_rgba(hex_str: str, alpha: int = 255) -> tuple[int, int, int, int]:
    """Convert hex string (e.g. '#8ab060') to RGBA tuple."""
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


PALETTE_HEX_SET = {v.lower() for v in PALETTE.values()}


def validate_image_palette(img: Image.Image, img_name: str = "Image") -> None:
    """Assert that every non-transparent pixel in img is in the 29-color PALETTE (C-accelerated)."""
    rgba_img = img.convert("RGBA")
    colors = rgba_img.getcolors(maxcolors=65536)
    if not colors:
        return

    invalid_colors: set[str] = set()
    for count, (r, g, b, a) in colors:
        if a > 0:
            h = f"#{r:02x}{g:02x}{b:02x}".lower()
            if h not in PALETTE_HEX_SET:
                invalid_colors.add(h)

    if invalid_colors:
        raise ValueError(
            f"Palette violation in {img_name}! Found non-palette colors: {invalid_colors}"
        )


def generate_button_base_sprite(ramp: list[str], state: str, s: int = 24) -> Image.Image:
    """Generate a 24x24 9-slice button base sprite using a 4-step ramp.

    Ramp order: [dark_outline, shadow, base, highlight]
    States: 'normal', 'hover', 'pressed', 'selected'
    """
    c_dark = hex_to_rgba(ramp[0])
    c_shadow = hex_to_rgba(ramp[1])
    c_base = hex_to_rgba(ramp[2])
    c_highlight = hex_to_rgba(ramp[3])

    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    pix = img.load()

    # Fill base interior
    for y in range(1, s - 1):
        for x in range(1, s - 1):
            pix[x, y] = c_base

    # Dark outlines (chamfered / cut corners for authentic pixel art rounding)
    for x in range(1, s - 1):
        pix[x, 0] = c_dark
        pix[x, s - 1] = c_dark
    for y in range(1, s - 1):
        pix[0, y] = c_dark
        pix[s - 1, y] = c_dark

    if state in ("normal", "idle"):
        # Top & Left highlight bevel
        for x in range(1, s - 2):
            pix[x, 1] = c_highlight
        for y in range(1, s - 2):
            pix[1, y] = c_highlight
        # Right & Bottom shadow bevel (2-row bottom shadow for tactile push-button weight)
        for y in range(2, s - 1):
            pix[s - 2, y] = c_shadow
        for x in range(2, s - 1):
            pix[x, s - 3] = c_shadow
            pix[x, s - 2] = c_shadow

    elif state == "hover":
        # Interactive hover: extended highlight glow along top and left
        for x in range(1, s - 2):
            pix[x, 1] = c_highlight
            pix[x, 2] = c_highlight
        for y in range(1, s - 2):
            pix[1, y] = c_highlight
            pix[2, y] = c_highlight
        # Bottom and right shadow
        for y in range(3, s - 1):
            pix[s - 2, y] = c_shadow
        for x in range(3, s - 1):
            pix[x, s - 3] = c_shadow
            pix[x, s - 2] = c_shadow

    elif state == "pressed":
        # Inverted bevel: top & left get shadow (depressed into panel)
        for x in range(1, s - 2):
            pix[x, 1] = c_shadow
            pix[x, 2] = c_shadow
        for y in range(1, s - 2):
            pix[1, y] = c_shadow
            pix[2, y] = c_shadow
        # Bottom and right get highlight rim
        for y in range(2, s - 1):
            pix[s - 2, y] = c_highlight
        for x in range(2, s - 1):
            pix[x, s - 2] = c_highlight

    elif state in ("selected", "active"):
        # Selected / active tab state: inner highlight frame with inset groove
        for x in range(1, s - 1):
            pix[x, 1] = c_highlight
            pix[x, s - 2] = c_highlight
        for y in range(1, s - 1):
            pix[1, y] = c_highlight
            pix[s - 2, y] = c_highlight
        for x in range(2, s - 2):
            pix[x, 2] = c_shadow
        for y in range(2, s - 2):
            pix[2, y] = c_shadow

    validate_image_palette(img, f"button_{state}")
    return img


def slice_9(src: Image.Image, target_w: int, target_h: int, c: int = 6) -> Image.Image:
    """Scales a 9-slice source image to target dimensions while keeping corners intact."""
    sw, sh = src.size
    dst = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))

    # 4 corners
    dst.paste(src.crop((0, 0, c, c)), (0, 0))
    dst.paste(src.crop((sw - c, 0, sw, c)), (target_w - c, 0))
    dst.paste(src.crop((0, sh - c, c, sh)), (0, target_h - c))
    dst.paste(src.crop((sw - c, sh - c, sw, sh)), (target_w - c, target_h - c))

    # 4 borders (nearest-neighbor stretched)
    if target_w > 2 * c:
        top = src.crop((c, 0, sw - c, c)).resize((target_w - 2 * c, c), Image.Resampling.NEAREST)
        bottom = src.crop((c, sh - c, sw - c, sh)).resize((target_w - 2 * c, c), Image.Resampling.NEAREST)
        dst.paste(top, (c, 0))
        dst.paste(bottom, (c, target_h - c))

    if target_h > 2 * c:
        left = src.crop((0, c, c, sh - c)).resize((c, target_h - 2 * c), Image.Resampling.NEAREST)
        right = src.crop((sw - c, c, sw, sh - c)).resize((c, target_h - 2 * c), Image.Resampling.NEAREST)
        dst.paste(left, (0, c))
        dst.paste(right, (target_w - c, c))

    # Center fill
    if target_w > 2 * c and target_h > 2 * c:
        center = src.crop((c, c, sw - c, sh - c)).resize(
            (target_w - 2 * c, target_h - 2 * c), Image.Resampling.NEAREST
        )
        dst.paste(center, (c, c))

    validate_image_palette(dst, f"slice_9_{target_w}x{target_h}")
    return dst


def generate_all_buttons(
    buttons_dir: Path,
    src_dir: Path,
    base_size: int = 24,
) -> dict[str, dict[str, Image.Image]]:
    """Generate and save all 16 button states and base templates."""
    buttons_dir.mkdir(parents=True, exist_ok=True)
    src_dir.mkdir(parents=True, exist_ok=True)

    colors = ["green", "orange", "red", "disabled"]
    states = ["normal", "hover", "pressed", "selected"]

    # 1. Generate base 9-slice template (orange wood base)
    base_template = generate_button_base_sprite(BUTTON_RAMPS["ORANGE"], "normal", base_size)
    base_template.save(src_dir / "button_base.png")

    sprites: dict[str, dict[str, Image.Image]] = {}

    # 2. Generate 16 button states
    for color_name in colors:
        ramp = BUTTON_RAMPS[color_name.upper()]
        sprites[color_name] = {}
        for state in states:
            sprite = generate_button_base_sprite(ramp, state, base_size)
            sprites[color_name][state] = sprite

            # Save primary file
            out_path = buttons_dir / f"btn_{color_name}_{state}.png"
            sprite.save(out_path)

            # Save alias for normal -> idle
            if state == "normal":
                sprite.save(buttons_dir / f"btn_{color_name}_idle.png")
            elif state == "selected":
                sprite.save(buttons_dir / f"btn_{color_name}_active.png")

    return sprites


def draw_pixel_text(
    canvas: Image.Image,
    pos: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    color: tuple[int, int, int, int],
    align: str = "left",
    threshold: int = 120,
) -> None:
    """Draw crisp non-antialiased text strictly in the given palette color."""
    if not hasattr(font, "getbbox"):
        return
    bbox = font.getbbox(text)
    if not bbox:
        return
    bw = bbox[2] - bbox[0]
    bh = bbox[3] - bbox[1]
    pad = 4
    w, h = bw + pad * 2, bh + pad * 2
    temp = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(temp)
    d.text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=255)
    mask = temp.point(lambda p: 255 if p >= threshold else 0, mode="1")

    x, y = pos
    if align == "center":
        x -= bw // 2
    elif align == "right":
        x -= bw

    solid = Image.new("RGBA", (w, h), color)
    canvas.paste(solid, (x - pad, y - pad), mask=mask)


def generate_preview_contact_sheet(
    sprites: dict[str, dict[str, Image.Image]],
    out_path: Path,
    scale: int = 3,
) -> None:
    """Generate a comprehensive contact sheet for all 16 button states with real samples."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    colors = ["green", "orange", "red", "disabled"]
    states = ["normal", "hover", "pressed", "selected"]

    # Try loading font for text labels in preview
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
    try:
        font = ImageFont.truetype(str(DEFAULT_FONT_PATH), 14)
        title_font = ImageFont.truetype(str(DEFAULT_FONT_PATH), 18)
    except Exception:
        font = ImageFont.load_default()
        title_font = font

    # Preview canvas parameters (Stardew parchment aesthetic)
    margin_x = 70
    margin_y = 20
    col_width = 175
    row_height = 80
    header_height = 60

    total_w = margin_x + col_width * len(colors) + 30
    total_h = margin_y * 2 + header_height + row_height * len(states)

    canvas = Image.new("RGBA", (total_w, total_h), hex_to_rgba(PALETTE["cream"]))
    draw = ImageDraw.Draw(canvas)

    # Outer decorative wood border
    c_wood = hex_to_rgba(PALETTE["wood"])
    c_brick = hex_to_rgba(PALETTE["brick"])
    c_tan = hex_to_rgba(PALETTE["tan"])
    c_ink = hex_to_rgba(PALETTE["ink"])

    draw.rectangle([0, 0, total_w - 1, total_h - 1], outline=c_brick, width=3)
    draw.rectangle([3, 3, total_w - 4, total_h - 4], outline=c_wood, width=2)
    draw.rectangle([5, 5, total_w - 6, total_h - 6], outline=c_tan, width=1)

    # Title header banner
    draw_pixel_text(
        canvas,
        (margin_x, 18),
        "BLOXORZ PIXEL BUTTONS (STARDEW AESTHETIC - 16 STATES)",
        title_font,
        c_ink,
        align="left",
    )

    # Render grid of buttons
    start_y = margin_y + header_height

    sample_labels = {
        "green": "PLAY",
        "orange": "STAGE",
        "red": "RESET",
        "disabled": "LOCKED",
    }

    for col_idx, color_name in enumerate(colors):
        x = margin_x + col_idx * col_width

        # Column header
        draw_pixel_text(canvas, (x + 8, start_y - 24), color_name.upper(), font, c_brick, align="left")

        for row_idx, state in enumerate(states):
            y = start_y + row_idx * row_height

            # Row label (only on first column)
            if col_idx == 0:
                draw_pixel_text(canvas, (margin_x - 14, y + 20), state.upper(), font, c_ink, align="right")

            sprite = sprites[color_name][state]

            # 1. Draw raw 9-slice base magnified 2x
            raw_magnified = sprite.resize((sprite.width * 2, sprite.height * 2), Image.Resampling.NEAREST)
            canvas.paste(raw_magnified, (x, y + 6), raw_magnified)

            # 2. Draw assembled wide button (96x28) using slice_9
            wide_btn = slice_9(sprite, 96, 28, c=6)

            # Draw sample text onto button
            btn_with_text = wide_btn.copy()
            label = sample_labels[color_name]
            text_color = hex_to_rgba(PALETTE["ink"]) if color_name != "red" else hex_to_rgba(PALETTE["ivory"])
            text_offset_y = 1 if state == "pressed" else 0
            draw_pixel_text(btn_with_text, (48, 8 + text_offset_y), label, font, text_color, align="center")

            canvas.paste(btn_with_text, (x + 56, y + 16), btn_with_text)

    # Verify preview canvas
    validate_image_palette(canvas, "preview_buttons")
    canvas.save(out_path)
    print(f"[OK] Preview contact sheet saved to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Bloxorz pixel button sprites.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "game" / "ursina_ui" / "assets" / "ui" / "buttons",
        help="Directory to save generated button sprites.",
    )
    parser.add_argument(
        "--src-dir",
        type=Path,
        default=PROJECT_ROOT / "game" / "ursina_ui" / "assets" / "ui" / "src",
        help="Directory to save base 9-slice source template.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Generate preview contact sheet in docs/pixel/preview_buttons.png.",
    )
    args = parser.parse_args()

    print("[GEN_BUTTONS] Generating 16 button states...")
    sprites = generate_all_buttons(args.output_dir, args.src_dir)
    print(f"[OK] 16 button states generated in {args.output_dir}")

    if args.preview:
        preview_path = PROJECT_ROOT / "docs" / "pixel" / "preview_buttons.png"
        print("[GEN_BUTTONS] Generating preview contact sheet...")
        generate_preview_contact_sheet(sprites, preview_path)


if __name__ == "__main__":
    main()
