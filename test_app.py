"""
测试 MissYou 纯业务逻辑：Google Sheets 无关的函数先测
"""
from datetime import date


def test_calc_decay_basic():
    """正常衰减：9000 余额，每天减 10，距今 5 天"""
    from app import calc_decay
    new_bal, days = calc_decay(9000, 10, date(2026, 6, 1))
    assert days == 5
    assert new_bal == 8950  # 9000 - 5*10


def test_calc_decay_no_days_passed():
    """今天刚更新过，0 天，余额不变"""
    from app import calc_decay
    new_bal, days = calc_decay(5000, 10, date.today())
    assert days == 0
    assert new_bal == 5000


def test_calc_decay_zero_balance():
    """余额为 0 时继续衰减（不会变成负数）"""
    from app import calc_decay
    new_bal, days = calc_decay(0, 5, date(2026, 1, 1))
    assert new_bal <= 0
    assert days > 0
