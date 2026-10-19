"""Cấu hình giao diện và bảng màu cho Bloxorz Studio.

Cung cấp các chủ đề màu sắc:
- "toy": Đồ chơi 3D tươi sáng (mặc định), lấy cảm hứng từ ảnh mẫu gốc Bloxorz.
- "dark": Tối hiện đại, độ tương phản cao.
- "light": Sáng trang nhã tối giản.
"""
from __future__ import annotations

from pathlib import Path

DEFAULT_THEME = "toy"

# Bán kính làm mờ Gaussian Blur cho ảnh nền (0 để giữ pixel art sắc nét)
BG_BLUR_RADIUS: int = 0

# Cấu hình Font chữ giao diện tiếng Việt hiện đại (Be Vietnam Pro)
FONT_DIR: Path = Path(__file__).resolve().parent / "assets" / "fonts"
UI_FONT: str = "BeVietnamPro.ttf"


def setup_ui_font() -> str:
    """Đăng ký thư mục font vào Panda3D model path và gán toàn cục qua Text.default_font."""
    from panda3d.core import getModelPath
    from ursina import Text, application

    if FONT_DIR.exists():
        _model_path = getModelPath()
        font_dir_str = str(FONT_DIR.resolve())
        if font_dir_str not in [str(p) for p in _model_path.directories]:
            _model_path.append_path(font_dir_str)
        if hasattr(application, "fonts_folder"):
            application.fonts_folder = FONT_DIR

    Text.default_font = UI_FONT
    return UI_FONT

