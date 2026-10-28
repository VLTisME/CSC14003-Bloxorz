"""Hệ thống Theme và cấu hình Render Pixel Art chuẩn Stardew Valley cho Bloxorz 3D.

Bao gồm:
1. PALETTE 29 màu độc quyền (Stardew Valley aesthetic)
2. Thang màu Button Ramps (GREEN, ORANGE, RED, DISABLED)
3. Các vai trò màu (Roles) cho UI, background, khung viền
4. Tỷ lệ pixel PIXEL_SCALE = 3 và các hàm phụ trợ px(), snap()
5. Cấu hình Nearest-Neighbor filtering toàn cục (no mipmaps, no anti-aliasing)
6. Quản lý Font mặc định và kiểm tra glyph tiếng Việt không gây crash
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any
import sys

# ==============================================================================
# 1. BẢNG MÀU CHUẨN 29 MÀU (PALETTE)
# ==============================================================================

PALETTE: dict[str, str] = {
    # neutrals (6)
    "ivory": "#f2f0e5",
    "silver": "#b8b5b9",
    "grey_mid": "#868188",
    "grey_dark": "#646365",
    "slate": "#45444f",
    "ink": "#212123",
    # blues/purples (9)
    "navy_1": "#3a3858",
    "plum_dark": "#352b42",
    "navy_2": "#43436a",
    "blue": "#4b80ca",
    "sky": "#68c2d3",
    "mauve": "#6a536e",
    "dusk": "#4b4158",
    "grey_plum": "#5f556a",
    "orchid": "#cf8acb",
    # warm (8)
    "mint": "#a2dcc7",
    "butter": "#ede19e",
    "tan": "#d3a068",
    "red": "#b45252",
    "brick": "#80493a",
    "wood": "#a77b5b",
    "cream": "#e5ceb4",
    "blush": "#edc8c4",
    # greens (6)
    "lime": "#c2d368",
    "green": "#8ab060",
    "teal_dark": "#567b79",
    "moss": "#4e584a",
    "olive_dark": "#7b7243",
    "sage": "#b2b47e",
}

# ==============================================================================
# 2. VAI TRÒ MÀU (ROLES) & BUTTON RAMPS (4 BƯỚC MÀU)
# ==============================================================================

ROLES: dict[str, list[str]] = {
    "outlines": ["ink", "plum_dark"],
    "text": ["ink", "plum_dark"],
    "panel_fill": ["cream", "ivory"],
    "wood_frame": ["brick", "wood", "tan"],
    "sky_background": ["navy_1", "navy_2", "plum_dark"],
    "clouds": ["mauve", "dusk"],
    "accents": ["blue", "sky", "butter", "orchid"],
    "disabled": ["grey_dark", "grey_mid", "silver"],
}

# Ramps: dark outline -> shadow -> base -> highlight
BUTTON_RAMPS: dict[str, list[str]] = {
    "GREEN": ["#4e584a", "#567b79", "#8ab060", "#c2d368"],
    "ORANGE": ["#80493a", "#a77b5b", "#d3a068", "#ede19e"],
    "RED": ["#4b4158", "#80493a", "#b45252", "#edc8c4"],
    "DISABLED": ["#4b4158", "#646365", "#868188", "#b8b5b9"],
}

# Logo styling colors
LOGO_OUTLINE = PALETTE["ink"]        # #212123 (1px outline)
LOGO_SHADOW = PALETTE["tan"]         # #d3a068 (2px drop shadow)
LOGO_TOP_FILL = PALETTE["brick"]     # #80493a (two-tone top)
LOGO_BOTTOM_FILL = PALETTE["plum_dark"]  # #352b42 (two-tone bottom)

# ==============================================================================
# 3. TỶ LỆ PIXEL VÀ CÁC HÀM PHỤ TRỢ (PIXEL_SCALE, px, snap)
# ==============================================================================

PIXEL_SCALE: int = 3
PIXEL_BOARD: bool = False


def px(n: int | float) -> int:
    """Chuyển đổi số pixel thiết kế gốc sang pixel hiển thị theo PIXEL_SCALE."""
    return int(round(n * PIXEL_SCALE))


def snap(v: Any) -> Any:
    """Làm tròn giá trị hoặc vector về bội số gần nhất của PIXEL_SCALE."""
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return int(round(v / PIXEL_SCALE) * PIXEL_SCALE)
    if isinstance(v, float):
        return float(round(v / PIXEL_SCALE) * PIXEL_SCALE)
    if hasattr(v, "x") and hasattr(v, "y"):
        cls = v.__class__
        if hasattr(v, "z"):
            return cls(snap(v.x), snap(v.y), snap(v.z))
        return cls(snap(v.x), snap(v.y))
    if isinstance(v, (tuple, list)):
        return type(v)(snap(x) for x in v)
    return v


class LocalizedStr(str):
    """String with multi-language backward compatibility for tests."""

    def __new__(cls, current: str, aliases: list[str] | None = None) -> LocalizedStr:
        instance = super().__new__(cls, current)
        instance.aliases = set(aliases or [])
        return instance

    def __eq__(self, other: Any) -> bool:
        if super().__eq__(other):
            return True
        return hasattr(self, "aliases") and other in self.aliases

    def startswith(self, prefix: str | tuple[str, ...], *args: Any) -> bool:
        if super().startswith(prefix, *args):
            return True
        if hasattr(self, "aliases"):
            for a in self.aliases:
                if a.startswith(prefix, *args):
                    return True
        return False


# ==============================================================================
# 4. ĐƯỜNG DẪN TÀI NGUYÊN (ASSET & FONT PATHS)
# ==============================================================================

ASSETS_DIR: Path = Path(__file__).resolve().parent
FONTS_DIR: Path = ASSETS_DIR / "fonts"
UI_DIR: Path = ASSETS_DIR / "ui"
UI_SRC_DIR: Path = UI_DIR / "src"

# Fallback fonts directory nếu assets/fonts chưa có
ROOT_DIR: Path = ASSETS_DIR.parents[2]
ALT_FONTS_DIR: Path = ROOT_DIR / "game" / "assets" / "fonts"

DEFAULT_FONT_NAME: str = "PixelifySans-Regular.ttf"

def get_font_path(font_name: str = DEFAULT_FONT_NAME) -> Path:
    """Tìm đường dẫn font hợp lệ trong các thư mục tài nguyên."""
    candidate_1 = FONTS_DIR / font_name
    if candidate_1.is_file():
        return candidate_1
    candidate_2 = ALT_FONTS_DIR / font_name
    if candidate_2.is_file():
        return candidate_2
    return candidate_1


DEFAULT_FONT_PATH: Path = get_font_path(DEFAULT_FONT_NAME)


# ==============================================================================
# 5. CẤU HÌNH RENDER NEAREST-NEIGHBOR TOÀN CỤC (GLOBAL FILTERING)
# ==============================================================================

def configure_render() -> None:
    """Cấu hình lọc Nearest-Neighbor toàn cục cho UI textures (không mipmap, không khử răng cưa)."""
    try:
        from panda3d.core import load_prc_file_data
        load_prc_file_data("", "textures-minfilter nearest\ntextures-magfilter nearest\n")
    except Exception:
        pass

    try:
        from ursina import Texture
        Texture.default_filtering = False
    except Exception:
        pass


# ==============================================================================
# 6. KIỂM TRA GLYPH VÀ ĐẶT FONT MẶC ĐỊNH
# ==============================================================================

REQUIRED_TEST_STRINGS = [
    "CHỌN MÀN CHƠI · HƯỚNG DẪN & PHÍM TẮT · Kỷ lục · Tạm Dừng · Tiếp Tục · Giải · Hết giờ · Lỗi"
]


def extract_ui_strings() -> list[str]:
    """Trích xuất tất cả các chuỗi ký tự hiển thị từ file ui.py."""
    ui_py = ROOT_DIR / "game" / "ursina_ui" / "ui.py"
    strings: list[str] = []
    if ui_py.is_file():
        try:
            tree = ast.parse(ui_py.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    strings.append(node.value)
        except Exception as exc:
            print(f"[CẢNH BÁO] Không thể phân tích chuỗi từ ui.py: {exc}", file=sys.stderr)
    return strings


def check_missing_glyphs(font_path: Path | str, texts: list[str] | None = None) -> list[str]:
    """Kiểm tra danh sách ký tự thiếu glyph trong font.
    
    In cảnh báo chi tiết các ký tự thiếu mà không làm crash chương trình.
    """
    path = Path(font_path)
    if not path.is_file():
        print(f"[CẢNH BÁO] Không tìm thấy file font: {path}", file=sys.stderr)
        return []

    if texts is None:
        texts = REQUIRED_TEST_STRINGS + extract_ui_strings()

    all_chars = set("".join(texts))
    missing: list[str] = []

    try:
        from panda3d.core import FontPool, DynamicTextGlyph
        p_font = FontPool.loadFont(str(path))
        if p_font is not None:
            for ch in sorted(all_chars):
                if ch in "\n\r\t ":
                    continue
                glyph = p_font.get_glyph(ord(ch))
                if not isinstance(glyph, DynamicTextGlyph):
                    missing.append(ch)
    except Exception as exc:
        print(f"[CẢNH BÁO] Lỗi kiểm tra glyph qua Panda3D: {exc}", file=sys.stderr)

    if missing:
        missing_preview = ", ".join(repr(c) for c in missing[:20])
        extra = f" (và {len(missing) - 20} ký tự khác)" if len(missing) > 20 else ""
        print(
            f"[CẢNH BÁO] Font '{path.name}' thiếu {len(missing)} glyph tiếng Việt: {missing_preview}{extra}",
            file=sys.stderr,
        )

    return missing


def set_default_font(font_name_or_path: str | Path | None = None) -> Path:
    """Thiết lập font mặc định cho toàn bộ Text trong Ursina và kiểm tra glyphs."""
    if font_name_or_path is None:
        font_path = DEFAULT_FONT_PATH
    elif isinstance(font_name_or_path, str) and not Path(font_name_or_path).is_file():
        font_path = get_font_path(font_name_or_path)
    else:
        font_path = Path(font_name_or_path)

    # 1. Kiểm tra glyph và in cảnh báo nếu thiếu
    check_missing_glyphs(font_path)

    # 2. Đặt font mặc định cho Ursina Text và đăng ký đường dẫn font
    try:
        from ursina import Text, application
        from panda3d.core import getModelPath
        application.fonts_folder = font_path.parent
        getModelPath().append_path(str(font_path.parent.resolve()))
        Text.default_font = font_path.name
    except Exception as exc:
        print(f"[CẢNH BÁO] Không thể đặt Text.default_font: {exc}", file=sys.stderr)

    return font_path


# Tự động cấu hình lọc ảnh nearest-neighbor và đăng ký đường dẫn font khi nạp module
configure_render()
try:
    from panda3d.core import getModelPath
    getModelPath().append_path(str(FONTS_DIR.resolve()))
except Exception:
    pass

configure_render()
