"""
测试 MissYou 纯业务逻辑：Google Sheets 无关的函数先测
"""
from datetime import date
from app import calc_decay


def test_calc_decay_basic():
    """正常衰减：9000 余额，每天减 10，距今 5 天"""
    new_bal, days = calc_decay(9000, 10, date(2026, 6, 1))
    assert days == 5
    assert new_bal == 8950  # 9000 - 5*10


def test_calc_decay_no_days_passed():
    """今天刚更新过，0 天，余额不变"""
    new_bal, days = calc_decay(5000, 10, date.today())
    assert days == 0
    assert new_bal == 5000


def test_calc_decay_zero_balance():
    """余额为 0 时继续衰减，返回负值"""
    new_bal, days = calc_decay(0, 5, date(2026, 1, 1))
    assert days > 0
    assert new_bal == -(days * 5)  # 精确验证衰减计算


def test_check_password_user():
    """输入用户密码应返回 'user'"""
    from app import check_password
    assert check_password("user123", "user123", "admin456") == "user"


def test_check_password_admin():
    """输入管理密码应返回 'admin'"""
    from app import check_password
    assert check_password("admin456", "user123", "admin456") == "admin"


def test_check_password_wrong():
    """输入错误密码应返回 None"""
    from app import check_password
    assert check_password("wrong", "user123", "admin456") is None
