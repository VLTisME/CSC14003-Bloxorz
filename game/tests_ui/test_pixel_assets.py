"""Unit tests for Phase 2: Pixel Button & Logo Asset Pipeline."""
from __future__ import annotations

import unittest
from pathlib import Path
from PIL import Image

from game.ursina_ui.assets.theme import PALETTE, BUTTON_RAMPS
from tools.gen_buttons import validate_image_palette, slice_9, generate_button_base_sprite
from tools.gen_logo import generate_logo_text_sprite


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UI_ASSETS_DIR = PROJECT_ROOT / "game" / "ursina_ui" / "assets" / "ui"
BUTTONS_DIR = UI_ASSETS_DIR / "buttons"
SRC_DIR = UI_ASSETS_DIR / "src"
LOGO_DIR = UI_ASSETS_DIR / "logo"
PREVIEW_DIR = PROJECT_ROOT / "docs" / "assets" / "pixel"


class TestPixelAssets(unittest.TestCase):
    """Test suite verifying generated pixel buttons and logo assets."""

    def test_all_16_button_states_exist(self) -> None:
        """Verify that all 16 button states exist as valid files."""
        colors = ["green", "orange", "red", "disabled"]
        states = ["normal", "hover", "pressed", "selected"]

        self.assertTrue(BUTTONS_DIR.exists(), f"Buttons dir {BUTTONS_DIR} does not exist.")

        for color_name in colors:
            for state in states:
                file_path = BUTTONS_DIR / f"btn_{color_name}_{state}.png"
                self.assertTrue(
                    file_path.exists(),
                    f"Missing button sprite: {file_path.name}",
                )
                with Image.open(file_path) as img:
                    self.assertEqual(img.format, "PNG")
                    self.assertGreater(img.width, 0)
                    self.assertGreater(img.height, 0)

    def test_button_base_template_exists(self) -> None:
        """Verify that base template was auto-generated in src directory."""
        base_path = SRC_DIR / "button_base.png"
        self.assertTrue(base_path.exists(), "Missing src/button_base.png template")

    def test_button_pixels_strict_palette_compliance(self) -> None:
        """Verify that 100% of non-transparent pixels in all button files are in PALETTE."""
        for png_file in BUTTONS_DIR.glob("*.png"):
            with Image.open(png_file) as img:
                try:
                    validate_image_palette(img, png_file.name)
                except ValueError as err:
                    self.fail(f"Palette violation in {png_file.name}: {err}")

    def test_slice_9_scaling_palette_compliance(self) -> None:
        """Verify that 9-slice resizing preserves pixel purity and stays strictly within PALETTE."""
        test_sprite = generate_button_base_sprite(BUTTON_RAMPS["GREEN"], "normal", 24)
        scaled_wide = slice_9(test_sprite, 96, 32, c=6)
        scaled_tall = slice_9(test_sprite, 32, 64, c=6)

        try:
            validate_image_palette(scaled_wide, "scaled_wide")
            validate_image_palette(scaled_tall, "scaled_tall")
        except ValueError as err:
            self.fail(f"9-slice scaling introduced invalid colors: {err}")

    def test_logo_assets_exist_and_comply(self) -> None:
        """Verify that logo_title.png and logo_sub.png exist and strictly comply with PALETTE."""
        title_path = LOGO_DIR / "logo_title.png"
        sub_path = LOGO_DIR / "logo_sub.png"

        self.assertTrue(title_path.exists(), "Missing logo_title.png")
        self.assertTrue(sub_path.exists(), "Missing logo_sub.png")

        with Image.open(title_path) as title_img:
            self.assertEqual(title_img.format, "PNG")
            validate_image_palette(title_img, "logo_title.png")

        with Image.open(sub_path) as sub_img:
            self.assertEqual(sub_img.format, "PNG")
            validate_image_palette(sub_img, "logo_sub.png")

    def test_preview_contact_sheets_exist_and_comply(self) -> None:
        """Verify that preview contact sheets exist and adhere strictly to PALETTE."""
        btn_preview = PREVIEW_DIR / "preview_buttons.png"
        logo_preview = PREVIEW_DIR / "preview_logo.png"

        self.assertTrue(btn_preview.exists(), "Missing preview_buttons.png")
        self.assertTrue(logo_preview.exists(), "Missing preview_logo.png")

        with Image.open(btn_preview) as img:
            validate_image_palette(img, "preview_buttons.png")

        with Image.open(logo_preview) as img:
            validate_image_palette(img, "preview_logo.png")


if __name__ == "__main__":
    unittest.main()
