"""原子写文件：先写临时文件再 os.replace，避免写入中断留下截断的 JSON。"""
import os
from pathlib import Path


def atomic_write(path, text: str) -> None:
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
