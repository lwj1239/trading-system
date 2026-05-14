from __future__ import annotations

from datetime import date, datetime, timedelta
import json
from pathlib import Path
from typing import Any


RISK_BY_LEVEL = {
    0: 0.02,
    1: 0.015,
    2: 0.01,
    3: 0.005,
    4: 0.0,
}


def load_risk_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "level": 0,
            "last_drawdown": 0.0,
            "stop_until": None,
            "post_level4_to_level2": False,
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        level = int(data.get("level", 0))
        last_drawdown = float(data.get("last_drawdown", 0.0))
        stop_until_raw = data.get("stop_until")
        stop_until = str(stop_until_raw) if stop_until_raw else None
        post_level4_to_level2 = bool(data.get("post_level4_to_level2", False))
        return {
            "level": max(0, min(4, level)),
            "last_drawdown": max(0.0, last_drawdown),
            "stop_until": stop_until,
            "post_level4_to_level2": post_level4_to_level2,
        }
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        return {
            "level": 0,
            "last_drawdown": 0.0,
            "stop_until": None,
            "post_level4_to_level2": False,
        }


def save_risk_state(path: Path, state: dict[str, Any]) -> None:
    stop_until = state.get("stop_until")
    payload = {
        "level": int(state.get("level", 0)),
        "last_drawdown": float(state.get("last_drawdown", 0.0)),
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


def _trigger_level_from_drawdown(drawdown: float) -> int:
    if drawdown >= 0.10:
        return 4
    if drawdown >= 0.08:
        return 3
    if drawdown >= 0.05:
        return 2
    if drawdown >= 0.03:
        return 1
    return 0


def _trigger_level_from_loss_streak(loss_streak: int) -> int:
    if loss_streak >= 7:
        return 4
    if loss_streak >= 5:
        return 3
    if loss_streak >= 3:
        return 2
    if loss_streak >= 2:
        return 1
    return 0


def evaluate_risk(
    metrics: dict[str, Any],
    state: dict[str, Any] | None = None,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    actions: list[str] = []
    current_drawdown = float(metrics.get("current_drawdown", 0.0))
    current_loss_streak = int(metrics.get("current_loss_streak", 0))
    current_effective_win_streak = int(metrics.get("current_effective_win_streak", 0))
    effective_win_threshold = float(metrics.get("effective_win_threshold", 0.01))
    current_date = _parse_date(as_of_date)

    trigger_level = max(
        _trigger_level_from_drawdown(current_drawdown),
        _trigger_level_from_loss_streak(current_loss_streak),
    )

    prev_level = int((state or {}).get("level", 0))
    prev_level = max(0, min(4, prev_level))
    last_drawdown = float((state or {}).get("last_drawdown", current_drawdown))
    last_drawdown = max(0.0, last_drawdown)
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

    if not just_released_from_stop and current_drawdown == 0.0 and last_drawdown > 0.0:
        level = 0
        actions.append("创新高，风险等级恢复为Level 0")
    elif not just_released_from_stop:
        recovery_steps = 0
        if current_effective_win_streak >= 2:
            recovery_steps += 1
            actions.append(f"连续2次有效盈利(>={effective_win_threshold:.0%})，风险等级降一级")
        if last_drawdown > 0 and current_drawdown <= last_drawdown * 0.5:
            recovery_steps += 1
            actions.append("回撤较上次恢复50%，风险等级降一级")

        if recovery_steps > 0:
            recovered = max(trigger_level, level - recovery_steps)
            if recovered < level:
                actions.append(f"风险等级从Level {level} 调整为Level {recovered}")
            level = recovered

    if current_loss_streak >= 7:
        actions.append("连亏7次，触发Level 4")
    elif current_loss_streak >= 5:
        actions.append("连亏5次，触发Level 3")
    elif current_loss_streak >= 3:
        actions.append("连亏3次，触发Level 2")
    elif current_loss_streak >= 2:
        actions.append("连亏2次，触发Level 1")

    if current_drawdown >= 0.10:
        actions.append("回撤达到10%，触发Level 4")
    elif current_drawdown >= 0.08:
        actions.append("回撤达到8%，触发Level 3")
    elif current_drawdown >= 0.05:
        actions.append("回撤达到5%，触发Level 2")
    elif current_drawdown >= 0.03:
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
