#!/usr/bin/env python3
"""Điểm khởi chạy chính cho trò chơi Bloxorz (GUI 3D Isometric Ursina & 2D Terminal).

Cách sử dụng:
    python play.py                         # GUI 3D Ursina, mở menu chọn màn
    python play.py --stage 01              # Mở thẳng màn 01
    python play.py --suite samples --stage 04
    python play.py --stage 01 --replay testcases/original/01.out.json
    python play.py --stage 01 --terminal   # Chế độ Terminal 2D
    python play.py --stage 01 --terminal --replay testcases/original/01.out.json --delay 0.2
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Panda3D receives special keys incorrectly when a Linux input method is active.
# Allow opting out for users who need the input method while running the game.
if sys.platform.startswith("linux") and not os.environ.get("BLOXORZ_KEEP_IM"):
    if "ursina" in sys.modules or "panda3d" in sys.modules:
        print("[WARN] IME fix must be applied before importing ursina/panda3d")
    os.environ["XMODIFIERS"] = "@im=none"

from game.visualize_2d import play_interactive, replay_solution


def resolve_stage_path(stage_arg: str | None, suite: str = "original") -> Path:
    """Xác định đường dẫn file .in.json từ tham số truyền vào."""
    testcases_dir = ROOT_DIR / "testcases"

    if not stage_arg:
        # Mặc định mở màn 01 của bộ được chọn
        default_file = testcases_dir / suite / "01.in.json"
        if default_file.exists():
            return default_file
        # Nếu không có 01 thì lấy file đầu tiên tìm thấy
        found = sorted(testcases_dir.glob(f"{suite}/*.in.json"))
        if found:
            return found[0]
        raise FileNotFoundError(f"Không tìm thấy file màn chơi nào trong testcases/{suite}")

    # Nếu người dùng truyền đường dẫn file trực tiếp
    p = Path(stage_arg)
    if p.exists() and p.is_file():
        return p

    # Nếu người dùng truyền số màn (ví dụ "01", "1", "stage01", "sample04")
    num_str = stage_arg.lower().replace("stage", "").replace("sample", "").strip()
    try:
        num = int(num_str)
        formatted_name = f"{num:02d}.in.json"
    except ValueError:
        formatted_name = f"{stage_arg}.in.json"

    candidate = testcases_dir / suite / formatted_name
    if candidate.exists():
        return candidate

    # Thử tìm trong cả 2 thư mục samples và original
    for s in ("original", "samples"):
        c = testcases_dir / s / formatted_name
        if c.exists():
            return c

    raise FileNotFoundError(f"Không tìm thấy màn chơi tương ứng với '{stage_arg}'.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bloxorz Game Studio: GUI 3D Isometric & 2D Terminal Player",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--stage", "-s", type=str, default=None,
                        help="Tên hoặc số thứ tự màn chơi (ví dụ: 01, 15, sample04, hoặc đường dẫn file .in.json)")
    parser.add_argument("--suite", choices=["original", "samples"], default="original",
                        help="Bộ testcase cần chọn: 'original' (33 màn gốc, mặc định) hoặc 'samples' (6 màn mẫu)")
    parser.add_argument("--replay", "-r", type=str, default=None,
                        help="Đường dẫn đến file lời giải .out.json để phát lại tự động")
    parser.add_argument("--terminal", "-t", action="store_true",
                        help="Chạy ở chế độ dòng lệnh 2D Terminal thay vì mở cửa sổ GUI 3D")
    parser.add_argument("--delay", type=float, default=0.25,
                        help="Độ trễ giữa các bước khi phát lại trên Terminal (mặc định 0.25s)")
    parser.add_argument("--step", action="store_true",
                        help="Dừng chờ nhấn Enter qua từng bước khi phát lại trên Terminal")
    parser.add_argument("--debug", "-d", action="store_true",
                        help="Bật chế độ debug (in chi tiết phím bấm, watchdog an toàn và trạng thái engine)")

    args = parser.parse_args()

    try:
        stage_path = resolve_stage_path(args.stage, args.suite)
    except FileNotFoundError as exc:
        print(f"[LỖI] {exc}")
        sys.exit(1)

    replay_path = Path(args.replay) if args.replay else None
    if replay_path and not replay_path.exists():
        print(f"[LỖI] Không tìm thấy file lời giải: {replay_path}")
        sys.exit(1)

    # 1. Chạy chế độ Terminal 2D
    if args.terminal:
        stage_data = json.loads(stage_path.read_text(encoding="utf-8"))
        if replay_path:
            answer_data = json.loads(replay_path.read_text(encoding="utf-8"))
            replay_solution(stage_data, answer_data, delay=args.delay, step_by_step=args.step)
        else:
            play_interactive(stage_data)
        return

    # 2. Chạy chế độ GUI 3D Isometric với Ursina
    from game.ursina_ui.app import launch_ursina_gui
    start_in_menu = (args.stage is None and args.replay is None)
    launch_ursina_gui(
        stage_path=stage_path,
        replay_path=replay_path,
        start_in_menu=start_in_menu,
        debug=args.debug,
    )



if __name__ == "__main__":
    main()
