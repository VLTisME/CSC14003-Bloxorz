"""Ứng dụng giao diện 3D chính (Main Ursina Application) cho Bloxorz Studio.

Điều phối toàn bộ các thành phần:
- BloxorzEngine (logic trò chơi chuẩn)
- StageCatalog (39 màn chơi & tiến độ hoàn thành)
- BoardView (bàn cờ 3D, cầu, công tắc, hố đích)
- BlockView (khối gỗ 3D và 2 khối tách rời)
- BlobShadow (bóng mềm siêu nhẹ)
- CameraRig (camera Isometric)
- AnimationManager (lăn Rodrigues, rơi vực, chiến thắng)
- ParticlePool (hạt bụi tiếp đất & pháo giấy chiến thắng)
- UIManager (HUD đỉnh, Replay đáy, Bảng chọn màn, Hướng dẫn)
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import queue
import subprocess
import sys
from threading import Thread
from typing import TYPE_CHECKING
from game.search_controller import SearchController, SearchStatus
from ursina import (
    AmbientLight,
    DirectionalLight,
    Entity,
    Ursina,
    Vec2,
    Vec3,
    application,
    camera,
    color,
    destroy,
    time,
    window,
)

from game.engine import BloxorzEngine, Posture
from game.stage_catalog import StageCatalog
from game.theme import get_theme, get_ursina_config, setup_ui_font
from game.ursina_ui.anim import AnimationManager
from game.ursina_ui.block_view import BlockView
from game.ursina_ui.board_view import BoardView
from game.ursina_ui.camera_rig import CameraRig
from game.ursina_ui.input_controller import InputController
from game.ursina_ui.materials import get_custom_background_texture
from game.ursina_ui.particles import ParticlePool
from game.ursina_ui.screens.loading_screen import LoadingScreen
from game.ursina_ui.screens.lose_screen import LoseScreen
from game.ursina_ui.screens.main_menu import MainMenuScreen
from game.ursina_ui.screens.pause_menu import PauseMenuScreen
from game.ursina_ui.screens.win_screen import WinScreen
from game.ursina_ui.shadows import BlobShadow
from game.ursina_ui.state_manager import GameState, StateManager
from game.ursina_ui.ui import UIManager
from checker import check as check_answer

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class BloxorzUrsinaApp(Entity):
    """Lớp điều khiển chính của toàn bộ trò chơi Bloxorz trên nền Ursina."""

    def __init__(
        self,
        stage_path: Path | None = None,
        replay_path: Path | None = None,
        theme_name: str = "toy",
        start_in_menu: bool = False,
        debug: bool = False,
        show_loading: bool = False,
    ) -> None:
        super().__init__(name="bloxorz_game_controller")

        # Khởi tạo font chữ Be Vietnam Pro hỗ trợ tiếng Việt toàn diện cho Ursina
        setup_ui_font()

        self.debug = debug
        self.theme_name = theme_name
        self.theme = get_theme(theme_name)
        self.cfg = get_ursina_config()

        # Thiết lập cửa sổ
        window.title = "Bloxorz 3D Studio (Ursina Engine)"
        window.borderless = False
        window.fullscreen = False
        window.exit_button.visible = False
        window.fps_counter.enabled = False
        window.entity_counter.enabled = False
        window.collider_counter.enabled = False
        window.vsync = True
        window.color = color.hex("#4E6075")

        # Ánh sáng 3D
        self.setup_lighting()

        # Nền pixel art hoàng hôn (Sunset Clouds) làm mờ nhẹ Depth of Field
        bg_blur = int(self.cfg.get("bg_blur_radius", 4))
        self.bg_glow = Entity(
            name="sunset_bg_glow",
            parent=camera,
            model="quad",
            scale=Vec2(100, 100),
            z=70,
            texture=get_custom_background_texture(blur_radius=bg_blur),
            color=color.white,
            transparent=False,
            unlit=True,
        )

        # Khởi tạo dữ liệu và hệ thống con
        self.catalog = StageCatalog()
        self.engine = BloxorzEngine()

        self.camera_rig = CameraRig()
        self.board_view = BoardView(theme_name=self.theme_name)
        self.block_view = BlockView(theme_name=self.theme_name)
        self.shadow = BlobShadow()
        self.particles = ParticlePool(capacity=60)

        self.anim = AnimationManager(
            block_view=self.block_view,
            board_view=self.board_view,
            shadow=self.shadow,
            particles=self.particles,
        )

        # Quản lý trạng thái FSM (State Machine)
        self.state_manager = StateManager(
            initial_state=GameState.MAIN_MENU if start_in_menu else GameState.PLAYING
        )

        # Bộ điều khiển nhập liệu và watchdog an toàn
        self.input_controller = InputController(
            on_move=self.make_move,
            is_busy_fn=lambda: self.anim.is_busy,
            is_playing_fn=lambda: self.engine.is_playing and self.state_manager.is_playing,
            on_watchdog_timeout=self._on_watchdog_timeout,
            max_queue_size=2,
            initial_repeat_delay=0.22,
            repeat_interval=0.16,
            max_lock_duration=2.5,
            enable_hold_repeat=False,
            debug=self.debug,

        )

        # Quản lý Replay tự động
        self.replay_actions: list[str] = []
        self.replay_index: int = 0
        self.is_replay_playing: bool = False
        self.replay_timer: float = 0.0
        self.replay_interval: float = 0.35
        self.current_replay_file: str | None = None

        # Bộ điều khiển solver chạy nền có hỗ trợ Pause/Resume/Cancel cho cả 4 thuật toán
        self.search_controller = SearchController()
        self._selected_algorithm: str = "A*"
        self._solver_stage_id: str | None = None
        self._solver_algorithm: str = "A*"
        self._solver_generation: int = 0
        self._solver_start_move_count: int = 0

        # Giao diện HUD 2D
        self.ui = UIManager(
            catalog=self.catalog,
            on_select_stage=self.load_stage_by_id,
            on_undo=self.action_undo,
            on_reset=self.action_reset,
            on_toggle_cube=self.action_toggle_cube,
            on_replay_play_pause=self.action_replay_toggle,
            on_replay_step_forward=self.action_replay_step_forward,
            on_replay_step_back=self.action_replay_step_back,
            on_replay_jump_start=self.action_replay_jump_start,
            on_replay_jump_end=self.action_replay_jump_end,
            on_replay_load_file=self.action_replay_load_custom,
            on_speed_change=self.set_speed_mult,
            on_solve_astar=self.action_solve_astar,
            on_cycle_algorithm=self.action_cycle_algorithm,
            on_solve=self.action_solve_current,
            on_load_benchmark_solution=self.action_load_solution_actions,
        )

        # Màn hình Menu chính và các Menu trạng thái
        self.main_menu_screen = MainMenuScreen(
            on_play=self._menu_play,
            on_select_stage=self._menu_select_stage,
            on_help=self._menu_help,
            on_quit=application.quit,
        )
        self.pause_screen = PauseMenuScreen(
            on_resume=self.action_resume,
            on_restart=self.action_reset,
            on_select_stage=self._menu_select_stage,
            on_help=self._menu_help,
            on_main_menu=self.action_main_menu,
        )
        self.win_screen = WinScreen(
            on_next_stage=self.action_next_stage,
            on_restart=self.action_reset,
            on_select_stage=self._menu_select_stage,
            on_main_menu=self.action_main_menu,
        )
        self.lose_screen = LoseScreen(
            on_retry=self.action_reset,
            on_undo=self.action_undo,
            on_select_stage=self._menu_select_stage,
            on_main_menu=self.action_main_menu,
        )

        # Bọc hook mở/đóng modal của UIManager để đồng bộ trạng thái FSM
        orig_open_stages = self.ui.open_stage_selector
        def wrapped_open_stages() -> None:
            if self.state_manager.current_state != GameState.LEVEL_SELECT:
                self.state_manager.push_state(GameState.LEVEL_SELECT)
            orig_open_stages()
        self.ui.open_stage_selector = wrapped_open_stages

        orig_close_stages = self.ui.close_stage_selector
        def wrapped_close_stages() -> None:
            was_open = self.ui.is_stage_selector_open
            orig_close_stages()
            if was_open:
                self._on_modal_closed()
        self.ui.close_stage_selector = wrapped_close_stages

        orig_open_help = self.ui.open_help_modal
        def wrapped_open_help() -> None:
            if self.state_manager.current_state != GameState.HELP:
                self.state_manager.push_state(GameState.HELP)
            orig_open_help()
        self.ui.open_help_modal = wrapped_open_help

        orig_close_help = self.ui.close_help_modal
        def wrapped_close_help() -> None:
            was_open = self.ui.is_help_modal_open
            orig_close_help()
            if was_open:
                self._on_modal_closed()
        self.ui.close_help_modal = wrapped_close_help

        # Nạp màn chơi ban đầu
        if stage_path and stage_path.exists():
            self.load_stage_from_file(stage_path, replay_path=replay_path)
        else:
            self.load_stage_by_id("01", replay_path=replay_path)

        # Áp dụng tỉ lệ nền ban đầu
        self._update_background_scale()

        self.start_in_menu = start_in_menu
        self.loading_screen: LoadingScreen | None = None

        # Hiển thị Loading Screen hoặc chuyển thẳng tới màn hình đầu
        if show_loading and not getattr(application, "headless", False):
            self.ui.ui_root.enabled = False
            self.main_menu_screen.hide()
            self.loading_screen = LoadingScreen(
                on_complete=self._on_loading_complete,
                duration=0.6,
            )
        else:
            if start_in_menu:
                self.ui.ui_root.enabled = False
                self.main_menu_screen.show()
                self.state_manager.transition_to(GameState.MAIN_MENU)
            else:
                self.ui.ui_root.enabled = True
                self.main_menu_screen.hide()

    def _on_loading_complete(self) -> None:
        """Callback khi màn hình tải hoàn tất."""
        self.loading_screen = None
        if self.start_in_menu:
            self.ui.ui_root.enabled = False
            self.main_menu_screen.show()
            self.state_manager.transition_to(GameState.MAIN_MENU)
        else:
            self.ui.ui_root.enabled = True
            self.main_menu_screen.hide()



    def setup_lighting(self) -> None:
        """Thiết lập hệ thống ánh sáng 3D Isometric hài hòa."""
        self.dlight = DirectionalLight(y=24, z=18, x=-12, shadows=False)
        self.dlight.look_at(Vec3(0, 0, 0))
        self.alight = AmbientLight(color=color.rgba(0.55, 0.60, 0.60, 1.0))

    def load_stage_by_id(self, stage_id: str, replay_path: Path | None = None) -> None:
        """Nạp màn chơi dựa trên ID (ví dụ: '01', 'sample04')."""
        meta = self.catalog.stage_by_id.get(stage_id)
        if meta and meta["input_path"].exists():
            self.load_stage_from_file(meta["input_path"], replay_path=replay_path)
        else:
            # Fallback tìm kiếm trong thư mục testcases
            for s in ("original", "samples"):
                cand = ROOT_DIR / "testcases" / s / f"{stage_id}.in.json"
                if cand.exists():
                    self.load_stage_from_file(cand, replay_path=replay_path)
                    return

    @property
    def _astar_running(self) -> bool:
        return self.search_controller.is_running

    @property
    def _astar_generation(self) -> int:
        return self._solver_generation

    @_astar_generation.setter
    def _astar_generation(self, value: int) -> None:
        self._solver_generation = value

    @property
    def selected_algorithm(self) -> str:
        return self._selected_algorithm

    @selected_algorithm.setter
    def selected_algorithm(self, value: str) -> None:
        self._selected_algorithm = value
        if hasattr(self, "ui") and hasattr(self.ui, "set_selected_algorithm"):
            self.ui.set_selected_algorithm(value)

    def load_stage_from_file(self, stage_path: Path, replay_path: Path | None = None) -> None:
        """Nạp màn chơi từ đường dẫn file .in.json cụ thể."""
        self._solver_generation += 1
        self._solver_stage_id = None
        self.search_controller.cancel()
        self.ui.set_solver_state(SearchStatus.IDLE)
        self.anim.stop_all()
        self.is_replay_playing = False
        self.ui.set_replay_play_state(False)
        self.input_controller.reset()

        if hasattr(self, "pause_screen"):
            self.pause_screen.hide()
        if hasattr(self, "win_screen"):
            self.win_screen.hide()
        if hasattr(self, "lose_screen"):
            self.lose_screen.hide()
        if hasattr(self, "main_menu_screen"):
            self.main_menu_screen.hide()
        if hasattr(self, "state_manager"):
            self.state_manager.transition_to(GameState.PLAYING)
        if hasattr(self, "ui") and hasattr(self.ui, "ui_root"):
            self.ui.ui_root.enabled = True

        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))
        self.engine.load_stage(stage_data)

        # Dựng lại bàn cờ và khối 3D
        self.board_view.load_stage(self.engine)
        self.block_view.sync_from_engine(self.engine)

        # Canh giữa Camera theo kích thước sàn
        self.camera_rig.focus_board(
            min_r=self.board_view.min_r,
            max_r=self.board_view.max_r,
            min_c=self.board_view.min_c,
            max_c=self.board_view.max_c,
        )

        # Cập nhật bóng ban đầu
        self._update_shadow_state()

        # Chỉ nạp file replay nếu được chỉ định rõ ràng qua tham số CLI hoặc tải file
        if replay_path and replay_path.exists():
            self._load_replay_file(replay_path)
        else:
            self.replay_actions.clear()
            self.replay_index = 0
            self.current_replay_file = None
            self.ui.inp_replay_path.text = ""
            self.ui.update_replay_status(0, 0)

        # Cập nhật HUD
        self.ui.update_hud(self.engine)
        self._sync_replay_button()

    def _load_replay_file(self, replay_path: Path) -> None:
        """Đọc danh sách các bước đi từ file .out.json."""
        try:
            ans_data = json.loads(replay_path.read_text(encoding="utf-8"))
            self.replay_actions = ans_data.get("actions", [])
            self.replay_index = 0
            self.current_replay_file = replay_path.name
            self.ui.inp_replay_path.text = replay_path.name
            self.ui.update_replay_status(0, len(self.replay_actions), self.current_replay_file)
        except Exception as ex:
            print(f"[REPLAY] Lỗi khi nạp file replay: {ex}")
            self.replay_actions.clear()
            self.replay_index = 0
            self.ui.update_replay_status(0, 0)
        self._sync_replay_button()

    def action_replay_load_custom(self, path_str: str) -> None:
        """Nạp file replay do người dùng gõ vào ô nhập."""
        p = Path(path_str)
        if not p.is_absolute():
            p = ROOT_DIR / p
        if p.exists() and p.is_file():
            self._load_replay_file(p)
        else:
            print(f"[REPLAY] Không tìm thấy file: {p}")

    def action_load_solution_actions(self, actions: list[str]) -> None:
        """Nạp trực tiếp danh sách actions lời giải từ Benchmark vào hệ thống Replay."""
        if not actions:
            return
        self.action_reset()
        self.replay_actions = list(actions)
        self.replay_index = 0
        self.current_replay_file = None
        self.ui.update_replay_status(0, len(self.replay_actions))
        self._sync_replay_button()
        print(f"[REPLAY] Đã nạp thành công {len(actions)} bước vào Replay từ Benchmark!")

    def _classify_fall_case(
        self,
        from_cells: list[tuple[int, int]],
        direction: str,
        is_split: bool,
        reason: str,
    ) -> tuple[str, dict | None, tuple[int, int] | None]:
        """Phân loại chính xác 8 kịch bản rơi trong Bloxorz để khối không rơi xuyên sàn."""
        # 1. Kịch bản 1: UPRIGHT đè vỡ gạch mỏng (FRAGILE_CRUMBLE)
        if "fragile" in reason.lower():
            fragile_pos = None
            import re
            m = re.search(r"\((\d+),\s*(\d+)\)", reason)
            if m:
                fragile_pos = (int(m.group(1)), int(m.group(2)))
            elif from_cells:
                fragile_pos = from_cells[0]
            return "FRAGILE_CRUMBLE", {"pos": fragile_pos}, fragile_pos

        # 2. Kịch bản 8: Chế độ tách 2 khối độc lập (SPLIT_CUBE_FALL)
        if is_split:
            return "SPLIT_CUBE_FALL", {"direction": direction}, None

        dir_map = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}
        dr, dc = dir_map.get(direction, (0, 0))

        def is_cell_solid(p: tuple[int, int]) -> bool:
            if self.engine.replay is None:
                return False
            ch = self.engine.cells.get(p, "#")
            if ch == "#":
                return False
            if ch == "B":
                bridge_idx = self.engine.replay.bridge_cells.get(p)
                if bridge_idx is not None and not self.engine.is_bridge_active(bridge_idx):
                    return False
            return True

        if len(from_cells) == 1:
            # Khối đang đứng thẳng (UPRIGHT)
            s = from_cells[0]
            p_near = (s[0] + dr, s[1] + dc)
            p_far = (s[0] + 2 * dr, s[1] + 2 * dc)

            near_solid = is_cell_solid(p_near)
            far_solid = is_cell_solid(p_far)

            if near_solid and not far_solid:
                # Kịch bản 3: UPRIGHT lăn qua mép: 1 ô sàn, 1 ô vực
                return "UPRIGHT_OVERHANG_CLIFF", {"p_near": p_near, "p_far": p_far, "direction": direction}, None
            elif not near_solid and far_solid:
                # Kịch bản hẫng chân ô gần
                return "UPRIGHT_DROP_NEAR", {"p_near": p_near, "p_far": p_far, "direction": direction}, None
            else:
                # Kịch bản 2: UPRIGHT lăn vào khoảng trống toàn phần
                return "UPRIGHT_TOTAL_VOID", {"direction": direction}, None

        elif len(from_cells) == 2:
            # Khối đang nằm ngang hoặc dọc
            c1, c2 = from_cells[0], from_cells[1]
            is_horizontal = (c1[0] == c2[0])
            is_vertical = (c1[1] == c2[1])

            # Nếu lăn dọc theo chiều dài -> thành đứng thẳng ở 1 ô duy nhất
            if (is_horizontal and direction in ("L", "R")) or (is_vertical and direction in ("U", "D")):
                # Kịch bản 6: HORIZONTAL/VERTICAL lăn dọc thành đứng vào vực
                return "LONGITUDINAL_TIP_VOID", {"direction": direction}, None

            # Nếu lăn ngang (bề rộng 2 ô)
            t1 = (c1[0] + dr, c1[1] + dc)
            t2 = (c2[0] + dr, c2[1] + dc)
            t1_solid = is_cell_solid(t1)
            t2_solid = is_cell_solid(t2)

            if t1_solid and not t2_solid:
                # Kịch bản 4: HORIZONTAL/VERTICAL vắt qua mép nghiêng về phía trống
                return "LATERAL_TEETER_TIP", {"solid": t1, "void": t2, "direction": direction}, None
            elif not t1_solid and t2_solid:
                # Kịch bản 4: HORIZONTAL/VERTICAL vắt qua mép nghiêng về phía trống
                return "LATERAL_TEETER_TIP", {"solid": t2, "void": t1, "direction": direction}, None
            else:
                # Kịch bản 5: HORIZONTAL/VERTICAL lăn ngang vào vực toàn phần
                return "LATERAL_TOTAL_VOID", {"direction": direction}, None

        return "UPRIGHT_TOTAL_VOID", {"direction": direction}, None

    def make_move(self, direction: str) -> bool:
        """Thực hiện một bước di chuyển (U/D/L/R) có hoạt ảnh 3D."""
        if self.anim.is_busy or not self.engine.is_playing or not self.state_manager.is_playing:
            return False

        is_split = self.engine.is_split
        is_cube_2 = (self.engine.selected_cube == 2) if is_split else False
        if is_split:
            from_cells = [self.engine.state.second] if is_cube_2 else [self.engine.state.first]
        else:
            from_cells = list(self.engine.block_cells)

        # Thử di chuyển trên engine
        success = self.engine.step(direction)

        if success:
            # 1. Bước đi hợp lệ
            self.anim.start_roll(
                from_cells=from_cells,
                direction=direction,
                is_cube_2=is_cube_2,
                is_split=is_split,
                on_complete=self._on_move_finished,
            )
            return True

        elif self.engine.is_lost:
            # 2. Bước đi gây thua (rơi xuống vực hoặc vỡ gạch mỏng)
            # BỎ HẲN BÓNG NGAY TỪ FRAME ĐẦU TIÊN CỦA BƯỚC ĐI THUA
            self.shadow.suppress()
            reason = self.engine.lost_reason or ""
            fall_type, fall_data, fragile_pos = self._classify_fall_case(from_cells, direction, is_split, reason)

            self.anim.start_roll(
                from_cells=from_cells,
                direction=direction,
                is_cube_2=is_cube_2,
                is_split=is_split,
                is_losing_move=True,
                on_complete=lambda: self.anim.start_fall(
                    direction=direction,
                    reason=reason,
                    fragile_pos=fragile_pos,
                    fall_type=fall_type,
                    fall_data=fall_data,
                    on_complete=self._on_fall_finished,
                ),
            )
            self.ui.update_hud(self.engine)
            return False

        return False

    def _update_shadow_state(self) -> None:
        """Cập nhật bóng đổ blob khớp hoàn hảo theo vị trí các khối (kể cả khi split tách rời)."""
        if self.engine.is_split and self.engine.state is not None:
            r1, c1 = self.engine.state.first
            r2, c2 = self.engine.state.second
            c1_y = self.block_view.cube_1.y if self.block_view.cube_1 else 0.5
            c2_y = self.block_view.cube_2.y if self.block_view.cube_2 else 0.5
            self.shadow.update_transform(
                world_x=float(c1),
                world_z=-float(r1),
                block_y=c1_y,
                posture=Posture.SPLIT,
                is_split=True,
                cube_2_pos=(float(c2), c2_y, -float(r2)),
            )
        else:
            w_bounds = self.block_view.get_world_bounds(self.engine)
            self.shadow.update_transform(
                world_x=w_bounds[0],
                world_z=w_bounds[2],
                block_y=w_bounds[1],
                posture=w_bounds[3],
                is_split=False,
                cube_2_pos=None,
            )

    def _on_move_finished(self) -> None:
        """Gọi khi khối vừa hoàn thành cú lăn chạm đất."""
        self.block_view.sync_from_engine(self.engine)
        self.ui.update_hud(self.engine)
        self._update_shadow_state()
        self._sync_replay_button()

        # Kiểm tra chiến thắng
        if self.engine.is_won:
            self.catalog.record_win(self.engine.stage_id, self.engine.move_count)
            self.catalog.save_progress()
            self.anim.start_victory(on_complete=self._on_victory_finished)

        # Thông báo hoàn tất nước đi cho hàng đợi input
        self.input_controller.on_animation_complete()


    def _on_watchdog_timeout(self) -> None:
        """Giải phóng khẩn cấp khi animation bị kẹt quá lâu."""
        if self.debug:
            print("[WATCHDOG] Cảnh báo: Animation bị kẹt, gọi anim.stop_all() để khôi phục điều khiển.")
        self.anim.stop_all()
        self.block_view.sync_from_engine(self.engine)

    def action_cycle_algorithm(self, target_algo: str | None = None) -> None:
        """Đặt thuật toán trực tiếp (nếu có target_algo) hoặc luân phiên: A* -> BFS -> DFS -> UCS -> A*."""
        algos = ["A*", "BFS", "DFS", "UCS"]
        if target_algo and target_algo in algos:
            next_algo = target_algo
        else:
            idx = algos.index(self.selected_algorithm) if self.selected_algorithm in algos else 0
            next_algo = algos[(idx + 1) % len(algos)]

        # Nếu solver đang chạy hoặc tạm dừng, hủy lượt giải cũ
        if self.search_controller.is_running:
            self._solver_generation += 1
            self._solver_stage_id = None
            self.search_controller.cancel()

        self.selected_algorithm = next_algo
        self.ui.set_selected_algorithm(next_algo)
        self.ui.set_solver_state(SearchStatus.IDLE)

    def action_solve_current(self) -> None:
        """Chạy hoặc tạm dừng / tiếp tục thuật toán đang được lựa chọn."""
        if self.search_controller.is_paused:
            print(f"[SOLVER] Tiếp tục quá trình tìm kiếm {self.selected_algorithm}...")
            self.search_controller.resume()
            self.ui.set_solver_state(SearchStatus.RUNNING, "Tạm Dừng")
            return

        if self.search_controller.is_running:
            print(f"[SOLVER] Tạm dừng quá trình tìm kiếm {self.selected_algorithm}...")
            self.search_controller.pause()
            self.ui.set_solver_state(SearchStatus.PAUSED, "Tiếp Tục")
            return

        if self.engine.stage is None:
            self.ui.set_solver_state(SearchStatus.FAILED, "Chưa có màn", failed=True)
            return

        if self.engine.move_count or not self.engine.is_playing:
            self.action_reset()

        self._solver_generation += 1
        self._solver_stage_id = self.engine.stage_id
        self._solver_algorithm = self.selected_algorithm
        self._solver_start_move_count = self.engine.move_count
        self.replay_actions.clear()
        self.replay_index = 0
        self.current_replay_file = None
        self.ui.update_replay_status(0, 0)

        st_id = self.engine.stage_id or "hiện tại"
        print(f"[SOLVER] >>> Bắt đầu tìm kiếm trực tiếp (live search) bằng thuật toán {self.selected_algorithm} trên màn {st_id}...")
        self.search_controller.start(
            stage=self.engine.stage,
            algorithm=self.selected_algorithm,
            generation=self._solver_generation,
            timeout=60.0,
        )
        self.ui.set_solver_state(SearchStatus.RUNNING, "Tạm Dừng", info=f"Đang giải {self.selected_algorithm}...")

    def action_solve_astar(self) -> None:
        """Hành động giải A* (tương thích ngược với các test case)."""
        if not self.search_controller.is_running and self.selected_algorithm != "A*":
            self.selected_algorithm = "A*"
            self.ui.set_selected_algorithm("A*")
        self.action_solve_current()

    def _poll_astar_results(self) -> None:
        """Xử lý kết quả trả về từ luồng solver chạy nền."""
        res = self.search_controller.poll()
        if res is None:
            return

        # 1. Đảm bảo đúng thế hệ (generation) của lượt tìm kiếm
        if res.generation != self._solver_generation:
            return

        # 2. Đảm bảo stage hiện tại vẫn trùng khớp với stage lúc bắt đầu giải
        if self.engine.stage_id != self._solver_stage_id:
            return

        # 3. Đảm bảo đúng thuật toán đang yêu cầu
        if res.algorithm != self._solver_algorithm:
            return

        if res.status == SearchStatus.CANCELLED:
            self.ui.set_solver_state(SearchStatus.IDLE)
            return

        if res.status == SearchStatus.TIMEOUT:
            self.ui.set_solver_state(SearchStatus.TIMEOUT, f"{res.algorithm}: Hết giờ", failed=True, info=res.error_message)
            print(f"[SOLVER] [{res.algorithm}] Hết thời gian tìm kiếm (timeout): {res.error_message}", file=sys.stderr)
            return

        if res.status == SearchStatus.FAILED:
            self.ui.set_solver_state(SearchStatus.FAILED, f"{res.algorithm}: Lỗi", failed=True, info=res.error_message)
            print(f"[SOLVER] [{res.algorithm}] Lỗi trong quá trình tìm kiếm: {res.error_message}", file=sys.stderr)
            return

        if res.status == SearchStatus.COMPLETED:
            ans = {"status": "solved", "actions": res.actions}
            try:
                verdict = check_answer(self.engine.stage, ans)
            except Exception as exc:
                self.ui.set_solver_state(SearchStatus.FAILED, f"{res.algorithm}: Đầu ra lỗi", failed=True, info=str(exc))
                print(f"[SOLVER] [{res.algorithm}] Định dạng kết quả không hợp lệ: {exc}", file=sys.stderr)
                return

            if verdict["verdict"] != "AC":
                self.ui.set_solver_state(SearchStatus.FAILED, f"{res.algorithm}: Lời giải lỗi", failed=True, info=verdict.get("message", "WA"))
                print(f"[SOLVER] [{res.algorithm}] Checker từ chối lời giải: {verdict['message']}", file=sys.stderr)
                return

            if self.engine.move_count != self._solver_start_move_count or not self.engine.is_playing:
                self.ui.set_solver_state(SearchStatus.FAILED, "Bàn đã đổi - giải lại", failed=True)
                return

            # Nạp bước đi vào Replay
            self.replay_actions = res.actions
            self.replay_index = 0
            self.current_replay_file = res.algorithm
            self.ui.update_replay_status(0, len(self.replay_actions), res.algorithm)

            time_ms = res.metrics.get("search_time_ms", 0.0)
            expanded = res.metrics.get("expanded_nodes", 0)
            cost = verdict.get("cost", len(res.actions))
            if res.algorithm == "UCS":
                info_text = f"{res.algorithm}: {len(self.replay_actions)}b | cost {cost} ({time_ms:.1f}ms)"
            else:
                info_text = f"{res.algorithm}: {len(self.replay_actions)} bước ({time_ms:.1f}ms)"

            print(
                f"[SOLVER] <<< Thuật toán {res.algorithm} giải thành công màn {self.engine.stage_id}: "
                f"{len(self.replay_actions)} bước | {expanded} nodes duyệt | {time_ms:.2f}ms"
            )

            self.ui.set_solver_state(SearchStatus.COMPLETED, f"{res.algorithm}: {len(self.replay_actions)}b", info=info_text)
            self.is_replay_playing = True
            self.replay_timer = self.replay_interval
            self._sync_replay_button()

    def action_undo(self) -> None:
        """Hoàn tác bước đi gần nhất."""
        self.input_controller.reset()
        if self.anim.is_busy:
            self.anim.stop_all()

        if hasattr(self, "lose_screen"):
            self.lose_screen.hide()
        if hasattr(self, "pause_screen"):
            self.pause_screen.hide()
        if hasattr(self, "win_screen"):
            self.win_screen.hide()
        if hasattr(self, "state_manager") and not self.state_manager.is_playing:
            self.state_manager.transition_to(GameState.PLAYING)

        if self.engine.undo():
            self.board_view.reset_fragile_tiles()
            self.block_view.sync_from_engine(self.engine)
            self.ui.update_hud(self.engine)
            self._update_shadow_state()
            if self.replay_index > 0 and self.engine.move_count < self.replay_index:
                self.replay_index -= 1
                self.ui.update_replay_status(self.replay_index, len(self.replay_actions), self.current_replay_file)
            self._sync_replay_button()

    def action_reset(self) -> None:
        """Đặt lại ván chơi về trạng thái ban đầu."""
        # Nếu đang giải, hủy và bỏ kết quả của trạng thái cũ sau khi người dùng reset.
        self._solver_generation += 1
        self._solver_stage_id = None
        self.search_controller.cancel()
        self.ui.set_solver_state(SearchStatus.IDLE)
        self.input_controller.reset()
        self.anim.stop_all()
        self.is_replay_playing = False
        self.replay_index = 0

        if hasattr(self, "lose_screen"):
            self.lose_screen.hide()
        if hasattr(self, "pause_screen"):
            self.pause_screen.hide()
        if hasattr(self, "win_screen"):
            self.win_screen.hide()
        if hasattr(self, "main_menu_screen"):
            self.main_menu_screen.hide()
        if hasattr(self, "ui") and hasattr(self.ui, "ui_root"):
            self.ui.ui_root.enabled = True
        if hasattr(self, "state_manager") and not self.state_manager.is_playing:
            self.state_manager.transition_to(GameState.PLAYING)

        self.engine.reset()
        self.board_view.reset_fragile_tiles()
        self.block_view.sync_from_engine(self.engine)
        self.board_view.update_bridges(self.engine, dt=1.0)
        self.ui.update_hud(self.engine)
        self.ui.update_replay_status(0, len(self.replay_actions), self.current_replay_file)
        self._update_shadow_state()
        self._sync_replay_button()

    def action_toggle_cube(self) -> None:
        """Chuyển đổi khối được chọn khi đang ở trạng thái split (Phím Space)."""
        if self.engine.is_split:
            self.engine.toggle_cube()
            self.block_view.sync_from_engine(self.engine)
            self._update_shadow_state()
            self.ui.update_hud(self.engine)

    def _is_replay_out_of_sync(self) -> bool:
        """Kiểm tra xem trạng thái ván chơi có bị lệch khỏi chuỗi Replay hay không."""
        if not self.engine.is_playing:
            return True
        if self.engine.move_count != self.replay_index:
            return True
        if self.replay_actions and self.replay_index >= len(self.replay_actions):
            return True
        return False

    def _sync_replay_button(self) -> None:
        """Đồng bộ trạng thái nút Phát/Đặt Lại/Tạm Dừng của Replay."""
        if not hasattr(self, "ui") or not hasattr(self.ui, "btn_replay_play"):
            return
        is_out_of_sync = self._is_replay_out_of_sync()
        self.ui.set_replay_play_state(
            is_playing=self.is_replay_playing,
            is_reset_mode=is_out_of_sync and not self.is_replay_playing and bool(self.replay_actions),
        )

    def action_replay_toggle(self) -> None:
        """Bật/tắt tự động phát Replay. Nếu chưa có lời giải, kích hoạt Solver tính toán trực tiếp."""
        if not self.replay_actions:
            print(f"[REPLAY] Chưa có lời giải có sẵn. Tự động kích hoạt thuật toán {self.selected_algorithm} để tìm kiếm trực tiếp...")
            self.action_solve_current()
            return

        # Nếu ván chơi bị lệch vị trí Replay (ví dụ đã tự đi 1-2 bước hoặc đã thắng/thua),
        # nút này chuyển thành nút Đặt Lại để đưa ván về vị trí đầu trước khi cho phép phát
        if self._is_replay_out_of_sync() and not self.is_replay_playing:
            self.action_reset()
            return

        self.is_replay_playing = not self.is_replay_playing
        self._sync_replay_button()
        self.replay_timer = 0.0

    def action_replay_step_forward(self) -> None:
        """Tua tới 1 bước trong lời giải."""
        if self.anim.is_busy or self.replay_index >= len(self.replay_actions):
            return

        # Nếu trạng thái bị lệch so với bước replay tiếp theo, reset trước khi bước
        if self.engine.move_count != self.replay_index:
            self.action_reset()
            if not self.replay_actions:
                return

        act = self.replay_actions[self.replay_index]
        # Nếu đang split mà action có dạng '1U' hoặc '2U', chọn cube tương ứng
        if self.engine.is_split and len(act) == 2:
            cube_target = int(act[0])
            if self.engine.selected_cube != cube_target:
                self.engine.selected_cube = cube_target

        direction = act[-1]
        self.replay_index += 1
        self.ui.update_replay_status(self.replay_index, len(self.replay_actions), self.current_replay_file)
        self.make_move(direction)
        self._sync_replay_button()

    def action_replay_step_back(self) -> None:
        """Lùi lại 1 bước trong lời giải."""
        self.action_undo()

    def action_replay_jump_start(self) -> None:
        """Nhảy về bước đầu tiên."""
        self.action_reset()

    def action_replay_jump_end(self) -> None:
        """Tua nhanh về bước kết thúc lời giải."""
        if self.engine.move_count != self.replay_index:
            self.action_reset()

        while self.replay_index < len(self.replay_actions) and self.engine.is_playing:
            act = self.replay_actions[self.replay_index]
            if self.engine.is_split and len(act) == 2:
                self.engine.selected_cube = int(act[0])
            self.engine.step(act[-1])
            self.replay_index += 1

        self.block_view.sync_from_engine(self.engine)
        self.ui.update_hud(self.engine)
        self.ui.update_replay_status(self.replay_index, len(self.replay_actions), self.current_replay_file)
        self._sync_replay_button()

    def set_speed_mult(self, speed: float) -> None:
        """Cài đặt tốc độ hoạt ảnh và tốc độ phát replay."""
        self.anim.speed_mult = speed
        self.replay_interval = 0.35 / max(0.1, speed)

    def _on_victory_finished(self) -> None:
        """Gọi khi kết thúc hoạt ảnh chiến thắng."""
        if hasattr(self, "lose_screen"):
            self.lose_screen.hide()
        if hasattr(self, "pause_screen"):
            self.pause_screen.hide()
        self.ui.update_hud(self.engine)
        self.state_manager.transition_to(GameState.WIN)
        self._sync_replay_button()
        best_moves = self.catalog.get_best_moves(self.engine.stage_id)
        stage_title = f"Màn {self.engine.stage_id}" if self.engine.stage_id else "Màn chơi"
        self.win_screen.show(
            stage_name=stage_title,
            moves=self.engine.move_count,
            best_moves=best_moves,
        )

    def _on_fall_finished(self) -> None:
        """Gọi khi kết thúc hoạt ảnh rơi."""
        if hasattr(self, "win_screen"):
            self.win_screen.hide()
        if hasattr(self, "pause_screen"):
            self.pause_screen.hide()
        self.ui.update_hud(self.engine)
        self.state_manager.transition_to(GameState.LOSE)
        self._sync_replay_button()
        reason = self.engine.lost_reason or "Khối đã bị rơi khỏi sàn đấu!"
        self.lose_screen.show(reason=reason)

    def _menu_play(self) -> None:
        """Bắt đầu chơi game từ menu chính."""
        self.main_menu_screen.hide()
        self.ui.ui_root.enabled = True
        if not self.engine.is_playing:
            self.action_reset()
        else:
            self.state_manager.transition_to(GameState.PLAYING)

    def _menu_select_stage(self) -> None:
        """Mở bảng chọn màn chơi."""
        self.main_menu_screen.hide()
        self.pause_screen.hide()
        self.win_screen.hide()
        self.lose_screen.hide()
        self.ui.open_stage_selector()

    def _menu_help(self) -> None:
        """Mở modal hướng dẫn & phím tắt."""
        self.ui.open_help_modal()

    def action_resume(self) -> None:
        """Tiếp tục ván chơi từ menu tạm dừng."""
        self.pause_screen.hide()
        self.state_manager.pop_state()

    def action_main_menu(self) -> None:
        """Quay trở về Menu chính."""
        self.pause_screen.hide()
        self.win_screen.hide()
        self.lose_screen.hide()
        if self.ui.is_stage_selector_open:
            self.ui.close_stage_selector()
        if self.ui.is_help_modal_open:
            self.ui.close_help_modal()
        self.anim.stop_all()
        self.is_replay_playing = False
        self.ui.set_replay_play_state(False)
        self.input_controller.reset()
        self._solver_generation += 1
        self._solver_stage_id = None
        self.search_controller.cancel()
        self.ui.set_solver_state(SearchStatus.IDLE)

        # Nếu ván chơi đã kết thúc (thắng hoặc thua), đặt lại trạng thái và hình ảnh khối trên bàn
        if not self.engine.is_playing:
            self.engine.reset()
            self.board_view.reset_fragile_tiles()
            self.block_view.sync_from_engine(self.engine)
            self.board_view.update_bridges(self.engine, dt=1.0)
            self.ui.update_hud(self.engine)
            self.ui.update_replay_status(0, len(self.replay_actions), self.current_replay_file)
            self._update_shadow_state()

        self.ui.ui_root.enabled = False
        self.main_menu_screen.show()
        self.state_manager.transition_to(GameState.MAIN_MENU)

    def action_next_stage(self) -> None:
        """Chuyển sang màn chơi kế tiếp."""
        self.win_screen.hide()
        next_id = self.catalog.get_next_stage_id(self.engine.stage_id)
        if next_id:
            self.load_stage_by_id(next_id)
        else:
            self.action_main_menu()

    def _on_modal_closed(self) -> None:
        """Khôi phục trạng thái phù hợp khi đóng modal chọn màn hoặc modal trợ giúp."""
        if self.state_manager.current_state in (GameState.LEVEL_SELECT, GameState.HELP):
            self.state_manager.pop_state()
            if self.state_manager.current_state == GameState.MAIN_MENU:
                self.main_menu_screen.show()
                self.ui.ui_root.enabled = False
            elif self.state_manager.current_state == GameState.PAUSED:
                st_name = f"Màn {self.engine.stage_id}" if self.engine.stage_id else "Màn chơi"
                self.pause_screen.show(stage_name=st_name, move_count=self.engine.move_count)
            elif self.state_manager.current_state == GameState.WIN:
                best_moves = self.catalog.get_best_moves(self.engine.stage_id)
                st_name = f"Màn {self.engine.stage_id}" if self.engine.stage_id else "Màn chơi"
                self.win_screen.show(stage_name=st_name, moves=self.engine.move_count, best_moves=best_moves)
            elif self.state_manager.current_state == GameState.LOSE:
                reason = self.engine.lost_reason or "Khối đã bị rơi khỏi sàn đấu!"
                self.lose_screen.show(reason=reason)
            elif self.state_manager.current_state == GameState.PLAYING:
                self.ui.ui_root.enabled = True

    def _update_background_scale(self) -> None:
        """Đảm bảo ảnh nền phủ kín góc nhìn camera cả ở Orthographic và Perspective."""
        aspect = max(window.aspect_ratio, 16.0 / 9.0)
        img_aspect = 988.0 / 556.0

        if camera.orthographic:
            bg_h = camera.fov * 1.05
        else:
            bg_h = 2.0 * self.bg_glow.z * math.tan(math.radians(camera.fov / 2.0)) * 1.05

        bg_w = bg_h * max(aspect, img_aspect)
        self.bg_glow.scale = Vec2(bg_w, bg_h)

    def input(self, key: str) -> None:
        """Lắng nghe phím bấm từ người chơi."""
        if self.debug:
            print(f"[DEBUG INPUT] Phím: {key!r} | Bận: {self.anim.is_busy} | Trạng thái: {self.engine.status.value} | FSM: {self.state_manager.current_state.value}")

        # Khi click chuột trái ra ngoài vùng input field, tự động nhả focus
        if key == "left mouse down":
            if getattr(self.ui.inp_replay_path, "active", False):
                if not getattr(self.ui.inp_replay_path, "hovered", False):
                    self.ui.inp_replay_path.active = False

        # 0. Bỏ qua phím khi đang nhập liệu trong ô input
        if getattr(self.ui.inp_replay_path, "active", False):
            if key == "enter":
                self.ui._submit_custom_replay()
                self.ui.inp_replay_path.active = False
            elif key == "escape":
                self.ui.inp_replay_path.active = False
            return

        # 0b. Khi modal đang mở, nhận ESC / phím tắt để đóng modal
        if self.ui.is_stage_selector_open or self.ui.is_help_modal_open:
            if key in ("escape", "tab", "m", "h", "f1"):
                if self.ui.is_stage_selector_open:
                    self.ui.close_stage_selector()
                elif self.ui.is_help_modal_open:
                    self.ui.close_help_modal()
            return

        # 0c. Điều hướng theo trạng thái StateManager
        if self.state_manager.current_state == GameState.MAIN_MENU:
            if key in ("enter", "space"):
                self._menu_play()
            elif key in ("tab", "m"):
                self._menu_select_stage()
            elif key in ("h", "f1"):
                self._menu_help()
            elif key == "escape":
                application.quit()
            return

        elif self.state_manager.current_state == GameState.PAUSED:
            if key == "escape":
                self.action_resume()
            elif key == "r":
                self.pause_screen.hide()
                self.action_reset()
                self.state_manager.transition_to(GameState.PLAYING)
            elif key in ("tab", "m"):
                self._menu_select_stage()
            elif key in ("h", "f1"):
                self._menu_help()
            return

        elif self.state_manager.current_state == GameState.WIN:
            if key in ("enter", "space"):
                self.action_next_stage()
            elif key == "r":
                self.win_screen.hide()
                self.action_reset()
                self.state_manager.transition_to(GameState.PLAYING)
            elif key in ("tab", "m"):
                self._menu_select_stage()
            elif key == "escape":
                self.action_main_menu()
            return

        elif self.state_manager.current_state == GameState.LOSE:
            if key in ("r", "enter", "space"):
                self.lose_screen.hide()
                self.action_reset()
                self.state_manager.transition_to(GameState.PLAYING)
            elif key == "u":
                self.lose_screen.hide()
                self.action_undo()
                self.state_manager.transition_to(GameState.PLAYING)
            elif key in ("tab", "m"):
                self._menu_select_stage()
            elif key == "escape":
                self.action_main_menu()
            return

        # 1. Trạng thái PLAYING: Phím ESC tạm dừng game (hoặc chuyển ngay sang kết thúc nếu đang rơi/thắng)
        if key == "escape":
            if self.anim.is_falling:
                self.anim.stop_all()
                self._on_fall_finished()
                return
            if self.anim.is_victory:
                self.anim.stop_all()
                self._on_victory_finished()
                return
            self.state_manager.push_state(GameState.PAUSED)
            st_name = f"Màn {self.engine.stage_id}" if self.engine.stage_id else "Màn chơi"
            self.pause_screen.show(stage_name=st_name, move_count=self.engine.move_count)
            return

        # 2. Xử lý nhả phím di chuyển (để dừng lặp hold-to-repeat).
        # Controller tự chuẩn hóa tên key để tương thích các backend Ursina.
        if self.input_controller.handle_key_up(key):
            return

        # 3. Xử lý phím di chuyển (WASD / Mũi tên qua InputController)
        if self.input_controller.handle_key_down(key):
            return

        # 4. Đổi khối khi split
        if key == "space":
            self.action_toggle_cube()

        # 5. Phím tắt chức năng
        elif key == "u":
            self.action_undo()
        elif key == "r":
            self.action_reset()
        elif key == "p":
            self.action_replay_toggle()
        elif key in ("tab", "m"):
            self._menu_select_stage()
        elif key in ("h", "f1"):
            self._menu_help()
        elif key == "c":
            self.camera_rig.reset_view()
            self._update_background_scale()
        elif key == "v":
            self.camera_rig.toggle_projection()
            self._update_background_scale()

        # 6. Chuyển tiếp sự kiện zoom/cuộn chuột cho camera rig
        self.camera_rig.input(key)
        self._update_background_scale()

    def update(self) -> None:
        """Vòng lặp cập nhật chính của trò chơi mỗi khung hình."""
        self._poll_astar_results()
        dt = time.dt

        # Cập nhật tỉ lệ nền
        self._update_background_scale()

        # Cập nhật bộ điều khiển nhập liệu (hold-to-repeat và watchdog)
        self.input_controller.update(dt)

        # Cập nhật camera
        self.camera_rig.update(dt)

        # Cập nhật hoạt ảnh
        self.anim.update(dt, self.engine)

        # Cập nhật bàn cờ (cầu, công tắc, xoay sao đích)
        self.board_view.update(dt)
        self.board_view.update_bridges(self.engine, dt)
        self.board_view.update_switches(self.engine, dt)

        # Cập nhật các hạt hiệu ứng
        self.particles.update(dt)

        # Tự động phát Replay theo khoảng thời gian
        if self.is_replay_playing:
            if not self.anim.is_busy:
                self.replay_timer += dt
                if self.replay_timer >= self.replay_interval:
                    self.replay_timer = 0.0
                    if self.replay_index < len(self.replay_actions) and self.engine.is_playing:
                        self.action_replay_step_forward()
                    else:
                        # Kết thúc replay
                        self.is_replay_playing = False
                        self._sync_replay_button()


def launch_ursina_gui(
    stage_path: Path | None = None,
    replay_path: Path | None = None,
    start_in_menu: bool = False,
    debug: bool = False,
    show_loading: bool = True,
) -> None:
    """Hàm khởi chạy cửa sổ game Bloxorz bằng Ursina Engine."""
    app = Ursina()
    BloxorzUrsinaApp(
        stage_path=stage_path,
        replay_path=replay_path,
        start_in_menu=start_in_menu,
        debug=debug,
        show_loading=show_loading,
    )
    app.run()
