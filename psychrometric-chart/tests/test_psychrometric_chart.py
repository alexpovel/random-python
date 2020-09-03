from collections import Counter

# For usage of nullcontext, see:
# https://docs.pytest.org/en/latest/example/parametrize.html#parametrizing-conditional-raising
from contextlib import nullcontext
from subprocess import run

import pytest

from psychrometric_chart import __version__
from psychrometric_chart.main import Substance, relative_humidity
from psychrometric_chart.physical_units import Q_, ureg


def run_tests() -> None:
    """Workaround to get poetry scripts working.

    This way, 'poetry run tests' can be invoked on CLI, if pyproject.toml has an entry
    like:
        [tool.poetry.scripts]
        tests = "tests.test_psychrometric_chart:run_tests"
    pointing to this very function. It has the form
        script_name = "module:function"

    # Code/Idea from https://medium.com/octopus-wealth/python-scripts-26e3d0bd5277.
    # This is a temporary workaround till Poetry supports scripts, see
    # https://github.com/sdispater/poetry/issues/241.
    """
    run(["pytest", "--cov=psychrometric_chart", "--verbose"], check=True)


def id_provider(value):
    """Provide IDs aka names for test cases.

    pytest generates automatic IDs. Using this function, they can be altered to
    whatever more legible representation, see
    http://doc.pytest.org/en/latest/example/parametrize.html#different-options-for-test-ids
    """
    if isinstance(value, nullcontext):
        return "NoError"
    elif hasattr(value, "expected_exception"):
        # Decided against try/except and for hasattr for a unified approach.
        # Get which exception was passed in pytest.raises(<Exception>):
        return str(value.expected_exception)
    else:
        # See if object has __str__ implemented
        try:
            return str(value)
        except:
            pass


def test_version():
    assert __version__ == "0.1.0"


@pytest.mark.parametrize(
    ["partial_pressure", "saturation_pressure", "expectation", "rel_humidity"],
    [
        (-1.0, 0.0, pytest.raises(ValueError), 0.0),
        (0.0, -1.0, pytest.raises(ValueError), 0.0),
        (0.0, 0.0, pytest.raises(ZeroDivisionError), 0.0),
        (0.5, 1.0, nullcontext(), 0.5),
        (0.0, 1.0, nullcontext(), 0.0),
        (1.0, 1.0, nullcontext(), 1.0),
        # 200% rel. hum. is possible if crystallization cannot occur:
        (2.0, 1.0, nullcontext(), 2.0,),
    ],
    ids=id_provider,
)
def test_relative_humidity(
    partial_pressure, saturation_pressure, expectation, rel_humidity
):
    partial_pressure = Q_(partial_pressure, ureg.bar)
    saturation_pressure = Q_(saturation_pressure, ureg.bar)
    rel_humidity = Q_(rel_humidity)
    with expectation:
        assert relative_humidity(partial_pressure, saturation_pressure) == rel_humidity


class TestPhysicalUnits:
    @pytest.mark.parametrize(
        ["value1", "unit1", "value2", "unit2", "expected_equal"],
        [
            (0, None, 0, None, True),
            (0, None, 1, None, False),
            (0, None, 0, ureg.meter, False),
            (0, None, 1, ureg.meter, False),
            #
            (0, ureg.meter, 0, ureg.meter, True),
            (1, ureg.meter, 1, ureg.meter, True),
            (1, ureg.meter, 1, ureg.kelvin, False),
            (1, ureg.meter, 0, ureg.kelvin, False),
            #
            (1.0000, None, 1.0000, None, True),
            (1.0001, None, 1.0000, None, False),  # Out of tolerance
            (1.0000000000, None, 1.0000000000, None, True),
            (1.0000000001, None, 1.0000000000, None, True),  # Within tolerance
            #
            (1.0000000000, None, 1.0000000000, ureg.meter, False),
            (1.0000000001, None, 1.0000000000, ureg.kelvin, False),
            (1.0000000000, ureg.meter, 1.0000000000, ureg.meter, True),
            (1.0000000001, ureg.meter, 1.0000000000, ureg.kelvin, False),
        ],
        ids=id_provider,
    )
    def test_patched_quantity(self, value1, unit1, value2, unit2, expected_equal):
        # We could do a less verbose
        # assert (Q_(1) == Q(2)) == expected_equal
        # but that turns up as
        # assert True == False
        # etc. in the test log, which is useless info. Also, this is more readable:
        if expected_equal:
            assert Q_(value1, unit1) == Q_(value2, unit2)
        else:
            assert Q_(value1, unit1) != Q_(value2, unit2)

    @pytest.mark.parametrize(
        ["value", "expected"],
        [
            (0, False),
            (-1.0, True),
            (-100000000, True),
            (1, False),
            (1000000000, False),
        ],
    )
    def test_is_negative(self, value, expected):
        assert Q_(value).is_negative() == expected


