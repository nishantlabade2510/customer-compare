import pytest

from customer_compare.values import display_value, normalize_key, values_match


@pytest.mark.parametrize(
    "source, target, transforms, compare, tolerance, expected",
    [
        ("Neha Garg", "NEHA GARG", ("upper",), "text", 0.0, True),
        ("Neha Garg", "Neha Garg", ("upper",), "text", 0.0, False),  # transform must be applied
        ("neha.garg@Mail.COM", "neha.garg@mail.com", ("lower",), "text", 0.0, True),
        ("Amit.Rao@mail.com", "amit.rao@mail.com", (), "text", 0.0, False),
        ("  c001 ", "C001", ("trim", "upper"), "text", 0.0, True),
        (" 555-1001 ", "555-1001", ("trim",), "text", 0.0, True),
        (" 555-1001 ", "555-1001", (), "text", 0.0, False),
        ("Canada", None, ("upper",), "text", 0.0, False),
        (None, None, (), "text", 0.0, True),
        ("1250.00", "1250", (), "numeric", 0.0, True),
        ("637.53", "687.53", (), "numeric", 0.0, False),
        ("3525.66", "3525.76", (), "numeric", 0.005, False),
        ("3525.66", "3525.67", (), "numeric", 0.01, True),
        ("1600.24", None, (), "numeric", 0.0, False),
        ("2004-06-25 00:00:00", "1990-01-01 00:00:00", (), "date", 0.0, False),
        ("1975-01-01 00:00:00", "1975-01-01", (), "date", 0.0, True),
    ],
)
def test_values_match(source, target, transforms, compare, tolerance, expected):
    assert values_match(
        source, target, transforms=transforms, compare=compare, tolerance=tolerance
    ) is expected


def test_display_value_formats_numbers_dates_and_nulls():
    assert display_value(1250, "numeric") == "1250.00"
    assert display_value("637.5", "numeric") == "637.50"
    assert display_value(None, "text") == "NULL"
    assert display_value(float("nan"), "numeric") == "NULL"
    assert display_value("1975-01-01 00:00:00", "date") == "1975-01-01"


@pytest.mark.parametrize(
    "raw, expected",
    [(1001, "1001"), (1001.0, "1001"), (" 1001 ", "1001"), (None, None), (float("nan"), None)],
)
def test_normalize_key(raw, expected):
    assert normalize_key(raw) == expected
