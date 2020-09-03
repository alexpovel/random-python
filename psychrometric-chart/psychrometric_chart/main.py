import math
from collections import Counter
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from physical_units import Q_, ureg


@dataclass
class Substance:
    _molar_masses = {
        "H": 1.008,
        "He": 4.003,
        "Li": 6.941,
        "Be": 9.012,
        "B": 10.811,
        "C": 12.011,
        "N": 14.007,
        "O": 15.999,
        "F": 18.998,
        "Ne": 20.180,
        "Na": 22.990,
        "Mg": 24.305,
        "Al": 26.982,
        "Si": 28.086,
        "P": 30.974,
        "S": 32.065,
        "Cl": 35.453,
        "Ar": 39.948,
        "K": 39.098,
        "Ca": 40.078,
        "Sc": 44.956,
        "Ti": 47.867,
        "V": 50.942,
        "Cr": 51.996,
        "Mn": 54.938,
        "Fe": 55.845,
        "Co": 58.933,
        "Ni": 58.693,
        "Cu": 63.546,
        "Zn": 65.409,
        "Ga": 69.723,
        "Ge": 72.640,
        "As": 74.922,
        "Se": 78.960,
        "Br": 79.904,
        "Kr": 83.798,
        "Rb": 85.468,
        "Sr": 87.620,
        "Y": 88.906,
        "Zr": 91.224,
        "Nb": 92.906,
        "Mo": 95.940,
        "Tc": 98.906,
        "Ru": 101.070,
        "Rh": 102.906,
        "Pd": 106.420,
        "Ag": 107.868,
        "Cd": 112.411,
        "In": 114.818,
        "Sn": 118.710,
        "Sb": 121.760,
        "Te": 127.600,
        "I": 126.904,
        "Xe": 131.293,
        "Cs": 132.905,
        "Ba": 137.327,
        "La": 138.905,
        "Ce": 140.116,
        "Pr": 140.905,
        "Nd": 144.242,
        "Pm": 146.915,
        "Sm": 150.360,
        "Eu": 151.964,
        "Gd": 157.250,
        "Tb": 158.925,
        "Dy": 162.500,
        "Ho": 164.930,
        "Er": 167.259,
        "Tm": 168.934,
        "Yb": 173.040,
        "Lu": 174.967,
        "Hf": 178.490,
        "Ta": 180.948,
        "W": 183.840,
        "Re": 186.207,
        "Os": 190.230,
        "Ir": 192.217,
        "Pt": 195.084,
        "Au": 196.967,
        "Hg": 200.590,
        "Tl": 204.383,
        "Pb": 207.200,
        "Bi": 208.980,
    }

    _molar_masses.update(
        {  # Cast to Quantity
            element: Q_(weight, ureg.gram / ureg.mole)
            for element, weight in _molar_masses.items()
        }
    )

    name: str
    empirical_formula: str
    temperature: ureg.Quantity
    pressure: ureg.Quantity

    def __post_init__(self):
        self._elements: Counter = self.chem_parser(self.empirical_formula)
        self.molar_mass = self.molar_mass(self._elements)

    def chem_parser(self, empirical_formula: str) -> Counter:
        """Counts and sums up elements in an empirical chemical formula.

        For example, 'Fe2O3' -> Counter(Fe=2, O=3)

        Args:
            empirical_formula: A chemical formula like 'H2O', 'N2', 'Fe2O3'.
        Returns:
            Counter of the containing chemical elements.
    """
        element = ""
        count = ""
        elements = Counter()

        if not empirical_formula:
            return elements

        def increment_elements(element_to_add: str, count_to_add: int = 1):
            """Helper function, reducing code repetition."""
            # Allow this inner function to rebind these variables from the outer scope:
            nonlocal element
            nonlocal count

            if element not in self._molar_masses:
                raise NotImplementedError(f"Unavailable element '{element}' requested.")

            # Don't just assign, increment; important for e.g. 'FeO3Fe', so 'Fe' is
            # picked up twice.
            elements[element_to_add] += count_to_add
            # Reset and start with next element:
            element = ""
            count = ""

        assembling_element = False
        assembling_count = False

        for char in empirical_formula:
            if char.isupper():
                if assembling_element:
                    # Found next element without encountering a digit first; implies
                    # atomic count of 1. Reset element and count, start with next
                    increment_elements(element)
                elif assembling_count:
                    assembling_count = False  # Now done, since next element found
                    increment_elements(element, int(count))
                assembling_element = True
                element += char
            elif char.islower():
                # Just grab these as they come
                element += char
            elif char.isdigit():
                # Digit found, aka element name has ended; count could be multi-digit,
                # therefore sum up string elements until done
                assembling_element = False
                assembling_count = True
                count += char
        else:
            # Handling of last element goes here
            if char.isdigit():
                # Ended on digit, add to counter, e.g. 'CO2'
                increment_elements(element, int(count))
            elif char.isalpha():
                # Ended on char, implies count of one, e.g. 'H2O'
                increment_elements(element)
        # Remove empty keys:
        elements = Counter({k: v for k, v in elements.items() if k})
        return elements

    def molar_mass(self, elements: Counter) -> ureg.Quantity:
        """Computes the molar mass aka weight from a count of elements.

        Args:
            elements: A Counter of the elements in the compound.
        Returns:
            Molar mass.
        """
        return sum(self._molar_masses[element] for element in elements.elements())


