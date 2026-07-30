"""
游戏系统单元测试 — 覆盖出题、验证、去重、加分流程
"""
import pytest
from unittest.mock import Mock, patch

from game_number_puzzle import (
    make_question_id,
    find_solutions,
    generate_question,
    validate_answer,
    _eval_expr,
)
from game_engine import GameDef, register_game, get_all_games, GAME_REGISTRY


class TestExprEval:
    """安全表达式求值"""

    def test_simple_arithmetic(self):
        assert _eval_expr("2+3") == 5
        assert _eval_expr("10-4") == 6
        assert _eval_expr("3*7") == 21
        assert _eval_expr("8/2") == 4

    def test_brackets(self):
        assert _eval_expr("(2+3)*4") == 20
        assert _eval_expr("2+(3*4)") == 14

    def test_division_rounding(self):
        """非整数除法返回 None"""
        assert _eval_expr("10/3") is None
        assert _eval_expr("5/2") is None

    def test_zero_division(self):
        assert _eval_expr("5/0") is None

    def test_syntax_error(self):
        assert _eval_expr("2+*3") is None
        assert _eval_expr("(2+3") is None
        assert _eval_expr("()") is None

    def test_malicious_input(self):
        """恶意代码被拒绝 — 空 builtins 下 __import__ 不可用"""
        assert _eval_expr("__import__('os').system('dir')") is None
        assert _eval_expr("open('/etc/passwd')") is None


class TestFindSolutions:
    """题目求解"""

    def test_standard_24_point(self):
        """经典 24 点：(3,8,3,8) → 24"""
        solutions = find_solutions([3, 8, 3, 8])
        targets = {v for v, _ in solutions}
        assert 24 in targets, "8÷(3−8÷3)=24 应该是合法解"

    def test_simple_case(self):
        """简单组合：(1,2,3,4) 应该有很多结果"""
        solutions = find_solutions([1, 2, 3, 4])
        assert len(solutions) > 5  # 至少能算出几种不同结果

    def test_all_results_positive(self):
        """所有结果都是正数"""
        solutions = find_solutions([5, 6, 7, 8])
        for val, expr in solutions:
            assert val > 0, f"{expr} = {val} 应该是正数"

    def test_all_results_in_range(self):
        """结果在合理范围"""
        solutions = find_solutions([1, 3, 5, 7])
        for val, _ in solutions:
            assert 1 <= val <= 100


class TestGenerateQuestion:
    """出题"""

    def test_returns_dict_with_keys(self):
        q = generate_question()
        assert "nums" in q
        assert "target" in q
        assert "solutions" in q

    def test_nums_are_4(self):
        q = generate_question()
        assert len(q["nums"]) == 4

    def test_target_is_positive_int(self):
        q = generate_question()
        assert isinstance(q["target"], int)
        assert q["target"] > 0

    def test_has_at_least_one_solution(self):
        q = generate_question()
        assert len(q["solutions"]) >= 1

    def test_solution_is_valid(self):
        """标准答案确实能算出目标数"""
        for _ in range(10):
            q = generate_question()
            # 用 validate_answer 验证自己的标准答案
            for sol in q["solutions"]:
                assert validate_answer(q, sol), f"{sol} 应该通过验证"


class TestMakeQuestionID:
    """题目 ID 生成"""

    def test_deterministic(self):
        q = {"nums": [3, 8, 3, 8], "target": 24}
        id1 = make_question_id(q)
        id2 = make_question_id(q)
        assert id1 == id2, "同样输入应产生同样 ID"

    def test_order_independent(self):
        """数字顺序不影响 ID"""
        id1 = make_question_id({"nums": [3, 8, 3, 8], "target": 24})
        id2 = make_question_id({"nums": [8, 3, 8, 3], "target": 24})
        assert id1 == id2

    def test_different_nums_different_id(self):
        id1 = make_question_id({"nums": [1, 2, 3, 4], "target": 10})
        id2 = make_question_id({"nums": [1, 2, 3, 5], "target": 10})
        assert id1 != id2

    def test_different_target_different_id(self):
        id1 = make_question_id({"nums": [3, 8, 3, 8], "target": 24})
        id2 = make_question_id({"nums": [3, 8, 3, 8], "target": 25})
        assert id1 != id2

    def test_returns_string_of_length_8(self):
        qid = make_question_id({"nums": [1, 2, 3, 4], "target": 10})
        assert isinstance(qid, str)
        assert len(qid) == 8


