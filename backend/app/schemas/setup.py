from pydantic import BaseModel


class SetupStatusResponse(BaseModel):
    """One read-only call that tells an agent (or the UI) what's configured.

    `state` is the install lifecycle: empty | demo | half_onboarded | onboarded.
    `next_steps` is ordered — do them top to bottom.
    """

    state: str
    demo_mode: bool  # hosted-demo hard lock (Monarch sync disabled)
    demo_persona: bool  # config still carries the seeded persona sentinel
    accounts_total: int
    accounts_monarch: int
    accounts_with_fire_role: int
    unknown_fire_roles: list[str]  # roles set on accounts but not in the vocabulary (typos)
    valid_fire_roles: dict[str, list[str]]  # grouped vocabulary — these are ALL the values
    config_present: bool
    config_updated_at: str | None  # projections run on config-side pools; staleness matters
    sepp_configured: bool  # retirement money enters projections ONLY through this block
    properties: int
    property_rules: int
    scenarios_total: int
    active_scenario: str | None
    income_sources_active: int
    next_steps: list[str]
