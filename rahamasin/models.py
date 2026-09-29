from dataclasses import dataclass, field

SECONDS = {"1h": 3600, "4h": 14400, "1d": 86400}

@dataclass(frozen=True)
class Candle:
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0

@dataclass(frozen=True)
class Config:
    entry_mode: str = "confirmation"
    plan_max_distance_atr: float = 3.0
    plan_expiry_bars: int = 6
    min_rr: float = 1.8
    risk_pct: float = 1.0
    pivot_span: int = 3
    lookback: int = 500
    zone_atr: float = 0.45
    stop_atr: float = 0.25
    min_displacement: float = 1.5
    max_tests: int = 2
    confirmation_atr: float = 0.25
    max_hold_days: int = 7
    fee_bps: float = 10
    slippage_bps: float = 5

    def __post_init__(self):
        if self.entry_mode not in ("confirmation", "planned_limit"):
            raise ValueError("Invalid entry mode")
        if not 0 < self.plan_max_distance_atr <= 20 or not 1 <= self.plan_expiry_bars <= 100:
            raise ValueError("Invalid plan distance or expiry")
        if not (0 < self.min_rr <= 20 and 0 < self.risk_pct <= 10):
            raise ValueError("R:R must be 0–20 and risk must be 0–10%, exclusive of zero")
        if not (1 <= self.pivot_span <= 20 and self.lookback >= 50):
            raise ValueError("Invalid pivot span or lookback")
        if min(self.zone_atr, self.stop_atr, self.min_displacement, self.confirmation_atr) <= 0 or self.max_tests < 0:
            raise ValueError("Widths, displacement and confirmation must be positive; tests nonnegative")
        if self.max_hold_days < 1 or min(self.fee_bps, self.slippage_bps) < 0:
            raise ValueError("Invalid holding period or costs")

    @classmethod
    def from_dict(cls, values):
        # v1 settings remain readable; its minimum-touch requirement was removed.
        return cls(**{k:v for k,v in values.items() if k != 'min_touches'})

@dataclass
class Zone:
    low: float
    high: float
    touches: int
    successes: int
    average_reaction: float
    median_reaction: float
    reaction_atr: float
    last_time: int
    first_time: int
    support_reactions: int
    resistance_reactions: int
    flips: int
    strength: float
    age_bars: int
    recency_bars: int
    role: str = ''
    origin_role: str = ''
    created_time: int = 0
    breakout_time: int = 0
    retests: int = 0
    role_retests: int = 0
    penetrations: int = 0
    failed_holds: int = 0
    role_failed_holds: int = 0
    displacement_atr: float = 0.0
    departure_efficiency: float = 0.0
    seed_atr: float = 0.0
    in_touch: bool = False
    last_touch_time: int = 0

    @property
    def midpoint(self):
        return (self.low + self.high) / 2

@dataclass
class Setup:
    state: str = "NO TRADE"
    signal_time: int = 0
    entry_low: float | None = None
    entry_high: float | None = None
    entry: float | None = None
    stop: float | None = None
    target: float | None = None
    rr: float | None = None
    reasons: list[str] = field(default_factory=list)
    zone: Zone | None = None
    long_zone: Zone | None = None
    short_zone: Zone | None = None
    market_state: str = "Awaiting confirmed rejection"
    features: dict = field(default_factory=dict)
    target_zone: Zone | None = None
    pipeline: dict = field(default_factory=dict)

    @property
    def risk_distance(self):
        return abs(self.entry-self.stop) if self.entry is not None else None

    @property
    def reward_distance(self):
        return abs(self.target-self.entry) if self.entry is not None else None

@dataclass
class Trade:
    setup: Setup
    entry_time: int
    entry_price: float
    exit_time: int
    exit_price: float
    outcome: str
    r: float
    return_pct: float
    exit_reason: str
    gross_r: float | None = None
    fees_r: float | None = None
    slippage_r: float | None = None

@dataclass
class Result:
    trades: list[Trade]
    metrics: dict
    equity: list[tuple[int, float]]
    config: Config
    timeframe: str
    start: int
    end: int
    source: str
    strategy_version: str = 'v1'
    diagnostics: dict = field(default_factory=dict)
    evaluation: dict = field(default_factory=dict)
    mode_comparison: dict = field(default_factory=dict)
    pipeline: dict = field(default_factory=dict)