class TestValidateAnswer:
    """答案验证"""

    def test_correct_answer_accepted(self):
        q = {"nums": [3, 8, 3, 8], "target": 24}
        assert validate_answer(q, "8/(3-8/3)") is True
        assert validate_answer(q, "8÷(3−8÷3)") is True  # 全角/显示符号也接受

    def test_wrong_result_rejected(self):
        q = {"nums": [3, 8, 3, 8], "target": 24}
        assert validate_answer(q, "3+8+3+8") is False  # =22 ≠ 24

    def test_wrong_numbers_rejected(self):
        """用了不在题目里的数字"""
        q = {"nums": [3, 8, 3, 8], "target": 24}
        assert validate_answer(q, "5+5+7+7") is False

    def test_duplicate_number_used(self):
        """同一个数字用了超过一次"""
        q = {"nums": [2, 2, 2, 4], "target": 20}
        assert validate_answer(q, "2+2+2+2") is False  # 多了一个 2，少了一个 4

    def test_missing_number(self):
        """没用完所有数字"""
        q = {"nums": [3, 8, 3, 8], "target": 24}
        assert validate_answer(q, "3*8") is False  # 只用了两个数字

    def test_malicious_rejected(self):
        q = {"nums": [1, 2, 3, 4], "target": 10}
        assert validate_answer(q, "__import__('os').system('rm')") is False
        assert validate_answer(q, "open('/etc/passwd')") is False
        assert validate_answer(q, "exec('print(1)')") is False

    def test_empty_rejected(self):
        q = {"nums": [1, 2, 3, 4], "target": 10}
        assert validate_answer(q, "") is False

    def test_real_case_from_generator(self):
        """用 generate_question 出的真实题目验证"""
        for _ in range(20):
            q = generate_question()
            sol = q["solutions"][0]
            # 标准答案应通过
            assert validate_answer(q, sol), f"标准答案 {sol} 未通过验证"
            # 随机乱写应不通过
            fake = f"{q['nums'][0]}+{q['nums'][1]}+{q['nums'][2]}+{q['nums'][3]}"
            if sum(q['nums']) != q['target']:
                assert validate_answer(q, fake) is False


class TestGameRegistry:
    """游戏注册表"""

    def test_register_and_retrieve(self):
        # 保存旧状态
        old = dict(GAME_REGISTRY)
        GAME_REGISTRY.clear()
        try:
            mock_render = lambda g, s: None
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
    """7 天去重 — mock sheet 测试去重逻辑"""

    def test_new_question_not_recent(self):
        from app import is_question_recent
        mock_sheet = Mock()
        mock_ws = Mock()
        mock_ws.get_all_values.return_value = [
            ["时间", "游戏类型", "题目ID", "题目数据", "用户答案", "得分", "操作后余额"],
            ["2026-01-15 10:00", "other_game", "OTHER_01", "...", "...", "370", "1000"],
        ]
        mock_sheet.worksheet.return_value = mock_ws
        result = is_question_recent(mock_sheet, "number_puzzle", "NP_new")
        assert result is False

    def test_recent_question_detected(self):
        from app import is_question_recent
        from datetime import date
        mock_sheet = Mock()
        mock_ws = Mock()
        today_str = date.today().strftime("%Y-%m-%d")
        mock_ws.get_all_values.return_value = [
            ["时间", "游戏类型", "题目ID", "题目数据", "用户答案", "得分", "操作后余额"],
            [f"{today_str} 10:00", "number_puzzle", "NP_a3f7", "...", "...", "370", "1000"],
        ]
        mock_sheet.worksheet.return_value = mock_ws
        result = is_question_recent(mock_sheet, "number_puzzle", "NP_a3f7")
        assert result is True

    def test_old_question_not_recent(self):
        from app import is_question_recent
        mock_sheet = Mock()
        mock_ws = Mock()
        mock_ws.get_all_values.return_value = [
            ["时间", "游戏类型", "题目ID", "题目数据", "用户答案", "得分", "操作后余额"],
            ["2025-01-01 10:00", "number_puzzle", "NP_old", "...", "...", "370", "1000"],
        ]
        mock_sheet.worksheet.return_value = mock_ws
        result = is_question_recent(mock_sheet, "number_puzzle", "NP_old")
        assert result is False


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


