"""Kiểm thử tự động UCS sau khi chuyển từ cost 1 sang chi phí có phụ phí.

File này chỉ dùng để kiểm thử, không được gọi khi chạy solver để giải game.
Công thức cần kiểm chứng: cost mỗi bước = 1 + 2*chạm F + chạm B + 3*tách khối.

Cách đọc:
* Các hàm đầu file tạo màn thử và tính kết quả tham chiếu để đối chiếu.
* ActionCostTests kiểm tra chi phí của từng bước, nhất là lúc tách/ghép khối.
* WeightedSearchTests kiểm tra đường đi tối ưu và dữ liệu xuất ra JSON/runner.

Chạy từ thư mục gốc dự án:
    python3 -m unittest discover -s tests -p test_ucs.py -v
"""
from __future__ import annotations

from collections import deque
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

# Thêm đường dẫn để unittest có thể import solver và checker từ thư mục gốc.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "algorithms"))
sys.path.insert(0, str(ROOT))

import BFS
import UCS
from checker import DIRECTIONS, Lost, Replay, State, check, execute_and_check, resolve_manifest_testcases
from run_tests import parse_args, run
from solver_support import SearchMetrics


# Màn đối chứng: BFS tìm đường 6 bước/cost 16; UCS tìm đường 7 bước/cost 15.
# Dùng để chứng minh mục tiêu "ít bước nhất" khác "tổng chi phí nhỏ nhất".
DETOUR_STAGE = {
    "id": "weighted-detour", "board": ["SF.F.", ".FFFF", "F....", ".F..G"],
    "bridges": [], "switches": [], "splitters": [],
}


def feature_stage(tiles=None, destinations=((0, 2), (0, 5))):
    """Tạo bàn 5×7; tiles ánh xạ (hàng, cột) sang ký hiệu ô muốn kiểm tra.

    Cầu được bật sẵn để thử phụ phí trên nước đi hợp lệ. Nếu dùng O/X, người
    gọi cần đặt thêm ô B để công tắc có cầu điều khiển. destinations là hai
    điểm đến không kề nhau khi kích hoạt T, theo yêu cầu của luật chơi.
    """
    board = [list(".......") for _ in range(5)]
    board[0][0], board[4][6] = "S", "G"
    for (r, c), tile in (tiles or {}).items():
        board[r][c] = tile
    cells = [(r, c, tile) for r, row in enumerate(board) for c, tile in enumerate(row)]
    bridges = [[r, c] for r, c, tile in cells if tile == "B"]
    return {
        "id": "cost-features", "board": ["".join(row) for row in board],
        "bridges": [{"id": "bridge", "cells": bridges, "active": True}] if bridges else [],
        "switches": [
            {"at": [r, c], "effects": [{"bridge": "bridge", "mode": "toggle"}]}
            for r, c, tile in cells if tile in "OX"
        ],
        "splitters": [
            {"at": [r, c], "destinations": [list(p) for p in destinations]}
            for r, c, tile in cells if tile == "T"
        ],
    }


def reference_step(model, state, action):
    """Tính một bước tham chiếu (test oracle) để đối chiếu với UCS.

    Dùng chung Replay để áp dụng luật game, nhưng tự tính phí bằng các số
    1/2/1/3 đã chốt; không lấy hằng số hay gọi action_cost của UCS. Nhờ vậy,
    nếu sửa nhầm trọng số trong UCS thì kết quả tham chiếu không đổi theo.
    """
    successor, split_at = model.step(state, action)
    if len(action) == 2:
        # Token như 1R/2L chỉ rõ cube di chuyển. Lấy vị trí TRƯỚC bước đi vì
        # sau khi ghép, Replay sắp xếp lại tọa độ và không còn giữ ID cube.
        origin = (state.first, state.second)[int(action[0]) - 1]
        delta = DIRECTIONS[action[-1]]
        cells = [(origin[0] + delta[0], origin[1] + delta[1])]
    else:
        cells = [successor.first, successor.second]
    penalty = 0
    # any(...) chỉ tính mỗi loại phí một lần, dù khối chạm hai ô cùng loại.
    for tile, weight in (("F", 2), ("B", 1)):
        if any(model.cells[p] == tile for p in cells):
            penalty += weight
    # split_at do Replay trả về chỉ có giá trị khi thực sự kích hoạt tách;
    # chạm T trong tư thế nằm không được tính là một lần tách.
    return successor, 1 + penalty + (3 if split_at is not None else 0)


