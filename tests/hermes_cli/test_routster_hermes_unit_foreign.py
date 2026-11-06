"""A Hermes install's hermes-gateway unit (~/.hermes) beside Routster (~/.routster) is another install:
Routster must ignore it, not refuse to start with profile_mismatch."""
import pytest

from hermes_cli.gateway_runtime_service_identity import ForeignRoot, verify_home


def test_hermes_home_unit_is_foreign_to_routster(tmp_path):
    with pytest.raises(ForeignRoot):
        verify_home(tmp_path / ".routster", str(tmp_path / ".hermes"))


def test_own_named_profile_unit_is_still_a_profile_mismatch(tmp_path):
    with pytest.raises(ValueError) as exc:
        verify_home(tmp_path / ".routster" / "profiles" / "work", str(tmp_path / ".routster"))
    assert not isinstance(exc.value, ForeignRoot) and str(exc.value) == "profile_mismatch"


def test_own_home_unit_verifies(tmp_path):
    verify_home(tmp_path / ".routster", str(tmp_path / ".routster"))
