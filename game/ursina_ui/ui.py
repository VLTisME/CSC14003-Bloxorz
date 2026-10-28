"""Giao diện người dùng (UI / HUD) cho Bloxorz Ursina.

Bao gồm:
- Thanh trạng thái đỉnh (Top Bar): Tên màn, số bước, trạng thái ván chơi, chỉ định khối đang điều khiển
- Thanh điều khiển Replay (Bottom Bar): Tự động nạp file lời giải .out.json tương ứng, phát/tạm dừng, tua bước, thanh nhập đường dẫn tùy chỉnh
- Bảng chọn màn chơi (Stage Selector Modal): 33 màn gốc (original) + 6 màn mẫu (samples) kèm đánh dấu màn đã thắng
- Bảng phím tắt & hướng dẫn trợ giúp (Help Modal)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Callable
from ursina import (
    Button,
    Entity,
    InputField,
    Text,
    Vec2,
    Vec3,
    camera,
    color,
    destroy,
    mouse,
)

from game.stage_catalog import StageCatalog
from game.theme import get_theme
from game.ursina_ui.assets.theme import (
    PALETTE,
    DEFAULT_FONT_NAME,
    LocalizedStr,
    snap,
)
from game.ursina_ui.pixel_widgets import (
    PixelButton,
    PixelPanel,
    PixelTab,
    PixelLevelTile,
    PixelCloseButton,
    get_pixel_panel_texture,
)
from game.ursina_ui.screens.benchmark_modal import BenchmarkModal
from game.ursina_ui.theme import (
    BTN_HOVER,
    BTN_PRESSED,
    BTN_WOOD_BASE,
    FRAME_BEZEL,
    FRAME_DARK,
    PARCHMENT_LIGHT,
    PARCHMENT_SHADOW,
    SOLVER_COMPLETED,
    SOLVER_ERROR,
    SOLVER_IDLE,
    SOLVER_PAUSED,
    SOLVER_RUNNING,
    TEXT_DARK,
    TEXT_MUTED,
)

if TYPE_CHECKING:
    from game.engine import BloxorzEngine

FONT_NAME = DEFAULT_FONT_NAME


def rgba255(r: int, g: int, b: int, a: int = 255) -> color.Color:
    """Chuyển đổi RGBA 0-255 sang đối tượng Color chuẩn (0.0 - 1.0) của Ursina."""
    return color.rgba(r / 255.0, g / 255.0, b / 255.0, a / 255.0)


class UIManager:
    """Quản lý toàn bộ các thành phần hiển thị 2D trên màn hình."""

    def __init__(
        self,
        catalog: StageCatalog,
        on_select_stage: Callable[[str], None],
        on_undo: Callable[[], None],
        on_reset: Callable[[], None],
        on_toggle_cube: Callable[[], None],
        on_replay_play_pause: Callable[[], None],
        on_replay_step_forward: Callable[[], None],
        on_replay_step_back: Callable[[], None],
        on_replay_jump_start: Callable[[], None],
        on_replay_jump_end: Callable[[], None],
        on_replay_load_file: Callable[[str], None],
        on_speed_change: Callable[[float], None],
        on_solve_astar: Callable[[], None],
        on_cycle_algorithm: Callable[[], None] | None = None,
        on_solve: Callable[[], None] | None = None,
        on_load_benchmark_solution: Callable[[list[str]], None] | None = None,
    ) -> None:
        self.catalog = catalog
        self.on_select_stage = on_select_stage
        self.on_undo = on_undo
        self.on_reset = on_reset
        self.on_toggle_cube = on_toggle_cube
        self.on_replay_play_pause = on_replay_play_pause
        self.on_replay_step_forward = on_replay_step_forward
        self.on_replay_step_back = on_replay_step_back
        self.on_replay_jump_start = on_replay_jump_start
        self.on_replay_jump_end = on_replay_jump_end
        self.on_replay_load_file = on_replay_load_file
        self.on_speed_change = on_speed_change
        self.on_solve_astar = on_solve_astar
        self.on_cycle_algorithm = on_cycle_algorithm
        self.on_solve = on_solve if on_solve is not None else on_solve_astar
        self.on_load_benchmark_solution = on_load_benchmark_solution
        self.selected_algorithm: str = "A*"

        self.theme = get_theme("toy")
        self.ui_root = Entity(parent=camera.ui, name="ui_root")

        # 1. Thanh tiêu đề đỉnh (Top Header) - Lấp đầy trọn vẹn mép trên
        self.header_panel = Entity(
            parent=self.ui_root,
            model="quad",
            scale=(2.5, 0.1),
            position=(0, 0.465, 0.05),
            texture=get_pixel_panel_texture(512, 180),
            color=color.white,
        )

        self.txt_stage = Text(
            parent=self.ui_root,
            text="STAGE 01",
            font=FONT_NAME,
            scale=1.20,
            origin=(-0.5, 0),
            position=(-0.84, 0.46, -0.01),
            color=color.hex(PALETTE["ink"]),
        )

        self.txt_moves = Text(
            parent=self.ui_root,
            text="MOVES: 0",
            font=FONT_NAME,
            scale=1.15,
            origin=(-0.5, 0),
            position=(-0.64, 0.46, -0.01),
            color=color.hex(PALETTE["brick"]),
        )

        self.txt_status = Text(
            parent=self.ui_root,
            text=LocalizedStr("PLAYING", ["ĐANG CHƠI"]),
            font=FONT_NAME,
            scale=1.15,
            origin=(-0.5, 0),
            position=(-0.48, 0.46, -0.01),
            color=color.hex(PALETTE["green"]),
        )

        self.txt_cube_info = Text(
            parent=self.ui_root,
            text="",
            font=FONT_NAME,
            scale=1.00,
            origin=(-0.5, 0),
            position=(-0.35, 0.46, -0.01),
            color=color.hex(PALETTE["green"]),
        )

        # Nhãn thông tin chi tiết của Solver (Được canh phải tại x=0.08, tuyệt đối không bị nút che)
        self.txt_solver_info = Text(
            parent=self.ui_root,
            text="",
            font=FONT_NAME,
            scale=0.82,
            origin=(0.5, 0),
            position=(0.08, 0.46, -0.01),
            color=color.hex(PALETTE["brick"]),
        )

        # Nút chọn thuật toán (BFS / DFS / UCS / A*)
        self.btn_algo_select = PixelButton(
            parent=self.ui_root,
            text="A* v",
            color_ramp="orange",
            scale=(0.095, 0.058),
            position=(0.15, 0.46, -0.01),
            on_click=self.toggle_algorithm_selector,
        )

        # Nút chạy Solver
        self.btn_solve = PixelButton(
            parent=self.ui_root,
            text=LocalizedStr("Solve A*", ["Giải A*"]),
            color_ramp="green",
            scale=(0.13, 0.058),
            position=(0.27, 0.46, -0.01),
            on_click=self.on_solve,
        )
        self.btn_solve_astar = self.btn_solve  # Alias tương thích ngược 100%

        # Nút mở bảng Benchmark thuật toán
        self.btn_benchmark = PixelButton(
            parent=self.ui_root,
            text=LocalizedStr("Benchmark", ["Đo Hiệu Năng"]),
            color_ramp="orange",
            scale=(0.155, 0.058),
            position=(0.415, 0.46, -0.01),
            on_click=self.toggle_benchmark_modal,
        )

        self.btn_select_stage = PixelButton(
            parent=self.ui_root,
            text=LocalizedStr("Stage Select", ["Chọn Màn"]),
            color_ramp="orange",
            scale=(0.175, 0.058),
            position=(0.59, 0.46, -0.01),
            on_click=self.toggle_stage_selector,
        )

        self.btn_help = PixelButton(
            parent=self.ui_root,
            text=LocalizedStr("Help", ["Trợ Giúp"]),
            color_ramp="orange",
            scale=(0.09, 0.058),
            position=(0.73, 0.46, -0.01),
            on_click=self.toggle_help_modal,
        )

        # 2. Thanh điều khiển Replay đáy (Bottom Replay Bar) - Lấp đầy trọn vẹn mép dưới
        self.replay_panel = Entity(
            parent=self.ui_root,
            model="quad",
            scale=(2.5, 0.1),
            position=(0, -0.465, 0.05),
            texture=get_pixel_panel_texture(512, 210),
            color=color.white,
        )

        self.txt_replay_info = Text(
            parent=self.ui_root,
            text="Replay: No solution loaded",
            font=FONT_NAME,
            scale=1.05,
            origin=(-0.5, 0),
            position=(-0.82, -0.46, -0.01),
            color=color.hex(PALETTE["ink"]),
        )

        # Cụm nút tua Replay
        self.btn_replay_start = PixelButton(
            parent=self.ui_root,
            text="Start",
            color_ramp="orange",
            scale=(0.075, 0.054),
            position=(-0.25, -0.46, -0.01),
            on_click=self.on_replay_jump_start,
        )

        self.btn_replay_prev = PixelButton(
            parent=self.ui_root,
            text="Prev",
            color_ramp="orange",
            scale=(0.075, 0.054),
            position=(-0.165, -0.46, -0.01),
            on_click=self.on_replay_step_back,
        )

        self.btn_replay_play = PixelButton(
            parent=self.ui_root,
            text=LocalizedStr("Play", ["Phát"]),
            color_ramp="green",
            scale=(0.095, 0.054),
            position=(-0.07, -0.46, -0.01),
            on_click=self.on_replay_play_pause,
        )

        self.btn_replay_next = PixelButton(
            parent=self.ui_root,
            text="Next",
            color_ramp="orange",
            scale=(0.075, 0.054),
            position=(0.025, -0.46, -0.01),
            on_click=self.on_replay_step_forward,
        )

        self.btn_replay_end = PixelButton(
            parent=self.ui_root,
            text="End",
            color_ramp="orange",
            scale=(0.075, 0.054),
            position=(0.11, -0.46, -0.01),
            on_click=self.on_replay_jump_end,
        )

        # Nút chuyển tốc độ
        self.current_speed = 1.0
        self.btn_speed = PixelButton(
            parent=self.ui_root,
            text="1x",
            color_ramp="orange",
            scale=(0.075, 0.054),
            position=(0.195, -0.46, -0.01),
            on_click=self._cycle_speed,
        )

        # Khung nhập file Replay thủ công
        self.inp_replay_path = InputField(
            parent=self.ui_root,
            default_value="",
            scale=(0.20, 0.050),
            position=(0.345, -0.46, -0.01),
            font=FONT_NAME,
            color=color.hex(PALETTE["ivory"]),
        )
        self.inp_replay_path.highlight_color = color.hex(PALETTE["cream"])
        self.inp_replay_path.pressed_color = color.hex(PALETTE["ivory"])
        if hasattr(self.inp_replay_path, "text_field"):
            tf = self.inp_replay_path.text_field
            if hasattr(tf, "text_entity"):
                tf.text_entity.color = color.hex(PALETTE["ink"])
                tf.text_entity.font = FONT_NAME
            if hasattr(tf, "cursor"):
                tf.cursor.color = color.hex(PALETTE["ink"])

        self.btn_replay_load = PixelButton(
            parent=self.ui_root,
            text=LocalizedStr("Load", ["Nạp File"]),
            color_ramp="green",
            scale=(0.095, 0.054),
            position=(0.505, -0.46, -0.01),
            on_click=self._submit_custom_replay,
        )

        # 3. La bàn định hướng góc nhìn Isometric (Direction Compass) - Đầy đặn và lấp đầy mép
        self.compass_panel = Entity(
            parent=self.ui_root,
            model="quad",
            scale=(0.32, 0.18),
            position=(0.725, -0.315, 0.05),
            texture=get_pixel_panel_texture(240, 140),
            color=color.white,
        )
        self.txt_compass_title = Text(
            parent=self.ui_root,
            text=LocalizedStr("CONTROLS", ["HƯỚNG DI CHUYỂN"]),
            font=FONT_NAME,
            scale=0.95,
            origin=(0, 0),
            position=(0.725, -0.25, -0.01),
            color=color.hex(TEXT_MUTED),
        )
        self.txt_compass_u = Text(
            parent=self.ui_root,
            text=LocalizedStr("W / Up\nUp-Left", ["W / ^\nLên-Trái"]),
            font=FONT_NAME,
            scale=0.76,
            origin=(0, 0),
            position=(0.66, -0.30, -0.01),
            color=color.hex(TEXT_DARK),
        )
        self.txt_compass_r = Text(
            parent=self.ui_root,
            text=LocalizedStr("D / Right\nUp-Right", ["D / >\nLên-Phải"]),
            font=FONT_NAME,
            scale=0.76,
            origin=(0, 0),
            position=(0.79, -0.30, -0.01),
            color=color.hex(TEXT_DARK),
        )
        self.txt_compass_l = Text(
            parent=self.ui_root,
            text=LocalizedStr("A / Left\nDown-Left", ["A / <\nXuống-Trái"]),
            font=FONT_NAME,
            scale=0.76,
            origin=(0, 0),
            position=(0.66, -0.36, -0.01),
            color=color.hex(TEXT_DARK),
        )
        self.txt_compass_d = Text(
            parent=self.ui_root,
            text=LocalizedStr("S / Down\nDown-Right", ["S / v\nXuống-Phải"]),
            font=FONT_NAME,
            scale=0.76,
            origin=(0, 0),
            position=(0.79, -0.36, -0.01),
            color=color.hex(TEXT_DARK),
        )

        # 4. Modal Bảng chọn màn chơi (Stage Selector Modal)
        self.stage_selector_modal: Entity | None = None
        self.is_stage_selector_open = False
        self.stage_selector_tab: str = "original"
        self.current_stage_id: str = "stage01"

        # 5. Modal Trợ giúp & Phím tắt (Help Modal)
        self.help_modal: Entity | None = None
        self.is_help_modal_open = False

        # 6. Modal Chọn thuật toán tìm kiếm (Algorithm Selector Modal)
        self.algo_modal: Entity | None = None
        self.is_algorithm_selector_open = False

        # 7. Modal Đo hiệu năng thuật toán (Benchmark Modal)
        self.benchmark_modal: BenchmarkModal | None = None
        self.is_benchmark_modal_open = False

    def _cycle_speed(self) -> None:
        """Chuyển đổi luân phiên tốc độ Replay: 1x -> 2x -> 4x -> 1x."""
        if self.current_speed == 1.0:
            self.current_speed = 2.0
        elif self.current_speed == 2.0:
            self.current_speed = 4.0
        else:
            self.current_speed = 1.0

        self.btn_speed.text = f"{int(self.current_speed)}x"
        self.on_speed_change(self.current_speed)

    def set_solver_status(self, text: str, *, failed: bool = False) -> None:
        """Show solve progress/result in the solver button."""
        self.btn_solve.text = text
        if hasattr(self.btn_solve, "color_ramp"):
            self.btn_solve.color_ramp = "red" if failed else "green"
        else:
            self.btn_solve.color = color.hex(SOLVER_ERROR) if failed else color.hex(SOLVER_IDLE)

    def set_selected_algorithm(self, algo: str) -> None:
        """Cập nhật thuật toán đang được chọn (BFS, DFS, UCS, A*)."""
        self.selected_algorithm = algo
        self.btn_algo_select.text = f"{algo} v"
        self.btn_solve.text = LocalizedStr(f"Solve {algo}", [f"Giải {algo}"])

    def toggle_algorithm_selector(self) -> None:
        """Bật/tắt cửa sổ danh sách chọn thuật toán tìm kiếm."""
        if self.is_algorithm_selector_open:
            self.close_algorithm_selector()
        else:
            self.open_algorithm_selector()

    def open_algorithm_selector(self) -> None:
        """Mở cửa sổ danh sách thuật toán với mô tả trực quan và nút chọn."""
        self.close_stage_selector()
        self.close_help_modal()
        if self.algo_modal is not None:
            destroy(self.algo_modal)

        self.is_algorithm_selector_open = True
        self.algo_modal = PixelPanel(
            scale=(0.86, 0.65),
            position=(0, 0, -16),
            title="SELECT SEARCH ALGORITHM",
            subtitle="Choose a search algorithm to solve the puzzle",
            close_button=True,
            on_close=self.close_algorithm_selector,
        )

        algo_definitions = [
            ("A*", "A* Heuristic", "Heuristic search using Manhattan distance.\nFast and finds optimal shortest path."),
            ("BFS", "Breadth-First", "Explores level by level across all branches.\nGuarantees fewest moves sequence."),
            ("UCS", "Uniform Cost", "Dijkstra uniform-cost search.\nGuarantees path with minimum total cost."),
            ("DFS", "Depth-First", "Deep branch exploration with low memory usage.\nFast execution, not guaranteed optimal."),
        ]

        start_y = 0.12
        dy = 0.092
        for i, (key, title, desc) in enumerate(algo_definitions):
            py = start_y - i * dy
            is_active = (key == self.selected_algorithm)
            btn_text = f"{key} [Active]" if is_active else f"Select {key}"
            ramp = "orange" if is_active else "green"

            PixelButton(
                parent=self.algo_modal,
                text=btn_text,
                color_ramp=ramp,
                scale=(0.19, 0.065),
                position=(-0.28, py, -0.02),
                on_click=lambda a=key: self._on_algorithm_chosen(a),
            )

            Text(
                parent=self.algo_modal,
                text=f"{title}\n{desc}",
                font=FONT_NAME,
                scale=0.86,
                origin=(-0.5, 0),
                position=(-0.15, py, -0.02),
                color=color.hex(PALETTE["ink"]),
            )

        # Nút chuyển nhanh sang Benchmark tất cả thuật toán
        PixelButton(
            parent=self.algo_modal,
            text="Open Algorithm Benchmark",
            color_ramp="orange",
            scale=(0.34, 0.052),
            position=(0, -0.24, -0.02),
            on_click=self._switch_from_algo_to_benchmark,
        )

    def _switch_from_algo_to_benchmark(self) -> None:
        """Chuyển đổi trực tiếp từ modal chọn thuật toán sang modal benchmark."""
        self.close_algorithm_selector()
        self.open_benchmark_modal()

    def toggle_benchmark_modal(self) -> None:
        """Bật/tắt cửa sổ đo hiệu năng tất cả thuật toán."""
        if self.is_benchmark_modal_open:
            self.close_benchmark_modal()
        else:
            self.open_benchmark_modal()

    def open_benchmark_modal(self) -> None:
        """Mở cửa sổ đo hiệu năng đối sánh 4 thuật toán trên màn chơi hiện tại."""
        self.close_stage_selector()
        self.close_help_modal()
        self.close_algorithm_selector()
        if self.benchmark_modal is not None:
            destroy(self.benchmark_modal)

        self.is_benchmark_modal_open = True
        self.benchmark_modal = BenchmarkModal(
            catalog=self.catalog,
            current_stage_id=getattr(self, "current_stage_id", "stage01"),
            on_close=self.close_benchmark_modal,
            on_load_solution=self._handle_load_benchmark_solution,
        )

    def close_benchmark_modal(self) -> None:
        """Đóng cửa sổ đo hiệu năng."""
        if self.benchmark_modal is not None:
            destroy(self.benchmark_modal)
            self.benchmark_modal = None
        self.is_benchmark_modal_open = False

    def _handle_load_benchmark_solution(self, actions: list[str]) -> None:
        """Nạp lời giải từ Benchmark vào thanh Replay và đóng modal."""
        if self.on_load_benchmark_solution:
            self.on_load_benchmark_solution(actions)
        self.close_benchmark_modal()

    def close_algorithm_selector(self) -> None:
        """Đóng cửa sổ danh sách thuật toán."""
        if self.algo_modal is not None:
            destroy(self.algo_modal)
            self.algo_modal = None
        self.is_algorithm_selector_open = False

    def _on_algorithm_chosen(self, algo: str) -> None:
        """Callback khi người chơi chọn một thuật toán trong danh sách."""
        self.set_selected_algorithm(algo)
        if self.on_cycle_algorithm:
            import inspect
            sig = inspect.signature(self.on_cycle_algorithm)
            if len(sig.parameters) > 0:
                self.on_cycle_algorithm(algo)
            else:
                self.on_cycle_algorithm()
        self.close_algorithm_selector()

    def _handle_cycle_algorithm(self) -> None:
        """Chuyển đổi luân phiên giữa các thuật toán (tương thích ngược)."""
        algos = ["A*", "BFS", "DFS", "UCS"]
        idx = algos.index(self.selected_algorithm) if self.selected_algorithm in algos else 0
        next_algo = algos[(idx + 1) % len(algos)]
        self.set_selected_algorithm(next_algo)
        if self.on_cycle_algorithm:
            import inspect
            sig = inspect.signature(self.on_cycle_algorithm)
            if len(sig.parameters) > 0:
                self.on_cycle_algorithm(next_algo)
            else:
                self.on_cycle_algorithm()

    def set_solver_state(
        self,
        status: str,
        text: str | None = None,
        *,
        failed: bool = False,
        info: str | None = None,
    ) -> None:
        """Cập nhật nhãn, thông tin và màu sắc nút Solver theo trạng thái tìm kiếm."""
        if text:
            self.btn_solve.text = text
        elif status == "RUNNING":
            self.btn_solve.text = LocalizedStr("Pause", ["Tạm Dừng"])
        elif status == "PAUSED":
            self.btn_solve.text = LocalizedStr("Resume", ["Tiếp Tục"])
        elif status == "IDLE":
            self.btn_solve.text = LocalizedStr(f"Solve {self.selected_algorithm}", [f"Giải {self.selected_algorithm}"])

        if info is not None:
            self.txt_solver_info.text = info
        elif status == "IDLE":
            self.txt_solver_info.text = ""

        if hasattr(self.btn_solve, "color_ramp"):
            if failed or status in ("FAILED", "TIMEOUT"):
                self.btn_solve.color_ramp = "red"
            elif status == "RUNNING":
                self.btn_solve.color_ramp = "orange"
            else:
                self.btn_solve.color_ramp = "green"
        else:
            if failed or status in ("FAILED", "TIMEOUT"):
                self.btn_solve.color = color.hex(SOLVER_ERROR)
            elif status == "PAUSED":
                self.btn_solve.color = color.hex(SOLVER_PAUSED)
            elif status == "RUNNING":
                self.btn_solve.color = color.hex(SOLVER_RUNNING)
            elif status == "COMPLETED":
                self.btn_solve.color = color.hex(SOLVER_COMPLETED)
            else:
                self.btn_solve.color = color.hex(SOLVER_IDLE)

    def _submit_custom_replay(self) -> None:
        """Người dùng nhấn nút nạp đường dẫn file replay nhập tay."""
        raw_path = self.inp_replay_path.text.strip()
        if raw_path:
            self.on_replay_load_file(raw_path)

    def set_replay_play_state(self, is_playing: bool, is_reset_mode: bool = False) -> None:
        """Đổi nhãn và màu sắc nút phát Replay."""
        if is_playing:
            self.btn_replay_play.text = LocalizedStr("Pause", ["Tạm Dừng"])
            if hasattr(self.btn_replay_play, "color_ramp"):
                self.btn_replay_play.color_ramp = "orange"
            else:
                self.btn_replay_play.color = color.hex(SOLVER_RUNNING)
        elif is_reset_mode:
            self.btn_replay_play.text = LocalizedStr("Reset", ["Đặt Lại"])
            if hasattr(self.btn_replay_play, "color_ramp"):
                self.btn_replay_play.color_ramp = "red"
            else:
                self.btn_replay_play.color = color.hex(SOLVER_ERROR)
        else:
            self.btn_replay_play.text = LocalizedStr("Play", ["Phát"])
            if hasattr(self.btn_replay_play, "color_ramp"):
                self.btn_replay_play.color_ramp = "green"
            else:
                self.btn_replay_play.color = color.hex("#4E8A3A")

    def update_hud(self, engine: BloxorzEngine) -> None:
        """Cập nhật các số liệu trên thanh HUD theo trạng thái ván chơi."""
        st_id = engine.stage_id or "01"
        self.current_stage_id = st_id
        self.txt_stage.text = f"STAGE {st_id}"
        self.txt_moves.text = f"MOVES: {engine.move_count}"

        if engine.is_won:
            self.txt_status.text = LocalizedStr("CLEARED!", ["CHIẾN THẮNG!"])
            self.txt_status.color = color.hex(PALETTE["butter"])
        elif engine.is_lost:
            self.txt_status.text = LocalizedStr("FALLEN!", ["THẤT BẠI: Rơi xuống vực!"])
            self.txt_status.color = color.hex(PALETTE["red"])
        else:
            self.txt_status.text = LocalizedStr("PLAYING", ["ĐANG CHƠI"])
            self.txt_status.color = color.hex(PALETTE["green"])

        if engine.is_split and not (engine.is_lost or engine.is_won):
            self.txt_cube_info.text = f"Cube {engine.selected_cube} (Space)"
            self.txt_cube_info.color = color.hex(PALETTE["green"]) if engine.selected_cube == 1 else color.hex(PALETTE["blue"])
        else:
            self.txt_cube_info.text = ""

        # Tự động tính toán tọa độ theo luồng (Dynamic Flow Layout) chống đè chữ tuyệt đối
        start_x = -0.82
        gap = 0.038
        self.txt_stage.x = start_x
        self.txt_moves.x = self.txt_stage.x + (self.txt_stage.width * self.txt_stage.scale_x) + gap
        self.txt_status.x = self.txt_moves.x + (self.txt_moves.width * self.txt_moves.scale_x) + gap
        if self.txt_cube_info.text:
            self.txt_cube_info.x = self.txt_status.x + (self.txt_status.width * self.txt_status.scale_x) + gap

    def update_replay_status(self, step_idx: int, total_steps: int, file_name: str | None = None) -> None:
        """Cập nhật thông tin bước phát lại trên thanh Replay."""
        if total_steps <= 0:
            self.txt_replay_info.text = "Replay: No solution loaded"
        else:
            name_part = f" [{file_name}]" if file_name else ""
            self.txt_replay_info.text = f"Replay: Step {step_idx}/{total_steps}{name_part}"

    def toggle_stage_selector(self) -> None:
        """Bật/tắt cửa sổ modal chọn màn chơi."""
        if self.is_stage_selector_open:
            self.close_stage_selector()
        else:
            self.open_stage_selector()

    def open_stage_selector(self) -> None:
        """Mở modal chọn màn chơi cao cấp gồm 33 màn original và 6 màn samples."""
        self.close_help_modal()
        if self.stage_selector_modal is not None:
            destroy(self.stage_selector_modal)

        self.is_stage_selector_open = True
        if not hasattr(self, "stage_selector_tab"):
            self.stage_selector_tab = "original"

        won_count = len(self.catalog.progress)
        total_count = len(self.catalog.all_stages)

        # Modal Panel with Stardew parchment styling
        self.stage_selector_modal = PixelPanel(
            scale=(1.60, 0.92),
            position=(0, 0, -15),
            title="STAGE SELECT",
            subtitle=f"Completed: {won_count}/{total_count} Stages  •  Press ESC or Click Outside to Close",
            close_button=True,
            on_close=self.close_stage_selector,
        )

        self.tab_container = Entity(parent=self.stage_selector_modal, z=-0.06)
        self.grid_container = Entity(parent=self.stage_selector_modal, z=-0.06)

        self._render_stage_selector_tabs()
        self._render_stage_selector_grid()

    def _render_stage_selector_tabs(self) -> None:
        """Hiển thị các nút tab chuyển danh mục."""
        for c in self.tab_container.children:
            destroy(c)

        is_orig = (self.stage_selector_tab == "original")
        orig_count = len(self.catalog.original_stages)
        sample_count = len(self.catalog.sample_stages)
        orig_won = sum(1 for s in self.catalog.original_stages if s["id"] in self.catalog.progress)
        sample_won = sum(1 for s in self.catalog.sample_stages if s["id"] in self.catalog.progress)

        tab_w, tab_h = 0.52, 0.054

        # Tab 1: Main Stages
        btn_tab1 = PixelTab(
            parent=self.tab_container,
            text=f"Main Stages ({orig_count})  •  {orig_won}/{orig_count} Cleared",
            tab_id="original",
            is_active=is_orig,
            scale=(tab_w, tab_h),
            position=(-0.28, 0.305, -0.02),
            on_click=lambda: self._switch_stage_tab("original"),
        )

        # Tab 2: Sample Stages
        btn_tab2 = PixelTab(
            parent=self.tab_container,
            text=f"Sample Stages ({sample_count})  •  {sample_won}/{sample_count} Cleared",
            tab_id="samples",
            is_active=not is_orig,
            scale=(tab_w, tab_h),
            position=(0.28, 0.305, -0.02),
            on_click=lambda: self._switch_stage_tab("samples"),
        )

    def _switch_stage_tab(self, tab_name: str) -> None:
        """Chuyển đổi tab."""
        if self.stage_selector_tab != tab_name:
            self.stage_selector_tab = tab_name
            self._render_stage_selector_tabs()
            self._render_stage_selector_grid()

    def _render_stage_selector_grid(self) -> None:
        """Hiển thị lưới các thẻ bài màn chơi với phân tầng Z tuyệt đối không bị đè."""
        for c in self.grid_container.children:
            destroy(c)

        stages = self.catalog.original_stages if self.stage_selector_tab == "original" else self.catalog.sample_stages
        current_id = getattr(self, "current_stage_id", "stage01")

        if self.stage_selector_tab == "original":
            # 33 màn: 7 cột x 5 hàng
            cols = 7
            start_x = -0.63
            start_y = 0.225
            dx = 0.21
            dy = 0.115
            card_w, card_h = 0.192, 0.092
        else:
            # 6 màn mẫu: 3 cột x 2 hàng, kích thước lớn
            cols = 3
            start_x = -0.44
            start_y = 0.14
            dx = 0.44
            dy = 0.18
            card_w, card_h = 0.39, 0.14

        for i, st in enumerate(stages):
            st_id = st["id"]
            row = i // cols
            col = i % cols
            px_pos = start_x + col * dx
            py_pos = start_y - row * dy

            is_curr = (st_id == current_id)
            is_won = st_id in self.catalog.progress
            best_moves = self.catalog.progress[st_id].get("best_moves") if is_won else None
            ref_len = st.get("reference_length")

            PixelLevelTile(
                parent=self.grid_container,
                stage_id=st_id,
                is_current=is_curr,
                is_won=is_won,
                best_moves=best_moves,
                ref_len=ref_len,
                scale=(card_w, card_h),
                position=(px_pos, py_pos, -0.02),
                on_click=lambda tid=st_id: self._on_stage_clicked(tid),
            )

    def _on_stage_clicked(self, st_id: str) -> None:
        """Xử lý khi click vào nút chọn màn."""
        self.close_stage_selector()
        self.on_select_stage(st_id)

    def close_stage_selector(self) -> None:
        """Đóng modal chọn màn."""
        if self.stage_selector_modal:
            destroy(self.stage_selector_modal)
            self.stage_selector_modal = None
        self.is_stage_selector_open = False

    def toggle_help_modal(self) -> None:
        """Bật/tắt modal hướng dẫn phím tắt."""
        if self.is_help_modal_open:
            self.close_help_modal()
        else:
            self.open_help_modal()

    def open_help_modal(self) -> None:
        """Mở modal hướng dẫn chi tiết toàn bộ phím tắt."""
        self.close_stage_selector()
        if self.help_modal is not None:
            destroy(self.help_modal)

        self.is_help_modal_open = True
        self.help_modal = PixelPanel(
            scale=(1.25, 0.82),
            position=(0, 0, -16),
            title="HOW TO PLAY & CONTROLS",
            subtitle="Press ESC or Click Outside to Close",
            close_button=True,
            on_close=self.close_help_modal,
        )

        help_text = (
            "• W / A / S / D or Arrow Keys: Roll the Bloxorz block\n\n"
            "• Space: Switch block in split mode (two 1x1 cubes)\n\n"
            "• U: Undo last move\n\n"
            "• R: Reset stage to start\n\n"
            "• P: Pause / Resume replay\n\n"
            "• Tab or M: Open Stage Select modal (39 stages)\n\n"
            "• C: Reset Camera view to default\n\n"
            "• V: Toggle Isometric / Perspective Camera\n\n"
            "• Mouse Wheel: Zoom in / Zoom out\n\n"
            "• Right Mouse Drag: Free 3D camera rotation"
        )

        Text(
            parent=self.help_modal.content_area,
            text=help_text,
            font=FONT_NAME,
            scale=1.12,
            origin=(0, 0),
            position=(0, 0.02, -0.01),
            color=color.hex(PALETTE["ink"]),
        )

        PixelButton(
            parent=self.help_modal.content_area,
            text=LocalizedStr("Close", ["Đóng"]),
            color_ramp="orange",
            scale=(0.14, 0.06),
            position=(0, -0.32, -0.02),
            on_click=self.close_help_modal,
        )

    def close_help_modal(self) -> None:
        """Đóng modal hướng dẫn."""
        if self.help_modal:
            destroy(self.help_modal)
            self.help_modal = None
        self.is_help_modal_open = False