@ureg.check("[pressure]", "[pressure]")
def relative_humidity(
    vapour_partial_pressure: ureg.Quantity, vapour_saturation_pressure: ureg.Quantity
) -> ureg.Quantity:
    if vapour_partial_pressure.is_negative():
        raise ValueError("Negative vapour partial pressure.")
    if vapour_saturation_pressure.is_negative():
        raise ValueError("Negative vapour saturation pressure.")
    return vapour_partial_pressure / vapour_saturation_pressure

from functools import wraps

from pint import DimensionalityError

# @ureg.check
def my_check(units, *args):
    def decorator(function):
        @ureg.wraps(units)
        def wrapper(*args, **kwargs):
            # for unit, quantity in zip(units, args):
            #     quantity_units = quantity.units
            #     if not unit == quantity_units:
            #         raise TypeError(f"Expected unit {unit}, got {quantity_units}.")
            vectorized = np.vectorize(function)
            return vectorized(*args, **kwargs)
        return wrapper
    return decorator

# @ureg.check("[temperature]")
# @u.quantity_input(temperature=u.deg_C)
# @ureg.wraps(ureg.degC, ureg.Pa, strict=False)
@my_check(ureg.Pa, ureg.degC)
# @np.vectorize
# @ureg.wraps(ureg.Pa, ureg.degC)
def vapour_saturation_pressure(temperature: ureg.Quantity) -> ureg.Quantity:
    """Returns the saturation pressure for water vapour according to Buck.

    Approximate equation according to:
    Arden L. Buck. ‘New Equations for Computing Vapor Pressure and Enhancement Factor’.
    In: Journal of Applied Meteorology 20.12 (Dec. 1981), pp. 1527–1532.
    Original source and parameters in millibar (written as 'mb' there). Scaled to Pa
    here.

    Args:
        temperature: Temperature value, between -80 and 100 degC.
    Returns:
        Corresponding water vapour saturation pressure.
    """
    # 'Magic' Buck numbers; found through empirical experiments/fitting
    # if temperature < Q_(-80, ureg.degC):
    if temperature < -80:
        raise ValueError(f"Temperature too low ({temperature}).")
    # elif temperature < Q_(0, ureg.degC):
    elif temperature < 0:
        A = 611.15
        B = 23.036
        C = 279.82
        D = 333.7
    elif temperature <= 100:
        A = 611.21
        B = 18.564
        C = 255.57
        D = 254.4
    else:
        raise ValueError(f"Temperature too high ({temperature}).")
    magnitude = A * math.exp(
        ((B - temperature / D) * temperature)
        / (temperature + C)
    )
    # return magnitude * u.Pa
    return magnitude
    # return Q_(magnitude, ureg.Pa)


def specific_heat_capacity(gas_type: str):
    gas_type_to_specific_heat_capacity = {
        "air": 1004.5,
        "water_g": 1860.0,
        "water_l": 4190.0,
        "water_s": 2050.0,
    }
    return gas_type_to_specific_heat_capacity[gas_type]



print(vapour_saturation_pressure.__name__)
print(vapour_saturation_pressure.__doc__)



# vapour_saturation_pressure = np.vectorize(vapour_saturation_pressure)

# temperatures = Q_(np.linspace(-70, 100, 200), "kelvin")

temperatures = Q_(np.linspace(-70, 100, 200), ureg.degC)

# print(temperatures)

# temperatures = Q_(200, "kelvin")
# temperatures = np.linspace(-70, 100, 200) * ureg("kelvin")

# print(temperatures)
# temperatures = Q_(np.arange(-70, 100, 0.5), ureg.degC)


def c_p_vapour(t, p):
    """Computes the specific heat capacity of water vapour.

    Approximate equation according to:
    Vestfálová, Magda, and Pavel Šafařík.
    ‘Dependence of the Isobaric Specific Heat Capacity of Water Vapor on the Pressure
    and Temperature’. Edited by P. Dančová and M. Veselý. EPJ Web of Conferences 114
    (2016): 02133. https://doi.org/10.1051/epjconf/201611402133.

    Args:
        temperature: The vapour temperature. Valid 
    """
    if t < 50:
        A_E = 1877.2
        B_E = -0.49545
        C_E = 0.0081818
    else:
        A_E = 1856.1
        B_E = 0.28056
        C_E = 0.00069444
    A_F = 22.537
    B_F = 0.49321
    C_F = 0.048927
    return A_E + B_E * t + C_E * t ** 2 + (p - 611.657) / (A_F + B_F * t + C_F * t ** 2)


c_p = np.vectorize(c_p_vapour)

plt.plot(temperatures, vapour_saturation_pressure(temperatures))

plt.xlabel("t")
plt.ylabel("p")

plt.title("Simple Plot")

plt.legend()

plt.yscale("log")

plt.show()
