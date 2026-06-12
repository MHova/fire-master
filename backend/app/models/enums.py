import enum


class AccountType(str, enum.Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    FOUR_OH_ONE_K = "401k"
    IRA = "ira"
    ROTH_IRA = "roth_ira"
    TAXABLE = "taxable"
    HSA = "hsa"
    REAL_ESTATE = "real_estate"
    CRYPTO = "crypto"
    CREDIT_CARD = "CREDIT_CARD"
    VEHICLE = "VEHICLE"
    PRIVATE = "PRIVATE"
    OTHER = "other"


class DataSource(str, enum.Enum):
    MONARCH = "monarch"
    PROJECTION_LAB = "projection_lab"
    FIRE_TRADING = "fire_trading"
    MANUAL = "manual"


class AssetCategory(str, enum.Enum):
    REAL_ESTATE = "real_estate"
    VEHICLE = "vehicle"
    PRIVATE_INVESTMENT = "private_investment"


class AspirationPriority(str, enum.Enum):
    MUST_HAVE = "must_have"
    NICE_TO_HAVE = "nice_to_have"
    DREAM = "dream"


class AspirationStatus(str, enum.Enum):
    PLANNED = "planned"
    APPROVED = "approved"
    PURCHASED = "purchased"
    CANCELLED = "cancelled"


class IncomeType(str, enum.Enum):
    SALARY = "salary"
    BONUS = "bonus"
    RENTAL = "rental"
    DIVIDEND = "dividend"
    SIDE_HUSTLE = "side_hustle"
    SOCIAL_SECURITY = "social_security"
    PENSION = "pension"
    OTHER = "other"


class GoalType(str, enum.Enum):
    NET_WORTH_TARGET = "net_worth_target"
    SAVINGS_RATE_TARGET = "savings_rate_target"
    EXPENSE_REDUCTION = "expense_reduction"
    DEBT_PAYOFF = "debt_payoff"
    INCOME_TARGET = "income_target"
    RETIREMENT_DATE = "retirement_date"
    CUSTOM = "custom"


class GoalStatus(str, enum.Enum):
    ACTIVE = "active"
    ACHIEVED = "achieved"
    MISSED = "missed"
    CANCELLED = "cancelled"
