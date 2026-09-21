from app.graph.repository import _to_vector_literal


def test_formats_as_bracketed_comma_separated_floats():
    assert _to_vector_literal([1.0, 2.5, -3.0]) == "[1.0,2.5,-3.0]"


def test_handles_a_single_value():
    assert _to_vector_literal([0.0]) == "[0.0]"


def test_coerces_ints_to_floats():
    assert _to_vector_literal([1, 2, 3]) == "[1.0,2.0,3.0]"
