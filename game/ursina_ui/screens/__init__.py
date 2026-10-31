"""Các màn hình giao diện (Screens) của Bloxorz Ursina UI."""

from game.ursina_ui.screens.main_menu import MainMenuScreen
from game.ursina_ui.screens.pause_menu import PauseMenuScreen
from game.ursina_ui.screens.win_screen import WinScreen
from game.ursina_ui.screens.lose_screen import LoseScreen
from game.ursina_ui.screens.loading_screen import LoadingScreen
from game.ursina_ui.screens.benchmark_modal import BenchmarkModal

__all__ = [
    "MainMenuScreen",
    "PauseMenuScreen",
    "WinScreen",
    "LoseScreen",
    "LoadingScreen",
    "BenchmarkModal",
]
