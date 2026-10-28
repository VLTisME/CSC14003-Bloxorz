"""Quản lý vật liệu, bảng màu và texture thủ tục (procedural textures) cho Bloxorz Ursina UI.

Sử dụng Pillow để tạo các texture nhẹ, sắc nét và bám sát phong cách đồ chơi/gỗ của ảnh mẫu:
- Vân gỗ tự nhiên cho khối Bloxorz
- Ô sàn xanh lá có viền nổi
- Ô cam nứt (fragile)
- Mặt công tắc O (tròn) và X (chữ thập)
- Ô phân tách T
- Ngôi sao vàng phát sáng ở lỗ đích
- Texture bóng blob (radial gradient mềm)
- Gradient nền xanh ngọc
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING
from PIL import Image, ImageDraw, ImageFilter
from ursina import Texture, color

from game.theme import get_theme

# Bộ nhớ đệm lưu texture tránh tạo lại nhiều lần
_TEXTURE_CACHE: dict[str, Texture] = {}


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Chuyển đổi chuỗi hex dạng '#RRGGBB' hoặc '#RGB' sang tuple (r, g, b)."""
    s = hex_str.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    val = int(s, 16)
    return ((val >> 16) & 255, (val >> 8) & 255, val & 255)


def hex_to_rgba(hex_str: str, alpha: int = 255) -> tuple[int, int, int, int]:
    """Chuyển đổi chuỗi hex kèm alpha sang tuple (r, g, b, a)."""
    r, g, b = hex_to_rgb(hex_str)
    return (r, g, b, alpha)


def hex_to_ursina_color(hex_str: str, alpha: float = 1.0) -> color.Color:
    """Chuyển đổi mã màu hex sang đối tượng color của Ursina."""
    c = color.hex(hex_str)
    return color.Color(c[0], c[1], c[2], float(alpha))


