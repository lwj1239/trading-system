from __future__ import annotations

from datetime import date, datetime, timedelta
import json
from pathlib import Path
from typing import Any
from decimal import Decimal

from core.precision import format_8, q8


RISK_BY_LEVEL = {
    0: Decimal("0.02"),
    1: Decimal("0.015"),
    2: Decimal("0.01"),
    3: Decimal("0.005"),
    4: Decimal("0"),
}

DRAWDOWN_THRESHOLDS = {
    1: Decimal("0.03"),
    2: Decimal("0.05"),
    3: Decimal("0.08"),
    4: Decimal("0.12"),
}


def load_risk_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "level": 0,
            "last_drawdown": Decimal("0"),
            "stop_until": None,
            "post_level4_to_level2": False,
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        level = int(data.get("level", 0))
        last_drawdown = q8(data.get("last_drawdown", "0"))
        stop_until_raw = data.get("stop_until")
        stop_until = str(stop_until_raw) if stop_until_raw else None
        post_level4_to_level2 = bool(data.get("post_level4_to_level2", False))
        return {
            "level": max(0, min(4, level)),
            "last_drawdown": max(Decimal("0"), last_drawdown),
            "stop_until": stop_until,
            "post_level4_to_level2": post_level4_to_level2,
        }
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        return {
            "level": 0,
            "last_drawdown": Decimal("0"),
            "stop_until": None,
            "post_level4_to_level2": False,
        }


def save_risk_state(path: Path, state: dict[str, Any]) -> None:
    stop_until = state.get("stop_until")
    last_drawdown = q8(state.get("last_drawdown", "0"))
    payload = {
        "level": int(state.get("level", 0)),
        "last_drawdown": format_8(last_drawdown),
        "stop_until": str(stop_until) if stop_until else None,
        "post_level4_to_level2": bool(state.get("post_level4_to_level2", False)),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None


def level_from_drawdown(drawdown: Decimal) -> int:
    if drawdown <= Decimal("0"):
        return 0
    for level in sorted(DRAWDOWN_THRESHOLDS.keys(), reverse=True):
        if drawdown >= DRAWDOWN_THRESHOLDS[level]:
            return level
    return 0


def evaluate_risk(
    metrics: dict[str, Any],
    state: dict[str, Any] | None = None,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    actions: list[str] = []
    current_drawdown = q8(metrics.get("current_drawdown", "0"))
    current_date = _parse_date(as_of_date)
    trigger_level = level_from_drawdown(current_drawdown)

    prev_level = int((state or {}).get("level", 0))
    prev_level = max(0, min(4, prev_level))
    last_drawdown = q8((state or {}).get("last_drawdown", current_drawdown))
    last_drawdown = max(Decimal("0"), last_drawdown)
    stop_until = _parse_date((state or {}).get("stop_until"))
    post_level4_to_level2 = bool((state or {}).get("post_level4_to_level2", False))

    level = max(trigger_level, prev_level)

    if trigger_level == 4 and current_date is not None:
        stop_until = current_date + timedelta(days=1)
        post_level4_to_level2 = True

    if stop_until is not None and current_date is not None and current_date <= stop_until:
        actions.append("触发Level 4后进入2天停交易窗口")
        return {
            "base_risk": RISK_BY_LEVEL[0],
            "level": 4,
            "current_risk": RISK_BY_LEVEL[4],
            "actions": actions,
            "status": "stopped",
            "state": {
                "level": 4,
                "last_drawdown": current_drawdown,
                "stop_until": stop_until.isoformat(),
                "post_level4_to_level2": post_level4_to_level2,
            },
        }

    just_released_from_stop = False
    if (
        stop_until is not None
        and current_date is not None
        and current_date > stop_until
        and post_level4_to_level2
    ):
        level = max(trigger_level, 2)
        post_level4_to_level2 = False
        stop_until = None
        just_released_from_stop = True
        actions.append("Level 4停牌2天结束，风险恢复到Level 2")

    if not just_released_from_stop and current_drawdown == 0 and last_drawdown > 0:
        level = 0
        actions.append("创新高，风险等级恢复为Level 0")
    elif not just_released_from_stop:
        if last_drawdown > 0 and current_drawdown <= q8(last_drawdown * Decimal("0.5")):
            recovered = max(trigger_level, level - 1)
            actions.append("回撤较上次恢复50%，风险等级降一级")
            if recovered < level:
                actions.append(f"风险等级从Level {level} 调整为Level {recovered}")
            level = recovered

    if current_drawdown >= DRAWDOWN_THRESHOLDS[4]:
        actions.append("回撤达到12%，触发Level 4")
    elif current_drawdown >= DRAWDOWN_THRESHOLDS[3]:
        actions.append("回撤达到8%，触发Level 3")
    elif current_drawdown >= DRAWDOWN_THRESHOLDS[2]:
        actions.append("回撤达到5%，触发Level 2")
    elif current_drawdown >= DRAWDOWN_THRESHOLDS[1]:
        actions.append("回撤达到3%，触发Level 1")

    return {
        "base_risk": RISK_BY_LEVEL[0],
        "level": level,
        "current_risk": RISK_BY_LEVEL[level],
        "actions": actions,
        "status": "stopped" if level == 4 else "active",
        "state": {
            "level": level,
            "last_drawdown": current_drawdown,
            "stop_until": stop_until.isoformat() if stop_until else None,
            "post_level4_to_level2": post_level4_to_level2,
        },
    }