class TestWordMatch:
    """单词匹配 — 出题、验证、QID"""

    def test_generate_question_structure(self):
        from game_word_match import generate_question
        q = generate_question()
        assert "pairs" in q
        assert "en_display" in q
        assert "zh_display" in q
        assert "difficulty" in q
        assert "count" in q
        assert 8 <= q["count"] <= 12
        assert q["difficulty"] in ("easy", "hard")

    def test_en_display_is_shuffled(self):
        from game_word_match import generate_question
        q = generate_question()
        en_from_pairs = [p[0] for p in q["pairs"]]
        assert sorted(q["en_display"]) == sorted(en_from_pairs)

    def test_zh_display_is_shuffled(self):
        from game_word_match import generate_question
        q = generate_question()
        zh_from_pairs = [p[1] for p in q["pairs"]]
        assert sorted(q["zh_display"]) == sorted(zh_from_pairs)

    def test_validate_all_correct(self):
        from game_word_match import validate_answer
        q = {"pairs": [("apple", "苹果"), ("book", "书")]}
        assert validate_answer(q, {"matches": [["apple", "苹果"], ["book", "书"]]}) is True

    def test_validate_wrong_pair(self):
        from game_word_match import validate_answer
        q = {"pairs": [("apple", "苹果"), ("book", "书")]}
        assert validate_answer(q, {"matches": [["apple", "书"], ["book", "苹果"]]}) is False

    def test_validate_missing_pair(self):
        from game_word_match import validate_answer
        q = {"pairs": [("apple", "苹果"), ("book", "书")]}
        assert validate_answer(q, {"matches": [["apple", "苹果"]]}) is False

    def test_validate_string_rejected(self):
        from game_word_match import validate_answer
        assert validate_answer({"pairs": []}, "wrong type") is False

    def test_qid_same_words_same_id(self):
        from game_word_match import make_question_id
        q1 = {"pairs": [("apple", "苹果"), ("book", "书")]}
        q2 = {"pairs": [("book", "书"), ("apple", "苹果")]}
        assert make_question_id(q1) == make_question_id(q2)

    def test_qid_different_words_different_id(self):
        from game_word_match import make_question_id
        a = make_question_id({"pairs": [("apple", "苹果")]})
        b = make_question_id({"pairs": [("dog", "狗")]})
        assert a != b


class TestDynamicScore:
    """动态计分 _calc_game_score"""

    def test_number_puzzle_fixed_score(self):
        from app import _calc_game_score
        from game_engine import GameDef
        g = GameDef(game_id="number_puzzle", name="test", description="", score=370)
        assert _calc_game_score(g, {}, "3+8+3+8") == 370

    def test_memory_match_perfect(self):
        from app import _calc_game_score
        from game_engine import GameDef
        g = GameDef(game_id="memory_match", name="test", description="", score=370)
        # 6 对，最优 12 次翻牌 → 系数 1.0
        score = _calc_game_score(g, {"pair_count": 6}, {"total_flips": 12, "time_seconds": 30})
        assert score == 370

    def test_memory_match_terrible(self):
        from app import _calc_game_score
        from game_engine import GameDef
        g = GameDef(game_id="memory_match", name="test", description="", score=370)
        # 6 对，60 次翻牌 → 系数 12/60=0.2, clamp to 0.5
        score = _calc_game_score(g, {"pair_count": 6}, {"total_flips": 60, "time_seconds": 180})
        assert score == int(370 * 0.5)

    def test_memory_match_string_answer(self):
        from app import _calc_game_score
        from game_engine import GameDef
        g = GameDef(game_id="memory_match", name="test", description="", score=370)
        # 传入字符串（兼容旧格式），应返回默认分
        assert _calc_game_score(g, {"pair_count": 6}, "old_format") == 370

    def test_word_match_perfect(self):
        from app import _calc_game_score
        from game_engine import GameDef
        g = GameDef(game_id="word_match", name="test", description="", score=370)
        score = _calc_game_score(g, {}, {"errors": 0})
        assert score == 370

    def test_word_match_many_errors(self):
        from app import _calc_game_score
        from game_engine import GameDef
        g = GameDef(game_id="word_match", name="test", description="", score=370)
        # 7 次错误 → penalty = 1-7*0.1 = 0.3
        score = _calc_game_score(g, {}, {"errors": 7})
        assert score == int(370 * 0.3)

    def test_word_match_string_answer(self):
        from app import _calc_game_score
        from game_engine import GameDef
        g = GameDef(game_id="word_match", name="test", description="", score=370)
        assert _calc_game_score(g, {}, "old_format") == 370


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
