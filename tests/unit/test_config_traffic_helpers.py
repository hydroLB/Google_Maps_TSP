from __future__ import annotations

import pytest

from fastest_route.config.loading.accessors import get_bool
from fastest_route.config.loading.parsers import parse_traffic_model
from fastest_route.shared.errors import ConfigError
from fastest_route.shared.types import TrafficModel


def test_get_bool_reads_default_and_value() -> None:
    assert get_bool({}, "flag", False, "loc") is False
    assert get_bool({"flag": True}, "flag", False, "loc") is True


def test_get_bool_rejects_non_bool() -> None:
    with pytest.raises(ConfigError):
        get_bool({"flag": "yes"}, "flag", False, "loc")
    with pytest.raises(ConfigError):
        get_bool(123, "flag", False, "loc")


def test_parse_traffic_model_accepts_known_values() -> None:
    assert parse_traffic_model("best_guess", "loc") == TrafficModel.BEST_GUESS
    assert parse_traffic_model("OPTIMISTIC", "loc") == TrafficModel.OPTIMISTIC


def test_parse_traffic_model_rejects_invalid_values() -> None:
    with pytest.raises(ConfigError):
        parse_traffic_model("wild_guess", "loc")
    with pytest.raises(ConfigError):
        parse_traffic_model(123, "loc")
