# Disable Pint's old fallback behavior (must come before importing Pint)
import os
os.environ['PINT_ARRAY_PROTOCOL_FALLBACK'] = "0"

from pint import UnitRegistry

# A central UnitRegistry and Quantity.
# Very important to retain globally unified functionalities. Else, e.g. tests break.
# See: https://pint.readthedocs.io/en/0.10.1/tutorial.html#using-pint-in-your-projects,
# where there is the warning:
#
#    There are no global units in Pint.
#    All units belong to a registry and you can have multiple registries instantiated at
#    the same time.
#    However, you are not supposed to operate between quantities that belong to
#    different registries.
#

ureg = UnitRegistry(force_ndarray=True)


class PatchedQuantity(ureg.Quantity):
    def __eq__(self, other):
        """Re-implements equality checking to account for floating-point precision.

        This is mainly important for testing; however, we cannot use pytest.approx()
        on pint's Quantity objects. Therefore, introduce some (very low) tolerance to
        equality checking, such that e.g. `10.00000001 == 10` is True.
        """
        if self.dimensionality != other.dimensionality:
            # Can never be equal, no matter the magnitude
            return False

        relative_tolerance = 1e-9
        # Allow lesser and equal, the latter for if self's magnitude is zero.
        return abs(self - other) <= self * relative_tolerance

    def is_negative(self):
        return self.magnitude < 0


Q_ = PatchedQuantity




# Silence NEP 18 warning
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    Q_([])