def replay_cost(stage, actions):
    """Phát lại lời giải và cộng phí từng bước; chưa tới đích thì báo lỗi.

    Hàm này xác nhận tổng phí được báo cáo đúng với đường đi, nhưng riêng
    việc phát lại không chứng minh đó là đường có chi phí nhỏ nhất.
    """
    model = Replay(stage)
    state, total = model.initial, 0
    for action in actions:
        state, cost = reference_step(model, state, action)
        total += cost
    if not model.won(state):
        raise AssertionError("Lời giải chưa tới đích")
    return total


def reference_optimum(stage):
    """Duyệt đồ thị nhỏ rồi dùng Bellman-Ford, độc lập với heap/search UCS."""
    model = Replay(stage)
    states, queue, edges = {model.initial}, deque([model.initial]), []
    # Giai đoạn 1: liệt kê mọi state/cạnh có thể tới. Queue ở đây chỉ dùng
    # để dựng đồ thị; không dùng BFS để kết luận tối ưu cho cạnh khác cost.
    while queue:
        state = queue.popleft()
        if model.won(state):
            continue
        actions = [prefix + direction for prefix in (("1", "2") if state.split else ("",))
                   for direction in DIRECTIONS]
        for action in actions:
            try:
                successor, cost = reference_step(model, state, action)
            except Lost:
                continue
            edges.append((state, successor, cost))
            if successor not in states:
                states.add(successor)
                queue.append(successor)
    distances = {state: float("inf") for state in states}
    distances[model.initial] = 0
    # Giai đoạn 2: Bellman-Ford thử cải thiện chi phí trên tất cả các cạnh.
    # Với V state, tối đa V-1 lượt là đủ; dừng sớm nếu không còn cải thiện.
    # Cách này dễ đối chiếu nhưng chỉ dùng cho màn nhỏ vì tốn O(V*E).
    for _ in range(len(states) - 1):
        changed = False
        for state, successor, cost in edges:
            candidate = distances[state] + cost
            if candidate < distances[successor]:
                distances[successor] = candidate
                changed = True
        if not changed:
            break
    # Có thể có nhiều state thắng với trạng thái cầu khác nhau: lấy rẻ nhất.
    return min(distances[s] for s in states if model.won(s))


