import pytest

from server.app.core.runtime_security import assert_safe_exposure, is_loopback_host


def test_루프백_주소는_인증_없이도_허용된다():
    assert_safe_exposure(server_host="127.0.0.1", app_env="development", auth_enabled=False)


def test_외부_바인딩에서_인증이_꺼져_있으면_기동을_거부한다():
    with pytest.raises(RuntimeError, match="루프백"):
        assert_safe_exposure(server_host="0.0.0.0", app_env="development", auth_enabled=False)


def test_외부_바인딩이라도_인증이_켜져_있으면_허용된다():
    assert_safe_exposure(server_host="0.0.0.0", app_env="development", auth_enabled=True)


def test_production에서는_인증이_꺼져_있으면_루프백이어도_거부한다():
    with pytest.raises(RuntimeError, match="production"):
        assert_safe_exposure(server_host="127.0.0.1", app_env="production", auth_enabled=False)


def test_루프백_판정은_대소문자와_공백을_무시한다():
    assert is_loopback_host(" LocalHost ")
    assert not is_loopback_host("192.168.0.10")
