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
from game.theme import UI_FONT, get_theme

if TYPE_CHECKING:
    from game.engine import BloxorzEngine

FONT_NAME = UI_FONT


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

        self.theme = get_theme("toy")
        self.ui_root = Entity(parent=camera.ui, name="ui_root")

        # 1. Thanh tiêu đề đỉnh (Top Header)
        self.header_panel = Entity(
            parent=self.ui_root,
            model="quad",
            scale=(2.2, 0.08),
            position=(0, 0.46, 0.05),
            color=rgba255(16, 44, 42, 230),
        )

        self.txt_stage = Text(
            parent=self.ui_root,
            text="Màn 01",
            font=FONT_NAME,
            scale=1.25,
            origin=(-0.5, 0),
            position=(-0.82, 0.46, -0.01),
            color=color.hex("#E6F7F7"),
        )

        self.txt_moves = Text(
            parent=self.ui_root,
            text="Số bước: 0",
            font=FONT_NAME,
            scale=1.20,
            origin=(-0.5, 0),
            position=(-0.60, 0.46, -0.01),
            color=color.hex("#FFD700"),
        )

        self.txt_status = Text(
            parent=self.ui_root,
            text="ĐANG CHƠI",
            font=FONT_NAME,
            scale=1.20,
            origin=(-0.5, 0),
            position=(-0.38, 0.46, -0.01),
            color=color.hex("#2ECC71"),
        )

        self.txt_cube_info = Text(
            parent=self.ui_root,
            text="",
            font=FONT_NAME,
            scale=1.05,
            origin=(-0.5, 0),
            position=(0.14, 0.46, -0.01),
            color=color.hex("#10B981"),
        )

        # Các nút chức năng trên đỉnh
        self.btn_select_stage = Button(
            parent=self.ui_root,
            text="Chọn Màn",
            font=FONT_NAME,
            scale=(0.13, 0.05),
            position=(0.60, 0.46, -0.01),
            color=rgba255(0, 121, 107, 230),
            text_color=color.white,
            on_click=self.toggle_stage_selector,
        )

        self.btn_help = Button(
            parent=self.ui_root,
            text="Trợ Giúp",
            font=FONT_NAME,
            scale=(0.11, 0.05),
            position=(0.74, 0.46, -0.01),
            color=rgba255(0, 77, 64, 230),
            text_color=color.white,
            on_click=self.toggle_help_modal,
        )

        # 2. Thanh điều khiển Replay đáy (Bottom Replay Bar)
        self.replay_panel = Entity(
            parent=self.ui_root,
            model="quad",
            scale=(2.2, 0.08),
            position=(0, -0.46, 0.05),
            color=rgba255(16, 44, 42, 230),
        )

        self.txt_replay_info = Text(
            parent=self.ui_root,
            text="Replay: Chưa nạp lời giải",
            font=FONT_NAME,
            scale=1.05,
            origin=(-0.5, 0),
            position=(-0.82, -0.46, -0.01),
            color=color.hex("#E6F7F7"),
        )

        # Cụm nút tua Replay
        self.btn_replay_start = Button(
            parent=self.ui_root,
            text="Đầu",
            font=FONT_NAME,
            scale=(0.065, 0.05),
            position=(-0.25, -0.46, -0.01),
            color=rgba255(40, 60, 70, 230),
            on_click=self.on_replay_jump_start,
        )

        self.btn_replay_prev = Button(
            parent=self.ui_root,
            text="Lùi",
            font=FONT_NAME,
            scale=(0.065, 0.05),
            position=(-0.17, -0.46, -0.01),
            color=rgba255(40, 60, 70, 230),
            on_click=self.on_replay_step_back,
        )

        self.btn_replay_play = Button(
            parent=self.ui_root,
            text="Phát",
            font=FONT_NAME,
            scale=(0.10, 0.05),
            position=(-0.07, -0.46, -0.01),
            color=rgba255(0, 150, 136, 230),
            on_click=self.on_replay_play_pause,
        )

        self.btn_replay_next = Button(
            parent=self.ui_root,
            text="Tiến",
            font=FONT_NAME,
            scale=(0.065, 0.05),
            position=(0.03, -0.46, -0.01),
            color=rgba255(40, 60, 70, 230),
            on_click=self.on_replay_step_forward,
        )

        self.btn_replay_end = Button(
            parent=self.ui_root,
            text="Cuối",
            font=FONT_NAME,
            scale=(0.065, 0.05),
            position=(0.11, -0.46, -0.01),
            color=rgba255(40, 60, 70, 230),
            on_click=self.on_replay_jump_end,
        )

        # Nút chuyển tốc độ
        self.current_speed = 1.0
        self.btn_speed = Button(
            parent=self.ui_root,
            text="1x",
            font=FONT_NAME,
            scale=(0.065, 0.05),
            position=(0.19, -0.46, -0.01),
            color=rgba255(50, 75, 90, 230),
            on_click=self._cycle_speed,
        )

        # Khung nhập file Replay thủ công
        self.inp_replay_path = InputField(
            parent=self.ui_root,
            default_value="",
            scale=(0.22, 0.045),
            position=(0.33, -0.46, -0.01),
            font=FONT_NAME,
        )

        self.btn_replay_load = Button(
            parent=self.ui_root,
            text="Nạp File",
            font=FONT_NAME,
            scale=(0.09, 0.045),
            position=(0.50, -0.46, -0.01),
            color=rgba255(38, 166, 154, 230),
            on_click=self._submit_custom_replay,
        )

        # 3. La bàn định hướng góc nhìn Isometric (Direction Compass)
        self.compass_panel = Entity(
            parent=self.ui_root,
            model="quad",
            scale=(0.23, 0.13),
            position=(0.74, -0.34, 0.05),
            color=rgba255(16, 44, 42, 210),
        )
        self.txt_compass_title = Text(
            parent=self.ui_root,
            text="HƯỚNG DI CHUYỂN",
            font=FONT_NAME,
            scale=0.85,
            origin=(0, 0),
            position=(0.74, -0.29, -0.01),
            color=color.hex("#80CBC4"),
        )
        self.txt_compass_u = Text(
            parent=self.ui_root,
            text="W / ^\nLên-Trái",
            font=FONT_NAME,
            scale=0.75,
            origin=(0, 0),
            position=(0.67, -0.33, -0.01),
            color=color.hex("#E6F7F7"),
        )
        self.txt_compass_r = Text(
            parent=self.ui_root,
            text="D / >\nLên-Phải",
            font=FONT_NAME,
            scale=0.75,
            origin=(0, 0),
            position=(0.81, -0.33, -0.01),
            color=color.hex("#E6F7F7"),
        )
        self.txt_compass_l = Text(
            parent=self.ui_root,
            text="A / <\nXuống-Trái",
            font=FONT_NAME,
            scale=0.75,
            origin=(0, 0),
            position=(0.67, -0.38, -0.01),
            color=color.hex("#E6F7F7"),
        )
        self.txt_compass_d = Text(
            parent=self.ui_root,
            text="S / v\nXuống-Phải",
            font=FONT_NAME,
            scale=0.75,
            origin=(0, 0),
            position=(0.81, -0.38, -0.01),
            color=color.hex("#E6F7F7"),
        )

        # 4. Modal Bảng chọn màn chơi (Stage Selector Modal)
        self.stage_selector_modal: Entity | None = None
        self.is_stage_selector_open = False
        self.stage_selector_tab: str = "original"
        self.current_stage_id: str = "stage01"

        # 5. Modal Trợ giúp & Phím tắt (Help Modal)
        self.help_modal: Entity | None = None
        self.is_help_modal_open = False

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

    def _submit_custom_replay(self) -> None:
        """Người dùng nhấn nút nạp đường dẫn file replay nhập tay."""
        raw_path = self.inp_replay_path.text.strip()
        if raw_path:
            self.on_replay_load_file(raw_path)

    def set_replay_play_state(self, is_playing: bool) -> None:
        """Đổi nhãn nút phát Replay."""
        self.btn_replay_play.text = "Tạm Dừng" if is_playing else "Phát"
        self.btn_replay_play.color = rgba255(230, 126, 34, 230) if is_playing else rgba255(0, 150, 136, 230)

    def update_hud(self, engine: BloxorzEngine) -> None:
        """Cập nhật các số liệu trên thanh HUD theo trạng thái ván chơi."""
        st_id = engine.stage_id or "01"
        self.current_stage_id = st_id
        self.txt_stage.text = f"Màn {st_id}"
        self.txt_moves.text = f"Số bước: {engine.move_count}"

        if engine.is_won:
            self.txt_status.text = "CHIẾN THẮNG!"
            self.txt_status.color = color.hex("#FFD700")
        elif engine.is_lost:
            self.txt_status.text = "THẤT BẠI: Rơi xuống vực!"
            self.txt_status.color = color.hex("#E74C3C")
        else:
            self.txt_status.text = "ĐANG CHƠI"
            self.txt_status.color = color.hex("#2ECC71")

        if engine.is_split and not (engine.is_lost or engine.is_won):
            self.txt_cube_info.text = f"Đang chọn: Khối {engine.selected_cube} (Space)"
            self.txt_cube_info.color = color.hex("#10B981") if engine.selected_cube == 1 else color.hex("#38BDF8")
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
            self.txt_replay_info.text = "Replay: Không có lời giải"
        else:
            name_part = f" [{file_name}]" if file_name else ""
            self.txt_replay_info.text = f"Replay: Bước {step_idx}/{total_steps}{name_part}"

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

        # Container gốc của modal, đặt ở z thấp để luôn nổi lên trên toàn bộ UI và game 3D
        self.stage_selector_modal = Entity(
            parent=camera.ui,
            name="stage_selector_modal",
            z=-15,
        )

        # Nền mờ sang trọng, click vào nền để đóng modal
        backdrop = Button(
            parent=self.stage_selector_modal,
            model="quad",
            scale=(3, 3),
            color=color.rgba(4 / 255.0, 8 / 255.0, 15 / 255.0, 0.85),
            z=0.2,
            on_click=self.close_stage_selector,
        )
        backdrop.highlight_color = backdrop.color

        modal_w, modal_h = 1.60, 0.92
        panel_border = Entity(
            parent=self.stage_selector_modal,
            model="quad",
            scale=(modal_w + 0.006, modal_h + 0.006),
            position=(0, 0, 0.12),
            color=color.hex("#1E3A8A"),
        )

        window_panel = Entity(
            parent=self.stage_selector_modal,
            model="quad",
            scale=(modal_w, modal_h),
            position=(0, 0, 0.1),
            color=color.rgba(11 / 255.0, 18 / 255.0, 32 / 255.0, 0.98),
        )

        # Tiêu đề & Thông tin tiến độ
        title = Text(
            parent=self.stage_selector_modal,
            text="CHỌN MÀN CHƠI",
            font=FONT_NAME,
            scale=1.7,
            origin=(0, 0),
            position=(0, 0.405, -0.05),
            color=color.hex("#F8FAFC"),
        )

        won_count = len(self.catalog.progress)
        total_count = len(self.catalog.all_stages)
        subtitle = Text(
            parent=self.stage_selector_modal,
            text=f"Tiến độ hoàn thành: {won_count}/{total_count} màn  •  Nhấn ESC hoặc click ngoài để đóng",
            font=FONT_NAME,
            scale=0.88,
            origin=(0, 0),
            position=(0, 0.36, -0.05),
            color=color.hex("#94A3B8"),
        )

        # Nút Đóng (X)
        btn_close = Button(
            parent=self.stage_selector_modal,
            text="X",
            font=FONT_NAME,
            scale=(0.046, 0.046),
            position=(modal_w / 2 - 0.048, 0.405, -0.08),
            color=color.rgba(30 / 255.0, 41 / 255.0, 59 / 255.0, 0.9),
            text_color=color.hex("#CBD5E1"),
            on_click=self.close_stage_selector,
        )
        btn_close.highlight_color = color.hex("#EF4444")

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

        # Tab 1: Màn gốc
        t1_col = color.hex("#0284C7") if is_orig else color.rgba(30 / 255.0, 41 / 255.0, 59 / 255.0, 0.95)
        t1_txt = color.white if is_orig else color.hex("#94A3B8")
        btn_tab1 = Button(
            parent=self.tab_container,
            text=f"Màn Gốc ({orig_count})  •  {orig_won}/{orig_count} Đã qua",
            font=FONT_NAME,
            scale=(tab_w, tab_h),
            position=(-0.28, 0.305, -0.02),
            color=t1_col,
            text_color=t1_txt,
            on_click=lambda: self._switch_stage_tab("original"),
        )
        btn_tab1.highlight_color = color.hex("#0369A1") if is_orig else color.hex("#334155")
        if hasattr(btn_tab1, "text_entity") and btn_tab1.text_entity:
            btn_tab1.text_entity.world_scale *= 0.88

        # Tab 2: Màn mẫu (Thử nghiệm)
        t2_col = color.hex("#0284C7") if not is_orig else color.rgba(30 / 255.0, 41 / 255.0, 59 / 255.0, 0.95)
        t2_txt = color.white if not is_orig else color.hex("#94A3B8")
        btn_tab2 = Button(
            parent=self.tab_container,
            text=f"Màn Thử Nghiệm ({sample_count})  •  {sample_won}/{sample_count} Đã qua",
            font=FONT_NAME,
            scale=(tab_w, tab_h),
            position=(0.28, 0.305, -0.02),
            color=t2_col,
            text_color=t2_txt,
            on_click=lambda: self._switch_stage_tab("samples"),
        )
        btn_tab2.highlight_color = color.hex("#0369A1") if not is_orig else color.hex("#334155")
        if hasattr(btn_tab2, "text_entity") and btn_tab2.text_entity:
            btn_tab2.text_entity.world_scale *= 0.88

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
            px = start_x + col * dx
            py = start_y - row * dy

            is_curr = (st_id == current_id)
            is_won = st_id in self.catalog.progress
            best_moves = self.catalog.progress[st_id].get("best_moves") if is_won else None
            ref_len = st.get("reference_length")

            if st.get("is_sample"):
                num_part = st_id.replace("sample", "")
                title_str = f"MẪU {num_part}"
            else:
                num_part = st_id.replace("stage", "")
                title_str = f"MÀN {num_part}"

            if is_curr:
                status_str = "ĐANG CHƠI"
                bg_col = color.rgba(30 / 255.0, 58 / 255.0, 138 / 255.0, 0.95)   # Sapphire đậm
                txt_col = color.hex("#60A5FA")                                    # Cyan sáng
                border_col = color.hex("#38BDF8")
            elif is_won:
                status_str = f"Kỷ lục: {best_moves} bước"
                bg_col = color.rgba(15 / 255.0, 35 / 255.0, 26 / 255.0, 0.95)   # Pine green trầm
                txt_col = color.hex("#34D399")                                    # Ngọc lục bảo
                border_col = color.hex("#059669")
            else:
                status_str = f"{ref_len}b tối ưu" if ref_len else "Chưa chơi"
                bg_col = color.rgba(24 / 255.0, 32 / 255.0, 47 / 255.0, 0.9)    # Graphite slate
                txt_col = color.hex("#94A3B8")                                    # Muted gray
                border_col = color.hex("#334155")

            full_label = f"{title_str}\n{status_str}"

            # Viền thẻ bài
            Entity(
                parent=self.grid_container,
                model="quad",
                scale=(card_w + 0.005, card_h + 0.005),
                position=(px, py, -0.01),
                color=border_col,
            )

            btn = Button(
                parent=self.grid_container,
                text=full_label,
                font=FONT_NAME,
                scale=(card_w, card_h),
                position=(px, py, -0.02),
                color=bg_col,
                text_color=txt_col,
                on_click=lambda tid=st_id: self._on_stage_clicked(tid),
            )
            btn.highlight_color = color.tint(bg_col, 0.35)
            btn.pressed_color = color.tint(bg_col, -0.15)
            if hasattr(btn, "text_entity") and btn.text_entity:
                btn.text_entity.world_scale *= 0.88

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
        self.help_modal = Entity(parent=camera.ui, name="help_modal", z=-1)

        backdrop = Entity(
            parent=self.help_modal,
            model="quad",
            scale=(2, 2),
            color=rgba255(0, 0, 0, 180),
        )

        window_panel = Entity(
            parent=self.help_modal,
            model="quad",
            scale=(1.2, 0.75),
            color=rgba255(14, 38, 38, 250),
        )

        Text(
            parent=window_panel,
            text="HƯỚNG DẪN & PHÍM TẮT ĐIỀU KHIỂN",
            font=FONT_NAME,
            scale=1.5,
            origin=(0, 0),
            position=(0, 0.42),
            color=color.hex("#FFD700"),
        )

        help_text = (
            "• W / A / S / D hoặc Phím Mũi Tên: Lăn khối Bloxorz\n\n"
            "• Space: Đổi khối điều khiển (khi khối bị phân tách thành 2)\n\n"
            "• U: Hoàn tác bước đi (Undo)\n\n"
            "• R: Đặt lại ván chơi từ đầu (Reset)\n\n"
            "• P: Tạm dừng / Tiếp tục phát Replay tự động\n\n"
            "• Tab hoặc M: Mở bảng chọn màn chơi (39 màn)\n\n"
            "• C: Đặt lại góc xoay và cự ly Camera về mặc định\n\n"
            "• V: Chuyển đổi qua lại giữa góc Isometric và Phối cảnh\n\n"
            "• Con lăn chuột: Phóng to / Thu nhỏ camera\n\n"
            "• Kéo chuột phải: Xoay tự do góc nhìn 3D"
        )

        Text(
            parent=window_panel,
            text=help_text,
            font=FONT_NAME,
            scale=1.15,
            origin=(0, 0),
            position=(0, 0.02),
            color=color.hex("#E6F7F7"),
        )

        Button(
            parent=window_panel,
            text="Đóng",
            font=FONT_NAME,
            scale=(0.12, 0.075),
            position=(0, -0.40),
            color=rgba255(0, 150, 136, 230),
            on_click=self.close_help_modal,
        )

    def close_help_modal(self) -> None:
        """Đóng modal hướng dẫn."""
        if self.help_modal:
            destroy(self.help_modal)
            self.help_modal = None
        self.is_help_modal_open = False
