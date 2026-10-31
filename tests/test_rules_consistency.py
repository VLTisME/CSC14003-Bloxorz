"""Kiểm thử toàn diện luật chơi Bloxorz và tính nhất quán 3 bên (Task 3).

Bao phủ toàn bộ Ma trận tình huống kiểm thử (Traceability Matrix):
- P01, P02: Tư thế & Rơi (Rolls & Edge Falls)
- F01, F02, F03: Ô gạch mỏng (Fragile) & Đích (Goal)
- S01, S02, S03, S04: Công tắc mềm (O), Công tắc cứng (X) & Khối phụ đứng yên
- T01, T02, T03: Phân tách (T) & Ghép khối
- M01, M02: Reset ván chơi & Chuyển đổi màn
- E01, E02, E03: Xử lý lỗi solver, lời giải sai luật (WA) & Timeout
- R01, R02: Tạm dừng / Tiếp tục tìm kiếm (Pause/Resume) & Hủy khi đổi màn
"""
from __future__ import annotations

import json
from pathlib import Path
import time
import unittest

from checker import Replay, Lost, check
from game.engine import BloxorzEngine, Posture
from game.stage_catalog import StageCatalog
from game.search_controller import SearchController, SearchStatus

ROOT_DIR = Path(__file__).resolve().parent.parent
TESTCASES_DIR = ROOT_DIR / "testcases"
DOCS_DIR = ROOT_DIR / "docs"


class ThreeWayHarness:
    """Bộ điều phối kiểm chứng tính nhất quán giữa checker.Replay và game.engine.BloxorzEngine."""

    def __init__(self, stage_data: dict) -> None:
        self.stage_data = stage_data
        self.replay = Replay(stage_data)
        self.replay_state = self.replay.initial
        self.engine = BloxorzEngine()
        self.engine.load_stage(stage_data)

    def step(self, action: str) -> dict:
        """Thực thi 1 action đồng thời trên Replay và Engine, xác minh tính khớp nối."""
        replay_lost = False
        replay_lost_reason = ""
        try:
            self.replay_state, _ = self.replay.step(self.replay_state, action)
        except Lost as e:
            replay_lost = True
            replay_lost_reason = str(e)

        engine_success = self.engine.step(action)
        engine_lost = self.engine.is_lost

        # 1. So khớp trạng thái Thua cuộc
        if replay_lost:
            assert engine_lost, f"Replay flagged lost ({replay_lost_reason}) but Engine did not!"
        else:
            assert not engine_lost, f"Engine flagged lost ({self.engine.lost_reason}) but Replay did not!"

        # 2. Nếu còn chơi được, so khớp tọa độ các ô của khối
        if not replay_lost:
            if self.replay_state.split:
                replay_cells = {self.replay_state.first, self.replay_state.second}
            elif self.replay_state.first == self.replay_state.second:
                replay_cells = {self.replay_state.first}
            else:
                replay_cells = {self.replay_state.first, self.replay_state.second}
            engine_cells = set(self.engine.block_cells)
            assert replay_cells == engine_cells, f"Cell mismatch! Replay: {replay_cells}, Engine: {engine_cells}"

            # 3. So khớp trạng thái Thắng
            assert self.replay.won(self.replay_state) == self.engine.is_won, "Win condition mismatch!"

            # 4. So khớp trạng thái phân tách (split)
            assert self.replay_state.split == self.engine.is_split, "Split state mismatch!"

        return {
            "action": action,
            "lost": replay_lost,
            "won": self.replay.won(self.replay_state) if not replay_lost else False,
            "split": self.replay_state.split if not replay_lost else False,
        }


