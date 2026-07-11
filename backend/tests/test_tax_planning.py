"""Tax-planning behavior tests: MAGI, ACA, Roth conversion ladder, withdrawal
sequencing.

These cover the higher-order planners that sit above the bracket primitives
(which test_tax_engine.py already covers). All DB access is mocked; balances
are given in DOLLARS in the helper for readability and converted to cents on
the account mocks.

Documented simplifications (asserted here as intended behavior, not bugs):
- ACA below 100% FPL still gets max subsidy (no Medicaid-gap modeling), and
  cliff_warning only fires on the *approaching* side of the 400% FPL cliff.
- The withdrawal sequencer reports taxes but does not deduct them from
  balances, and pre-retirement years take no withdrawals even if spending
  exceeds income (the plan starts working at retirement).
- total_withdrawn excludes cash draws (cash is already-taxed money; the
  average_effective_rate denominator is withdrawals with tax consequences).
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.tax_engine import (
    DEFAULT_STANDARD_DEDUCTION,
    AccountsByTaxTreatment,
    TaxEngine,
)
from app.models.enums import IncomeType

from .conftest import FROZEN_TODAY, _make_fire_config

STD_DED = DEFAULT_STANDARD_DEDUCTION["single"]  # 15,700
CEILING_22 = 103_350  # single-filer 22% bracket ceiling (2026 estimates)
STATE_RATE = 4.4  # persona tax config (CO)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def frozen_today_tax():
    """Patch date.today() in the tax engine to 2026-04-14."""
    with patch("app.engines.tax_engine.date") as mock_date:
        mock_date.today.return_value = FROZEN_TODAY
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        yield mock_date


def _acct(dollars: float) -> MagicMock:
    a = MagicMock()
    a.current_balance = round(dollars * 100)
    return a


def _income_source(name: str, itype: IncomeType, annual_dollars: float,
                   start=None, end=None) -> MagicMock:
    s = MagicMock()
    s.name = name
    s.income_type = itype
    s.annual_amount = round(annual_dollars * 100)
    s.start_date = start
    s.end_date = end
    s.is_active = True
    s.growth_rate = None
    return s


def _make_planning_engine(
    *, deferred=0.0, roth=0.0, taxable=0.0, cash=0.0, income_sources=(),
) -> TaxEngine:
    """TaxEngine with all DB access mocked (balances in DOLLARS)."""
    engine = TaxEngine(db=None)
    grouped = AccountsByTaxTreatment(
        tax_deferred=[_acct(deferred)] if deferred else [],
        tax_free=[_acct(roth)] if roth else [],
        taxable=[_acct(taxable)] if taxable else [],
        already_taxed=[_acct(cash)] if cash else [],
    )
    engine.get_accounts_by_tax_treatment = AsyncMock(return_value=grouped)
    engine._get_active_income_sources = AsyncMock(return_value=list(income_sources))
    return engine


def _patch_config(config):
    """TaxEngine constructs a FireProjectionsEngine internally for config."""
    return patch(
        "app.engines.fire_projections.FireProjectionsEngine.get_or_create_config",
        AsyncMock(return_value=config),
    )


# ---------------------------------------------------------------------------
# MAGI
# ---------------------------------------------------------------------------

class TestComputeMagi:
    def test_sums_all_components(self, tax_engine):
        magi = tax_engine.compute_magi(
            earned_income=50_000, pension=10_000, deferred_withdrawals=20_000,
            roth_conversions=30_000, capital_gains=5_000, rental_income=12_000,
            dividend_income=3_000,
        )
        assert magi == 130_000

    def test_ss_85pct_haircut(self, tax_engine):
        assert tax_engine.compute_magi(social_security=40_000) == pytest.approx(34_000)

    def test_zero_inputs_zero(self, tax_engine):
        assert tax_engine.compute_magi() == 0


# ---------------------------------------------------------------------------
# ACA subsidy eligibility
# ---------------------------------------------------------------------------

class TestACAEligibility:
    def test_household_size_scales_fpl(self, tax_engine):
        # FPL = 15,060 + 5,380 × (n − 1)
        assert tax_engine.compute_aca_eligibility(30_000, household_size=1).fpl == 15_060
        assert tax_engine.compute_aca_eligibility(30_000, household_size=4).fpl == 31_200

    def test_below_150_fpl_max_subsidy(self, tax_engine):
        r = tax_engine.compute_aca_eligibility(20_000, household_size=1, age=55)
        assert r.fpl_percentage < 150
        assert r.estimated_monthly_subsidy == pytest.approx(r.estimated_monthly_premium * 0.95)

    def test_subsidy_tiers_slide(self, tax_engine):
        # Same premium (fixed age), rising MAGI → monotonically non-increasing subsidy
        fpl = 15_060
        subsidies = [
            tax_engine.compute_aca_eligibility(fpl * pct / 100, household_size=1, age=55)
            .estimated_monthly_subsidy
            for pct in (140, 190, 240, 290, 390, 450)
        ]
        assert subsidies == sorted(subsidies, reverse=True)
        assert subsidies[-1] == 0  # above 400% FPL

    def test_at_400_fpl_still_eligible(self, tax_engine):
        r = tax_engine.compute_aca_eligibility(15_060 * 4, household_size=1)
        assert r.subsidy_eligible is True

    def test_above_400_fpl_not_eligible(self, tax_engine):
        r = tax_engine.compute_aca_eligibility(15_060 * 4 + 1, household_size=1)
        assert r.subsidy_eligible is False
        assert r.estimated_monthly_subsidy == 0

    def test_cliff_warning_approaching_side_only(self, tax_engine):
        cliff = 15_060 * 4
        # Just under the cliff → warn
        assert tax_engine.compute_aca_eligibility(cliff - 3_000).cliff_warning is True
        # Over the cliff → no warning (already fallen off)
        assert tax_engine.compute_aca_eligibility(cliff + 1_000).cliff_warning is False
        # Far below → no warning
        assert tax_engine.compute_aca_eligibility(20_000).cliff_warning is False

    def test_premium_age_clamps(self, tax_engine):
        assert tax_engine.compute_aca_eligibility(30_000, age=10).estimated_monthly_premium == 300
        assert tax_engine.compute_aca_eligibility(30_000, age=110).estimated_monthly_premium == 1_200


# ---------------------------------------------------------------------------
# Roth conversion ladder
# ---------------------------------------------------------------------------

class TestRothConversionPlan:
    async def test_no_dob_returns_empty_plan(self, frozen_today_tax):
        config = _make_fire_config(date_of_birth=None)
        engine = _make_planning_engine(deferred=500_000)
        with _patch_config(config):
            plan = await engine.plan_roth_conversions()
        assert plan.years == []
        assert plan.total_converted == 0
        assert "N/A" in plan.conversion_window

    async def test_window_closed_after_ss_start(self, frozen_today_tax):
        # DOB 1953 → SS start (67) was 2020, long before the frozen today.
        config = _make_fire_config(date_of_birth=date(1953, 6, 1))
        engine = _make_planning_engine(deferred=500_000)
        with _patch_config(config):
            plan = await engine.plan_roth_conversions()
        assert plan.years == []
        assert "No conversion window" in plan.conversion_window

    async def test_fills_to_bracket_ceiling(self, base_fire_config, frozen_today_tax):
        """With zero baseline income the conversion absorbs the unused standard
        deduction: converted = ceiling + std_ded, post-deduction taxable lands
        exactly at the 22% ceiling."""
        engine = _make_planning_engine(deferred=2_000_000)
        with _patch_config(base_fire_config):
            plan = await engine.plan_roth_conversions(target_bracket_rate=0.22)
        # Window: retirement (2026-07) → SS start (2040-07) = 14 annual rungs
        assert len(plan.years) == 14
        first = plan.years[0]
        assert first.conversion_amount == pytest.approx(CEILING_22 + STD_DED)
        assert first.total_taxable_income == pytest.approx(CEILING_22)

    async def test_respects_deferred_balance(self, base_fire_config, frozen_today_tax):
        engine = _make_planning_engine(deferred=150_000)
        with _patch_config(base_fire_config):
            plan = await engine.plan_roth_conversions()
        assert plan.total_converted == pytest.approx(150_000)
        assert len(plan.years) == 2  # 119,050 then the 30,950 remainder

    async def test_zero_room_years_skipped(self, base_fire_config, frozen_today_tax):
        # Baseline (rental) income above ceiling + deduction → no room, ever.
        big_rental = _income_source("Rental", IncomeType.RENTAL, 150_000)
        engine = _make_planning_engine(deferred=500_000, income_sources=[big_rental])
        with _patch_config(base_fire_config):
            plan = await engine.plan_roth_conversions(target_bracket_rate=0.22)
        assert plan.years == []
        assert plan.total_converted == 0

    async def test_per_year_tax_is_marginal_delta(self, base_fire_config, frozen_today_tax, tax_engine):
        """Year tax = federal(baseline+conversion−ded) − federal(baseline−ded)
        + state on the conversion, recomputed via the tested primitives."""
        rental = _income_source("Rental", IncomeType.RENTAL, 30_000)
        engine = _make_planning_engine(deferred=2_000_000, income_sources=[rental])
        with _patch_config(base_fire_config):
            plan = await engine.plan_roth_conversions(target_bracket_rate=0.22)
        yr = plan.years[0]
        assert yr.conversion_amount == pytest.approx(CEILING_22 + STD_DED - 30_000)
        fed_with = tax_engine.compute_federal_tax(max(0, 30_000 + yr.conversion_amount - STD_DED)).total_federal_tax
        fed_without = tax_engine.compute_federal_tax(max(0, 30_000 - STD_DED)).total_federal_tax
        expected = fed_with - fed_without + tax_engine.compute_state_tax(yr.conversion_amount, STATE_RATE)
        assert yr.tax_on_conversion == pytest.approx(expected, abs=0.01)

    async def test_savings_uses_config_rmd_rate(self, frozen_today_tax):
        config = _make_fire_config()
        config.custom_assumptions["tax"] = {
            **config.custom_assumptions["tax"],
            "assumed_rmd_marginal_rate": 0.32,
        }
        engine = _make_planning_engine(deferred=300_000)
        with _patch_config(config):
            plan = await engine.plan_roth_conversions()
        assert plan.assumed_rmd_marginal_rate == 0.32
        expected = round(max(0, plan.total_converted * 0.32 - plan.total_tax_paid), 2)
        assert plan.estimated_tax_saved == pytest.approx(expected, abs=0.02)


# ---------------------------------------------------------------------------
# Withdrawal sequencing
# ---------------------------------------------------------------------------

class TestWithdrawalSequence:
    async def test_waterfall_order_taxable_first(self, base_fire_config, frozen_today_tax):
        engine = _make_planning_engine(taxable=800_000, deferred=400_000, roth=200_000)
        with _patch_config(base_fire_config):
            plan = await engine.optimize_withdrawal_sequence(
                years=3, roth_conversions_enabled=False)
        # Year 0 (2026): retirement is 2026-07, plan year starts Jan 1 → not
        # yet retired, no withdrawals (documented simplification).
        assert plan.years[0].from_taxable == 0
        # Year 1: taxable covers the whole need; nothing from deferred/Roth.
        y1 = plan.years[1]
        assert y1.from_taxable == pytest.approx(153_000 * 1.03, rel=1e-6)
        assert y1.from_deferred == 0
        assert y1.from_roth == 0
        assert y1.capital_gains_income == pytest.approx(y1.from_taxable * 0.4)

    async def test_depletion_cascades(self, base_fire_config, frozen_today_tax):
        engine = _make_planning_engine(taxable=150_000, deferred=300_000, roth=500_000)
        with _patch_config(base_fire_config):
            plan = await engine.optimize_withdrawal_sequence(
                years=4, roth_conversions_enabled=False)
        y1, y2 = plan.years[1], plan.years[2]
        # Year 1 drains most of taxable (150k grew 7% in year 0).
        assert y1.from_taxable == pytest.approx(153_000 * 1.03, rel=1e-6)
        assert y1.from_deferred == 0
        # Year 2: taxable remainder first, then deferred picks up the rest.
        need_y2 = 153_000 * 1.03**2
        assert 0 < y2.from_taxable < need_y2
        assert y2.from_deferred == pytest.approx(need_y2 - y2.from_taxable, rel=1e-6)

    async def test_rmd_forced_at_73_excess_lands_in_taxable(self, frozen_today_tax):
        """Age 73+: the full RMD comes out of deferred even when spending needs
        far less, and the unspent excess is redeposited into taxable — visible
        as taxable draws in the following year (pre-fix, taxable stayed 0 and
        the excess RMD simply vanished from the model)."""
        config = _make_fire_config(
            date_of_birth=date(1953, 6, 1),  # age 73.6 in plan year 2027
            target_annual_spending=3_000_000,  # $30K — far below the RMD
            social_security_monthly=None,
        )
        engine = _make_planning_engine(deferred=2_000_000)
        with _patch_config(config):
            plan = await engine.optimize_withdrawal_sequence(
                years=3, roth_conversions_enabled=False)
        y0, y1, y2 = plan.years[0], plan.years[1], plan.years[2]
        # 2026 (age 72.6): below RMD age → draws only what spending needs.
        assert y0.from_deferred == pytest.approx(30_000)
        # 2027 (73.6): RMD divisor 26.5 forces the minimum on the post-draw
        # balance (model simplification vs the IRS prior-Dec-31 basis).
        need_y1 = 30_000 * 1.03
        deferred_after_draw = (2_000_000 - 30_000) * 1.07 - need_y1
        assert y1.from_deferred == pytest.approx(deferred_after_draw / 26.5, rel=1e-6)
        assert y1.from_deferred > need_y1
        # 2028: spending is drawn from taxable — the redeposited RMD excess.
        assert y2.from_taxable == pytest.approx(30_000 * 1.03**2, rel=1e-6)

    async def test_roth_conversion_fills_bracket_in_window(self, base_fire_config, frozen_today_tax):
        engine = _make_planning_engine(taxable=800_000, deferred=400_000)
        with _patch_config(base_fire_config):
            plan = await engine.optimize_withdrawal_sequence(years=3)
        y1 = plan.years[1]  # 2027: retired, pre-SS (2040), pre-RMD
        # Zero other ordinary income → conversion = ceiling + std deduction,
        # landing post-deduction taxable exactly at the 22% ceiling.
        assert y1.roth_conversion == pytest.approx(CEILING_22 + STD_DED)
        assert y1.ordinary_income - STD_DED == pytest.approx(CEILING_22)
        # Toggle off → no conversions anywhere.
        with _patch_config(base_fire_config):
            plan_off = await engine.optimize_withdrawal_sequence(
                years=3, roth_conversions_enabled=False)
        assert all(y.roth_conversion == 0 for y in plan_off.years)

    async def test_year_tax_matches_primitives(self, base_fire_config, frozen_today_tax, tax_engine):
        engine = _make_planning_engine(taxable=800_000, deferred=400_000)
        with _patch_config(base_fire_config):
            plan = await engine.optimize_withdrawal_sequence(years=2)
        y1 = plan.years[1]
        taxable_income = max(0, y1.ordinary_income - STD_DED)
        fed = tax_engine.compute_federal_tax(taxable_income).total_federal_tax
        cg = tax_engine.compute_capital_gains_tax(y1.capital_gains_income, taxable_income)
        state = tax_engine.compute_state_tax(
            y1.ordinary_income + y1.capital_gains_income - STD_DED, STATE_RATE)
        assert y1.federal_tax == pytest.approx(fed + cg, abs=0.02)
        assert y1.state_tax == pytest.approx(state, abs=0.02)
        assert y1.fica_tax == 0  # no earned income in retirement
        assert y1.total_tax == pytest.approx(fed + cg + state, abs=0.05)

    async def test_totals_consistent(self, base_fire_config, frozen_today_tax):
        engine = _make_planning_engine(taxable=500_000, deferred=300_000, roth=200_000)
        with _patch_config(base_fire_config):
            plan = await engine.optimize_withdrawal_sequence(years=5)
        total_drawn = sum(y.from_taxable + y.from_deferred + y.from_roth for y in plan.years)
        total_tax = sum(y.total_tax for y in plan.years)
        assert plan.total_withdrawn == pytest.approx(total_drawn, abs=0.05)
        assert plan.total_tax_paid == pytest.approx(total_tax, abs=0.05)
        if total_drawn > 0:
            assert plan.average_effective_rate == pytest.approx(total_tax / total_drawn, abs=1e-4)
