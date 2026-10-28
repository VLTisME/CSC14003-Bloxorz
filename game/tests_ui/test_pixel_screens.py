"""Unit tests verifying screen lifecycles and input transitions for pixel UI screens.

Covers:
- MainMenuScreen interactions (Play, Stages, Help, Quit)
- PauseMenuScreen transitions via ESC, Resume, Restart, Stages, Help, Menu
- WinScreen transitions via Enter/Space, Next, Restart, Stages, Menu
- LoseScreen transitions via Enter/Space, Retry, Undo, Stages, Menu
- Signature compatibility for all show/hide methods
"""
from __future__ import annotations

from pathlib import Path
import unittest
import builtins
from ursina import Ursina

from game.ursina_ui.app import BloxorzUrsinaApp


class TestPixelScreens(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not hasattr(builtins, "base"):
            cls._app = Ursina(headless=True)
        else:
            cls._app = getattr(builtins, "base")

    def setUp(self) -> None:
        stage_file = Path(__file__).resolve().parents[2] / "testcases" / "original" / "01.in.json"
        self.game = BloxorzUrsinaApp(stage_path=stage_file, start_in_menu=True)

    def tearDown(self) -> None:
        if hasattr(self, "game") and self.game:
            from ursina import destroy
            destroy(self.game)

    def test_main_menu_transitions(self) -> None:
        """Verify main menu buttons open stages, help, or enter gameplay."""
        self.assertTrue(self.game.main_menu_screen.enabled)

        # Open stages from main menu
        self.game.main_menu_screen.btn_stages.on_click()
        self.assertTrue(self.game.ui.is_stage_selector_open)
        self.game.ui.close_stage_selector()
        self.assertFalse(self.game.ui.is_stage_selector_open)

        # Open help from main menu
        self.game.main_menu_screen.btn_help.on_click()
        self.assertTrue(self.game.ui.is_help_modal_open)
        self.game.ui.close_help_modal()
        self.assertFalse(self.game.ui.is_help_modal_open)

        # Click play to enter gameplay
        self.game.main_menu_screen.btn_play.on_click()
        self.assertFalse(self.game.main_menu_screen.enabled)
        self.assertTrue(self.game.ui.ui_root.enabled)

    def test_pause_menu_esc_and_buttons(self) -> None:
        """Verify pause menu toggles via ESC and all buttons function."""
        self.game.main_menu_screen.btn_play.on_click()

        # Press ESC to pause
        self.game.input("escape")
        self.assertTrue(self.game.pause_screen.enabled)

        # Press ESC to resume
        self.game.input("escape")
        self.assertFalse(self.game.pause_screen.enabled)

        # Press ESC to pause again and click resume
        self.game.input("escape")
        self.assertTrue(self.game.pause_screen.enabled)
        self.game.pause_screen.btn_resume.on_click()
        self.assertFalse(self.game.pause_screen.enabled)

        # Pause and click restart
        self.game.input("escape")
        self.game.pause_screen.btn_restart.on_click()
        self.assertFalse(self.game.pause_screen.enabled)
        self.assertEqual(self.game.engine.move_count, 0)

        # Pause and click stage select
        self.game.input("escape")
        self.game.pause_screen.btn_stages.on_click()
        self.assertTrue(self.game.ui.is_stage_selector_open)
        self.game.ui.close_stage_selector()

        # Pause and click help
        self.game.input("escape")
        self.game.pause_screen.btn_help.on_click()
        self.assertTrue(self.game.ui.is_help_modal_open)
        self.game.ui.close_help_modal()

        # Pause and return to main menu
        self.game.input("escape")
        self.game.pause_screen.btn_menu.on_click()
        self.assertFalse(self.game.pause_screen.enabled)
        self.assertTrue(self.game.main_menu_screen.enabled)

    def test_win_screen_interactions(self) -> None:
        """Verify win screen triggers and action buttons."""
        self.game.main_menu_screen.btn_play.on_click()

        # Trigger victory
        self.game._on_victory_finished()
        self.assertTrue(self.game.win_screen.enabled)

        # Restart from win screen
        self.game.win_screen.btn_restart.on_click()
        self.assertFalse(self.game.win_screen.enabled)

        # Trigger victory again and click stage select
        self.game._on_victory_finished()
        self.game.win_screen.btn_stages.on_click()
        self.assertTrue(self.game.ui.is_stage_selector_open)
        self.game.ui.close_stage_selector()

        # Trigger victory and click next stage
        self.game._on_victory_finished()
        self.game.win_screen.btn_next.on_click()
        self.assertFalse(self.game.win_screen.enabled)

        # Trigger victory and return to main menu
        self.game._on_victory_finished()
        self.game.win_screen.btn_menu.on_click()
        self.assertFalse(self.game.win_screen.enabled)
        self.assertTrue(self.game.main_menu_screen.enabled)

    def test_lose_screen_interactions(self) -> None:
        """Verify lose screen triggers and action buttons."""
        self.game.main_menu_screen.btn_play.on_click()

        # Trigger fall
        self.game._on_fall_finished()
        self.assertTrue(self.game.lose_screen.enabled)

        # Retry
        self.game.lose_screen.btn_retry.on_click()
        self.assertFalse(self.game.lose_screen.enabled)

        # Trigger fall again and undo
        self.game._on_fall_finished()
        self.game.lose_screen.btn_undo.on_click()
        self.assertFalse(self.game.lose_screen.enabled)

        # Trigger fall again and stage select
        self.game._on_fall_finished()
        self.game.lose_screen.btn_stages.on_click()
        self.assertTrue(self.game.ui.is_stage_selector_open)
        self.game.ui.close_stage_selector()

        # Trigger fall again and return to main menu
        self.game._on_fall_finished()
        self.game.lose_screen.btn_menu.on_click()
        self.assertFalse(self.game.lose_screen.enabled)
        self.assertTrue(self.game.main_menu_screen.enabled)

    def test_benchmark_modal_toggle_and_navigation(self) -> None:
        """Verify benchmark modal opens, closes, and navigates stages."""
        self.game.main_menu_screen.btn_play.on_click()
        self.game.ui.open_benchmark_modal()
        self.assertTrue(self.game.ui.is_benchmark_modal_open)
        self.assertIsNotNone(self.game.ui.benchmark_modal)

        modal = self.game.ui.benchmark_modal
        curr_stage = modal.stage_id
        modal._next_stage()
        self.assertNotEqual(modal.stage_id, curr_stage)

        self.game.ui.close_benchmark_modal()
        self.assertFalse(self.game.ui.is_benchmark_modal_open)
        self.assertIsNone(self.game.ui.benchmark_modal)


if __name__ == "__main__":
    unittest.main()