class ActionCostTests(unittest.TestCase):
    """Nhóm 1: kiểm tra hàm cost từng bước bằng các giá trị tính tay."""

    def assert_cost(self, stage, split, first, second, action, expected, expected_split=None):
        """Tạo state, đi một bước thật bằng Replay rồi so phí với expected.

        State được đặt trực tiếp để cô lập tình huống, không cần tìm đường
        từ S tới đó. expected_split kiểm tra thêm có tách/ghép như dự kiến.
        """
        model = Replay(stage)
        state = State(split, first, second, model.initial.bridges)
        successor, _ = model.step(state, action)
        self.assertEqual(UCS.action_cost(state, action, successor, model), expected)
        if expected_split is not None:
            self.assertEqual(successor.split, expected_split)

    def test_joined_tiles_and_additive_penalties(self):
        # Lăn từ tư thế đứng sang phải sẽ chiếm (2,2) và (2,3).
        # FF vẫn là 1+2=3; BB là 1+1=2; FB cộng cả hai phí: 1+2+1=4.
        for tiles, expected in (("..", 1), ("F.", 3), ("B.", 2), ("FF", 3), ("BB", 2), ("FB", 4)):
            with self.subTest(tiles=tiles):
                stage = feature_stage({(2, 2): tiles[0], (2, 3): tiles[1]})
                self.assert_cost(stage, False, (2, 1), (2, 1), "R", expected)

    def test_parked_cube_is_not_charged(self):
        # Cube đứng yên nằm trên F/B, cube kia đi tới sàn thường: cost phải
        # là 1. Thử cả ID 1 và ID 2 để tránh xử lý đúng chỉ một cube.
        for parked in ("F", "B"):
            for cube in (1, 2):
                with self.subTest(parked=parked, cube=cube):
                    first, second = ((2, 1), (2, 5)) if cube == 1 else ((2, 5), (2, 1))
                    self.assert_cost(feature_stage({(2, 5): parked}), True,
                                     first, second, f"{cube}R", 1, True)

    def test_rejoining_uses_moved_cube_before_coordinate_sort(self):
        # Cube từ (2,4) đi trái tới (2,3), kề cube đứng yên ở (2,2) nên ghép.
        # Sau khi ghép, first luôn là (2,2); đó lại là ô của cube đứng yên.
        # Chỉ được tính phí ô (2,3), bất kể cube vừa di chuyển mang ID nào.
        for cube in (1, 2):
            for moved, parked, expected in ((".", "F", 1), ("F", "B", 3), ("B", "F", 2)):
                with self.subTest(cube=cube, moved=moved, parked=parked):
                    first, second = ((2, 4), (2, 2)) if cube == 1 else ((2, 2), (2, 4))
                    self.assert_cost(feature_stage({(2, 3): moved, (2, 2): parked}),
                                     True, first, second, f"{cube}L", expected, False)

    def test_splitter_only_charges_when_activated(self):
        # Ca đầu: khối nằm ngang phủ lên T, không tách -> chỉ tốn 1.
        self.assert_cost(feature_stage({(2, 2): "T"}), False, (2, 1), (2, 1), "R", 1, False)
        # Các ca sau: khối đứng trên T -> cơ bản 1 + phí tách 3 = 4.
        # Cộng phụ phí tại hai điểm dịch chuyển; F+B cho tổng 4+2+1=7.
        for tiles, expected in (("..", 4), ("F.", 6), ("B.", 5), ("FF", 6), ("BB", 5), ("FB", 7)):
            with self.subTest(destinations=tiles):
                stage = feature_stage({(2, 2): "T", (0, 2): tiles[0], (0, 5): tiles[1]})
                self.assert_cost(stage, False, (2, 0), (2, 1), "R", expected, True)

    def test_switches_and_goal_have_no_extra_fee(self):
        # Nhấn O/X có thể đổi trạng thái cầu nhưng không có phụ phí công tắc.
        # Đứng vào G để thắng cũng chỉ tính chi phí di chuyển cơ bản.
        for tile in ("O", "X"):
            stage = feature_stage({(2, 2): tile, (4, 1): "B"})
            self.assert_cost(stage, False, (2, 0), (2, 1), "R", 1)
        self.assert_cost(feature_stage(), False, (4, 4), (4, 5), "R", 1)


