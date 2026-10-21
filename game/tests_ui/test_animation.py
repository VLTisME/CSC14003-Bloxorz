"""Kiểm thử tính toàn vẹn hoạt ảnh và chuyển động 3D (game/tests_ui/test_animation.py).

Kiểm tra:
1. Tính toàn vẹn kích thước hình học (Scale Integrity): Khi lăn nhiều bước liên tiếp,
   hiệu ứng squash đàn hồi không được ghi đè làm sai lệch kích thước khối (UPRIGHT vs HORIZONTAL/VERTICAL).
2. Hoạt ảnh rơi tự do khi thua (Smooth Fall): Khối tiếp nối góc nghiêng lăn tự nhiên,
   không bị giật snap về góc 0 hay sinh bụi tiếp đất trên không khí.
3. Khôi phục ô gạch mỏng (Fragile Tile Reset): Ô gạch mỏng vỡ được hoàn trả đúng vị trí khi Undo/Reset.
4. Tải bàn chơi (Stage Loading): Cả 39 màn chơi đều nạp thành công vào BoardView không phát sinh lỗi.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest
from ursina import Entity, Ursina, Vec3

from game.engine import BloxorzEngine, Posture
from game.stage_catalog import StageCatalog
from game.ursina_ui.anim import AnimationManager
from game.ursina_ui.block_view import BlockView
from game.ursina_ui.board_view import BoardView
from game.ursina_ui.particles import ParticlePool
from game.ursina_ui.shadows import BlobShadow

# Khởi tạo instance Ursina headless một lần duy nhất cho unit tests
_app = Ursina(headless=True)


class TestAnimationIntegrity(unittest.TestCase):
    """Kiểm thử tính chính xác của hệ thống hoạt ảnh AnimationManager."""

    def setUp(self) -> None:
        self.catalog = StageCatalog()
        self.engine = BloxorzEngine()
        data = json.loads(self.catalog.stage_by_id["stage01"]["input_path"].read_text(encoding="utf-8"))
        self.engine.load_stage(data)

        self.board_view = BoardView()
        self.board_view.load_stage(self.engine)

        self.block_view = BlockView()
        self.block_view.sync_from_engine(self.engine)

        self.shadow = BlobShadow()
        self.particles = ParticlePool()
        self.anim = AnimationManager(self.block_view, self.board_view, self.shadow, self.particles)

    def tearDown(self) -> None:
        self.anim.stop_all()

    def test_scale_integrity_across_moves(self) -> None:
        """Kiểm tra kích thước khối không bao giờ bị squash ghi đè thành sai tư thế."""
        # 1. Bắt đầu: Đứng thẳng (UPRIGHT)
        self.assertEqual(self.engine.posture, Posture.UPRIGHT)
        self.assertAlmostEqual(self.block_view.cube_1.scale.y, 0.98, places=2)
        self.assertAlmostEqual(self.block_view.cube_2.scale.y, 0.98, places=2)
        self.assertAlmostEqual(self.block_view.cube_2.position.y - self.block_view.cube_1.position.y, 1.0, places=2)

        # 2. Lăn sang phải -> Nằm ngang (HORIZONTAL)
        from_cells = list(self.engine.block_cells)
        self.assertTrue(self.engine.step("R"))
        self.assertEqual(self.engine.posture, Posture.HORIZONTAL)

        self.anim.start_roll(
            from_cells=from_cells,
            direction="R",
            on_complete=lambda: self.block_view.sync_from_engine(self.engine),
        )

        # Cập nhật qua toàn bộ thời lượng roll + squash recovery
        dt = 0.016
        for _ in range(30):
            self.anim.update(dt, self.engine)

        # Sau khi hoàn tất và squash kết thúc, khối PHẢI là HORIZONTAL (cube_1 và cube_2 xếp cạnh nhau theo trục X)
        self.assertAlmostEqual(self.block_view.cube_2.position.x - self.block_view.cube_1.position.x, 1.0, places=2)
        self.assertAlmostEqual(self.block_view.cube_1.position.y, 0.5, places=2)
        self.assertAlmostEqual(self.block_view.cube_2.position.y, 0.5, places=2)

        # 3. Lăn tiếp sang phải -> Đứng thẳng trở lại (UPRIGHT)
        from_cells = list(self.engine.block_cells)
        self.assertTrue(self.engine.step("R"))
        self.assertEqual(self.engine.posture, Posture.UPRIGHT)

        self.anim.start_roll(
            from_cells=from_cells,
            direction="R",
            on_complete=lambda: self.block_view.sync_from_engine(self.engine),
        )

        for _ in range(30):
            self.anim.update(dt, self.engine)

        # Khối PHẢI là UPRIGHT (cube_2 nằm chồng lên trên cube_1 theo trục Y)
        self.assertAlmostEqual(self.block_view.cube_2.position.y - self.block_view.cube_1.position.y, 1.0, places=2)

    def test_falling_move_seamless_transition(self) -> None:
        """Kiểm tra bước đi rơi tự do không bị giật snap góc xoay về 0."""
        # Tại stage01 ô xuất phát (1, 1), đi U là rơi xuống vực
        from_cells = list(self.engine.block_cells)
        success = self.engine.step("U")
        self.assertFalse(success)
        self.assertTrue(self.engine.is_lost)

        fall_started = False

        def on_roll_complete():
            nonlocal fall_started
            fall_started = True
            # Kiểm tra góc xoay tại cạnh vực không bị snap về 0
            self.assertGreater(abs(self.block_view.block_entity.rotation.x), 45.0)
            self.anim.start_fall(direction="U", reason=self.engine.lost_reason)

        self.anim.start_roll(
            from_cells=from_cells,
            direction="U",
            is_losing_move=True,
            on_complete=on_roll_complete,
        )

        dt = 0.016
        for _ in range(15):
            self.anim.update(dt, self.engine)

        self.assertTrue(fall_started)
        self.assertTrue(self.anim.is_falling)
        # Khối đang rơi với gia tốc âm (y giảm dần)
        initial_y = self.block_view.block_entity.y
        for _ in range(15):
            self.anim.update(dt, self.engine)
        self.assertLess(self.block_view.block_entity.y, initial_y)

    def test_reset_fragile_tiles(self) -> None:
        """Kiểm tra khôi phục độ cao của các ô gạch mỏng khi reset."""
        # Tạo giả lập gạch mỏng bị rơi
        dummy_tile = Entity(model="cube", position=Vec3(0, -10.0, 0), rotation=Vec3(45, 0, 0))
        self.board_view.fragile_entities[(0, 0)] = dummy_tile

        self.board_view.reset_fragile_tiles()
        self.assertAlmostEqual(dummy_tile.y, -self.board_view.thickness / 2.0, places=3)
        self.assertEqual(dummy_tile.rotation, Vec3(0, 0, 0))

    def test_all_39_stages_loading_and_geometry(self) -> None:
        """Kiểm tra toàn bộ 39 màn chơi nạp vào BoardView và BlockView không sinh lỗi."""
        for meta in self.catalog.all_stages:
            stage_id = meta["id"]
            data = json.loads(meta["input_path"].read_text(encoding="utf-8"))
            self.engine.load_stage(data)
            self.board_view.load_stage(self.engine)
            self.block_view.sync_from_engine(self.engine)

            # Khối phải có vị trí hợp lệ trên bàn
            self.assertIsNotNone(self.block_view.block_entity)
            self.assertGreater(self.board_view.tile_size, 0)

    def test_main_menu_escape_and_replay_resets_block_after_lose(self) -> None:
        """Kiểm tra sau khi thua ván và nhấn ESC về Main Menu, bấm Chơi ngay sẽ reset lại khối."""
        from game.ursina_ui.app import BloxorzUrsinaApp
        from game.ursina_ui.state_manager import GameState

        app = BloxorzUrsinaApp(start_in_menu=False)
        app.load_stage_by_id("01")

        # 1. Thực hiện nước đi thua (U tại ô 1,1)
        app.make_move("U")
        self.assertTrue(app.engine.is_lost)

        # Mô phỏng hoạt ảnh rơi kết thúc -> hiện màn hình Lose
        app.anim.block_view.block_entity.y = -25.0
        app._on_fall_finished()
        self.assertEqual(app.state_manager.current_state, GameState.LOSE)

        # 2. Người chơi nhấn ESC để về Main Menu
        app.input("escape")
        self.assertEqual(app.state_manager.current_state, GameState.MAIN_MENU)

        # Trạng thái khối và engine phải được khôi phục tại Main Menu
        self.assertTrue(app.engine.is_playing)
        self.assertEqual(app.engine.move_count, 0)
        self.assertAlmostEqual(app.block_view.block_entity.y, 0.0, places=2)
        self.assertAlmostEqual(app.block_view.block_entity.scale.x, 1.0, places=2)

        # 3. Người chơi bấm "CHƠI NGAY"
        app._menu_play()
        self.assertEqual(app.state_manager.current_state, GameState.PLAYING)
        self.assertTrue(app.engine.is_playing)

        # Khối lăn bình thường từ ô xuất phát
        self.assertTrue(app.make_move("R"))

    def test_main_menu_escape_and_replay_resets_block_after_win(self) -> None:
        """Kiểm tra sau khi thắng ván và nhấn ESC về Main Menu, bấm Chơi ngay sẽ reset lại khối."""
        from game.engine import GameStatus
        from game.ursina_ui.app import BloxorzUrsinaApp
        from game.ursina_ui.state_manager import GameState

        app = BloxorzUrsinaApp(start_in_menu=False)
        app.load_stage_by_id("01")

        # Mô phỏng chiến thắng
        app.engine.status = GameStatus.WON
        app.anim.block_view.block_entity.y = -2.5
        app.anim.block_view.block_entity.scale = Vec3(0.2, 0.2, 0.2)
        app._on_victory_finished()
        self.assertEqual(app.state_manager.current_state, GameState.WIN)

        # Nhấn ESC về Main Menu
        app.input("escape")
        self.assertEqual(app.state_manager.current_state, GameState.MAIN_MENU)

        # Khối và engine phải được khôi phục
        self.assertTrue(app.engine.is_playing)
        self.assertEqual(app.engine.move_count, 0)
        self.assertAlmostEqual(app.block_view.block_entity.y, 0.0, places=2)
        self.assertAlmostEqual(app.block_view.block_entity.scale.x, 1.0, places=2)

        # Bấm "CHƠI NGAY"
        app._menu_play()
        self.assertEqual(app.state_manager.current_state, GameState.PLAYING)
        self.assertTrue(app.engine.is_playing)
        self.assertTrue(app.make_move("R"))

    def test_stage_selector_close_returns_to_main_menu(self) -> None:
        """Kiểm tra khi mở bảng chọn màn từ Menu chính rồi đóng lại, Menu chính phải xuất hiện lại."""
        from game.ursina_ui.app import BloxorzUrsinaApp
        from game.ursina_ui.state_manager import GameState

        app = BloxorzUrsinaApp(start_in_menu=True)
        self.assertEqual(app.state_manager.current_state, GameState.MAIN_MENU)

        # Mở chọn màn
        app._menu_select_stage()
        self.assertEqual(app.state_manager.current_state, GameState.LEVEL_SELECT)
        self.assertTrue(app.ui.is_stage_selector_open)

        # Đóng chọn màn mà không chọn stage nào
        app.ui.close_stage_selector()
        self.assertEqual(app.state_manager.current_state, GameState.MAIN_MENU)
        self.assertTrue(app.main_menu_screen.enabled)

    def test_replay_button_switches_to_reset_when_moves_deviate(self) -> None:
        """Kiểm tra nếu người chơi tự đi trước 1-2 bước, nút Phát Replay biến thành nút Đặt Lại."""
        from game.ursina_ui.app import BloxorzUrsinaApp

        app = BloxorzUrsinaApp(start_in_menu=False)
        app.load_stage_by_id("01")

        self.assertEqual(app.ui.btn_replay_play.text, "Phát")

        # Đi tay 1 bước
        app.make_move("R")
        app.anim.stop_all()
        app._on_move_finished()

        # Nút chuyển thành "Đặt Lại"
        self.assertEqual(app.ui.btn_replay_play.text, "Đặt Lại")

        # Bấm nút Đặt Lại -> ván chơi được reset về đầu và nút chuyển lại thành "Phát"
        app.action_replay_toggle()
        self.assertEqual(app.ui.btn_replay_play.text, "Phát")
        self.assertEqual(app.engine.move_count, 0)
        self.assertEqual(app.replay_index, 0)

        # Bấm Phát -> chạy replay tự động
        app.action_replay_toggle()
        self.assertEqual(app.ui.btn_replay_play.text, "Tạm Dừng")
        self.assertTrue(app.is_replay_playing)


if __name__ == "__main__":
    unittest.main()