# Bảng màu cho các Theme
THEMES: dict[str, dict] = {
    "toy": {
        "name": "Khối đá Công nghiệp (Dark Industrial Stone)",
        "bg_blur_radius": BG_BLUR_RADIUS,
        "bg_top": "#1E2638",          # Xanh tím than ngân hà (Cosmic Indigo)
        "bg_bottom": "#070A10",       # Đen vũ trụ sâu ở rìa
        "bg_glow": "#1E2638",         # Tâm phát sáng radial gradient
        "bg_outer": "#070A10",        # Màu nền ngoài cùng
        "bg": "#070A10",              # Màu nền fallback
        "panel_bg": "#1A2230",
        "panel_sub_bg": "#121824",
        "text_primary": "#E2E8F0",
        "text_secondary": "#94A3B8",
        "text_dim": "#64748B",
        "grid_outline": "#0D1117",
        # Ô sàn thông thường (Xám đá phiến & Xám than xen kẽ, có rãnh sâu)
        "regular": {
            "top": "#2D3748",         # Xám đá phiến (Slate Grey)
            "top_alt": "#222831",     # Xám than (Charcoal) xen kẽ
            "left": "#1A202C",
            "right": "#13171F",
            "outline": "#0D1117",
        },
        # Ô xuất phát
        "start": {
            "top": "#34495E",
            "left": "#243342",
            "right": "#1A2530",
            "outline": "#0D1117",
        },
        # Lỗ đích 3D lõm và ngôi sao vàng kim ấm áp
        "goal": {
            "top": "#0A0E17",
            "left": "#070A10",
            "right": "#05070B",
            "outline": "#000000",
            "star": "#E5A93B",        # Vàng kim ấm áp (giảm bão hòa)
            "star_border": "#A06D18",
            "glow": "#D48817",
        },
        # Ô cam nứt (Fragile) - Cam đất cháy / đá nứt sẫm
        "fragile": {
            "top": "#8D4424",         # Cam đất cháy (Burnt Terracotta)
            "left": "#683018",
            "right": "#4A200F",
            "outline": "#2D1207",
            "crack": "#150702",
        },
        # Ô cầu (Bridge) khi bật và tắt
        "bridge_active": {
            "top": "#3D5A80",         # Thép xám xanh công nghiệp
            "left": "#293E58",
            "right": "#1B2B3E",
            "outline": "#101B27",
        },
        "bridge_inactive": {
            "outline": "#1F2937",
            "top": "#111827",
            "fill": "",
        },
        # Công tắc tròn mềm (Soft switch - nút tròn đỏ ruby sẫm)
        "switch_soft": {
            "top": "#2D3748",
            "left": "#1A202C",
            "right": "#13171F",
            "outline": "#0D1117",
            "circle": "#C0392B",      # Đỏ ruby sẫm
            "circle_side": "#8E2519",
            "circle_highlight": "#D9534F",
        },
        # Công tắc chữ X cứng (Hard switch - chữ X đỏ thép sẫm)
        "switch_hard": {
            "top": "#2D3748",
            "left": "#1A202C",
            "right": "#13171F",
            "outline": "#0D1117",
            "cross": "#A93226",       # Đỏ thép sẫm
            "cross_side": "#782017",
            "cross_inner": "#E0E0E0",
        },
        # Ô phân tách (Splitter)
        "splitter": {
            "top": "#2D3748",
            "left": "#1A202C",
            "right": "#13171F",
            "outline": "#0D1117",
            "icon": "#A93226",
        },
        # Khối gỗ chính (Gỗ gụ sẫm/óc chó ấm, thớ ghép đặc không rỗng ruột)
        "block_main": {
            "top": "#8B5A2B",         # Nâu gỗ ấm (Dark Mahogany / Warm Walnut)
            "color": "#8B5A2B",       # Màu nhuộm khối
            "texture": "brick",       # Texture brick dạng thớ ghép gỗ vững chắc
            "transparent": False,     # Không trong suốt, không rỗng ruột
            "left": "#68401C",
            "right": "#4A2E14",
            "grain": "#2E1A0A",       # Vân gỗ đen sẫm
            "outline": "#1A0E05",
            "edge_highlight": "#B87333",
        },
        # Hai nửa khối khi bị phân tách (Gỗ Hổ Phách viền Ngọc Lục Bảo & Gỗ Anh Đào viền Lam Ngọc)
        "cube_1_active": {
            "top": "#D48C46", "accent": "#10B981", "bevel_hl": "#F6C176",
            "outline": "#065F46", "edge_highlight": "#34D399"
        },
        "cube_1_dim": {
            "top": "#A66B33", "accent": "#059669", "bevel_hl": "#D48C46",
            "outline": "#064E3B", "edge_highlight": "#10B981"
        },
        "cube_2_active": {
            "top": "#C85A32", "accent": "#38BDF8", "bevel_hl": "#E58F65",
            "outline": "#1E40AF", "edge_highlight": "#60A5FA"
        },
        "cube_2_dim": {
            "top": "#9E4324", "accent": "#2563EB", "bevel_hl": "#C85A32",
            "outline": "#1E3A8A", "edge_highlight": "#3B82F6"
        },
        # Bóng đổ
        "shadow": {
            "contact": "#030508",
            "ambient": "#0A0E17",
        },
        # La bàn và điều hướng
        "compass_bg": "#1A2230",
        "compass_border": "#334155",
        "compass_arrow": "#60A5FA",
        "compass_text": "#E2E8F0",
    },
    "dark": {
        "name": "Tối hiện đại (Dark)",
        "bg_top": "#0B1120",
        "bg_bottom": "#080D1A",
        "bg": "#0B1120",
        "panel_bg": "#1E293B",
        "panel_sub_bg": "#0F172A",
        "text_primary": "#F8FAFC",
        "text_secondary": "#94A3B8",
        "text_dim": "#64748B",
        "grid_outline": "#334155",
        "regular": {"top": "#CBD5E1", "left": "#94A3B8", "right": "#64748B", "outline": "#475569"},
        "start": {"top": "#6EE7B7", "left": "#10B981", "right": "#059669", "outline": "#047857"},
        "goal": {"top": "#1E1B4B", "left": "#312E81", "right": "#1E1B4B", "star": "#F59E0B", "glow": "#F59E0B", "outline": "#0F172A"},
        "fragile": {"top": "#FBBF24", "left": "#D97706", "right": "#B45309", "outline": "#78350F", "crack": "#78350F"},
        "bridge_active": {"top": "#60A5FA", "left": "#3B82F6", "right": "#1D4ED8", "outline": "#1E3A8A"},
        "bridge_inactive": {"outline": "#334155", "top": "#0F172A", "fill": ""},
        "switch_soft": {"top": "#E2E8F0", "left": "#94A3B8", "right": "#64748B", "circle": "#10B981", "circle_side": "#059669", "circle_highlight": "#6EE7B7", "outline": "#475569"},
        "switch_hard": {"top": "#E2E8F0", "left": "#94A3B8", "right": "#64748B", "cross": "#8B5CF6", "cross_side": "#6D28D9", "cross_inner": "#FFFFFF", "outline": "#475569"},
        "splitter": {"top": "#FEE2E2", "left": "#FCA5A5", "right": "#EF4444", "icon": "#DC2626", "outline": "#991B1B"},
        "block_main": {
            "top": "#FBBF24", "left": "#D97706", "right": "#B45309",
            "outline": "#78350F", "edge_highlight": "#FDE68A", "grain": "#D97706"
        },
        "cube_1_active": {"top": "#34D399", "left": "#059669", "right": "#047857", "outline": "#064E3B", "edge_highlight": "#A7F3D0"},
        "cube_1_dim": {"top": "#10B981", "left": "#047857", "right": "#064E3B", "outline": "#022C22", "edge_highlight": "#6EE7B7"},
        "cube_2_active": {"top": "#60A5FA", "left": "#2563EB", "right": "#1D4ED8", "outline": "#1E3A8A", "edge_highlight": "#BFDBFE"},
        "cube_2_dim": {"top": "#3B82F6", "left": "#1D4ED8", "right": "#1E3A8A", "outline": "#172554", "edge_highlight": "#93C5FD"},
        "shadow": {"contact": "#020617", "ambient": "#0B1120"},
        "compass_bg": "#1E293B",
        "compass_border": "#475569",
        "compass_arrow": "#38BDF8",
        "compass_text": "#F8FAFC",
    },
    "light": {
        "name": "Sáng trang nhã (Light)",
        "bg_top": "#F8FAFC",
        "bg_bottom": "#E2E8F0",
        "bg": "#F1F5F9",
        "panel_bg": "#E2E8F0",
        "panel_sub_bg": "#CBD5E1",
        "text_primary": "#0F172A",
        "text_secondary": "#475569",
        "text_dim": "#64748B",
        "grid_outline": "#94A3B8",
        "regular": {"top": "#FFFFFF", "left": "#CBD5E1", "right": "#94A3B8", "outline": "#64748B"},
        "start": {"top": "#A7F3D0", "left": "#34D399", "right": "#10B981", "outline": "#059669"},
        "goal": {"top": "#312E81", "left": "#1E1B4B", "right": "#312E81", "star": "#D97706", "glow": "#D97706", "outline": "#1E1B4B"},
        "fragile": {"top": "#FDE68A", "left": "#F59E0B", "right": "#D97706", "outline": "#B45309", "crack": "#92400E"},
        "bridge_active": {"top": "#BFDBFE", "left": "#60A5FA", "right": "#2563EB", "outline": "#1D4ED8"},
        "bridge_inactive": {"outline": "#94A3B8", "top": "#E2E8F0", "fill": ""},
        "switch_soft": {"top": "#F8FAFC", "left": "#CBD5E1", "right": "#94A3B8", "circle": "#059669", "circle_side": "#047857", "circle_highlight": "#34D399", "outline": "#64748B"},
        "switch_hard": {"top": "#F8FAFC", "left": "#CBD5E1", "right": "#94A3B8", "cross": "#7C3AED", "cross_side": "#6D28D9", "cross_inner": "#FFFFFF", "outline": "#64748B"},
        "splitter": {"top": "#FECACA", "left": "#F87171", "right": "#DC2626", "icon": "#B91C1C", "outline": "#991B1B"},
        "block_main": {
            "top": "#F59E0B", "left": "#D97706", "right": "#B45309",
            "outline": "#78350F", "edge_highlight": "#FEF3C7", "grain": "#D97706"
        },
        "cube_1_active": {"top": "#10B981", "left": "#059669", "right": "#047857", "outline": "#064E3B", "edge_highlight": "#D1FAE5"},
        "cube_1_dim": {"top": "#6EE7B7", "left": "#10B981", "right": "#059669", "outline": "#065F46", "edge_highlight": "#A7F3D0"},
        "cube_2_active": {"top": "#3B82F6", "left": "#2563EB", "right": "#1D4ED8", "outline": "#1E3A8A", "edge_highlight": "#DBEAFE"},
        "cube_2_dim": {"top": "#93C5FD", "left": "#60A5FA", "right": "#2563EB", "outline": "#1D4ED8", "edge_highlight": "#BFDBFE"},
        "shadow": {"contact": "#94A3B8", "ambient": "#CBD5E1"},
        "compass_bg": "#E2E8F0",
        "compass_border": "#94A3B8",
        "compass_arrow": "#0284C7",
        "compass_text": "#0F172A",
    }
}


