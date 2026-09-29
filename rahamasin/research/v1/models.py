# Frozen v1 audit reference. Never imported by live analysis.
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
    min_rr: float = 1.8
    risk_pct: float = 1.0
    pivot_span: int = 3
    lookback: int = 500
    zone_atr: float = 0.45
    stop_atr: float = 0.2
    min_touches: int = 2
    max_hold_days: int = 7
    fee_bps: float = 10
    slippage_bps: float = 5

    def __post_init__(self):
        if not (0 < self.min_rr <= 20 and 0 < self.risk_pct <= 10):
            raise ValueError("R:R must be 0–20 and risk must be 0–10%, exclusive of zero")
        if not (1 <= self.pivot_span <= 20 and self.lookback >= 50):
            raise ValueError("Invalid pivot span or lookback")
        if min(self.zone_atr, self.stop_atr) <= 0 or self.min_touches < 1:
            raise ValueError("Zone, buffer and touches must be positive")
        if self.max_hold_days < 1 or min(self.fee_bps, self.slippage_bps) < 0:
            raise ValueError("Invalid holding period or costs")

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
