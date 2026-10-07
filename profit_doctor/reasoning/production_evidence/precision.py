"""Exact finite base-ten ratios; no ambient Decimal context or rounding policy."""
from decimal import Decimal
from fractions import Fraction


NON_TERMINATING = 'NON_TERMINATING_DECIMAL_REQUIRES_GOVERNED_PRECISION_POLICY'


def exact_percentage(numerator: Decimal, denominator: Decimal) -> Decimal:
    if not isinstance(numerator, Decimal) or not isinstance(denominator, Decimal):
        raise TypeError('Exact Decimal components required')
    if not numerator.is_finite() or not denominator.is_finite():
        raise ValueError('Finite components required')
    if denominator <= 0:
        raise ValueError('POSITIVE_REVENUE_REQUIRED')
    value = 100 * Fraction(numerator) / Fraction(denominator)
    remaining, twos, fives = value.denominator, 0, 0
    while remaining % 2 == 0:
        remaining //= 2
        twos += 1
    while remaining % 5 == 0:
        remaining //= 5
        fives += 1
    if remaining != 1:
        raise ValueError(NON_TERMINATING)
    scale = max(twos, fives)
    coefficient = abs(value.numerator) * 2 ** (scale - twos) * 5 ** (scale - fives)
    return Decimal((int(value.numerator < 0), Decimal(coefficient).as_tuple().digits, -scale))
