"""SEPP / 72(t) calculator tests.

Anchored to the IRS's own worked example (irs.gov "Substantially equal
periodic payments", Notice 2022-6 era): age 50, $400,000, 4% → Single Life
expectancy 36.2, amortization factor 18.9559 → $21,102/yr. Our closed-form
factor is 18.9562 (the IRS example rounds intermediates), so we assert
within $2.
"""

import pytest

from app.engines.sepp import (
    SEPP_RATE_FLOOR,
    SINGLE_LIFE_EXPECTANCY,
    amortization_payment,
    compute_sepp,
    max_sepp_rate,
    required_balance_for_payment,
    rmd_method_payment,
    single_life_expectancy,
)


class TestIRSAnchors:
    def test_amortization_irs_worked_example(self):
        """IRS example: Bob, 50, $400K, 4% → 36.2 yrs, ≈$21,102/yr."""
        assert single_life_expectancy(50) == 36.2
        annual = amortization_payment(400_000, 50, 0.04)
        assert annual == pytest.approx(21_102, abs=2)

    def test_rmd_method_is_balance_over_le(self):
        assert rmd_method_payment(400_000, 50) == pytest.approx(400_000 / 36.2)


class TestAmortizationMath:
    def test_zero_rate_degenerates_to_straight_line(self):
        assert amortization_payment(400_000, 50, 0.0) == pytest.approx(400_000 / 36.2)

    def test_monthly_is_annual_over_12(self):
        result = compute_sepp(500_000, 53, 0.05)
        assert result["amortization"]["monthly"] == pytest.approx(
            result["amortization"]["annual"] / 12, abs=0.01)

    def test_reverse_roundtrip(self):
        """required_balance(amortization(B)) == B across ages and rates."""
        for age in (45, 50, 53, 55, 59, 65):
            for rate in (0.0, 0.03, 0.05):
                annual = amortization_payment(750_000, age, rate)
                back = required_balance_for_payment(annual, age, rate)
                assert back == pytest.approx(750_000, abs=0.01)

    def test_higher_rate_higher_payment(self):
        low = amortization_payment(400_000, 53, 0.02)
        high = amortization_payment(400_000, 53, 0.05)
        assert high > low


class TestRateCap:
    def test_five_percent_floor_always_allowed(self):
        assert max_sepp_rate(None) == SEPP_RATE_FLOOR
        assert max_sepp_rate(0.031) == SEPP_RATE_FLOOR  # low AFR → floor wins
        result = compute_sepp(400_000, 53, 0.05)  # exactly at cap: OK
        assert result["rate"] == 0.05

    def test_rate_above_cap_rejected(self):
        with pytest.raises(ValueError, match="exceeds the IRS cap"):
            compute_sepp(400_000, 53, 0.055)

    def test_high_afr_raises_cap(self):
        assert max_sepp_rate(0.062) == 0.062
        result = compute_sepp(400_000, 53, 0.06, afr_120_mid_term=0.062)
        assert result["max_rate"] == pytest.approx(0.062)

    def test_negative_rate_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            compute_sepp(400_000, 53, -0.01)


class TestTableAndShape:
    def test_table_boundary_ages(self):
        assert single_life_expectancy(0) == 84.6
        assert single_life_expectancy(120) == 1.0
        with pytest.raises(ValueError, match="outside the Single Life Table"):
            single_life_expectancy(121)

    def test_response_shape(self):
        result = compute_sepp(400_000, 53, 0.05, target_monthly=2_800)
        assert result["annuitization"] is None
        assert result["life_expectancy"] == 33.4
        assert set(result["amortization"]) == {"annual", "monthly"}
        assert result["reverse"]["target_monthly"] == 2_800
        assert result["reverse"]["required_balance"] == pytest.approx(
            required_balance_for_payment(2_800 * 12, 53, 0.05), abs=0.01)
        assert "life_expectancy_table" in result["assumptions"]
        # No reverse block when no target given
        assert compute_sepp(400_000, 53, 0.05)["reverse"] is None

    def test_zero_balance_rejected(self):
        with pytest.raises(ValueError, match="balance must be positive"):
            compute_sepp(0, 53, 0.05)

    def test_table_is_complete_and_monotonic(self):
        """Every age 0-120 present; LE strictly decreases until the flat tail."""
        assert set(SINGLE_LIFE_EXPECTANCY) == set(range(121))
        values = [SINGLE_LIFE_EXPECTANCY[a] for a in range(121)]
        assert all(a >= b for a, b in zip(values, values[1:]))
