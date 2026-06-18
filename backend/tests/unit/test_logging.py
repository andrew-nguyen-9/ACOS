import logging

from backend.logging_config import configure_logging, get_logger


def test_configure_logging_sets_root_level():
    configure_logging("DEBUG")
    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_info_level():
    configure_logging("INFO")
    assert logging.getLogger().level == logging.INFO


def test_get_logger_returns_named_logger():
    logger = get_logger("test.module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.module"


def test_noisy_loggers_are_quieted():
    configure_logging("DEBUG")
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("chromadb").level == logging.WARNING
    assert logging.getLogger("sqlalchemy.engine").level == logging.WARNING