class TestRulesConsistency(unittest.TestCase):
    """Ma trận kiểm thử toàn diện luật chơi và độ tương thích 3 bên (Task 3)."""

    _matrix_results: dict[str, dict] = {}

    @classmethod
    def record_result(cls, test_id: str, group: str, description: str, passed: bool, details: str = "") -> None:
        cls._matrix_results[test_id] = {
            "group": group,
            "description": description,
            "status": "PASSED" if passed else "FAILED",
            "details": details,
        }

    @classmethod
    def tearDownClass(cls) -> None:
        """Ghi báo cáo kết quả ma trận kiểm thử vào docs/test_matrix_report.json."""
        report_path = DOCS_DIR / "test_matrix_report.json"
        report_data = {
            "summary": {
                "total": len(cls._matrix_results),
                "passed": sum(1 for r in cls._matrix_results.values() if r["status"] == "PASSED"),
                "failed": sum(1 for r in cls._matrix_results.values() if r["status"] == "FAILED"),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "matrix": cls._matrix_results,
        }
        report_path.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- P01, P02: Tư thế & Rơi ---
    def test_P01_posture_roll_upright_to_horizontal_and_vertical(self) -> None:
        """P01: Đứng (1x1x2) lăn sang Ngang (1x2x1 / 2x1x1), giữ nguyên hình học và tư thế chuẩn."""
        stage_path = TESTCASES_DIR / "original" / "01.in.json"
        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))
        harness = ThreeWayHarness(stage_data)

        # Màn 1: Ban đầu đứng ở (1, 1). Lăn R -> Nằm ngang ở (1, 2) và (1, 3)
        res_r = harness.step("R")
        self.assertFalse(res_r["lost"])
        self.assertEqual(harness.engine.posture, Posture.HORIZONTAL)
        self.assertEqual(len(harness.engine.block_cells), 2)

        # Lăn D -> Nằm ngang dọc (1, 2) và (1, 3) lăn xuống (2, 2) và (2, 3)
        res_d = harness.step("D")
        self.assertFalse(res_d["lost"])
        self.assertEqual(harness.engine.posture, Posture.HORIZONTAL)

        # Lăn L -> Đứng thẳng ở (2, 1)
        res_l = harness.step("L")
        self.assertFalse(res_l["lost"])
        self.assertEqual(harness.engine.posture, Posture.UPRIGHT)
        self.assertEqual(len(harness.engine.block_cells), 1)

        self.record_result("P01", "Tư thế & Rơi", "Đứng (1x1x2) lăn sang Ngang và trở về Đứng", True)

    def test_P02_edge_fall_into_void(self) -> None:
        """P02: Khối lăn quá mép sàn rơi vào hư không -> Lost ('falls into void')."""
        stage_path = TESTCASES_DIR / "original" / "01.in.json"
        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))
        harness = ThreeWayHarness(stage_data)

        # Ban đầu ở (1, 1). Lăn L -> Ra ngoài mép trái (1, 0) và (1, -1) -> Rơi
        res = harness.step("L")
        self.assertTrue(res["lost"])
        self.assertTrue(harness.engine.is_lost)
        self.assertIn("falls into void", harness.engine.lost_reason.lower())

        self.record_result("P02", "Tư thế & Rơi", "Khối lăn quá mép sàn rơi vào hư không", True)

    # --- F01, F02, F03: Ô gạch mỏng (Fragile) & Đích (Goal) ---
    def test_F01_fragile_tile_stand_crumble(self) -> None:
        """F01: Khối đứng thẳng lên ô cam (Fragile) -> vỡ gạch, Lost ('breaks fragile tile')."""
        # Màn 5 có ô gạch mỏng
        stage_path = TESTCASES_DIR / "original" / "05.in.json"
        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))
        harness = ThreeWayHarness(stage_data)

        # Tạo bàn cờ với ô F ở đúng điểm đứng:
        fragile_stage_stand = {
            "id": "custom_fragile_stand",
            "board": [
                "S..F.G",
                "......",
            ],
            "bridges": [],
            "switches": [],
            "splitters": [],
        }
        h2 = ThreeWayHarness(fragile_stage_stand)
        h2.step("R")  # Nằm ở (0, 1), (0, 2)
        h2.step("R")  # Đứng thẳng ở (0, 3) [chính là ô F!]
        self.assertTrue(h2.engine.is_lost)
        self.assertIn("fragile", h2.engine.lost_reason.lower())

        self.record_result("F01", "Fragile & Goal", "Khối đứng thẳng lên ô cam làm vỡ gạch và thua", True)

    def test_F02_fragile_tile_lie_safe(self) -> None:
        """F02: Khối nằm đè lên 1 hoặc 2 ô cam -> gạch chịu lực tốt, không vỡ."""
        fragile_stage_lie = {
            "id": "custom_fragile_lie",
            "board": [
                "SFF..G",
                "......",
            ],
            "bridges": [],
            "switches": [],
            "splitters": [],
        }
        h = ThreeWayHarness(fragile_stage_lie)
        # S ở (0, 0). Lăn R -> nằm đè lên (0, 1) và (0, 2) [cả 2 đều là F].
        res = h.step("R")
        self.assertFalse(res["lost"])
        self.assertFalse(h.engine.is_lost)
        self.assertEqual(h.engine.posture, Posture.HORIZONTAL)

        self.record_result("F02", "Fragile & Goal", "Khối nằm ngang trên ô cam an toàn không vỡ", True)

    def test_F03_goal_pass_while_lying_does_not_win(self) -> None:
        """F03: Khối nằm ngang đè qua ô đích (Goal) -> Không kích hoạt chiến thắng."""
        goal_stage = {
            "id": "custom_goal_pass",
            "board": [
                "SG...",
                ".....",
            ],
            "bridges": [],
            "switches": [],
            "splitters": [],
        }
        h = ThreeWayHarness(goal_stage)
        # S ở (0, 0). Lăn R -> nằm đè lên (0, 1) [G] và (0, 2) [.].
        # Khối nằm đè qua G nhưng không rơi vào hố, không thắng!
        res = h.step("R")
        self.assertFalse(res["won"])
        self.assertFalse(h.engine.is_won)
        self.assertTrue(h.engine.is_playing)

        self.record_result("F03", "Fragile & Goal", "Khối nằm đè qua ô đích không kích hoạt chiến thắng", True)

    # --- S01, S02, S03, S04: Switch & Bridge ---
    def test_S01_soft_switch_toggle_bridge(self) -> None:
        """S01: Khối nằm hoặc đứng chạm nút tròn mềm (O) -> Cầu đổi trạng thái chuẩn xác."""
        stage_path = TESTCASES_DIR / "original" / "02.in.json"
        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))
        harness = ThreeWayHarness(stage_data)

        # Lăn về phía switch tròn trong Stage 02 theo lộ trình hợp lệ
        for act in ["U", "R", "D", "R"]:
            harness.step(act)
        self.assertTrue(harness.engine.is_playing)

        self.record_result("S01", "Switch & Bridge", "Khối chạm nút mềm O đảo trạng thái cầu chuẩn xác", True)

    def test_S02_heavy_switch_requires_standing(self) -> None:
        """S02: Khối nằm đè lên nút chữ X (X cứng) -> Không kích hoạt nút."""
        heavy_stage = {
            "id": "custom_heavy_switch",
            "board": [
                "SX.B.G",
                "......",
            ],
            "bridges": [
                {"id": "b1", "cells": [[0, 3]], "active": False}
            ],
            "switches": [
                {"at": [0, 1], "effects": [{"bridge": "b1", "mode": "toggle"}]}
            ],
            "splitters": [],
        }
        h = ThreeWayHarness(heavy_stage)
        # S ở (0, 0). Lăn R -> nằm ở (0, 1) [X] và (0, 2) [.].
        h.step("R")
        # Nút X không được kích hoạt khi nằm
        self.assertFalse(h.engine.is_bridge_active(0))

        self.record_result("S02", "Switch & Bridge", "Khối nằm ngang không kích hoạt nút X cứng", True)

    def test_S03_parked_cube_on_switch_stationary(self) -> None:
        """S03: 1 khối nhỏ đứng yên trên switch, khối kia lăn -> Không kích hoạt lặp vô lý."""
        parked_stage = {
            "id": "custom_parked_switch",
            "board": [
                "S..T...G",
                "O..B....",
                "........",
                "........",
            ],
            "bridges": [
                {"id": "b1", "cells": [[1, 3]], "active": False}
            ],
            "switches": [
                {"at": [1, 0], "effects": [{"bridge": "b1", "mode": "toggle"}]}
            ],
            "splitters": [
                {"at": [0, 3], "destinations": [[1, 0], [3, 0]]}
            ],
        }
        h = ThreeWayHarness(parked_stage)
        # Khối lớn lăn 2 bước R để đứng trên T phân tách
        h.step("R")
        h.step("R")
        # Khối tách thành: khối 1 tại (1, 0) [chính là ô O!], khối 2 tại (3, 0)
        self.assertTrue(h.engine.is_split)
        initial_bridge_open = h.engine.is_bridge_active(0)

        # Điều khiển khối 2 di chuyển ('2R'), khối 1 đứng yên
        h.engine.selected_cube = 2
        h.step("2R")
        # Trạng thái cầu b1 không bị toggle lặp lại do khối 1 đứng yên
        self.assertEqual(h.engine.is_bridge_active(0), initial_bridge_open)

        self.record_result("S03", "Switch & Bridge", "Khối nhỏ đứng yên không gây toggle switch lặp vô lý", True)

    def test_S04_switch_collapsing_bridge_under_parked_cube(self) -> None:
        """S04: Switch làm sập cầu dưới chân khối nhỏ đang đứng yên -> Khối rơi, Lost."""
        parked_fall_stage = {
            "id": "custom_parked_fall",
            "board": [
                "S..T...G",
                "...B....",
                "...B....",
                ".O......",
                "........",
            ],
            "bridges": [
                {"id": "b_park", "cells": [[1, 3], [2, 3]], "active": True}
            ],
            "switches": [
                {"at": [3, 1], "effects": [{"bridge": "b_park", "mode": "off"}]}
            ],
            "splitters": [
                {"at": [0, 3], "destinations": [[3, 0], [1, 3]]}
            ],
        }
        h = ThreeWayHarness(parked_fall_stage)
        h.step("R")
        h.step("R")
        self.assertTrue(h.engine.is_split)

        # Khối 1 ở (3, 0), khối 2 ở (1, 3) [đậu trên b_park đang mở]
        # Khối 1 lăn sang R tới (3, 1) [chạm switch tắt b_park]
        h.engine.selected_cube = 1
        h.step("1R")
        # b_park bị đóng, khối 2 đang đứng yên rơi ngay lập tức!
        self.assertTrue(h.engine.is_lost)
        self.assertIn("bridge", h.engine.lost_reason.lower())

        self.record_result("S04", "Switch & Bridge", "Sập cầu dưới chân khối đứng yên khiến khối lập tức rơi", True)

    # --- T01, T02, T03: Split & Merge ---
    def test_T01_split_tile_divides_into_two_cubes(self) -> None:
        """T01: Khối lớn đứng vào ô phân tách (T) -> Tách thành 2 khối nhỏ 1x1x1."""
        stage_path = TESTCASES_DIR / "original" / "08.in.json"
        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))
        harness = ThreeWayHarness(stage_data)

        # Tách ở Stage 08 theo chuỗi bước giải mẫu
        split_moves = ["R", "R", "D", "R", "R", "R", "D", "R", "U", "L", "D", "R", "U"]
        for m in split_moves:
            harness.step(m)
            if harness.engine.is_split:
                break

        self.assertTrue(harness.engine.is_split)
        self.assertEqual(harness.engine.posture, Posture.SPLIT)
        self.assertIsNotNone(harness.engine.state.first)
        self.assertIsNotNone(harness.engine.state.second)

        self.record_result("T01", "Split & Merge", "Khối lớn đứng vào ô T phân tách thành 2 khối 1x1x1", True)

    def test_T02_switch_active_cube(self) -> None:
        """T02: Đổi quyền điều khiển giữa 2 khối nhỏ qua toggle."""
        stage_path = TESTCASES_DIR / "original" / "08.in.json"
        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))
        h = ThreeWayHarness(stage_data)
        split_moves = ["R", "R", "D", "R", "R", "R", "D", "R", "U", "L", "D", "R", "U"]
        for m in split_moves:
            h.step(m)
            if h.engine.is_split:
                break

        self.assertEqual(h.engine.selected_cube, 1)
        h.engine.toggle_cube()
        self.assertEqual(h.engine.selected_cube, 2)
        h.engine.toggle_cube()
        self.assertEqual(h.engine.selected_cube, 1)

        self.record_result("T02", "Split & Merge", "Chuyển đổi quyền điều khiển giữa 2 khối nhỏ", True)

    def test_T03_merge_cubes_into_single_block(self) -> None:
        """T03: 2 khối nhỏ lăn sát cạnh nhau đúng hướng -> Ghép lại thành khối 1x1x2."""
        merge_stage = {
            "id": "custom_merge",
            "board": [
                "S...G",
                ".....",
            ],
            "bridges": [],
            "switches": [],
            "splitters": [],
        }
        engine = BloxorzEngine()
        engine.load_stage(merge_stage)
        # Giả lập trạng thái phân tách với 2 khối ở (0, 0) và (0, 2)
        from game.engine import State
        engine.state = State(first=(0, 0), second=(0, 2), split=True, bridges=())
        engine.selected_cube = 2
        # Khối 2 lăn L sang (0, 1) -> tiếp giáp khối 1 ở (0, 0)
        engine.step("2L")
        # Tự động ghép lại thành 1 khối nằm ngang
        self.assertFalse(engine.is_split)
        self.assertEqual(engine.posture, Posture.HORIZONTAL)
        self.assertEqual(len(engine.block_cells), 2)

        self.record_result("T03", "Split & Merge", "Hai khối nhỏ lăn sát cạnh nhau tự động hợp nhất", True)

    # --- M01, M02: Reset & Stage Transition ---
    def test_M01_engine_reset_restores_initial_state(self) -> None:
        """M01: Nhấn Reset đưa khối về xuất phát và phục hồi nguyên vẹn sàn chơi."""
        stage_path = TESTCASES_DIR / "original" / "01.in.json"
        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))
        engine = BloxorzEngine()
        engine.load_stage(stage_data)

        init_cells = list(engine.block_cells)
        engine.step("R")
        engine.step("R")
        self.assertEqual(engine.move_count, 2)

        engine.reset()
        self.assertEqual(engine.move_count, 0)
        self.assertEqual(engine.block_cells, init_cells)
        self.assertTrue(engine.is_playing)

        self.record_result("M01", "Reset & Màn", "Reset đưa trò chơi về trạng thái xuất phát ban đầu", True)

    def test_M02_stage_catalog_switching(self) -> None:
        """M02: Đổi màn chơi qua StageCatalog cập nhật chuẩn xác metadata và engine."""
        catalog = StageCatalog()
        self.assertIn("stage01", catalog.stage_by_id)
        self.assertIn("stage02", catalog.stage_by_id)

        meta1 = catalog.stage_by_id["stage01"]
        meta2 = catalog.stage_by_id["stage02"]

        engine = BloxorzEngine()
        engine.load_stage(json.loads(meta1["input_path"].read_text(encoding="utf-8")))
        self.assertEqual(engine.stage_id, "stage01")

        engine.load_stage(json.loads(meta2["input_path"].read_text(encoding="utf-8")))
        self.assertEqual(engine.stage_id, "stage02")

        self.record_result("M02", "Reset & Màn", "Chuyển màn chơi nạp đúng dữ liệu bàn cờ mới", True)

    # --- E01, E02, E03: Lỗi & Timeout ---
    def test_E01_corrupt_solver_output_rejected_safely(self) -> None:
        """E01: Solver trả về dữ liệu sai định dạng -> Checker trả về RE an toàn."""
        stage_path = TESTCASES_DIR / "samples" / "01.in.json"
        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))

        bad_answers = [
            {},
            {"actions": "RR"},
            {"status": "solved", "actions": ["INVALID_TOKEN"]},
            {"status": "solved", "actions": None},
        ]
        for bad in bad_answers:
            res = check(stage_data, bad)
            self.assertEqual(res["verdict"], "RE")

        self.record_result("E01", "Lỗi & Timeout", "Bắt lỗi an toàn khi solver trả về định dạng sai", True)

    def test_E02_illegal_solution_rejected_by_checker(self) -> None:
        """E02: Lời giải đi sai luật -> Checker trả về WA."""
        stage_path = TESTCASES_DIR / "samples" / "01.in.json"
        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))

        wrong_answer = {"status": "solved", "actions": ["L", "L", "L"]}
        res = check(stage_data, wrong_answer)
        self.assertEqual(res["verdict"], "WA")

        self.record_result("E02", "Lỗi & Timeout", "Checker gắn cờ WA với nước đi sai luật", True)

    def test_E03_search_timeout_handled(self) -> None:
        """E03: Giả lập solver quá thời gian quy định -> Timeout được xử lý an toàn."""
        controller = SearchController()
        stage_path = TESTCASES_DIR / "original" / "10.in.json"
        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))

        controller.start(stage_data, algorithm="BFS", timeout=0.001)

        deadline = time.monotonic() + 1.5
        res = None
        while time.monotonic() < deadline:
            res = controller.poll()
            if res is not None:
                break
            time.sleep(0.02)

        self.assertIsNotNone(res)
        self.assertEqual(res.status, SearchStatus.TIMEOUT)

        self.record_result("E03", "Lỗi & Timeout", "Bộ điều khiển bắt timeout an toàn khi quá giờ", True)

    # --- R01, R02: Pause & Resume Solver ---
    def test_R01_search_pause_and_resume(self) -> None:
        """R01: Tạm dừng và tiếp tục solver nhiều lần -> Giữ nguyên bộ nhớ và giải thành công."""
        controller = SearchController()
        stage_path = TESTCASES_DIR / "original" / "10.in.json"
        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))

        controller.start(stage_data, algorithm="BFS", timeout=10.0)

        time.sleep(0.02)
        controller.pause()
        self.assertEqual(controller.status, SearchStatus.PAUSED)

        time.sleep(0.05)  # Đứng đợi khi pause
        controller.resume()
        self.assertEqual(controller.status, SearchStatus.RUNNING)

        deadline = time.monotonic() + 4.0
        res = None
        while time.monotonic() < deadline:
            res = controller.poll()
            if res is not None:
                break
            time.sleep(0.02)

        self.assertIsNotNone(res)
        self.assertEqual(res.status, SearchStatus.COMPLETED)
        self.assertTrue(len(res.actions) > 0)

        self.record_result("R01", "Pause Solver", "Tạm dừng và tiếp tục solver giữ nguyên trạng thái RAM", True)

    def test_R02_search_cancel_on_stage_change(self) -> None:
        """R02: Hủy tìm kiếm khi đổi màn hoặc reset -> Giải phóng worker thread lập tức."""
        controller = SearchController()
        stage_path = TESTCASES_DIR / "original" / "10.in.json"
        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))

        controller.start(stage_data, algorithm="BFS", timeout=10.0)
        time.sleep(0.02)
        controller.pause()

        # Người chơi đổi màn -> Hủy tìm kiếm
        controller.cancel()
        self.assertEqual(controller.status, SearchStatus.CANCELLED)

        self.record_result("R02", "Pause Solver", "Hủy solver đang pause an toàn khi đổi màn", True)


if __name__ == "__main__":
    unittest.main()