def blend_rgb(c1: tuple[int, int, int], c2: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Hòa trộn 2 màu RGB đặc (không dùng kênh Alpha) để triệt tiêu hoàn toàn hiệu ứng xuyên thấu."""
    f = max(0.0, min(1.0, factor))
    return (
        int(c1[0] * (1.0 - f) + c2[0] * f),
        int(c1[1] * (1.0 - f) + c2[1] * f),
        int(c1[2] * (1.0 - f) + c2[2] * f),
    )


def get_wood_texture(theme_name: str = "toy", size: int = 16) -> Texture:
    """Tạo texture khối gỗ pixel art cơ bản (Basic Pixel-Art Wooden Block)."""
    theme = get_theme(theme_name)
    bm = theme.get("block_main", {})
    base_hex = bm.get("color", bm.get("top", "#8B5A2B"))
    return get_solid_wood_texture(base_hex, size=size)


def get_split_cube_texture(cube_index: int, theme_name: str = "toy", size: int = 128) -> Texture:
    """Tạo texture cho khối nhỏ 1 (ngọc lục bảo tối) hoặc 2 (sapphire đêm) trên canvas RGB đặc."""
    key = f"split_{cube_index}_{theme_name}_{size}"
    if key in _TEXTURE_CACHE:
        return _TEXTURE_CACHE[key]

    theme = get_theme(theme_name)
    cfg_key = "cube_1_active" if cube_index == 1 else "cube_2_active"
    cfg = theme.get(cfg_key, theme.get("block_main", {}))

    top_rgb = hex_to_rgb(cfg.get("top", "#1E4D40" if cube_index == 1 else "#203A5E"))
    left_rgb = hex_to_rgb(cfg.get("left", "#13352B" if cube_index == 1 else "#142640"))
    outline_rgb = hex_to_rgb(cfg.get("outline", "#06130F" if cube_index == 1 else "#070D17"))
    highlight_rgb = hex_to_rgb(cfg.get("edge_highlight", "#367A66" if cube_index == 1 else "#3B6096"))

    img = Image.new("RGB", (size, size), top_rgb)
    draw = ImageDraw.Draw(img)

    # Họa tiết tinh thể tinh xảo
    crystal_color = blend_rgb(top_rgb, left_rgb, 0.5)
    for i in range(4):
        offset = i * (size // 8)
        draw.rectangle([(offset, offset), (size - 1 - offset, size - 1 - offset)],
                       outline=crystal_color, width=1)

    # Viền nổi
    draw.rectangle([(0, 0), (size - 1, size - 1)], outline=outline_rgb, width=2)
    draw.line([(1, 1), (size - 2, 1)], fill=highlight_rgb, width=1)
    draw.line([(1, 1), (1, size - 2)], fill=highlight_rgb, width=1)

    tex = Texture(img)
    _TEXTURE_CACHE[key] = tex
    return tex


def get_tile_texture(theme_name: str = "toy", is_alt: bool = False, size: int = 128) -> Texture:
    """Tạo texture ô sàn khối đá công nghiệp trên canvas RGB đặc 100%."""
    key = f"tile_{theme_name}_{'alt' if is_alt else 'main'}_{size}"
    if key in _TEXTURE_CACHE:
        return _TEXTURE_CACHE[key]

    theme = get_theme(theme_name)
    reg = theme.get("regular", {})
    color_hex = reg.get("top_alt" if is_alt else "top", "#222831" if is_alt else "#2D3748")
    outline_hex = reg.get("outline", "#0D1117")

    top_rgb = hex_to_rgb(color_hex)
    outline_rgb = hex_to_rgb(outline_hex)

    img = Image.new("RGB", (size, size), top_rgb)
    draw = ImageDraw.Draw(img)

    # Vân sớ đá phiến ngang bằng hòa trộn màu RGB đặc
    for i in range(16):
        y = int(i * (size / 16))
        grain_factor = 0.15 + ((i * 17) % 25) / 100.0
        draw.line([(4, y), (size - 5, y)], fill=blend_rgb(top_rgb, outline_rgb, grain_factor), width=1)

    # Rãnh viền sâu giữa các ô (chiseled edge grooves)
    draw.rectangle([(0, 0), (size - 1, size - 1)], outline=outline_rgb, width=2)
    inner_groove = blend_rgb(top_rgb, outline_rgb, 0.75)
    draw.rectangle([(3, 3), (size - 4, size - 4)], outline=inner_groove, width=1)

    # Gờ bắt sáng tinh tế trên cạnh trên và cạnh trái
    highlight_color = blend_rgb(top_rgb, (255, 255, 255), 0.18)
    draw.line([(4, 4), (size - 5, 4)], fill=highlight_color, width=1)
    draw.line([(4, 4), (4, size - 5)], fill=highlight_color, width=1)

    tex = Texture(img)
    _TEXTURE_CACHE[key] = tex
    return tex


def get_fragile_texture(theme_name: str = "toy", size: int = 128) -> Texture:
    """Tạo texture cho ô gạch cam đất cháy nứt sẫm trên canvas RGB đặc 100%."""
    key = f"fragile_{theme_name}_{size}"
    if key in _TEXTURE_CACHE:
        return _TEXTURE_CACHE[key]

    theme = get_theme(theme_name)
    fr = theme.get("fragile", {})
    top_rgb = hex_to_rgb(fr.get("top", "#8D4424"))
    crack_rgb = hex_to_rgb(fr.get("crack", "#150702"))
    outline_rgb = hex_to_rgb(fr.get("outline", "#2D1207"))

    img = Image.new("RGB", (size, size), top_rgb)
    draw = ImageDraw.Draw(img)

    # Bề mặt đá nứt với các đường nứt sâu, đen thẫm
    cracks = [
        [(size * 0.2, size * 0.1), (size * 0.35, size * 0.3), (size * 0.5, size * 0.5)],
        [(size * 0.5, size * 0.5), (size * 0.7, size * 0.4), (size * 0.85, size * 0.2)],
        [(size * 0.5, size * 0.5), (size * 0.45, size * 0.75), (size * 0.6, size * 0.9)],
        [(size * 0.35, size * 0.3), (size * 0.2, size * 0.5)],
        [(size * 0.45, size * 0.75), (size * 0.25, size * 0.8)],
        [(size * 0.7, size * 0.4), (size * 0.8, size * 0.65)],
    ]
    sub_edge = blend_rgb(top_rgb, (255, 140, 80), 0.35)
    for pts in cracks:
        draw.line(pts, fill=crack_rgb, width=3)
        draw.line(pts, fill=sub_edge, width=1)

    draw.rectangle([(0, 0), (size - 1, size - 1)], outline=outline_rgb, width=2)
    draw.rectangle([(3, 3), (size - 4, size - 4)], outline=blend_rgb(top_rgb, outline_rgb, 0.6), width=1)

    tex = Texture(img)
    _TEXTURE_CACHE[key] = tex
    return tex


def get_soft_switch_texture(theme_name: str = "toy", size: int = 128) -> Texture:
    """Tạo texture bề mặt công tắc mềm O trên canvas RGB đặc 100%."""
    key = f"sw_soft_{theme_name}_{size}"
    if key in _TEXTURE_CACHE:
        return _TEXTURE_CACHE[key]

    theme = get_theme(theme_name)
    sw = theme.get("switch_soft", {})
    base_rgb = hex_to_rgb(sw.get("top", "#2D3748"))
    btn_rgb = hex_to_rgb(sw.get("circle", "#C0392B"))
    side_rgb = hex_to_rgb(sw.get("circle_side", "#8E2519"))
    hl_rgb = hex_to_rgb(sw.get("circle_highlight", "#D9534F"))

    img = Image.new("RGB", (size, size), base_rgb)
    draw = ImageDraw.Draw(img)

    # Rãnh viền sàn đá
    draw.rectangle([(0, 0), (size - 1, size - 1)], outline=hex_to_rgb("#0D1117"), width=2)

    pad = size // 5
    # Vòng tròn bóng đổ / viền chìm của nút
    draw.ellipse([pad - 2, pad - 2, size - pad + 2, size - pad + 2], fill=side_rgb)
    # Nút tròn đỏ ruby
    draw.ellipse([pad, pad, size - pad, size - pad], fill=btn_rgb)
    # Điểm phản chiếu ánh sáng tinh tế
    hl_pad = pad + size // 10
    draw.arc([hl_pad, hl_pad, size - hl_pad, size - hl_pad], 200, 340, fill=hl_rgb, width=3)

    tex = Texture(img)
    _TEXTURE_CACHE[key] = tex
    return tex


def get_hard_switch_texture(theme_name: str = "toy", size: int = 128) -> Texture:
    """Tạo texture bề mặt công tắc cứng X trên canvas RGB đặc 100%."""
    key = f"sw_hard_{theme_name}_{size}"
    if key in _TEXTURE_CACHE:
        return _TEXTURE_CACHE[key]

    theme = get_theme(theme_name)
    sw = theme.get("switch_hard", {})
    base_rgb = hex_to_rgb(sw.get("top", "#2D3748"))
    cross_rgb = hex_to_rgb(sw.get("cross", "#A93226"))
    side_rgb = hex_to_rgb(sw.get("cross_side", "#782017"))

    img = Image.new("RGB", (size, size), base_rgb)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (size - 1, size - 1)], outline=hex_to_rgb("#0D1117"), width=2)

    pad = size // 4
    w = max(4, size // 8)

    # Bóng chìm chữ X
    draw.line([(pad + 1, pad + 2), (size - pad + 1, size - pad + 2)], fill=side_rgb, width=w)
    draw.line([(pad + 1, size - pad + 2), (size - pad + 1, pad + 2)], fill=side_rgb, width=w)

    # Chữ X đỏ thép sẫm
    draw.line([(pad, pad), (size - pad, size - pad)], fill=cross_rgb, width=w)
    draw.line([(pad, size - pad), (size - pad, pad)], fill=cross_rgb, width=w)

    tex = Texture(img)
    _TEXTURE_CACHE[key] = tex
    return tex


def get_splitter_texture(theme_name: str = "toy", size: int = 128) -> Texture:
    """Tạo texture bề mặt ô phân tách T trên canvas RGB đặc 100%."""
    key = f"splitter_{theme_name}_{size}"
    if key in _TEXTURE_CACHE:
        return _TEXTURE_CACHE[key]

    theme = get_theme(theme_name)
    sp = theme.get("splitter", {})
    base_rgb = hex_to_rgb(sp.get("top", "#2D3748"))
    icon_rgb = hex_to_rgb(sp.get("icon", "#A93226"))

    img = Image.new("RGB", (size, size), base_rgb)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (size - 1, size - 1)], outline=hex_to_rgb("#0D1117"), width=2)

    cx, cy = size // 2, size // 2
    r = size // 3
    w_box = max(5, size // 6)
    draw.rectangle([(cx - r, cy - w_box), (cx - w_box // 2, cy + w_box)], fill=icon_rgb)
    draw.rectangle([(cx + w_box // 2, cy - w_box), (cx + r, cy + w_box)], fill=icon_rgb)

    tex = Texture(img)
    _TEXTURE_CACHE[key] = tex
    return tex


def get_blob_shadow_texture(size: int = 128) -> Texture:
    """Tạo texture bóng đổ dạng blob (mềm ở rìa, tối ở giữa) cho khối 3D."""
    key = f"blob_shadow_{size}"
    if key in _TEXTURE_CACHE:
        return _TEXTURE_CACHE[key]

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size / 2.0, size / 2.0
    radius = size * 0.46

    # Vẽ radial gradient từ tâm ra ngoài bằng các vòng ellipse đồng tâm
    steps = 32
    for i in range(steps, 0, -1):
        fraction = i / float(steps)
        r = radius * fraction
        # Tăng alpha tối đa lên 220 để bóng đậm đà, nổi khối rõ rệt trên nền đá tối
        alpha = int(220 * (0.5 * (1.0 + math.cos(math.pi * (1.0 - fraction)))))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(2, 4, 8, alpha))

    tex = Texture(img)
    _TEXTURE_CACHE[key] = tex
    return tex


def get_gradient_background_texture(theme_name: str = "toy", height: int = 256) -> Texture:
    """Tạo texture gradient cho nền không gian tối (từ đen #0a0e17 lên xanh than #162032)."""
    key = f"bg_gradient_{theme_name}_{height}"
    if key in _TEXTURE_CACHE:
        return _TEXTURE_CACHE[key]

    theme = get_theme(theme_name)
    top_rgb = hex_to_rgb(theme.get("bg_top", "#162032"))
    bottom_rgb = hex_to_rgb(theme.get("bg_bottom", "#0A0E17"))

    img = Image.new("RGB", (2, height))
    for y in range(height):
        t = y / float(height - 1)
        r = int(top_rgb[0] + (bottom_rgb[0] - top_rgb[0]) * t)
        g = int(top_rgb[1] + (bottom_rgb[1] - top_rgb[1]) * t)
        b = int(top_rgb[2] + (bottom_rgb[2] - top_rgb[2]) * t)
        img.putpixel((0, y), (r, g, b))
        img.putpixel((1, y), (r, g, b))

    tex = Texture(img)
    _TEXTURE_CACHE[key] = tex
    return tex


def get_contrast_bg_texture(
    center_hex: str = "#2E3C62",
    edge_hex: str = "#070A10",
    size: int = 512,
) -> Texture:
    """Tạo texture nền Cosmic Radial Gradient RGB đặc 100% với quầng sáng tương phản nhẹ ở tâm."""
    key = f"contrast_bg_{center_hex}_{edge_hex}_{size}"
    if key in _TEXTURE_CACHE:
        return _TEXTURE_CACHE[key]

    c_center = hex_to_rgb(center_hex)
    c_edge = hex_to_rgb(edge_hex)

    img = Image.new("RGB", (size, size))
    pixels = img.load()

    cx, cy = size / 2.0, size / 2.0
    for y in range(size):
        dy = (y - cy) / cy
        for x in range(size):
            dx = (x - cx) / cx
            d = math.sqrt(dx * dx + dy * dy)
            t = min(1.0, d / 1.18)
            factor = (1.0 - math.cos(t * math.pi)) / 2.0
            r = int(c_center[0] + (c_edge[0] - c_center[0]) * factor)
            g = int(c_center[1] + (c_edge[1] - c_center[1]) * factor)
            b = int(c_center[2] + (c_edge[2] - c_center[2]) * factor)
            img = Image.new("RGB", (size, size))
            pixels = img.load()
            assert pixels is not None

    tex = Texture(img)
    _TEXTURE_CACHE[key] = tex
    return tex


def get_solid_wood_texture(
    base_hex: str = "#8B5A2B",
    size: int = 16,
) -> Texture:
    """Tạo texture khối gỗ pixel art cơ bản (Basic Pixel-Art Wooden Block) với nearest filtering."""
    key = f"pixel_wood_block_{base_hex}_{size}"
    if key in _TEXTURE_CACHE:
        return _TEXTURE_CACHE[key]

    base_rgb = hex_to_rgb(base_hex)
    dark_border = (max(0, base_rgb[0] - 70), max(0, base_rgb[1] - 48), max(0, base_rgb[2] - 30))
    shadow_rgb = (max(0, base_rgb[0] - 40), max(0, base_rgb[1] - 28), max(0, base_rgb[2] - 18))
    light_rgb = (min(255, base_rgb[0] + 25), min(255, base_rgb[1] + 18), min(255, base_rgb[2] + 12))
    highlight_rgb = (min(255, base_rgb[0] + 55), min(255, base_rgb[1] + 40), min(255, base_rgb[2] + 25))
    nail_rgb = (max(0, base_rgb[0] - 90), max(0, base_rgb[1] - 65), max(0, base_rgb[2] - 45))

    img = Image.new("RGB", (size, size), base_rgb)
    pixels = img.load()
    assert pixels is not None

    # 1. Khung viền pixel tối ngoài cùng (1-pixel outer dark border)
    for x in range(size):
        pixels[x, 0] = dark_border
        pixels[x, size - 1] = dark_border
    for y in range(size):
        pixels[0, y] = dark_border
        pixels[size - 1, y] = dark_border

    # 2. Vát cạnh 3D nổi khối pixel (Top/Left highlight, Bottom/Right shadow)
    for x in range(1, size - 1):
        pixels[x, 1] = highlight_rgb
        pixels[x, size - 2] = shadow_rgb
    for y in range(1, size - 1):
        pixels[1, y] = highlight_rgb
        pixels[size - 2, y] = shadow_rgb

    # 3. Rãnh chia các thanh ván gỗ ngang (Horizontal plank seams)
    plank_h = size // 3
    seams = [plank_h, plank_h * 2]
    for sy in seams:
        if 2 <= sy < size - 2:
            for x in range(1, size - 1):
                pixels[x, sy] = shadow_rgb
                if sy + 1 < size - 2:
                    pixels[x, sy + 1] = light_rgb

    # 4. Đinh tán 1-pixel ở 4 góc (Corner iron nails)
    corners = [(2, 2), (size - 3, 2), (2, size - 3), (size - 3, size - 3)]
    for cx, cy in corners:
        if 0 <= cx < size and 0 <= cy < size:
            pixels[cx, cy] = nail_rgb

    # 5. Vài chấm thớ gỗ nhẹ tạo chất cảm pixel mộc mạc
    grain_pts = [(5, 3), (size - 6, 4), (4, size - 5), (size - 5, size - 5)]
    for gx, gy in grain_pts:
        if 2 <= gx < size - 2 and 2 <= gy < size - 2:
            pixels[gx, gy] = shadow_rgb

    tex = Texture(img)
    tex.filtering = False
    _TEXTURE_CACHE[key] = tex
    return tex


def get_custom_background_texture(
    rel_path: str = "game/assets/background.png",
    blur_radius: int = 4,
) -> Texture:
    """Tải texture hình ảnh nền tùy chỉnh (Sunset Clouds) và làm mờ nhẹ Gaussian Blur tạo Depth of Field."""
    key = f"custom_bg_{rel_path}_blur{blur_radius}"
    if key in _TEXTURE_CACHE:
        return _TEXTURE_CACHE[key]

    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent
    full_path = root / rel_path
    if not full_path.exists():
        full_path = Path(rel_path)

    if full_path.exists():
        img = Image.open(full_path).convert("RGB")
        if blur_radius > 0:
            img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        tex = Texture(img)
        _TEXTURE_CACHE[key] = tex
        return tex

    return get_contrast_bg_texture("#2E3C62", "#070A10")


def get_split_wood_texture(
    cube_index: int,
    is_active: bool = True,
    size: int = 16,
) -> Texture:
    """Tạo texture khối pixel art cơ bản cho 2 nửa khối khi split (Khối 1: Hổ Phách & Khối 2: Gỗ Đỏ)."""
    key = f"split_pixel_wood_{cube_index}_{is_active}_{size}"
    if key in _TEXTURE_CACHE:
        return _TEXTURE_CACHE[key]

    if cube_index == 1:
        base_hex = "#C87832" if is_active else "#7A4818"
        nail_hex = "#2E8B57" if is_active else "#1A4E30"
    else:
        base_hex = "#A64024" if is_active else "#682414"
        nail_hex = "#3A72A4" if is_active else "#204260"

    base_rgb = hex_to_rgb(base_hex)
    nail_rgb = hex_to_rgb(nail_hex)
    dark_border = (max(0, base_rgb[0] - 70), max(0, base_rgb[1] - 48), max(0, base_rgb[2] - 30))
    shadow_rgb = (max(0, base_rgb[0] - 40), max(0, base_rgb[1] - 28), max(0, base_rgb[2] - 18))
    light_rgb = (min(255, base_rgb[0] + 25), min(255, base_rgb[1] + 18), min(255, base_rgb[2] + 12))
    highlight_rgb = (min(255, base_rgb[0] + 55), min(255, base_rgb[1] + 40), min(255, base_rgb[2] + 25))

    img = Image.new("RGB", (size, size), base_rgb)
    pixels = img.load()
    assert pixels is not None

    for x in range(size):
        pixels[x, 0] = dark_border
        pixels[x, size - 1] = dark_border
    for y in range(size):
        pixels[0, y] = dark_border
        pixels[size - 1, y] = dark_border

    for x in range(1, size - 1):
        pixels[x, 1] = highlight_rgb
        pixels[x, size - 2] = shadow_rgb
    for y in range(1, size - 1):
        pixels[1, y] = highlight_rgb
        pixels[size - 2, y] = shadow_rgb

    plank_h = size // 3
    seams = [plank_h, plank_h * 2]
    for sy in seams:
        if 2 <= sy < size - 2:
            for x in range(1, size - 1):
                pixels[x, sy] = shadow_rgb
                if sy + 1 < size - 2:
                    pixels[x, sy + 1] = light_rgb

    corners = [(2, 2), (size - 3, 2), (2, size - 3), (size - 3, size - 3)]
    for cx, cy in corners:
        if 0 <= cx < size and 0 <= cy < size:
            pixels[cx, cy] = nail_rgb

    tex = Texture(img)
    tex.filtering = False
    _TEXTURE_CACHE[key] = tex
    return tex


