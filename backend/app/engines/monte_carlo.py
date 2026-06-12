"""Monte Carlo simulation engine for FIRE projections."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.fire_projections import SS_COLA_RATE, _spending_multiplier
from app.schemas.tax import MonteCarloResponse, PercentileCurvePoint

logger = logging.getLogger(__name__)

# Historical S&P 500 annual returns (real, inflation-adjusted) 1928-2024
# Mean ~7%, std dev ~16% (nominal ~10%, std dev ~16%)
HISTORICAL_MEAN_REAL = 0.07
HISTORICAL_STD_DEV = 0.16


@dataclass
class SimulationRun:
    """Result of a single Monte Carlo run."""
    final_net_worth: float
    money_lasted: bool
    yearly_net_worths: list[float]  # net worth at each year


class MonteCarloEngine:
    """Monte Carlo simulation wrapper around the FIRE projections engine."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_simulation(
        self,
        n_runs: int = 1000,
        seed: int | None = None,
    ) -> MonteCarloResponse:
        """Run N Monte Carlo simulations with randomized annual returns.

        Each run uses the same config/spending/income but draws random
        annual return rates from a normal distribution matching historical
        stock market performance. This captures sequence-of-returns risk.
        """
        from app.engines.fire_projections import FireProjectionsEngine
        from app.engines.net_worth import NetWorthEngine

        fire_engine = FireProjectionsEngine(self.db)
        config = await fire_engine.get_or_create_config()
        nw_engine = NetWorthEngine(self.db)
        nw = await nw_engine.calculate_current()

        current_nw = nw.net_worth  # already in dollars
        annual_spending_cents = await fire_engine._get_annual_spending(config)
        annual_spending = annual_spending_cents / 100
        income_sources = await fire_engine._get_income_sources()

        retirement_date = fire_engine._get_retirement_date(config)
        today = date.today()

        if config.date_of_birth:
            end_date = config.date_of_birth + relativedelta(years=config.life_expectancy)
        else:
            end_date = today + relativedelta(years=40)

        total_years = max(1, (end_date.year - today.year))
        years_to_retirement = 0
        if retirement_date and retirement_date > today:
            years_to_retirement = max(0, (retirement_date.year - today.year))

        # Mean real return from config (or historical default)
        mean_return = (config.expected_annual_return - config.expected_inflation_rate) / 100
        std_dev = HISTORICAL_STD_DEV

        inflation = config.expected_inflation_rate / 100

        # Social Security and pension (annual, in dollars)
        ss_annual = 0.0
        if config.social_security_monthly:
            ss_annual = config.social_security_monthly * 12 / 100
        ss_start_year = 0
        if config.date_of_birth:
            ss_start_date = config.date_of_birth + relativedelta(years=config.social_security_start_age)
            ss_start_year = max(0, ss_start_date.year - today.year)

        pension_annual = 0.0
        if config.pension_monthly:
            pension_annual = config.pension_monthly * 12 / 100
        pension_start_year = 0
        if config.pension_start_age and config.date_of_birth:
            pension_start_date = config.date_of_birth + relativedelta(years=config.pension_start_age)
            pension_start_year = max(0, pension_start_date.year - today.year)

        # Pre-compute income from sources by category
        earned_annual = 0.0  # stops at retirement
        continuing_annual = 0.0  # rental, dividends, etc. — continues post-retirement
        for src in income_sources:
            if not src.is_active:
                continue
            if src.income_type.value in ("salary", "bonus", "side_hustle"):
                earned_annual += src.annual_amount / 100
            else:
                continuing_annual += src.annual_amount / 100

        # Compute starting age for spending phase lookup
        start_age = fire_engine._compute_age(config, today) if config.date_of_birth else 30

        if seed is not None:
            random.seed(seed)

        # Run simulations
        runs: list[SimulationRun] = []
        for _ in range(n_runs):
            nw_val = current_nw * 100  # work in cents for consistency
            yearly_nw: list[float] = [current_nw]
            money_lasted = True

            for yr in range(total_years):
                # Random annual return
                annual_return = random.gauss(mean_return, std_dev)

                age = start_age + yr
                is_retired = yr >= years_to_retirement

                # Spending (inflation-adjusted + retirement phase reduction)
                yr_spending = annual_spending * ((1 + inflation) ** yr)
                if is_retired:
                    yr_spending *= _spending_multiplier(age)

                # Income
                yr_income = continuing_annual * ((1 + inflation) ** yr)

                if not is_retired:
                    yr_income += earned_annual * ((1 + inflation) ** yr)

                # SS with COLA (~2.5%/yr from start)
                if yr >= ss_start_year:
                    ss_years_active = yr - ss_start_year
                    yr_income += ss_annual * ((1 + SS_COLA_RATE) ** ss_years_active)
                # Pension with COLA
                if yr >= pension_start_year:
                    pension_years_active = yr - pension_start_year
                    yr_income += pension_annual * ((1 + SS_COLA_RATE) ** pension_years_active)

                # Net cash flow
                net_cash = yr_income - yr_spending

                # Apply return + cash flow (all in dollars)
                nw_dollars = nw_val / 100
                nw_dollars = nw_dollars * (1 + annual_return) + net_cash
                nw_val = nw_dollars * 100

                yearly_nw.append(round(nw_dollars, 2))

                if nw_val < 0:
                    money_lasted = False
                    # Pad remaining years with negative values
                    for _ in range(yr + 1, total_years):
                        yearly_nw.append(round(nw_val / 100, 2))
                    break

            runs.append(SimulationRun(
                final_net_worth=round(nw_val / 100, 2),
                money_lasted=money_lasted,
                yearly_net_worths=yearly_nw,
            ))

        # Compute results
        finals = sorted(r.final_net_worth for r in runs)
        success_count = sum(1 for r in runs if r.money_lasted)

        # Percentile curves (year-by-year percentiles)
        curves: list[PercentileCurvePoint] = []
        for yr in range(total_years + 1):
            values = sorted(r.yearly_net_worths[yr] for r in runs if yr < len(r.yearly_net_worths))
            if not values:
                break
            n = len(values)
            curves.append(PercentileCurvePoint(
                age=round(start_age + yr, 1),
                p10=round(values[int(n * 0.10)], 2),
                p25=round(values[int(n * 0.25)], 2),
                p50=round(values[int(n * 0.50)], 2),
                p75=round(values[int(n * 0.75)], 2),
                p90=round(values[min(int(n * 0.90), n - 1)], 2),
            ))

        return MonteCarloResponse(
            success_rate=round(success_count / n_runs * 100, 1),
            percentile_10=round(finals[int(n_runs * 0.10)], 2),
            percentile_25=round(finals[int(n_runs * 0.25)], 2),
            percentile_50=round(finals[int(n_runs * 0.50)], 2),
            percentile_75=round(finals[int(n_runs * 0.75)], 2),
            percentile_90=round(finals[min(int(n_runs * 0.90), n_runs - 1)], 2),
            mean_final_nw=round(sum(finals) / n_runs, 2),
            total_runs=n_runs,
            percentile_curves=curves,
            worst_final_nw=round(finals[0], 2),
            best_final_nw=round(finals[-1], 2),
        )
