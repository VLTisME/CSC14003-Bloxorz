"""Hệ thống hiệu ứng hạt (Particles System) sử dụng Object Pooling cho Bloxorz Ursina UI.

Tính năng:
- Bụi tiếp đất (Landing dust puffs) khi khối gỗ đập xuống sàn sau mỗi cú lăn
- Pháo giấy chiến thắng (Victory confetti) bung nở rực rỡ khi hoàn thành màn chơi
- Tái sử dụng đối tượng (Object Pooling), không cấp phát hay hủy Entity trong vòng lặp game,
  đảm bảo duy trì ổn định 60 FPS.
"""
from __future__ import annotations

import random
from ursina import Entity, Vec3, color, destroy


class ParticlePool:
    """Quản lý các hạt hiệu ứng bằng kỹ thuật pool để tối ưu hiệu năng."""

    def __init__(self, capacity: int = 60) -> None:
        self.capacity = capacity
        self.pool: list[Entity] = []
        self.velocities: list[Vec3] = []
        self.lifetimes: list[float] = []
        self.max_lifetimes: list[float] = []
        self.rot_speeds: list[Vec3] = []

        self.root = Entity(name="particles_root")

        # Tạo sẵn toàn bộ Entity trong pool
        colors = [
            color.hex("#FFD700"), color.hex("#E74C3C"), color.hex("#3498DB"),
            color.hex("#2ECC71"), color.hex("#9B59B6"), color.hex("#F39C12")
        ]
        for i in range(capacity):
            ent = Entity(
                parent=self.root,
                model="quad",
                scale=0.12,
                color=random.choice(colors),
                enabled=False,
                double_sided=True,
            )
            self.pool.append(ent)
            self.velocities.append(Vec3(0, 0, 0))
            self.lifetimes.append(0.0)
            self.max_lifetimes.append(1.0)
            self.rot_speeds.append(Vec3(0, 0, 0))

    def destroy_all(self) -> None:
        """Hủy pool khi thoát game."""
        if self.root:
            destroy(self.root)
            self.root = None
        self.pool.clear()

    def spawn_dust(self, pos: Vec3, count: int = 6) -> None:
        """Tạo chùm bụi nhỏ màu trắng kem khi khối tiếp đất."""
        dust_color = color.rgba(0.94, 0.96, 0.90, 0.78)
        spawned = 0
        for i, ent in enumerate(self.pool):
            if not ent.enabled:
                ent.enabled = True
                ent.position = pos + Vec3(random.uniform(-0.25, 0.25), 0.05, random.uniform(-0.25, 0.25))
                ent.scale = random.uniform(0.08, 0.14)
                ent.color = dust_color

                vx = random.uniform(-1.2, 1.2)
                vz = random.uniform(-1.2, 1.2)
                vy = random.uniform(0.4, 1.1)
                self.velocities[i] = Vec3(vx, vy, vz)

                lifetime = random.uniform(0.2, 0.4)
                self.lifetimes[i] = lifetime
                self.max_lifetimes[i] = lifetime
                self.rot_speeds[i] = Vec3(random.uniform(-90, 90), random.uniform(-90, 90), 0)

                spawned += 1
                if spawned >= count:
                    break

    def spawn_confetti(self, pos: Vec3, count: int = 35) -> None:
        """Bung pháo giấy rực rỡ khi chiến thắng."""
        confetti_colors = [
            color.hex("#FFD700"), color.hex("#FF5722"), color.hex("#4CAF50"),
            color.hex("#00BCD4"), color.hex("#E91E63"), color.hex("#9C27B0")
        ]
        spawned = 0
        for i, ent in enumerate(self.pool):
            if not ent.enabled:
                ent.enabled = True
                ent.position = pos + Vec3(random.uniform(-0.3, 0.3), random.uniform(0.2, 0.6), random.uniform(-0.3, 0.3))
                ent.scale = Vec3(random.uniform(0.08, 0.16), random.uniform(0.08, 0.16), 1)
                ent.color = random.choice(confetti_colors)

                vx = random.uniform(-2.5, 2.5)
                vz = random.uniform(-2.5, 2.5)
                vy = random.uniform(3.5, 7.0)
                self.velocities[i] = Vec3(vx, vy, vz)

                lifetime = random.uniform(1.2, 2.0)
                self.lifetimes[i] = lifetime
                self.max_lifetimes[i] = lifetime
                self.rot_speeds[i] = Vec3(random.uniform(-360, 360), random.uniform(-360, 360), random.uniform(-360, 360))

                spawned += 1
                if spawned >= count:
                    break

    def update(self, dt: float) -> None:
        """Cập nhật tọa độ, trọng lực và độ mờ của toàn bộ các hạt đang hoạt động."""
        gravity = -9.8
        for i, ent in enumerate(self.pool):
            if ent.enabled:
                self.lifetimes[i] -= dt
                if self.lifetimes[i] <= 0:
                    ent.enabled = False
                    continue

                # Cập nhật vị trí
                self.velocities[i].y += gravity * dt
                ent.position += self.velocities[i] * dt

                # Xoay hạt
                ent.rotation += self.rot_speeds[i] * dt

                # Giảm độ mờ (fade out)
                alpha_pct = max(0.0, min(1.0, self.lifetimes[i] / self.max_lifetimes[i]))
                ent.alpha = alpha_pct
