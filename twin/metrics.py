"""
健康指标时序数据：血压 / 血糖 / 心率 / 体重 / 睡眠等日常记录，
支撑数字孪生体的"实时同步"与趋势分析。
"""
import json
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

import config

# 指标定义：key -> (中文名, 单位, 正常参考范围)
METRIC_TYPES: Dict[str, tuple] = {
    "systolic": ("收缩压", "mmHg", "90-139"),
    "diastolic": ("舒张压", "mmHg", "60-89"),
    "heart_rate": ("心率", "次/分", "60-100"),
    "blood_glucose": ("空腹血糖", "mmol/L", "3.9-6.1"),
    "weight": ("体重", "kg", "BMI 18.5-23.9"),
    "sleep_hours": ("睡眠时长", "小时", "7-9"),
    "steps": ("步数", "步", "≥6000"),
}


class MetricStore:
    """指标本地 JSON 存储 + DataFrame / 摘要输出"""

    def __init__(self, path=None):
        self.path = path or config.METRICS_PATH

    def _load_raw(self) -> List[dict]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save_raw(self, rows: List[dict]) -> None:
        self.path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def add(self, metric: str, value: float, date: str = "", note: str = "") -> dict:
        if metric not in METRIC_TYPES:
            raise ValueError(f"未知指标: {metric}")
        rows = self._load_raw()
        row = {
            "metric": metric,
            "value": float(value),
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "note": note,
        }
        rows.append(row)
        rows.sort(key=lambda r: r["date"])
        self._save_raw(rows)
        return row

    def delete(self, index: int) -> None:
        rows = self._load_raw()
        if 0 <= index < len(rows):
            rows.pop(index)
            self._save_raw(rows)

    def dataframe(self) -> pd.DataFrame:
        rows = self._load_raw()
        if not rows:
            return pd.DataFrame(columns=["metric", "value", "date", "note"])
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date")

    def summary(self, recent_days: int = 90) -> str:
        """生成面向 LLM 的指标趋势摘要（数字孪生上下文的组成部分）。"""
        df = self.dataframe()
        if df.empty:
            return "（暂无指标记录）"
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=recent_days)
        df = df[df["date"] >= cutoff]
        if df.empty:
            df = self.dataframe().groupby("metric").tail(1).copy()
            df["date"] = pd.to_datetime(df["date"])

        lines = []
        for key, (cn, unit, ref) in METRIC_TYPES.items():
            sub = df[df["metric"] == key].sort_values("date")
            if sub.empty:
                continue
            latest = sub.iloc[-1]
            trend = ""
            if len(sub) >= 2:
                first, last = float(sub.iloc[0]["value"]), float(latest["value"])
                diff = last - first
                arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "→")
                trend = f"，趋势{arrow}（{len(sub)}次记录，首末差{diff:+.1f}）"
            note = f"，备注：{latest['note']}" if latest["note"] else ""
            lines.append(
                f"- {cn}：{latest['value']:.1f}{unit}（{latest['date'].strftime('%Y-%m-%d')}），参考范围{ref}{trend}{note}"
            )
        return "\n".join(lines) if lines else "（暂无指标记录）"
