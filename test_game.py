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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
