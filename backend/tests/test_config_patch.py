"""Config PATCH regression tests — prevents the Apr 14 data-wipe bug.

The bug: saving from the config page sent nullable fields as null when the
form was empty, overwriting target_annual_spending, social_security_monthly,
and healthcare_monthly_cost to NULL on every save. Also: parseFloat("0") || 2
treated zero as falsy, silently replacing 0% rates with fallback defaults.

These tests verify the Pydantic schema + setattr pattern at the heart of the
PATCH endpoint, with zero DB or server dependency.
"""

from app.models.fire_config import FireConfig
from app.schemas.fire import FireConfigUpdate


class TestExcludeUnset:
    """Verify model_dump(exclude_unset=True) correctly distinguishes
    'field not sent' from 'field explicitly sent as null'."""

    def test_partial_update_excludes_absent_fields(self):
        """PATCH with only safe_withdrawal_rate should NOT include spending/SS/healthcare."""
        update = FireConfigUpdate(safe_withdrawal_rate=3.5)
        dump = update.model_dump(exclude_unset=True)
        assert "safe_withdrawal_rate" in dump
        assert dump["safe_withdrawal_rate"] == 3.5
        # These must NOT be in the dump — they weren't sent
        assert "target_annual_spending" not in dump
        assert "social_security_monthly" not in dump
        assert "healthcare_monthly_cost" not in dump
        assert "custom_assumptions" not in dump

    def test_explicit_null_is_included(self):
        """When a field is explicitly sent as None, it SHOULD appear in the dump."""
        update = FireConfigUpdate(**{"target_annual_spending": None, "safe_withdrawal_rate": 3.5})
        dump = update.model_dump(exclude_unset=True)
        assert "target_annual_spending" in dump
        assert dump["target_annual_spending"] is None

    def test_custom_assumptions_included_when_sent(self):
        """custom_assumptions should be in dump when explicitly provided."""
        ca = {"projection": {"re_appreciation_rate": 0.0}}
        update = FireConfigUpdate(**{"custom_assumptions": ca})
        dump = update.model_dump(exclude_unset=True)
        assert "custom_assumptions" in dump
        assert dump["custom_assumptions"]["projection"]["re_appreciation_rate"] == 0.0


class TestSetAttrPreservesFields:
    """Verify the PATCH endpoint's setattr loop doesn't wipe existing values."""

    def test_partial_update_preserves_existing(self, base_fire_config: FireConfig):
        """Changing one field must not null out other fields."""
        update = FireConfigUpdate(safe_withdrawal_rate=3.5)
        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(base_fire_config, field, value)

        # Changed field updated
        assert base_fire_config.safe_withdrawal_rate == 3.5
        # Critical fields preserved (the Apr 14 bug wiped these)
        assert base_fire_config.target_annual_spending == 15_300_000
        assert base_fire_config.social_security_monthly == 465_000
        assert base_fire_config.healthcare_monthly_cost == 60_000

    def test_custom_assumptions_with_zero_values(self, base_fire_config: FireConfig):
        """Zero-value rates must survive the setattr round-trip (the || fallback bug)."""
        ca = dict(base_fire_config.custom_assumptions)
        ca["projection"] = {**ca["projection"], "re_appreciation_rate": 0.0, "cash_savings_rate_late": 0.0}

        update = FireConfigUpdate(**{"custom_assumptions": ca})
        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(base_fire_config, field, value)

        proj = base_fire_config.custom_assumptions["projection"]
        assert proj["re_appreciation_rate"] == 0.0
        assert proj["cash_savings_rate_late"] == 0.0

    def test_full_save_round_trip(self, base_fire_config: FireConfig):
        """Simulate a full config page save with all projection fields."""
        # The frontend builds the full custom_assumptions dict on every save
        ca = dict(base_fire_config.custom_assumptions)
        ca["projection"] = {
            "surplus_investment_rate": 0.04,
            "cash_reserve_months": 12,
            "cash_savings_rate_early": 0.01,
            "cash_savings_rate_late": 0.0,  # zero — must not become 0.02
            "cash_savings_cutover_month": 60,
            "re_appreciation_rate": 0.0,  # zero — must not become 0.02
            "primary_property_purchase_price": 510_000,
            "primary_property_agent_fee_pct": 0.06,
            "primary_property_mortgage_pi": 3_100,
            "ss_early_reduction": 0.70,
            "ss_claim_age": 62,
            "spending_phase_slow": 0.85,
            "spending_phase_floor": 0.75,
            "spending_phase_slow_age": 70,
            "spending_phase_floor_age": 80,
            "ira_b_draw_threshold_months": 12,
        }

        update = FireConfigUpdate(**{
            "safe_withdrawal_rate": 4.0,
            "custom_assumptions": ca,
        })
        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(base_fire_config, field, value)

        proj = base_fire_config.custom_assumptions["projection"]
        assert proj["re_appreciation_rate"] == 0.0
        assert proj["cash_savings_rate_late"] == 0.0
        assert proj["surplus_investment_rate"] == 0.04
        # Non-projection fields preserved
        assert base_fire_config.target_annual_spending == 15_300_000
        assert base_fire_config.social_security_monthly == 465_000
