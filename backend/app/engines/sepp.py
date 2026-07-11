"""SEPP / 72(t) calculator — Rev. Rul. 2002-62 as modified by IRS Notice 2022-6.

Computes the substantially-equal-periodic-payment amount that lets an IRA
owner withdraw before 59½ without the 10% penalty, plus the REVERSE solve:
given a target monthly payment, the IRA balance that produces it — the
dual-IRA split question ("fund IRA-A with exactly $X, leave IRA-B growing").

Methods (Notice 2022-6 §3.01):
- Fixed amortization: level amortization of the balance over the single-life
  expectancy at the chosen rate. Highest payment; fixed for the series.
- RMD method: balance ÷ life expectancy, REDETERMINED annually (year-1 value
  computed here). Lower payment, varies with balance.
- Fixed annuitization: not implemented in v1 (requires the §1.401(a)(9)-9(e)
  mortality table; yields slightly less than amortization).

Interest rate cap (§3.02(c)): not more than the GREATER of 5% or 120% of the
federal mid-term rate for either of the two months preceding the first
distribution — so 5% is always allowed.

Life expectancy: Single Life Table, Treas. Reg. §1.401(a)(9)-9(b) (post-2022
values, effective Jan 1 2022). Age = owner's age on their birthday in the
first distribution year. Verified against the IRS worked example: age 50,
$400,000, 4% → 36.2 years → $21,102/yr.

Pure module-level functions — no DB, no engine class.
"""

from __future__ import annotations

SEPP_RATE_FLOOR = 0.05  # Notice 2022-6 §3.02(c): cap = max(5%, 120% mid-term AFR)

# Single Life Expectancy — Treas. Reg. §1.401(a)(9)-9(b), 2022 and thereafter.
# (IRS Pub 590-B Table I. NOT the pre-2022 table: e.g. age 50 is 36.2, not 34.2.)
SINGLE_LIFE_EXPECTANCY: dict[int, float] = {
    0: 84.6, 1: 83.7, 2: 82.8, 3: 81.8, 4: 80.8, 5: 79.8, 6: 78.8, 7: 77.9,
    8: 76.9, 9: 75.9, 10: 74.9, 11: 73.9, 12: 72.9, 13: 71.9, 14: 70.9,
    15: 69.9, 16: 69.0, 17: 68.0, 18: 67.0, 19: 66.0, 20: 65.0, 21: 64.1,
    22: 63.1, 23: 62.1, 24: 61.1, 25: 60.2, 26: 59.2, 27: 58.2, 28: 57.3,
    29: 56.3, 30: 55.3, 31: 54.4, 32: 53.4, 33: 52.5, 34: 51.5, 35: 50.5,
    36: 49.6, 37: 48.6, 38: 47.7, 39: 46.7, 40: 45.7, 41: 44.8, 42: 43.8,
    43: 42.9, 44: 41.9, 45: 41.0, 46: 40.0, 47: 39.0, 48: 38.1, 49: 37.1,
    50: 36.2, 51: 35.3, 52: 34.3, 53: 33.4, 54: 32.5, 55: 31.6, 56: 30.6,
    57: 29.8, 58: 28.9, 59: 28.0, 60: 27.1, 61: 26.2, 62: 25.4, 63: 24.5,
    64: 23.7, 65: 22.9, 66: 22.0, 67: 21.2, 68: 20.4, 69: 19.6, 70: 18.8,
    71: 18.0, 72: 17.2, 73: 16.4, 74: 15.6, 75: 14.8, 76: 14.1, 77: 13.3,
    78: 12.6, 79: 11.9, 80: 11.2, 81: 10.5, 82: 9.9, 83: 9.3, 84: 8.7,
    85: 8.1, 86: 7.6, 87: 7.1, 88: 6.6, 89: 6.1, 90: 5.7, 91: 5.3, 92: 4.9,
    93: 4.6, 94: 4.3, 95: 4.0, 96: 3.7, 97: 3.4, 98: 3.2, 99: 3.0, 100: 2.8,
    101: 2.6, 102: 2.5, 103: 2.3, 104: 2.2, 105: 2.1, 106: 2.1, 107: 2.1,
    108: 2.0, 109: 2.0, 110: 2.0, 111: 2.0, 112: 2.0, 113: 1.9, 114: 1.9,
    115: 1.8, 116: 1.8, 117: 1.6, 118: 1.4, 119: 1.1, 120: 1.0,
}


