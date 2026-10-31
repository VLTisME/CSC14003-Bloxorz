#!/usr/bin/env python3
"""Pixel Art Logo Generator for Bloxorz 3D (Stardew Valley Aesthetic).

Generates:
1. logo_title.png ("BLOXORZ")
2. logo_sub.png ("3D PUZZLE")

Styling specifications from docs/assets/pixel/palette.md:
- 1px Outline: ink (#212123)
- 2px Drop Shadow: tan (#d3a068)
- Two-Tone Fill: Top brick (#80493a), Bottom plum_dark (#352b42) with pixel dither
- 100% compliant with the 29-color PALETTE.
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

from game.ursina_ui.assets.theme import (
    PALETTE,
    LOGO_OUTLINE,
    LOGO_SHADOW,
    LOGO_TOP_FILL,
    LOGO_BOTTOM_FILL,
    DEFAULT_FONT_PATH,
)


def hex_to_rgba(hex_str: str, alpha: int = 255) -> tuple[int, int, int, int]:
    """Convert hex string (e.g. '#8ab060') to RGBA tuple."""
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


PALETTE_HEX_SET = {v.lower() for v in PALETTE.values()}


def validate_image_palette(img: Image.Image, img_name: str = "Image") -> None:
    """Assert that every non-transparent pixel in img is in the 29-color PALETTE."""
    rgba_img = img.convert("RGBA")
    width, height = rgba_img.size
    pixels = rgba_img.load()

    invalid_colors: set[str] = set()
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a > 0:
                h = f"#{r:02x}{g:02x}{b:02x}".lower()
                if h not in PALETTE_HEX_SET:
                    invalid_colors.add(h)

    if invalid_colors:
        raise ValueError(
            f"Palette violation in {img_name}! Found non-palette colors: {invalid_colors}"
        )


def generate_logo_text_sprite(
    text: str,
    font_size: int,
    shadow_offset: tuple[int, int] = (2, 2),
    threshold: int = 120,
    with_dither: bool = True,
) -> Image.Image:
    """Generate crisp pixel art logo text with 1px outline, 2px drop shadow, and two-tone fill."""
    try:
        font = ImageFont.truetype(str(DEFAULT_FONT_PATH), font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = font.getbbox(text)
    if not bbox:
        raise ValueError(f"Could not compute bbox for text '{text}'")

    bw = bbox[2] - bbox[0]
    bh = bbox[3] - bbox[1]
    pad = 8

    # Dimensions with padding to accommodate outline and shadow
    w = bw + pad * 2 + abs(shadow_offset[0]) + 4
    h = bh + pad * 2 + abs(shadow_offset[1]) + 4

    # 1. Render raw text mask
    mask_img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask_img)
    d.text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=255)

    # 2. Binarize mask to 1-bit (strict pixel art, no AA bleed)
    mask_pix = mask_img.load()
    is_fg = [[(mask_pix[x, y] >= threshold) for x in range(w)] for y in range(h)]

    # 3. Build 8-way 1px outline mask
    is_outline = [[False for _ in range(w)] for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if is_fg[y][x]:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        ox, oy = x + dx, y + dy
                        if 0 <= ox < w and 0 <= oy < h:
                            is_outline[oy][ox] = True

    # 4. Canvas setup
    out_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out_pix = out_img.load()

    c_ink = hex_to_rgba(LOGO_OUTLINE)
    c_shadow = hex_to_rgba(LOGO_SHADOW)
    c_brick = hex_to_rgba(LOGO_TOP_FILL)
    c_plum = hex_to_rgba(LOGO_BOTTOM_FILL)

    # 5. Layer 1: Drop Shadow (+2, +2) cast by the outlined text
    sx_off, sy_off = shadow_offset
    for y in range(h):
        for x in range(w):
            if is_outline[y][x]:
                sx, sy = x + sx_off, y + sy_off
                if 0 <= sx < w and 0 <= sy < h:
                    out_pix[sx, sy] = c_shadow

    # 6. Layer 2: 1px Outline in ink
    for y in range(h):
        for x in range(w):
            if is_outline[y][x]:
                out_pix[x, y] = c_ink

    # 7. Layer 3: Two-tone fill with subtle dither transition
    all_fg_y = [y for y in range(h) for x in range(w) if is_fg[y][x]]
    if all_fg_y:
        min_y, max_y = min(all_fg_y), max(all_fg_y)
        mid_y = (min_y + max_y) // 2

        for y in range(h):
            for x in range(w):
                if is_fg[y][x]:
                    if with_dither:
                        if y < mid_y - 1:
                            out_pix[x, y] = c_brick
                        elif y > mid_y + 1:
                            out_pix[x, y] = c_plum
                        else:
                            # 2-pixel dither transition band
                            if (x + y) % 2 == 0:
                                out_pix[x, y] = c_brick
                            else:
                                out_pix[x, y] = c_plum
                    else:
                        out_pix[x, y] = c_brick if y <= mid_y else c_plum

    # Crop tightly around bounding box of visible content
    bbox_visible = out_img.getbbox()
    if bbox_visible:
        # Add 1px safety border
        bx0, by0, bx1, by1 = bbox_visible
        bx0 = max(0, bx0 - 1)
        by0 = max(0, by0 - 1)
        bx1 = min(w, bx1 + 1)
        by1 = min(h, by1 + 1)
        out_img = out_img.crop((bx0, by0, bx1, by1))

    validate_image_palette(out_img, f"logo_{text}")
    return out_img


def generate_all_logos(output_dir: Path) -> tuple[Image.Image, Image.Image]:
    """Generate logo_title.png and logo_sub.png."""
    output_dir.mkdir(parents=True, exist_ok=True)

    title_sprite = generate_logo_text_sprite(
        text="BLOXORZ",
        font_size=42,
        shadow_offset=(2, 2),
        with_dither=True,
    )
    title_sprite.save(output_dir / "logo_title.png")

    sub_sprite = generate_logo_text_sprite(
        text="3D PUZZLE",
        font_size=18,
        shadow_offset=(1, 1),
        with_dither=False,
    )
    sub_sprite.save(output_dir / "logo_sub.png")

    return title_sprite, sub_sprite


def draw_pixel_label(
    canvas: Image.Image,
    pos: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    color: tuple[int, int, int, int],
    align: str = "left",
) -> None:
    """Helper to draw crisp label text without antialiasing bleed."""
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
    mask = temp.point(lambda p: 255 if p >= 120 else 0, mode="1")

    x, y = pos
    if align == "center":
        x -= bw // 2
    elif align == "right":
        x -= bw

    solid = Image.new("RGBA", (w, h), color)
    canvas.paste(solid, (x - pad, y - pad), mask=mask)


def generate_preview_contact_sheet(
    title_sprite: Image.Image,
    sub_sprite: Image.Image,
    out_path: Path,
) -> None:
    """Generate preview contact sheet demonstrating logo at 1x, 2x, 3x on parchment and dark backgrounds."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        font = ImageFont.truetype(str(DEFAULT_FONT_PATH), 14)
        header_font = ImageFont.truetype(str(DEFAULT_FONT_PATH), 18)
    except Exception:
        font = ImageFont.load_default()
        header_font = font

    c_ink = hex_to_rgba(PALETTE["ink"])
    c_brick = hex_to_rgba(PALETTE["brick"])
    c_wood = hex_to_rgba(PALETTE["wood"])
    c_tan = hex_to_rgba(PALETTE["tan"])
    c_cream = hex_to_rgba(PALETTE["cream"])
    c_navy = hex_to_rgba(PALETTE["navy_1"])
    c_ivory = hex_to_rgba(PALETTE["ivory"])

    sheet_w = 640
    sheet_h = 460
    canvas = Image.new("RGBA", (sheet_w, sheet_h), c_cream)
    draw = ImageDraw.Draw(canvas)

    # Frame border
    draw.rectangle([0, 0, sheet_w - 1, sheet_h - 1], outline=c_brick, width=3)
    draw.rectangle([3, 3, sheet_w - 4, sheet_h - 4], outline=c_wood, width=2)
    draw.rectangle([5, 5, sheet_w - 6, sheet_h - 6], outline=c_tan, width=1)

    # Title header
    draw_pixel_label(canvas, (24, 18), "BLOXORZ PIXEL LOGO (STARDEW AESTHETIC - PREVIEW)", header_font, c_ink)

    # Section 1: Parchment Background (Native 1x and 2x)
    draw_pixel_label(canvas, (24, 56), "1X NATIVE & 2X SCALE (PARCHMENT)", font, c_brick)

    # 1x title & sub
    canvas.paste(title_sprite, (24, 82), title_sprite)
    canvas.paste(sub_sprite, (24 + title_sprite.width + 16, 92), sub_sprite)

    # 2x title & sub
    title_2x = title_sprite.resize((title_sprite.width * 2, title_sprite.height * 2), Image.Resampling.NEAREST)
    sub_2x = sub_sprite.resize((sub_sprite.width * 2, sub_sprite.height * 2), Image.Resampling.NEAREST)
    canvas.paste(title_2x, (24, 134), title_2x)
    canvas.paste(sub_2x, (24 + title_2x.width // 2 - sub_2x.width // 2, 134 + title_2x.height + 6), sub_2x)

    # Section 2: Dark Night Sky Background (navy_1 #3a3858)
    draw_pixel_label(canvas, (340, 56), "DARK SKY CONTRAST (NAVY_1 #3A3858)", font, c_brick)

    dark_box_x = 340
    dark_box_y = 80
    dark_box_w = 276
    dark_box_h = 350
    draw.rectangle([dark_box_x, dark_box_y, dark_box_x + dark_box_w, dark_box_y + dark_box_h], fill=c_navy, outline=c_brick, width=2)

    # Centered assembled logo on dark background
    logo_center_x = dark_box_x + dark_box_w // 2
    canvas.paste(title_2x, (logo_center_x - title_2x.width // 2, dark_box_y + 40), title_2x)
    canvas.paste(sub_2x, (logo_center_x - sub_2x.width // 2, dark_box_y + 40 + title_2x.height + 8), sub_2x)

    draw_pixel_label(canvas, (logo_center_x, dark_box_y + 160), "OUTLINE: #212123 (INK)", font, c_ivory, align="center")
    draw_pixel_label(canvas, (logo_center_x, dark_box_y + 185), "SHADOW: #D3A068 (TAN)", font, c_tan, align="center")
    draw_pixel_label(canvas, (logo_center_x, dark_box_y + 210), "TOP FILL: #80493A (BRICK)", font, hex_to_rgba(PALETTE["brick"]), align="center")
    draw_pixel_label(canvas, (logo_center_x, dark_box_y + 235), "BOT FILL: #352B42 (PLUM_DARK)", font, hex_to_rgba(PALETTE["blush"]), align="center")

    validate_image_palette(canvas, "preview_logo")
    canvas.save(out_path)
    print(f"[OK] Preview contact sheet saved to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Bloxorz pixel logo sprites.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "game" / "ursina_ui" / "assets" / "ui" / "logo",
        help="Directory to save generated logo sprites.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Generate preview contact sheet in docs/assets/pixel/preview_logo.png.",
    )
    args = parser.parse_args()

    print("[GEN_LOGO] Generating logo_title.png and logo_sub.png...")
    title_sprite, sub_sprite = generate_all_logos(args.output_dir)
    print(f"[OK] Logo sprites generated in {args.output_dir}")

    if args.preview:
        preview_path = PROJECT_ROOT / "docs" / "assets" / "pixel" / "preview_logo.png"
        print("[GEN_LOGO] Generating preview contact sheet...")
        generate_preview_contact_sheet(title_sprite, sub_sprite, preview_path)


if __name__ == "__main__":
    main()
