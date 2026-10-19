"""Quản lý danh mục màn chơi Bloxorz và lưu trữ tiến độ người chơi.

Đọc dữ liệu từ testcases/manifest.json và lưu tiến độ thắng vào game/progress.json.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT_DIR / "testcases" / "manifest.json"
PROGRESS_PATH = Path(__file__).resolve().parent / "progress.json"


class StageCatalog:
    """Quản lý thông tin 39 màn chơi và tiến độ hoàn thành."""

    def __init__(self) -> None:
        self.original_stages: list[dict] = []
        self.sample_stages: list[dict] = []
        self.all_stages: list[dict] = []
        self.stage_by_id: dict[str, dict] = {}
        self.progress: dict[str, dict] = {}

        self._load_manifest()
        self._load_progress()

    def _load_manifest(self) -> None:
        """Đọc danh mục màn chơi chuẩn từ testcases/manifest.json."""
        if not MANIFEST_PATH.exists():
            return

        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        for item in data.get("testcases", []):
            st_id = item["id"]
            in_file = ROOT_DIR / "testcases" / item["input"]
            out_file = ROOT_DIR / "testcases" / item["output"]

            meta = {
                "id": st_id,
                "input_path": in_file,
                "output_path": out_file,
                "reference_length": item.get("reference_length"),
                "passcode": item.get("passcode"),
                "rows": item.get("rows"),
                "columns": item.get("columns"),
                "features": item.get("features", {}),
                "is_sample": "samples" in item["input"],
            }
            self.stage_by_id[st_id] = meta
            self.all_stages.append(meta)

            if meta["is_sample"]:
                self.sample_stages.append(meta)
            else:
                self.original_stages.append(meta)

    def _load_progress(self) -> None:
        """Đọc file tiến độ đã thắng game/progress.json."""
        if PROGRESS_PATH.exists():
            try:
                data = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
                self.progress = data.get("won_stages", {})
            except Exception:
                self.progress = {}
        else:
            self.progress = {}

    def save_progress(self) -> None:
        """Lưu tiến độ ra file game/progress.json."""
        try:
            PROGRESS_PATH.write_text(
                json.dumps({"won_stages": self.progress}, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            pass

    def record_win(self, stage_id: str, moves: int) -> bool:
        """Ghi nhận chiến thắng một màn chơi và lưu số bước ít nhất.

        Trả về True nếu đây là lần đầu thắng hoặc phá kỷ lục số bước cũ.
        """
        is_new_record = False
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if stage_id not in self.progress:
            self.progress[stage_id] = {
                "best_moves": moves,
                "first_won": now_str,
                "last_won": now_str,
            }
            is_new_record = True
        else:
            rec = self.progress[stage_id]
            rec["last_won"] = now_str
            if moves < rec["best_moves"]:
                rec["best_moves"] = moves
                is_new_record = True

        self.save_progress()
        return is_new_record

    def is_won(self, stage_id: str) -> bool:
        return stage_id in self.progress

    def get_best_moves(self, stage_id: str) -> int | None:
        if stage_id in self.progress:
            return self.progress[stage_id].get("best_moves")
        return None

    def get_meta(self, stage_id: str) -> dict | None:
        return self.stage_by_id.get(stage_id)

    def get_next_stage_id(self, current_stage_id: str) -> str | None:
        """Tìm ID của màn chơi tiếp theo trong danh mục."""
        for i, st in enumerate(self.all_stages):
            if st["id"] == current_stage_id and i + 1 < len(self.all_stages):
                return self.all_stages[i + 1]["id"]
        return None

    @property
    def won_count(self) -> int:
        return len(self.progress)

    @property
    def total_count(self) -> int:
        return len(self.all_stages)