class TestSubstance:
    @pytest.mark.parametrize(
        ["empirical_formula", "molar_mass"],
        [
            ("N", 14.007),
            ("N2", 14.007 * 2),
            ("CO2", 12.011 + 15.999 * 2),
            ("H2O", 1.008 * 2 + 15.999),
            ("FeO3", 55.845 + 15.999 * 3),
            ("Fe2O3", 55.845 * 2 + 15.999 * 3),
            ("Fe2O3O3", 55.845 * 2 + 15.999 * 6),
            ("Fe2O3O3Fe", 55.845 * 3 + 15.999 * 6),
            ("Fe2O3O3Fe25", 55.845 * 27 + 15.999 * 6),
            ("Fe2O3O3Fe25N2", 55.845 * 27 + 15.999 * 6 + 14.007 * 2),
            ("Fe2O3O3Fe25N2N2N2", 55.845 * 27 + 15.999 * 6 + 14.007 * 6),
            ("Fe2O3O3Fe25N2N2N2N", 55.845 * 27 + 15.999 * 6 + 14.007 * 7),
        ],
    )
    def test_molar_mass(self, empirical_formula, molar_mass):
        molar_mass = Q_(molar_mass, ureg.gram / ureg.mole)
        assert Substance("", empirical_formula, None, None).molar_mass == molar_mass

    @pytest.mark.parametrize(
        ["empirical_formula", "expectation", "counts"],
        [
            ("", nullcontext(), {}),
            ("2", pytest.raises(NotImplementedError), {}),
            ("Bb", pytest.raises(NotImplementedError), {}),
            ("Non-Existent-Element", pytest.raises(NotImplementedError), {}),
            ("N", nullcontext(), {"N": 1}),
            ("N2", nullcontext(), {"N": 2}),
            ("CO2", nullcontext(), {"C": 1, "O": 2}),
            ("H2O", nullcontext(), {"H": 2, "O": 1}),
            ("FeO3", nullcontext(), {"Fe": 1, "O": 3}),
            ("Fe2O3", nullcontext(), {"Fe": 2, "O": 3}),
            ("Fe2O3O3", nullcontext(), {"Fe": 2, "O": 6}),
            ("Fe2O3O3Fe", nullcontext(), {"Fe": 3, "O": 6}),
            ("Fe2O3O3Fe25", nullcontext(), {"Fe": 27, "O": 6}),
            ("Fe2O3O3Fe25N2", nullcontext(), {"Fe": 27, "O": 6, "N": 2}),
            ("Fe2O3O3Fe25N2N2N2", nullcontext(), {"Fe": 27, "O": 6, "N": 6}),
            ("Fe2O3O3Fe25N2N2N2N", nullcontext(), {"Fe": 27, "O": 6, "N": 7}),
        ],
        ids=id_provider,
    )
    def test_chem_parser(self, empirical_formula, expectation, counts):
        with expectation:
            assert Substance("", "", None, None).chem_parser(
                empirical_formula
            ) == Counter(counts)
