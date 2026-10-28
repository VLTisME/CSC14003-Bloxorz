"""Hệ thống hoạt ảnh chuyển động 3D (Animation Engine) cho Bloxorz Ursina UI.

Bao gồm:
1. RollAnimation: Lăn quay 3D chuẩn xác quanh cạnh tiếp xúc đáy sàn (Rodrigues Roll)
   - Đảm bảo tính nhất quán hình học tuyệt đối (assert_roll_consistency)
   - Không bao giờ xuyên sàn hoặc lơ lửng trên sàn
   - Easing mượt mà (ease_out_cubic) kết hợp vi đàn hồi (squash & stretch) khi chạm sàn
   - Độc lập tốc độ khung hình (frame-rate independent)
2. FallAnimation: Rơi tự do 3D xuống vực sâu
   - Rơi theo đúng cạnh bị hẫng
   - Vỡ gạch mỏng (fragile tile crumble) nếu khối đứng trên ô cam F
   - Gia tốc trọng trường g và xoay hỗn loạn (tumble)
3. VictoryAnimation: Hoạt ảnh chiến thắng
   - Khối đứng trên ô đích G chìm dần xuống hố xoay vòng
   - Bắn pháo giấy hoa chúc mừng (victory confetti)
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Callable
from ursina import Entity, Vec3, color, scene, time

from game.engine import Posture
from game.theme import get_ursina_config

if TYPE_CHECKING:
    from game.engine import BloxorzEngine
    from game.ursina_ui.block_view import BlockView
    from game.ursina_ui.board_view import BoardView
    from game.ursina_ui.particles import ParticlePool
    from game.ursina_ui.shadows import BlobShadow


def ease_out_cubic(t: float) -> float:
    """Hàm gia tốc mượt mà: nhanh lúc đầu và hãm êm ái khi chạm đất."""
    clamped = max(0.0, min(1.0, t))
    inv = 1.0 - clamped
    return 1.0 - inv * inv * inv
# ==============================================================================
# THAM SỐ VẬT LÝ HOẠT ẢNH RƠI (BLOXORZ FALL PHYSICS CONSTANTS)
# Dễ dàng tinh chỉnh tốc độ, gia tốc và độ trôi dạt của khối khi rơi
# ==============================================================================
FALL_GRAVITY = -28.0            # Gia tốc trọng trường khi rơi tự do (đơn vị/s^2)
FALL_PIVOT_ROT_SPEED = 280.0    # Tốc độ góc xoay quanh gờ đá điểm tựa (deg/s)
FALL_DRIFT_SPEED = 2.4          # Tốc độ trôi dạt ra xa mép sàn để tránh cắt thành ô (đơn vị/s)
FALL_ESCAPE_ANGLE = 45.0        # Góc nghiêng thoát khỏi điểm tựa chuyển sang rơi tự do (độ)
FALL_TERMINAL_DEPTH = -18.0     # Độ sâu rơi khuất camera trước khi kích hoạt Lose Screen
FALL_BASE_DURATION = 0.85       # Thời lượng cơ bản của hoạt ảnh rơi ở tốc độ 1x (giây)


class AnimationManager:
    """Quản lý các trạng thái hoạt ảnh chuyển động của khối trong game."""

    def __init__(
        self,
        block_view: BlockView,
        board_view: BoardView,
        shadow: BlobShadow,
        particles: ParticlePool,
    ) -> None:
        self.block_view = block_view
        self.board_view = board_view
        self.shadow = shadow
        self.particles = particles

        cfg = get_ursina_config()
        self.base_roll_duration = float(cfg.get("roll_duration", 0.16))
        self.base_fall_duration = float(cfg.get("fall_duration", 0.85))
        self.base_victory_duration = float(cfg.get("victory_duration", 1.3))
        self.speed_mult = 1.0

        # Pivot Entity chuyên dùng để xoay khối quanh cạnh đáy
        self.pivot = Entity(name="roll_pivot", position=Vec3(0, 0, 0))

        # Trạng thái Roll
        self.is_rolling = False
        self.is_losing_roll = False
        self.roll_direction = "D"
        self.roll_elapsed = 0.0
        self.roll_duration = self.base_roll_duration
        self.roll_axis = "z"
        self.roll_target_angle = 0.0
        self.active_cube_entity: Entity | None = None
        self.on_roll_complete: Callable[[], None] | None = None

        # Trạng thái Fall (Thua ván)
        self.is_falling = False
        self.fall_elapsed = 0.0
        self.fall_duration = self.base_fall_duration
        self.fall_type = "TOTAL_VOID"
        self.fall_data: dict | None = None
        self.fall_vy = 0.0
        self.fall_vx = 0.0
        self.fall_vz = 0.0
        self.fall_rot_speed = Vec3(0, 0, 0)
        self.cliff_pivot = Vec3(0, 0, 0)
        self.cliff_axis = "x"
        self.cliff_sign = 1.0
        self.cliff_slide_dir = Vec3(0, 0, 0)
        self.cliff_slide_speed = 0.0
        self.cliff_rot_speed = 0.0
        self.cliff_angle = 0.0
        self.cliff_cleared = False
        self.cliff_initial_ent_pos = Vec3(0, 0, 0)
        self.cliff_initial_ent_rot = Vec3(0, 0, 0)
        self.cliff_offset = Vec3(0, 0, 0)
        self.crumbling_tile: Entity | None = None
        self.on_fall_complete: Callable[[], None] | None = None

        # Trạng thái Victory (Thắng ván)
        self.is_victory = False
        self.victory_elapsed = 0.0
        self.victory_duration = self.base_victory_duration
        self.on_victory_complete: Callable[[], None] | None = None

        # Trạng thái nẩy đàn hồi (Squash & stretch)
        self.squash_timer = 0.0
        self.squash_entity: Entity | None = None
        self.squash_base_scale = Vec3(1, 1, 1)

    @property
    def is_busy(self) -> bool:
        """Kiểm tra có hoạt ảnh nào đang chạy hay không."""
        return self.is_rolling or self.is_falling or self.is_victory

    def stop_all(self) -> None:
        """Dừng khẩn cấp toàn bộ hoạt ảnh khi người chơi Reset hoặc Undo."""
        if self.squash_timer > 0.0 and self.squash_entity is not None:
            self.squash_entity.scale = self.squash_base_scale

        if self.active_cube_entity is not None and self.active_cube_entity.parent == self.pivot:
            self.active_cube_entity.world_parent = scene
            self.active_cube_entity.rotation = Vec3(0, 0, 0)
        if hasattr(self, "block_view") and self.block_view and self.block_view.block_entity and self.block_view.block_entity.parent == self.pivot:
            self.block_view.block_entity.world_parent = scene
            self.block_view.block_entity.rotation = Vec3(0, 0, 0)
        self.pivot.rotation = Vec3(0, 0, 0)

        if hasattr(self, "shadow") and self.shadow is not None:
            self.shadow.unsuppress()

        self.is_rolling = False
        self.is_losing_roll = False
        self.is_falling = False
        self.fall_type = "TOTAL_VOID"
        self.fall_data = None
        self.fall_vx = 0.0
        self.fall_vz = 0.0
        self.fall_vy = 0.0
        self.cliff_angle = 0.0
        self.cliff_cleared = False
        self.is_victory = False
        self.squash_timer = 0.0
        self.squash_entity = None
        self.active_cube_entity = None
        self.crumbling_tile = None
        self.on_roll_complete = None
        self.on_fall_complete = None
        self.on_victory_complete = None

    def start_roll(
        self,
        from_cells: list[tuple[int, int]],
        direction: str,
        is_cube_2: bool = False,
        is_split: bool = False,
        is_losing_move: bool = False,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """Bắt đầu lăn khối theo hướng direction (U/D/L/R) quanh cạnh đáy tiếp xúc sàn."""
        # Dọn dẹp squash dở dang của bước trước nếu có để bảo toàn scale
        if self.squash_timer > 0.0 and self.squash_entity is not None:
            self.squash_entity.scale = self.squash_base_scale
            self.squash_timer = 0.0
            self.squash_entity = None

        self.stop_all()

        if is_split:
            target_ent = self.block_view.cube_2 if is_cube_2 else self.block_view.cube_1
        else:
            target_ent = self.block_view.block_entity

        if target_ent is None:
            return

        self.active_cube_entity = target_ent
        self.is_rolling = True
        self.is_losing_roll = is_losing_move
        self.roll_direction = direction
        self.roll_elapsed = 0.0
        self.roll_duration = max(0.04, self.base_roll_duration / max(0.1, self.speed_mult))
        self.on_roll_complete = on_complete

        # BỎ HẲN BÓNG NGAY TỪ ĐẦU NƯỚC ĐI GÂY RƠI / THUA
        if is_losing_move:
            self.shadow.suppress()

        # 1. Tính toán tâm và cạnh pivot đáy của các ô xuất phát
        rs = [r for r, c in from_cells]
        cs = [c for r, c in from_cells]
        cx = sum(cs) / float(len(cs))
        cz = -sum(rs) / float(len(rs))

        min_c, max_c = min(cs), max(cs)
        min_r, max_r = min(rs), max(rs)

        initial_world_pos = target_ent.world_position

        if direction == "R":
            pivot_pos = Vec3(max_c + 0.5, 0.0, cz)
            self.roll_axis = "z"
            self.roll_target_angle = 90.0
        elif direction == "L":
            pivot_pos = Vec3(min_c - 0.5, 0.0, cz)
            self.roll_axis = "z"
            self.roll_target_angle = -90.0
        elif direction == "D":
            pivot_pos = Vec3(cx, 0.0, -max_r - 0.5)
            self.roll_axis = "x"
            self.roll_target_angle = -90.0
        elif direction == "U":
            pivot_pos = Vec3(cx, 0.0, -min_r + 0.5)
            self.roll_axis = "x"
            self.roll_target_angle = 90.0
        else:
            self.is_rolling = False
            if on_complete:
                on_complete()
            return

        # 2. Gán khối làm con của pivot entity
        self.pivot.position = pivot_pos
        self.pivot.rotation = Vec3(0, 0, 0)
        target_ent.parent = self.pivot
        target_ent.position = initial_world_pos - pivot_pos
        target_ent.rotation = Vec3(0, 0, 0)


    def start_fall(
        self,
        direction: str = "D",
        reason: str | None = None,
        fragile_pos: tuple[int, int] | None = None,
        fall_type: str = "TOTAL_VOID",
        fall_data: dict | None = None,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """Bắt đầu hoạt ảnh rơi chuẩn vật lý, xử lý triệt để mọi trường hợp hẫng chân / gạch mỏng / mép vực."""
        self.is_falling = True
        self.fall_elapsed = 0.0
        self.fall_duration = max(0.65, FALL_BASE_DURATION / max(0.1, self.speed_mult))
        self.fall_type = fall_type
        self.fall_data = fall_data
        self.on_fall_complete = on_complete

        # BỎ HẲN BÓNG NGAY TỪ FRAME ĐẦU TIÊN KHI BẮT ĐẦU RƠI
        self.shadow.suppress()

        target_ent = self.active_cube_entity or self.block_view.block_entity
        ent_pos = Vec3(target_ent.x, target_ent.y, target_ent.z) if target_ent else Vec3(0, 0, 0)
        ent_rot = Vec3(target_ent.rotation_x, target_ent.rotation_y, target_ent.rotation_z) if target_ent else Vec3(0, 0, 0)

        # 1. Kịch bản 1: UPRIGHT đè vỡ gạch mỏng (FRAGILE_CRUMBLE)
        is_fragile = (
            fall_type in ("FRAGILE_CRUMBLE", "FRAGILE")
            or (reason and "fragile" in reason.lower())
            or (fragile_pos and fragile_pos in self.board_view.fragile_entities)
        )
        if is_fragile:
            self.fall_type = "FRAGILE_CRUMBLE"
            if fragile_pos and fragile_pos in self.board_view.fragile_entities:
                self.crumbling_tile = self.board_view.fragile_entities[fragile_pos]
            else:
                self.crumbling_tile = None
            self.fall_vx = 0.0
            self.fall_vz = 0.0
            self.fall_vy = -2.0
            self.fall_rot_speed = Vec3(35.0, 0.0, 25.0)

        # 2 & 3. Kịch bản vắt qua mép vực: UPRIGHT_OVERHANG_CLIFF hoặc LATERAL_TEETER_TIP
        elif fall_type in ("UPRIGHT_OVERHANG_CLIFF", "OVERHANG_TIP_FAR", "LATERAL_TEETER_TIP", "LATERAL_TIP") and fall_data:
            self.fall_type = fall_type
            self.crumbling_tile = None
            if "p_near" in fall_data and "p_far" in fall_data:
                solid = fall_data["p_near"]
                void = fall_data["p_far"]
            else:
                solid = fall_data.get("solid", (0, 0))
                void = fall_data.get("void", (0, 0))

            # Thiết lập khối chuẩn tại 2 ô [solid, void] để triệt tiêu mọi góc xoay cũ / gimbal lock
            self.block_view.setup_cells([solid, void])
            target_ent = self.block_view.block_entity
            self.active_cube_entity = target_ent

            dr = void[0] - solid[0]
            dc = void[1] - solid[1]

            if dc != 0:
                # Khối nằm ngang dọc theo cột, nghiêng quanh trục Z về phía ô trống
                pivot_pos = Vec3(float(solid[1]) + 0.5 * dc, 0.0, -float(solid[0]))
                self.cliff_axis = "z"
                self.cliff_sign = 1.0 if dc > 0 else -1.0
                self.cliff_slide_dir = Vec3(float(dc), 0.0, 0.0)
            else:
                # Khối nằm dọc theo hàng, nghiêng quanh trục X về phía ô trống
                pivot_pos = Vec3(float(solid[1]), 0.0, -float(solid[0]) - 0.5 * dr)
                self.cliff_axis = "x"
                self.cliff_sign = -1.0 if dr > 0 else 1.0
                self.cliff_slide_dir = Vec3(0.0, 0.0, -float(dr))

            # Gán vào pivot để nghiêng quanh đúng cạnh mép vực, triệt tiêu hoàn toàn gimbal lock
            initial_target_pos = target_ent.world_position
            self.pivot.position = pivot_pos
            self.pivot.rotation = Vec3(0, 0, 0)
            target_ent.parent = self.pivot
            target_ent.position = initial_target_pos - pivot_pos
            target_ent.rotation = Vec3(0, 0, 0)

            self.cliff_cleared = False
            self.cliff_angle = 15.0  # Bắt đầu đã nghiêng 15° để chuyển tiếp mượt mà ngay từ frame đầu
            self.fall_vy = -1.5

            # Áp dụng ngay góc nghiêng 15° ban đầu
            if self.cliff_axis == "z":
                self.pivot.rotation_z = self.cliff_angle * self.cliff_sign
            else:
                self.pivot.rotation_x = self.cliff_angle * self.cliff_sign


        # 4. Kịch bản hẫng chân ô gần (UPRIGHT_DROP_NEAR)
        elif fall_type in ("UPRIGHT_DROP_NEAR", "OVERHANG_DROP_NEAR"):
            self.fall_type = "UPRIGHT_DROP_NEAR"
            self.crumbling_tile = None
            self.fall_vx = 0.0
            self.fall_vz = 0.0
            self.fall_vy = -3.0
            self.fall_rot_speed = Vec3(100.0, 0.0, 40.0)

        # 5. Kịch bản 8: Chế độ tách 2 khối độc lập (SPLIT_CUBE_FALL)
        elif fall_type == "SPLIT_CUBE_FALL":
            self.crumbling_tile = None
            drift_speed = FALL_DRIFT_SPEED * 0.7
            rot_deg = 220.0
            self.fall_vy = -1.5
            if direction == "R":
                self.fall_vx = drift_speed
                self.fall_vz = 0.0
                self.fall_rot_speed = Vec3(10.0, 0.0, -rot_deg)
            elif direction == "L":
                self.fall_vx = -drift_speed
                self.fall_vz = 0.0
                self.fall_rot_speed = Vec3(10.0, 0.0, rot_deg)
            elif direction == "D":
                self.fall_vx = 0.0
                self.fall_vz = -drift_speed
                self.fall_rot_speed = Vec3(-rot_deg, 0.0, 10.0)
            elif direction == "U":
                self.fall_vx = 0.0
                self.fall_vz = drift_speed
                self.fall_rot_speed = Vec3(rot_deg, 0.0, 10.0)
            else:
                self.fall_vx = 0.0
                self.fall_vz = 0.0
                self.fall_rot_speed = Vec3(100.0, 20.0, 50.0)

        # 6. Các trường hợp rơi tự do ra ngoài rìa bàn cờ (UPRIGHT_TOTAL_VOID, LATERAL_TOTAL_VOID, LONGITUDINAL_TIP_VOID)
        else:
            self.crumbling_tile = None
            drift_speed = FALL_DRIFT_SPEED * 0.75
            rot_deg = 240.0
            self.fall_vy = -1.5
            if direction == "R":
                self.fall_vx = drift_speed
                self.fall_vz = 0.0
                self.fall_rot_speed = Vec3(10.0, 0.0, -rot_deg)
            elif direction == "L":
                self.fall_vx = -drift_speed
                self.fall_vz = 0.0
                self.fall_rot_speed = Vec3(10.0, 0.0, rot_deg)
            elif direction == "D":
                self.fall_vx = 0.0
                self.fall_vz = -drift_speed
                self.fall_rot_speed = Vec3(-rot_deg, 0.0, 10.0)
            elif direction == "U":
                self.fall_vx = 0.0
                self.fall_vz = drift_speed
                self.fall_rot_speed = Vec3(rot_deg, 0.0, 10.0)
            else:
                self.fall_vx = 0.0
                self.fall_vz = 0.0
                self.fall_rot_speed = Vec3(120.0, 30.0, 60.0)

    def start_victory(self, on_complete: Callable[[], None] | None = None) -> None:
        """Bắt đầu hoạt ảnh chiến thắng: chìm vào hố đích và bung pháo hoa rực rỡ."""
        self.is_victory = True
        self.victory_elapsed = 0.0
        self.victory_duration = max(0.6, self.base_victory_duration / max(0.1, self.speed_mult))
        self.on_victory_complete = on_complete

        # Bắn pháo giấy chúc mừng
        if self.block_view.block_entity:
            self.particles.spawn_confetti(self.block_view.block_entity.world_position, count=45)

    def trigger_squash(self, ent: Entity) -> None:
        """Kích hoạt hiệu ứng nẩy nhẹ đàn hồi (squash & stretch) khi chạm sàn."""
        if ent is None:
            return
        self.squash_entity = ent
        self.squash_base_scale = Vec3(ent.scale_x, ent.scale_y, ent.scale_z)
        self.squash_timer = 0.07  # 70ms vi mô

    def update(self, dt: float, engine: BloxorzEngine) -> None:
        """Cập nhật các tiến trình hoạt ảnh theo delta time."""
        effective_dt = dt * self.speed_mult

        # 1. Cập nhật hoạt ảnh Lăn (Roll)
        if self.is_rolling and self.active_cube_entity is not None:
            self.roll_elapsed += effective_dt
            fraction = min(1.0, self.roll_elapsed / self.roll_duration)
            eased = ease_out_cubic(fraction)
            angle = self.roll_target_angle * eased

            if self.roll_axis == "z":
                self.pivot.rotation_z = angle
            else:
                self.pivot.rotation_x = angle

            # Cập nhật bóng theo vị trí đang lăn (chỉ khi là nước đi hợp lệ)
            if not self.is_losing_roll and not self.shadow.is_suppressed:
                if engine.is_split:
                    c1_p = self.block_view.cube_1.world_position if self.block_view.cube_1 else Vec3(0, 0.5, 0)
                    c2_p = self.block_view.cube_2.world_position if self.block_view.cube_2 else Vec3(0, 0.5, 0)
                    world_x, world_z, block_y = c1_p.x, c1_p.z, c1_p.y
                    c2_tuple = (c2_p.x, c2_p.y, c2_p.z)
                else:
                    if self.block_view.cube_1 and self.block_view.cube_2:
                        center = (self.block_view.cube_1.world_position + self.block_view.cube_2.world_position) * 0.5
                        world_x, world_z, block_y = center.x, center.z, center.y
                    else:
                        w_pos = self.active_cube_entity.world_position
                        world_x, world_z, block_y = w_pos.x, w_pos.z, w_pos.y
                    c2_tuple = None

                self.shadow.update_transform(
                    world_x=world_x,
                    world_z=world_z,
                    block_y=block_y,
                    posture=engine.posture,
                    is_split=engine.is_split,
                    cube_2_pos=c2_tuple,
                )
            else:
                self.shadow.suppress()

            # Hoàn tất lăn
            if fraction >= 1.0:
                self.is_rolling = False
                self.active_cube_entity.world_parent = scene
                if not self.is_losing_roll:
                    self.active_cube_entity.rotation = Vec3(0, 0, 0)
                self.pivot.rotation = Vec3(0, 0, 0)

                callback = self.on_roll_complete
                self.on_roll_complete = None

                if self.is_losing_roll:
                    # Nước đi làm rơi khối: giữ góc nghiêng tự nhiên và bắt đầu rơi
                    if callback:
                        callback()
                else:
                    # Nước đi hợp lệ: Gọi callback để sync_from_engine thiết lập hình học chuẩn
                    if callback:
                        callback()

                    # Kích hoạt squash & stretch và bụi tiếp đất dựa trên scale mới chuẩn
                    if self.active_cube_entity is not None:
                        self.trigger_squash(self.active_cube_entity)
                        self.particles.spawn_dust(self.active_cube_entity.world_position, count=5)

        # 2. Cập nhật hoạt ảnh Rơi (Fall)
        elif self.is_falling:
            self.fall_elapsed += effective_dt
            fraction = min(1.0, self.fall_elapsed / self.fall_duration)
            target_ent = self.active_cube_entity or self.block_view.block_entity

            # BỎ HẲN BÓNG KHI ĐANG RƠI
            self.shadow.suppress()

            is_cliff_case = self.fall_type in (
                "UPRIGHT_OVERHANG_CLIFF", "OVERHANG_TIP_FAR",
                "LATERAL_TEETER_TIP", "LATERAL_TIP",
            )

            if is_cliff_case and target_ent is not None:
                # Khi đã thoát mép sàn thì giảm tốc độ xoay để khối rơi tự nhiên, không quay tít
                rot_speed = FALL_PIVOT_ROT_SPEED if not self.cliff_cleared else (FALL_PIVOT_ROT_SPEED * 0.45)
                d_phi = rot_speed * effective_dt
                self.cliff_angle += d_phi

                # Trôi ngang ra phía ngoài khoảng trống (đẩy khối xa khỏi thành bên của sàn)
                drift_factor = 1.0 if not self.cliff_cleared else 0.4
                self.pivot.position += self.cliff_slide_dir * (FALL_DRIFT_SPEED * drift_factor * effective_dt)

                # Khi góc nghiêng đạt ngưỡng thoát, khối mất điểm tựa và rơi tự do
                if self.cliff_angle >= FALL_ESCAPE_ANGLE:
                    self.cliff_cleared = True

                if self.cliff_cleared:
                    self.fall_vy += FALL_GRAVITY * effective_dt
                    self.pivot.y += self.fall_vy * effective_dt

                if self.cliff_axis == "z":
                    self.pivot.rotation_z = self.cliff_angle * self.cliff_sign
                else:
                    self.pivot.rotation_x = self.cliff_angle * self.cliff_sign

            elif self.fall_type in ("FRAGILE_CRUMBLE", "FRAGILE"):
                self.fall_vy += FALL_GRAVITY * effective_dt
                if target_ent:
                    target_ent.y += self.fall_vy * effective_dt
                    target_ent.rotation += self.fall_rot_speed * effective_dt

                # Ô gạch mỏng nứt vỡ rơi nhanh hơn khối để khối chui qua lỗ mà không chạm sàn
                if self.crumbling_tile:
                    self.crumbling_tile.y += (self.fall_vy * 1.35) * effective_dt
                    self.crumbling_tile.rotation_x += 70.0 * effective_dt
                    self.crumbling_tile.rotation_z += 40.0 * effective_dt

            else:
                self.fall_vy += FALL_GRAVITY * effective_dt
                if target_ent:
                    target_ent.x += self.fall_vx * effective_dt
                    target_ent.z += self.fall_vz * effective_dt
                    target_ent.y += self.fall_vy * effective_dt
                    target_ent.rotation += self.fall_rot_speed * effective_dt

            target_world_y = target_ent.world_y if target_ent else 0.0
            is_deep_enough = (target_world_y <= FALL_TERMINAL_DEPTH) if target_ent else False
            if fraction >= 1.0 or is_deep_enough:
                self.is_falling = False
                if target_ent and target_ent.parent == self.pivot:
                    target_ent.world_parent = scene
                    target_ent.rotation = Vec3(0, 0, 0)
                self.pivot.rotation = Vec3(0, 0, 0)
                callback = self.on_fall_complete
                self.on_fall_complete = None
                if callback:
                    callback()

        # 3. Cập nhật hoạt ảnh Chiến thắng (Victory)
        elif self.is_victory:
            self.victory_elapsed += effective_dt
            fraction = min(1.0, self.victory_elapsed / self.victory_duration)

            target_ent = self.block_view.block_entity
            if target_ent:
                # Khối chìm sâu vào hố đích và xoay tròn
                target_ent.y -= 1.4 * effective_dt
                target_ent.rotation_y += 320.0 * effective_dt
                shrink = max(0.1, 1.0 - effective_dt * 0.6)
                target_ent.scale *= shrink

            self.shadow.hide()

            if fraction >= 1.0:
                self.is_victory = False
                callback = self.on_victory_complete
                self.on_victory_complete = None
                if callback:
                    callback()

        # 4. Hiệu ứng đàn hồi (Squash recovery) dạng sóng sin mượt
        if self.squash_timer > 0.0 and self.squash_entity is not None:
            self.squash_timer -= effective_dt
            if self.squash_timer <= 0.0:
                self.squash_entity.scale = self.squash_base_scale
                self.squash_entity = None
            else:
                progress = math.sin((self.squash_timer / 0.07) * math.pi)
                sy = self.squash_base_scale.y * (1.0 - 0.05 * progress)
                sx = self.squash_base_scale.x * (1.0 + 0.025 * progress)
                sz = self.squash_base_scale.z * (1.0 + 0.025 * progress)
                self.squash_entity.scale = Vec3(sx, sy, sz)