class WeightedSearchTests(unittest.TestCase):
    """Nhóm 2: kiểm tra toàn bộ tìm kiếm và việc lưu kết quả ra bên ngoài."""

    def test_longer_path_is_cheaper_and_matches_independent_optimum(self):
        # Không chỉ so UCS với BFS: dùng thêm Bellman-Ford để biết cost tối
        # ưu thật sự, tránh chấp nhận một đường chỉ rẻ hơn BFS nhưng chưa tối ưu.
        with SearchMetrics() as metrics:
            actions, total = UCS.solve_with_cost(DETOUR_STAGE, metrics)
        with SearchMetrics() as metrics:
            bfs_actions = BFS.solve(DETOUR_STAGE, metrics)
        self.assertEqual((len(bfs_actions), replay_cost(DETOUR_STAGE, bfs_actions)), (6, 16))
        self.assertEqual((len(actions), total), (7, 15))
        self.assertEqual(total, replay_cost(DETOUR_STAGE, actions))
        self.assertEqual(total, reference_optimum(DETOUR_STAGE))
        self.assertEqual(check(DETOUR_STAGE, {"status": "solved", "actions": actions})["verdict"], "AC")
        # Cờ này vẫn kiểm tra số bước, không chứng nhận tối ưu weighted_cost.
        self.assertEqual(check(DETOUR_STAGE, {"status": "solved", "actions": actions}, 6, True)["verdict"], "WA")
        # Giao diện solve cũ vẫn phải trả đúng actions như solve_with_cost.
        with SearchMetrics() as metrics:
            self.assertEqual(UCS.solve(DETOUR_STAGE, metrics), actions)

    def test_improves_discovered_state_and_skips_stale_heap_entry(self):
        # Đồ thị giả chỉ để cô lập logic heap/best_cost, không mô phỏng bàn chơi:
        # start -> a tốn 5, nhưng start -> b -> a chỉ tốn 1+1=2.
        # a -> goal tốn 10, b -> goal tốn 20; lời giải tối ưu có cost 12.
        graph = {"start": [("a", "sa"), ("b", "sb")], "b": [("a", "ba"), ("goal", "bg")],
                 "a": [("goal", "ag")]}
        costs = {"sa": 5, "sb": 1, "ba": 1, "bg": 20, "ag": 10}
        # patch.object tạm thay các hàm luật chơi bằng đồ thị trên trong khối
        # with; tự khôi phục sau test. Vòng lặp tìm kiếm UCS vẫn chạy code thật.
        with patch.object(UCS, "parse_stage", return_value=None), \
             patch.object(UCS, "initial_state", return_value="start"), \
             patch.object(UCS, "is_goal", side_effect=lambda s, m: s == "goal"), \
             patch.object(UCS, "next_states", side_effect=lambda s, m: graph[s]), \
             patch.object(UCS, "action_cost", side_effect=lambda s, a, n, m: costs[a]):
            with SearchMetrics() as metrics:
                actions, total = UCS.solve_with_cost({}, metrics)
        self.assertEqual((actions, total), (["sb", "ba", "ag"], 12))
        # Chỉ mở rộng start, b, a. Bản ghi a với cost 5 đã lỗi thời phải bị
        # bỏ qua; đích không tính là nút mở rộng vì không sinh successor.
        self.assertEqual(metrics.as_dict()["expanded_nodes"], 3)

    def test_samples_match_reference_optimum_and_cli_metrics(self):
        # Chạy UCS qua tiến trình riêng trên cả 6 mẫu để kiểm tra luôn luồng
        # stdin -> solver -> JSON -> checker. Đối chiếu cả tổng phí phát lại
        # lẫn chi phí tối ưu Bellman-Ford, không dùng độ dài tham chiếu cũ.
        for item in resolve_manifest_testcases("samples"):
            stage = json.loads((ROOT / "testcases" / item["input"]).read_text())
            with self.subTest(stage=stage["id"]):
                result = execute_and_check(ROOT / "algorithms/UCS.py", stage)
                self.assertEqual(result["verdict"], "AC", result["message"])
                self.assertTrue(result["metrics_complete"], result["metrics_errors"])
                total = result["answer"]["metrics"]["weighted_cost"]
                self.assertEqual(total, replay_cost(stage, result["actions"]))
                self.assertEqual(total, reference_optimum(stage))
                self.assertEqual(result["statistics"]["weighted_cost"], total)
                self.assertEqual(result["statistics"]["cost"], len(result["actions"]))

    def test_runner_saves_weighted_cost_separately_from_length(self):
        # Dùng thư mục tạm để kiểm tra file JSON thật mà không ghi đè kết quả
        # trong results/. Thư mục này tự được xóa khi kết thúc khối with.
        with tempfile.TemporaryDirectory() as folder:
            args = parse_args(["--algorithm", str(ROOT / "algorithms/UCS.py"), "--suite", "samples",
                               "--test", "03", "--results_dir", folder])
            with redirect_stdout(io.StringIO()):
                self.assertEqual(run(args), 0)
            files = list(Path(folder).glob("*.json"))
            self.assertEqual(len(files), 1)
            result = json.loads(files[0].read_text())["tests"][0]
            # Sample 03 đi 2 bước, có 1 bước chạm F: weighted_cost = 2+2=4.
            # cost cũ vẫn phải bằng số bước (2) để giữ tương thích.
            self.assertEqual(result["statistics"]["solution_length"], 2)
            self.assertEqual(result["statistics"]["cost"], 2)
            self.assertEqual(result["statistics"]["weighted_cost"], 4)
            self.assertTrue(result["metrics_complete"])


if __name__ == "__main__":
    unittest.main()
