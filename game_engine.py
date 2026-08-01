"""
MissYou 游戏引擎 — 统一调度框架
所有游戏走同一套注册→验证→加分流程
"""
from dataclasses import dataclass, field
from typing import Callable, Any

# ============================================================
# 游戏定义
# ============================================================

@dataclass
class GameDef:
    """所有游戏类型的统一接口定义"""
    game_id: str                              # 唯一标识，如 "memory_match"
    name: str                                 # 显示名称，如 "🃏 记忆翻牌"
    description: str                          # 一句话介绍
    score: int = 370                          # 答对得分（基准分，实际可被 calc_game_score 调整）
    render: Callable = field(default=lambda g: None)      # (game_def) -> None
    generate: Callable = field(default=lambda: {})         # () -> question_data
    validate: Callable = field(default=lambda q, a: False) # (question_data, answer) -> bool
    question_id: Callable = field(default=lambda q: "")    # (question_data) -> str

# ============================================================
# 游戏注册表
# ============================================================

GAME_REGISTRY: dict[str, GameDef] = {}

def register_game(game: GameDef):
    """注册一款游戏到全局注册表"""
    GAME_REGISTRY[game.game_id] = game

def get_game(game_id: str) -> GameDef | None:
    """按 ID 获取游戏定义"""
    return GAME_REGISTRY.get(game_id)

def get_all_games() -> list[GameDef]:
    """获取所有已注册游戏"""
    return list(GAME_REGISTRY.values())


# ============================================================
# 动态计分（从 app.py 移入，属于游戏业务逻辑）
# ============================================================

def calc_game_score(game: GameDef, question_data: dict, user_answer) -> int:
    """根据翻牌表现计算实际得分：翻牌次数越接近最优，得分越高"""
    pair_count = question_data.get("pair_count", 0)
    if isinstance(user_answer, dict) and pair_count > 0:
        optimal = pair_count * 2
        actual = user_answer.get("total_flips", 999)
        multiplier = max(0.5, optimal / max(actual, optimal))
        return int(game.score * multiplier)
    return game.score
