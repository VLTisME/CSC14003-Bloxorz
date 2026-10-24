"""Chạy và so sánh BFS/A* trên các stage; xuất CSV/Markdown có thể tái lập."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import platform
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from checker import execute_and_check, read_json, resolve_manifest_testcases  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("original", "samples"), default="original")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--csv", type=Path, default=ROOT / "docs" / "astar-benchmark.csv")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs" / "astar-benchmark.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = resolve_manifest_testcases(args.suite)
    results = []
    for case in cases:
        stage = read_json(ROOT / "testcases" / case["input"])
        ref = case.get("reference_length")
        if ref is None:
            raise SystemExit(f"{case['id']}: no reference length; cannot establish optimality")
        row = {"test_id": case["id"], "reference_length": ref}
        for algorithm in ("BFS", "ASTAR"):
            result = execute_and_check(
                ROOT / "algorithms" / f"{algorithm}.py", stage,
                timeout=args.timeout, reference_length=ref, require_optimal=True,
            )
            if result["verdict"] != "AC":
                raise SystemExit(f"{algorithm} {case['id']}: {result['verdict']} - {result['message']}")
            if not result["metrics_complete"]:
                raise SystemExit(f"{algorithm} {case['id']}: incomplete metrics {result['metrics_errors']}")
            stats = result["statistics"]
            row[f"{algorithm.lower()}_steps"] = stats["solution_length"]
            row[f"{algorithm.lower()}_expanded"] = stats["expanded_nodes"]
            row[f"{algorithm.lower()}_generated"] = stats.get("generated_nodes")
            row[f"{algorithm.lower()}_search_ms"] = stats["search_time_ms"]
            row[f"{algorithm.lower()}_process_ms"] = stats["process_time_ms"]
            row[f"{algorithm.lower()}_peak_bytes"] = stats["peak_memory_bytes"]
            if algorithm == "ASTAR":
                row["astar_preprocess_ms"] = stats["heuristic_preprocessing_time_ms"]
                row["astar_core_search_ms"] = stats["astar_search_time_ms"]
                row["astar_relaxed_states"] = stats["relaxed_states"]
                row["astar_relaxed_edges"] = stats["relaxed_edges"]
        if row["bfs_steps"] != row["astar_steps"]:
            raise SystemExit(f"{case['id']}: BFS/A* path lengths differ")
        results.append(row)

    columns = list(results[0])
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)

    astar_total = [r["astar_search_ms"] for r in results]
    bfs_total = [r["bfs_search_ms"] for r in results]
    astar_expanded = [r["astar_expanded"] for r in results]
    bfs_expanded = [r["bfs_expanded"] for r in results]
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "# Benchmark BFS và A*",
        "",
        f"Ngày chạy: {now}  ",
        f"Môi trường: Python {platform.python_version()}, {platform.platform()}  ",
        f"Bộ testcase: `{args.suite}` ({len(results)} stage); một lượt đo cho mỗi thuật toán/stage.  ",
        "Checker xác nhận verdict và độ dài tối ưu theo số bước tham chiếu của fixture.",
        "",
        "`Thời gian tìm kiếm BFS (ms)` và `A* tổng thời gian tìm kiếm (ms)` được đo bên trong solver; tổng của A* bao gồm tiền xử lý heuristic. Hai cột `A* tiền xử lý` và `A* tìm kiếm chính` tách phần tổng để tiện phân tích; tổng hai phần có thể lệch nhẹ do ranh giới đo. Bộ nhớ đỉnh là cấp phát Python theo `tracemalloc`, không phải RSS của tiến trình. Process time bao gồm khởi động Python.",
        "",
        f"Tóm tắt: cả hai thuật toán AC {len(results)}/{len(results)} stage; mọi độ dài lời giải đều trùng nhau. Trung vị số nút mở rộng: BFS {statistics.median(bfs_expanded):.0f}, A* {statistics.median(astar_expanded):.0f}. Trung vị thời gian tìm kiếm được đo: BFS {statistics.median(bfs_total):.3f} ms, A* {statistics.median(astar_total):.3f} ms (đã gồm tiền xử lý). Thời gian một lượt chỉ mang tính mô tả, chưa đủ để kết luận tốc độ ổn định.",
        "",
        "| Stage | Số bước | BFS mở rộng | A* mở rộng | BFS tìm kiếm ms | A* tiền xử lý ms | A* tìm kiếm chính ms | A* tổng tìm kiếm ms | A* bộ nhớ đỉnh byte |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['test_id']} | {row['astar_steps']} | {row['bfs_expanded']} | {row['astar_expanded']} | "
            f"{row['bfs_search_ms']:.3f} | {row['astar_preprocess_ms']:.3f} | "
            f"{row['astar_core_search_ms']:.3f} | {row['astar_search_ms']:.3f} | {row['astar_peak_bytes']} |"
        )
    lines.extend([
        "",
        f"Dữ liệu thô từng stage: [`astar-benchmark.csv`]({args.csv.name}). Chạy lại bằng `python benchmark_search.py --suite {args.suite}`.",
        "",
    ])
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text("\n".join(lines), encoding="utf-8")
    print(f"Đã ghi {args.csv} và {args.markdown}; BFS và A* đều AC {len(results)}/{len(results)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
