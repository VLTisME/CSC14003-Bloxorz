"""Trình hiển thị 2D trên Terminal cho Bloxorz.

Hỗ trợ:
1. Vẽ bàn cờ và khối hộp với màu sắc ANSI trực quan.
2. Chế độ chơi tương tác bằng bàn phím (WASD / phím mũi tên / lệnh).
3. Chế độ phát lại (Replay) từ file kết quả JSON với tốc độ tùy chỉnh.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Đảm bảo import được engine từ package game
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from game.engine import BloxorzEngine, GameStatus, Posture


# Mã màu ANSI
class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Màu chữ
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Màu nền
    BG_GRID = "\033[48;5;236m"
    BG_BLOCK = "\033[48;5;220m"
    BG_BLOCK_ACTIVE = "\033[48;5;82m"
    BG_GOAL = "\033[48;5;196m"


def clear_screen() -> None:
    """Xóa màn hình terminal."""
    os.system("cls" if os.name == "nt" else "clear")


class TerminalVisualizer:
    """Render bàn cờ Bloxorz trên giao diện dòng lệnh."""

    def __init__(self, engine: BloxorzEngine) -> None:
        self.engine = engine

    def render(self) -> str:
        """Tạo chuỗi ký tự hiển thị toàn bộ trạng thái hiện tại của ván chơi."""
        rows, cols = self.engine.dimensions
        block_cells = set(self.engine.block_cells)
        is_split = self.engine.is_split
        selected_cube = self.engine.selected_cube

        lines = []
        # Header thông tin
        status_color = Color.GREEN if self.engine.is_won else (Color.RED if self.engine.is_lost else Color.CYAN)
        lines.append(f"{Color.BOLD}=== BLOXORZ 2D TERMINAL ==={Color.RESET}")
        lines.append(
            f"Màn: {Color.YELLOW}{self.engine.stage_id}{Color.RESET} | "
            f"Bước đi: {Color.BOLD}{self.engine.move_count}{Color.RESET} | "
            f"Tư thế: {Color.MAGENTA}{self.engine.posture.value}{Color.RESET} | "
            f"Trạng thái: {status_color}{self.engine.status.value}{Color.RESET}"
        )
        if is_split:
            c1_hl = f"{Color.BOLD}{Color.GREEN}[Khối 1]{Color.RESET}" if selected_cube == 1 else "Khối 1"
            c2_hl = f"{Color.BOLD}{Color.GREEN}[Khối 2]{Color.RESET}" if selected_cube == 2 else "Khối 2"
            lines.append(f"Đang điều khiển: {c1_hl} | {c2_hl}  (Nhấn Tab hoặc Phím cách để đổi)")

        if self.engine.is_lost and self.engine.lost_reason:
            lines.append(f"{Color.RED}[THUA] Nguyên nhân: {self.engine.lost_reason}{Color.RESET}")
        elif self.engine.is_won:
            lines.append(f"{Color.GREEN}{Color.BOLD}★ CHIẾN THẮNG! Khối đã đứng thẳng trên ô Đích! ★{Color.RESET}")

        lines.append("")

        # Hiển thị số cột ở trên cùng
        col_header = "    " + "".join(f"{c % 10:2}" for c in range(cols))
        lines.append(f"{Color.DIM}{col_header}{Color.RESET}")

        # Render từng ô
        for r in range(rows):
            row_str = f"{Color.DIM}{r:2} |{Color.RESET}"
            for c in range(cols):
                p = (r, c)
                tile = self.engine.get_cell_type_at(r, c)

                # Kiểm tra khối có đang đứng ở ô này không
                if p in block_cells:
                    if is_split:
                        if self.engine.state and p == self.engine.state.first:
                            cube_num = "1"
                            is_active = (selected_cube == 1)
                        else:
                            cube_num = "2"
                            is_active = (selected_cube == 2)
                        bg = Color.BG_BLOCK_ACTIVE if is_active else Color.BG_BLOCK
                        row_str += f"{bg}{Color.BLACK}{Color.BOLD}{cube_num:^2}{Color.RESET}"
                    else:
                        row_str += f"{Color.BG_BLOCK}{Color.BLACK}{Color.BOLD}██{Color.RESET}"
                    continue

                # Vẽ ô sàn
                if tile == "#":
                    row_str += "  "  # Vực thẳm
                elif tile == ".":
                    row_str += f"{Color.DIM}· {Color.RESET}"  # Ô thường
                elif tile == "S":
                    row_str += f"{Color.CYAN}S {Color.RESET}"  # Xuất phát
                elif tile == "G":
                    row_str += f"{Color.BG_GOAL}{Color.WHITE}{Color.BOLD}G {Color.RESET}"  # Đích
                elif tile == "F":
                    row_str += f"{Color.YELLOW}▒▒{Color.RESET}"  # Ô dễ vỡ
                elif tile == "B":
                    # Tìm xem cầu này có active không
                    bridge_idx = self.engine.replay.bridge_cells.get(p, None) if self.engine.replay else None
                    if bridge_idx is not None and self.engine.is_bridge_active(bridge_idx):
                        row_str += f"{Color.BLUE}══{Color.RESET}"  # Cầu đang bật
                    else:
                        row_str += f"{Color.RED}{Color.DIM}··{Color.RESET}"  # Cầu đang tắt
                elif tile == "O":
                    row_str += f"{Color.GREEN}○ {Color.RESET}"  # Công tắc nhẹ
                elif tile == "X":
                    row_str += f"{Color.MAGENTA}✕ {Color.RESET}"  # Công tắc nặng
                elif tile == "T":
                    row_str += f"{Color.RED}▲ {Color.RESET}"  # Ô tách
                else:
                    row_str += f"{tile} "

            lines.append(row_str)

        lines.append("")
        lines.append(f"{Color.DIM}Chú thích: [██] Khối hộp | [G] Đích | [▒▒] Dễ vỡ (F) | [══] Cầu (B) | [○] Công tắc nhẹ | [✕] Công tắc nặng | [▲] Ô tách{Color.RESET}")
        return "\n".join(lines)


def play_interactive(stage_data: dict) -> None:
    """Vòng lặp chơi game tương tác trên terminal."""
    engine = BloxorzEngine(stage_data)
    visualizer = TerminalVisualizer(engine)

    # Bản đồ phím điều khiển
    key_map = {
        "w": "U", "a": "L", "s": "D", "d": "R",
        "u": "U", "l": "L", "r": "R",
        "8": "U", "4": "L", "2": "D", "6": "R",
    }

    try:
        while True:
            clear_screen()
            print(visualizer.render())

            if engine.is_won:
                print(f"\n{Color.GREEN}Chúc mừng bạn đã hoàn thành màn chơi trong {engine.move_count} bước!{Color.RESET}")
                input("Nhấn Enter để thoát...")
                break

            prompt = f"\nĐiều khiển [W/A/S/D]: Di chuyển | [Tab/Space]: Đổi khối | [Z]: Hoàn tác | [R]: Chơi lại | [Q]: Thoát\nNhập lệnh: "
            cmd = input(prompt).strip().lower()

            if not cmd:
                continue
            if cmd == "q":
                print("Đã thoát game.")
                break
            elif cmd == "r":
                engine.reset()
            elif cmd in ("z", "undo"):
                if not engine.undo():
                    print("Không thể hoàn tác thêm!")
                    time.sleep(0.5)
            elif cmd in ("tab", " ", "switch", "c"):
                engine.toggle_cube()
            elif cmd in key_map:
                action_dir = key_map[cmd]
                engine.step(action_dir)
            elif cmd.upper() in ("1U", "1D", "1L", "1R", "2U", "2D", "2L", "2R", "U", "D", "L", "R"):
                engine.step(cmd.upper())
            else:
                print(f"Lệnh không hợp lệ: {cmd}")
                time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nĐã thoát game.")


def replay_solution(stage_data: dict, answer_data: dict, delay: float = 0.25, step_by_step: bool = False) -> None:
    """Phát lại lời giải trên terminal."""
    engine = BloxorzEngine(stage_data)
    visualizer = TerminalVisualizer(engine)
    actions = answer_data.get("actions", [])

    clear_screen()
    print(visualizer.render())
    print(f"\nBắt đầu phát lại lời giải ({len(actions)} bước)...")
    time.sleep(0.8)

    for i, act in enumerate(actions, 1):
        success = engine.step(act)
        clear_screen()
        print(visualizer.render())
        print(f"\nBước {i}/{len(actions)}: Thực hiện hành động {Color.YELLOW}{Color.BOLD}{act}{Color.RESET}")

        if not success:
            print(f"{Color.RED}Phát lại thất bại tại bước {i}!{Color.RESET}")
            break

        if step_by_step:
            input("Nhấn [Enter] để sang bước tiếp theo (hoặc Ctrl+C để dừng)...")
        else:
            time.sleep(delay)

    if engine.is_won:
        print(f"\n{Color.GREEN}{Color.BOLD}Phát lại thành công trọn vẹn! Kết quả: AC.{Color.RESET}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bloxorz 2D Terminal Visualizer & Player")
    parser.add_argument("stage", type=str, help="Đường dẫn file .in.json của màn chơi")
    parser.add_argument("--replay", type=str, default=None, help="Đường dẫn file .out.json để phát lại lời giải")
    parser.add_argument("--delay", type=float, default=0.25, help="Độ trễ giữa các bước khi phát lại (giây)")
    parser.add_argument("--step", action="store_true", help="Chờ nhấn Enter qua từng bước khi phát lại")
    args = parser.parse_args()

    stage_path = Path(args.stage)
    if not stage_path.exists():
        print(f"Lỗi: Không tìm thấy file {stage_path}")
        sys.exit(1)

    stage_data = json.loads(stage_path.read_text(encoding="utf-8"))

    if args.replay:
        replay_path = Path(args.replay)
        if not replay_path.exists():
            print(f"Lỗi: Không tìm thấy file lời giải {replay_path}")
            sys.exit(1)
        answer_data = json.loads(replay_path.read_text(encoding="utf-8"))
        replay_solution(stage_data, answer_data, delay=args.delay, step_by_step=args.step)
    else:
        play_interactive(stage_data)


if __name__ == "__main__":
    main()
