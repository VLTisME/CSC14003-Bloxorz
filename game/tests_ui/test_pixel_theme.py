"""Kiểm thử cấu hình Theme và Render cho Pixel Art UI (game/tests_ui/test_pixel_theme.py).

Kiểm tra:
1. PALETTE gồm đúng 29 màu hex hợp lệ và duy nhất.
2. Button Ramps sử dụng đúng các màu nằm trong PALETTE.
3. Các hàm phụ trợ PIXEL_SCALE, px(), snap() tính toán chính xác.
4. Font chữ nạp thành công vào hệ thống.
5. Kiểm tra glyph các chuỗi UI (bộ chuỗi bắt buộc + toàn bộ chuỗi ui.py) không gây crash và cảnh báo đúng.
6. Cấu hình lọc ảnh Nearest-Neighbor toàn cục (Texture.default_filtering == False).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path
from ursina import Texture, Vec2, Vec3

from game.ursina_ui.assets.theme import (
    PALETTE,
    BUTTON_RAMPS,
    ROLES,
    PIXEL_SCALE,
    px,
    snap,
    DEFAULT_FONT_PATH,
    DEFAULT_FONT_NAME,
    FONTS_DIR,
    set_default_font,
    check_missing_glyphs,
    configure_render,
    extract_ui_strings,
    REQUIRED_TEST_STRINGS,
)


class TestPixelTheme(unittest.TestCase):
    """Bộ kiểm thử cho Theme và Cấu hình Render Pixel."""

    def test_palette_29_unique_valid_hex(self) -> None:
        """Kiểm tra PALETTE có đúng 29 màu hex hợp lệ và không trùng lặp."""
        # 1. Số lượng màu đúng 29
        self.assertEqual(len(PALETTE), 29, f"PALETTE phải có đúng 29 màu, hiện có {len(PALETTE)}")

        # 2. 29 màu phải hoàn toàn độc nhất
        unique_hex = set(PALETTE.values())
        self.assertEqual(len(unique_hex), 29, "Các mã hex trong PALETTE phải duy nhất, không trùng lặp")

        # 3. Mọi mã màu đều tuân thủ định dạng #rrggbb
        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        for name, hex_val in PALETTE.items():
            self.assertRegex(hex_val, hex_pattern, f"Màu '{name}' ({hex_val}) không đúng định dạng hex #rrggbb")

        # 4. Mọi màu trong Button Ramps đều phải thuộc PALETTE
        palette_hexes = set(PALETTE.values())
        for ramp_name, colors in BUTTON_RAMPS.items():
            self.assertEqual(len(colors), 4, f"Ramp '{ramp_name}' phải có đúng 4 bước màu")
            for c in colors:
                self.assertIn(c.lower(), [p.lower() for p in palette_hexes], f"Màu {c} trong ramp {ramp_name} không nằm trong PALETTE")

    def test_pixel_scale_and_helpers(self) -> None:
        """Kiểm tra PIXEL_SCALE = 3 và các hàm phụ trợ px(), snap()."""
        self.assertEqual(PIXEL_SCALE, 3)

        # px() nhân đúng tỷ lệ
        self.assertEqual(px(1), 3)
        self.assertEqual(px(2), 6)
        self.assertEqual(px(10), 30)

        # snap() làm tròn về bội số của 3
        self.assertEqual(snap(0), 0)
        self.assertEqual(snap(1), 0)
        self.assertEqual(snap(2), 3)
        self.assertEqual(snap(4), 3)
        self.assertEqual(snap(5), 6)

        # snap() hỗ trợ Vec2, Vec3 và tuple
        v2 = snap(Vec2(2.1, 4.9))
        self.assertAlmostEqual(v2.x, 3.0)
        self.assertAlmostEqual(v2.y, 6.0)

        v3 = snap(Vec3(1.0, 3.0, 7.8))
        self.assertAlmostEqual(v3.x, 0.0)
        self.assertAlmostEqual(v3.y, 3.0)
        self.assertAlmostEqual(v3.z, 9.0)

    def test_font_loads(self) -> None:
        """Kiểm tra file font mặc định tồn tại và nạp thành công vào Panda3D FontPool."""
        self.assertTrue(DEFAULT_FONT_PATH.is_file(), f"Không tìm thấy file font: {DEFAULT_FONT_PATH}")

        from panda3d.core import FontPool
        font = FontPool.loadFont(str(DEFAULT_FONT_PATH))
        self.assertIsNotNone(font, f"Không thể nạp font qua FontPool: {DEFAULT_FONT_PATH}")

        # Thiết lập font mặc định cho Text
        applied_path = set_default_font(DEFAULT_FONT_PATH)
        self.assertEqual(applied_path, DEFAULT_FONT_PATH)

        from ursina import Text
        self.assertIn(Text.default_font, (str(DEFAULT_FONT_PATH), DEFAULT_FONT_NAME))

    def test_all_ui_strings_glyphs(self) -> None:
        """Kiểm tra glyph của các chuỗi UI (bộ bắt buộc + chuỗi trong ui.py)."""
        # 1. Trích xuất thành công các chuỗi từ ui.py
        ui_strings = extract_ui_strings()
        self.assertGreater(len(ui_strings), 0, "Không trích xuất được chuỗi nào từ ui.py")

        all_test_texts = REQUIRED_TEST_STRINGS + ui_strings

        # 2. Hàm check_missing_glyphs hoạt động ổn định, không crash
        missing_pixel = check_missing_glyphs(DEFAULT_FONT_PATH, all_test_texts)
        self.assertIsInstance(missing_pixel, list)

        # Ký tự ASCII / tiếng Anh cơ bản trong các chuỗi UI phải có đầy đủ 100%
        from panda3d.core import FontPool, DynamicTextGlyph
        p_font = FontPool.loadFont(str(DEFAULT_FONT_PATH))
        ascii_chars = set("".join(all_test_texts)) & set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:;!?-+/ ")
        for ch in ascii_chars:
            glyph = p_font.get_glyph(ord(ch))
            self.assertTrue(isinstance(glyph, DynamicTextGlyph), f"Ký tự ASCII '{ch}' bị thiếu glyph trong {DEFAULT_FONT_PATH.name}")

        # 3. Kiểm tra font đầy đủ BeVietnamPro.ttf bao phủ 100% tất cả các chuỗi tiếng Việt
        bev_path = FONTS_DIR / "BeVietnamPro.ttf"
        if bev_path.is_file():
            missing_bev = check_missing_glyphs(bev_path, all_test_texts)
            self.assertEqual(len(missing_bev), 0, f"Font tiếng Việt đầy đủ BeVietnamPro bị thiếu glyph: {missing_bev}")

    def test_nearest_neighbor_configured(self) -> None:
        """Kiểm tra cấu hình Texture.default_filtering đã được bật sang False (Nearest)."""
        configure_render()
        self.assertFalse(Texture.default_filtering, "Texture.default_filtering phải là False (nearest-neighbor)")


if __name__ == "__main__":
    unittest.main()
