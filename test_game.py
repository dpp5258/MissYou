"""
游戏系统单元测试 — 记忆翻牌：出题、验证、去重、加分流程
"""
import pytest
from unittest.mock import Mock

from game_engine import GameDef, register_game, get_all_games, GAME_REGISTRY, calc_game_score


class TestMemoryMatch:
    """记忆翻牌 — 出题、验证、QID"""

    def test_generate_question_structure(self):
        from game_memory_match import generate_question
        q = generate_question()
        assert "cards" in q
        assert "cols" in q
        assert "rows" in q
        assert "pair_count" in q
        assert "seed" in q
        assert len(q["cards"]) == q["cols"] * q["rows"]

    def test_cards_are_paired(self):
        from game_memory_match import generate_question
        for _ in range(10):
            q = generate_question()
            cards = q["cards"]
            # 每种 emoji 恰好出现 2 次
            from collections import Counter
            counts = Counter(cards)
            for v in counts.values():
                assert v == 2, f"每种卡牌应正好2张"

    def test_predictable_layout_size(self):
        from game_memory_match import generate_question
        valid = {(4, 3), (4, 4)}
        for _ in range(10):
            q = generate_question()
            assert (q["cols"], q["rows"]) in valid

    def test_validate_accepts_reasonable(self):
        from game_memory_match import validate_answer
        q = {"pair_count": 6}
        assert validate_answer(q, {"total_flips": 20, "time_seconds": 45}) is True

    def test_validate_rejects_too_few_flips(self):
        from game_memory_match import validate_answer
        q = {"pair_count": 6}
        assert validate_answer(q, {"total_flips": 6, "time_seconds": 30}) is False  # 最少 12

    def test_validate_rejects_string_input(self):
        from game_memory_match import validate_answer
        assert validate_answer({"pair_count": 6}, "some string") is False

    def test_validate_rejects_too_many_flips(self):
        from game_memory_match import validate_answer
        q = {"pair_count": 6}
        assert validate_answer(q, {"total_flips": 100, "time_seconds": 30}) is False  # > 6*10

    def test_validate_rejects_impossible_time(self):
        from game_memory_match import validate_answer
        q = {"pair_count": 6}
        assert validate_answer(q, {"total_flips": 20, "time_seconds": 0}) is False
        assert validate_answer(q, {"total_flips": 20, "time_seconds": 999}) is False

    def test_qid_deterministic(self):
        from game_memory_match import make_question_id
        q = {"seed": 42, "cols": 4, "rows": 3}
        assert make_question_id(q) == make_question_id(q)

    def test_qid_different_seed(self):
        from game_memory_match import make_question_id
        a = make_question_id({"seed": 1, "cols": 4, "rows": 3})
        b = make_question_id({"seed": 2, "cols": 4, "rows": 3})
        assert a != b


class TestGameRegistry:
    """游戏注册表"""

    def test_register_and_retrieve(self):
        # 保存旧状态
        old = dict(GAME_REGISTRY)
        GAME_REGISTRY.clear()
        try:
            mock_render = lambda g: None
            game = GameDef(
                game_id="test_game",
                name="🧪 测试游戏",
                description="测试用的",
                score=370,
                render=mock_render,
                generate=lambda: {"q": 1},
                validate=lambda q, a: True,
                question_id=lambda q: "TST_001",
            )
            register_game(game)
            assert "test_game" in GAME_REGISTRY
            assert get_all_games() == [game]
        finally:
            GAME_REGISTRY.clear()
            GAME_REGISTRY.update(old)

    def test_score_default(self):
        game = GameDef(game_id="x", name="X", description="D")
        assert game.score == 370


class TestIsQuestionRecent:
    """7 天去重 — mock store 测试去重逻辑"""

    def test_new_question_not_recent(self):
        from storage import MissYouStore
        store = MissYouStore({"test": "dummy"}, "test_id")
        mock_ws = Mock()
        mock_ws.get_all_values.return_value = [
            ["时间", "游戏类型", "题目ID", "题目数据", "用户答案", "得分", "操作后余额"],
            ["2026-01-15 10:00", "memory_match", "OTHER_01", "...", "...", "370", "1000"],
        ]
        store._sheet = Mock()
        store._sheet.worksheet.return_value = mock_ws
        result = store.is_question_recent("memory_match", "MM_new")
        assert result is False

    def test_recent_question_detected(self):
        from storage import MissYouStore
        from datetime import date
        store = MissYouStore({"test": "dummy"}, "test_id")
        mock_ws = Mock()
        today_str = date.today().strftime("%Y-%m-%d")
        mock_ws.get_all_values.return_value = [
            ["时间", "游戏类型", "题目ID", "题目数据", "用户答案", "得分", "操作后余额"],
            [f"{today_str} 10:00", "memory_match", "MM_a3f7", "...", "...", "370", "1000"],
        ]
        store._sheet = Mock()
        store._sheet.worksheet.return_value = mock_ws
        result = store.is_question_recent("memory_match", "MM_a3f7")
        assert result is True

    def test_old_question_not_recent(self):
        from storage import MissYouStore
        store = MissYouStore({"test": "dummy"}, "test_id")
        mock_ws = Mock()
        mock_ws.get_all_values.return_value = [
            ["时间", "游戏类型", "题目ID", "题目数据", "用户答案", "得分", "操作后余额"],
            ["2025-01-01 10:00", "memory_match", "MM_old", "...", "...", "370", "1000"],
        ]
        store._sheet = Mock()
        store._sheet.worksheet.return_value = mock_ws
        result = store.is_question_recent("memory_match", "MM_old")
        assert result is False


class TestDynamicScore:
    """动态计分 calc_game_score"""

    def test_memory_match_perfect(self):
        g = GameDef(game_id="memory_match", name="test", description="", score=370)
        # 6 对，最优 12 次翻牌 → 系数 1.0
        score = calc_game_score(g, {"pair_count": 6}, {"total_flips": 12, "time_seconds": 30})
        assert score == 370

    def test_memory_match_terrible(self):
        g = GameDef(game_id="memory_match", name="test", description="", score=370)
        # 6 对，60 次翻牌 → 系数 12/60=0.2, clamp to 0.5
        score = calc_game_score(g, {"pair_count": 6}, {"total_flips": 60, "time_seconds": 180})
        assert score == int(370 * 0.5)

    def test_memory_match_string_answer(self):
        g = GameDef(game_id="memory_match", name="test", description="", score=370)
        # 传入字符串（兼容旧格式），应返回默认分
        assert calc_game_score(g, {"pair_count": 6}, "old_format") == 370

    def test_fixed_score_for_unknown_game(self):
        g = GameDef(game_id="other_game", name="test", description="", score=100)
        assert calc_game_score(g, {}, "anything") == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
