import builtins
import unittest
from ursina import Ursina, destroy, Entity, camera

from game.ursina_ui.assets.theme import PALETTE, PIXEL_SCALE, snap, set_default_font
from game.ursina_ui.pixel_widgets import (
    PixelPanel,
    PixelButton,
    PixelTab,
    PixelLevelTile,
    PixelCloseButton,
    get_pixel_button_texture,
    get_pixel_panel_texture,
)

if not hasattr(builtins, "base"):
    _app = Ursina(headless=True)
set_default_font()


class TestPixelWidgets(unittest.TestCase):
    """Test suite for pixel art UI widgets in Ursina."""

    def setUp(self) -> None:
        self.root = Entity(name="test_ui_root")

    def tearDown(self) -> None:
        destroy(self.root)

    def test_pixel_button_creation_and_ramps(self) -> None:
        """Verify PixelButton creates properly across all color ramps."""
        for ramp in ("green", "orange", "red", "disabled"):
            btn = PixelButton(
                parent=self.root,
                text=f"BTN_{ramp.upper()}",
                color_ramp=ramp,
                scale=(0.14, 0.05),
                position=(0, 0, 0),
            )
            self.assertEqual(btn.color_ramp, ramp)
            self.assertIsNotNone(btn.texture)
            self.assertFalse(btn.texture.filtering)  # Nearest-neighbor verified

    def test_pixel_button_states_and_transitions(self) -> None:
        """Verify PixelButton transitions through normal, hover, pressed, and selected states."""
        btn = PixelButton(parent=self.root, text="CLICK", color_ramp="green")

        initial_tex = btn.texture
        btn.set_state("hover")
        self.assertEqual(btn._state, "hover")
        self.assertIsNotNone(btn.texture)

        btn.set_state("pressed")
        self.assertEqual(btn._state, "pressed")

        btn.is_selected = True
        self.assertTrue(btn.is_selected)
        self.assertEqual(btn._state, "selected")

        btn.is_selected = False
        self.assertFalse(btn.is_selected)
        self.assertEqual(btn._state, "normal")

    def test_pixel_button_disabled_state(self) -> None:
        """Verify PixelButton disabled property uses disabled ramp and prevents interaction."""
        btn = PixelButton(parent=self.root, text="DISABLED", color_ramp="orange")
        btn.disabled = True
        self.assertTrue(btn.disabled)

        # Entering mouse when disabled should not change state
        btn.on_mouse_enter()
        self.assertNotEqual(btn._state, "hover")

    def test_pixel_tab_active_toggle(self) -> None:
        """Verify PixelTab updates color ramp and active state."""
        tab = PixelTab(parent=self.root, text="MAIN STAGES", tab_id="main", is_active=False)
        self.assertFalse(tab.is_selected)
        self.assertEqual(tab.color_ramp, "disabled")

        tab.set_active(True)
        self.assertTrue(tab.is_selected)
        self.assertEqual(tab.color_ramp, "orange")

        tab.set_active(False)
        self.assertFalse(tab.is_selected)
        self.assertEqual(tab.color_ramp, "disabled")

    def test_pixel_level_tile_states(self) -> None:
        """Verify PixelLevelTile formats labels and color ramps for current, won, and unplayed stages."""
        # 1. Current stage
        tile_curr = PixelLevelTile(parent=self.root, stage_id="stage01", is_current=True)
        self.assertIn("STAGE 01", tile_curr.text)
        self.assertIn("PLAYING", tile_curr.text)
        self.assertEqual(tile_curr.color_ramp, "orange")

        # 2. Won stage
        tile_won = PixelLevelTile(parent=self.root, stage_id="stage02", is_won=True, best_moves=14)
        self.assertIn("STAGE 02", tile_won.text)
        self.assertIn("14 steps", tile_won.text)
        self.assertEqual(tile_won.color_ramp, "green")

        # 3. Unplayed stage
        tile_unplayed = PixelLevelTile(parent=self.root, stage_id="stage03", ref_len=20)
        self.assertIn("STAGE 03", tile_unplayed.text)
        self.assertIn("20b opt", tile_unplayed.text)
        self.assertEqual(tile_unplayed.color_ramp, "disabled")

    def test_pixel_close_button(self) -> None:
        """Verify PixelCloseButton has red ramp and 'X' text."""
        clicked = False

        def on_click():
            nonlocal clicked
            clicked = True

        close_btn = PixelCloseButton(parent=self.root, on_click=on_click)
        self.assertEqual(close_btn.text, "X")
        self.assertEqual(close_btn.color_ramp, "red")

        if close_btn.on_click:
            close_btn.on_click()
        self.assertTrue(clicked)

    def test_pixel_panel_modal_dismissal(self) -> None:
        """Verify PixelPanel opens with title/subtitle, and closes on on_close."""
        closed = False

        def handle_close():
            nonlocal closed
            closed = True

        panel = PixelPanel(
            title="SELECT STAGE",
            subtitle="Choose a stage to play",
            close_button=True,
            on_close=handle_close,
        )
        self.assertEqual(panel.txt_title.text, "SELECT STAGE")
        self.assertEqual(panel.txt_subtitle.text, "Choose a stage to play")
        self.assertIsNotNone(panel.btn_close)

        panel.close()
        self.assertTrue(closed)


if __name__ == "__main__":
    unittest.main()
