import os
import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mlb_project.settings")
django.setup()

from mlb_app.security import InputValidator


def test_validate_date_valid():
    assert InputValidator.validate_date_input("2024-05-10") == "2024-05-10"


def test_validate_date_invalid_format():
    assert InputValidator.validate_date_input("05-10-2024") is None


def test_validate_date_nonexistent():
    assert InputValidator.validate_date_input("2024-02-30") is None