def get_theme(name: str | None = None) -> dict:
    """Lấy cấu hình theme an toàn theo tên, mặc định trả về theme 'toy'."""
    if name and name in THEMES:
        return THEMES[name]
    return THEMES[DEFAULT_THEME]


# Cấu hình đồ họa & hiệu ứng Ursina 3D
URSINA_CONFIG = {
    # Camera
    "cam_yaw": 30.0,            # Góc xoay ngang quanh trục thẳng đứng (độ)
    "cam_pitch": 35.264,        # Góc nghiêng tiêu chuẩn isometric
    "cam_fov": 16.0,            # Kích thước khung nhìn orthographic
    "cam_ortho": True,          # True: Isometric chuẩn; False: Perspective
    # Bàn sàn & khối
    "floor_thickness": 0.35,    # Độ dày khối sàn 3D
    "tile_gap": 0.04,           # Khe hở rãnh giữa các ô sàn
    "block_scale": 0.98,        # Khối hơi thu nhỏ 2% để không cọ sát sàn
    # Hoạt ảnh
    "anim_speed": 1.0,          # Hệ số tốc độ hoạt ảnh
    "roll_duration": 0.16,      # Thời lượng lăn 1 bước (giây)
    "fall_duration": 0.85,      # Thời lượng rơi xuống vực (giây)
    "victory_duration": 1.3,    # Thời lượng hoạt ảnh chiến thắng (giây)
    # Hiệu ứng đồ họa (Toggles)
    "use_real_shadows": False,  # Shadow map Panda3D
    "use_blob_shadow": True,    # Bóng đổ giả dạng blob mềm (nhẹ & chuẩn)
    "use_squash_stretch": True, # Hiệu ứng nẩy đàn hồi vi mô khi tiếp đất
    "use_dust": True,           # Hạt bụi khi khối tiếp đất
    "use_confetti": True,       # Pháo giấy chúc mừng khi thắng
    "bg_blur_radius": BG_BLUR_RADIUS,  # Độ mờ Gaussian Blur cho ảnh nền DoF
    "quality": "high",          # "high" | "low"
}


def get_ursina_config() -> dict:
    """Trả về dict cấu hình hiển thị và animation cho Ursina."""
    return URSINA_CONFIG.copy()

