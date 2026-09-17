from __future__ import annotations

import io
import logging

from services import logger as logger_module


def test_safe_add_handler_falls_back_to_console_on_permission_error(monkeypatch):
    stream = io.StringIO()
    test_logger = logging.getLogger("maxload-test-bootstrap")
    test_logger.handlers.clear()
    test_logger.setLevel(logging.INFO)
    test_logger.propagate = False

    handler = logging.StreamHandler(stream)
    handler.addFilter(logger_module.ContextFilter())
    handler.setFormatter(logging.Formatter("%(message)s %(path)s %(error_type)s"))
    test_logger.addHandler(handler)

    monkeypatch.setattr(logger_module, "_base_logger", test_logger)
    log_path = "/app/logs/bot_log.log"

    def _raise_permission_error():
        raise PermissionError(13, "Permission denied", log_path)

    added = logger_module._safe_add_handler(
        _raise_permission_error,
        description="info file logger",
        path=log_path,
    )

    assert added is False
    output = stream.getvalue()
    assert "Disabled info file logger because it is not writable." in output
    assert log_path in output
    assert "PermissionError" in output


def test_third_party_loggers_route_through_app_handlers():
    logger_module._configure_third_party_loggers()

    for name, level in logger_module._THIRD_PARTY_LOG_LEVELS.items():
        third_party = logging.getLogger(name)
        assert third_party.propagate is False
        assert third_party.level == level
        for handler in logger_module._base_logger.handlers:
            assert handler in third_party.handlers


def test_sinks_disabled_env_parsing(monkeypatch):
    monkeypatch.setenv(logger_module._DISABLE_SINKS_ENV, "1")
    assert logger_module._sinks_disabled() is True
    monkeypatch.setenv(logger_module._DISABLE_SINKS_ENV, "0")
    assert logger_module._sinks_disabled() is False
    monkeypatch.delenv(logger_module._DISABLE_SINKS_ENV)
    assert logger_module._sinks_disabled() is False


def test_disable_log_sinks_detaches_and_closes_all_sinks(monkeypatch):
    # Register the env var with monkeypatch first so its mutation by
    # disable_log_sinks() is rolled back after the test.
    monkeypatch.setenv(logger_module._DISABLE_SINKS_ENV, "")

    shared_handler = logging.StreamHandler(io.StringIO())
    base = logging.getLogger("maxload-test-disable-base")
    base.handlers.clear()
    base.addHandler(shared_handler)

    third_name = "maxload-test-disable-third"
    third = logging.getLogger(third_name)
    third.handlers.clear()
    third.addHandler(shared_handler)

    monkeypatch.setattr(logger_module, "_base_logger", base)
    monkeypatch.setattr(
        logger_module,
        "_THIRD_PARTY_LOG_LEVELS",
        {third_name: logging.ERROR},
    )

    logger_module.disable_log_sinks()

    assert third.handlers == []
    assert len(base.handlers) == 1
    assert isinstance(base.handlers[0], logging.NullHandler)
    assert logger_module._sinks_disabled() is True

