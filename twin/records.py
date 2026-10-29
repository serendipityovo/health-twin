"""
病历与健康报告存储：本地 JSON 文件，可被 RAG 知识库索引。
"""
import json
import uuid
from datetime import datetime
from typing import List, Optional

import config


def _save_item(directory, item: dict) -> None:
    path = directory / f"{item['id']}.json"
    path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")


def _list_items(directory) -> List[dict]:
    items: List[dict] = []
    if not directory.exists():
        return items
    for f in sorted(directory.glob("*.json")):
        try:
            items.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    items.sort(key=lambda x: x.get("time", ""), reverse=True)
    return items


def _delete_item(directory, item_id: str) -> bool:
    path = directory / f"{item_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


# ------------------------- 病历 -------------------------

def save_record(content: str, title: str = "", source: str = "ai_interview") -> dict:
    rec = {
        "id": uuid.uuid4().hex[:12],
        "title": title or f"门诊病历 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": content,
        "source": source,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _save_item(config.RECORDS_DIR, rec)
    return rec


def list_records() -> List[dict]:
    return _list_items(config.RECORDS_DIR)


def delete_record(record_id: str) -> bool:
    return _delete_item(config.RECORDS_DIR, record_id)


# ------------------------- 检查报告 -------------------------

def save_report(filename: str, content: str, analysis: str = "") -> dict:
    rep = {
        "id": uuid.uuid4().hex[:12],
        "title": filename,
        "content": content,
        "analysis": analysis,
        "source": "upload",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _save_item(config.REPORTS_DIR, rep)
    return rep


def list_reports() -> List[dict]:
    return _list_items(config.REPORTS_DIR)


def delete_report(report_id: str) -> bool:
    return _delete_item(config.REPORTS_DIR, report_id)