def max_sepp_rate(afr_120_mid_term: float | None = None) -> float:
    """Highest rate the IRS allows: greater of 5% or 120% of the mid-term AFR."""
    return max(SEPP_RATE_FLOOR, afr_120_mid_term or 0.0)


def single_life_expectancy(age: int) -> float:
    """Single Life Table entry for the owner's age in the first distribution year."""
    try:
        return SINGLE_LIFE_EXPECTANCY[age]
    except KeyError:
        raise ValueError(f"age {age} outside the Single Life Table (0-120)") from None


def _amortization_factor(age: int, rate: float) -> float:
    """Present-value factor of a level annual payment over the life expectancy."""
    n = single_life_expectancy(age)
    if rate == 0:
        return n
    return (1 - (1 + rate) ** -n) / rate


def amortization_payment(balance: float, age: int, rate: float) -> float:
    """Fixed amortization method: annual payment, constant for the series."""
    return balance / _amortization_factor(age, rate)


def rmd_method_payment(balance: float, age: int) -> float:
    """RMD method: year-1 annual payment (balance ÷ life expectancy).

    Under this method the payment is redetermined every year from the new
    balance and that year's life expectancy — this is the first year only.
    """
    return balance / single_life_expectancy(age)


def required_balance_for_payment(annual_payment: float, age: int, rate: float) -> float:
    """Reverse amortization — the dual-IRA split solver.

    The IRA-A balance that yields exactly this annual payment under the fixed
    amortization method; the rest of the IRA stays in IRA-B, untouched.
    """
    return annual_payment * _amortization_factor(age, rate)


def compute_sepp(
    balance: float,
    age: int,
    rate: float,
    target_monthly: float | None = None,
    afr_120_mid_term: float | None = None,
) -> dict:
    """All-methods SEPP calculation + optional reverse solve.

    Raises ValueError when the rate exceeds the IRS cap or the age is outside
    the Single Life Table.
    """
    cap = max_sepp_rate(afr_120_mid_term)
    if rate > cap + 1e-9:
        raise ValueError(
            f"rate {rate:.4f} exceeds the IRS cap of {cap:.4f} "
            f"(greater of 5% or 120% of the federal mid-term rate — Notice 2022-6)"
        )
    if rate < 0:
        raise ValueError("rate must be non-negative")
    if balance <= 0:
        raise ValueError("balance must be positive")

    life_expectancy = single_life_expectancy(age)
    amort_annual = amortization_payment(balance, age, rate)
    rmd_annual = rmd_method_payment(balance, age)

    reverse = None
    if target_monthly is not None and target_monthly > 0:
        required = required_balance_for_payment(target_monthly * 12, age, rate)
        reverse = {
            "target_monthly": round(target_monthly, 2),
            "required_balance": round(required, 2),
        }

    return {
        "balance": round(balance, 2),
        "age": age,
        "rate": rate,
        "max_rate": round(cap, 6),
        "life_expectancy": life_expectancy,
        "amortization": {
            "annual": round(amort_annual, 2),
            "monthly": round(amort_annual / 12, 2),
        },
        "rmd_method": {
            "annual": round(rmd_annual, 2),
            "monthly": round(rmd_annual / 12, 2),
        },
        "annuitization": None,  # v1: amortization is the max-payment method
        "reverse": reverse,
        "assumptions": {
            "life_expectancy_table": "Single Life Table, Treas. Reg. §1.401(a)(9)-9(b) (post-2022)",
            "rate_cap_rule": "max(5%, 120% of federal mid-term rate) — IRS Notice 2022-6 §3.02(c)",
            "age_convention": "owner's age on their birthday in the first distribution year",
            "annuitization_note": "fixed annuitization not implemented in v1; amortization yields the highest payment",
        },
    }
