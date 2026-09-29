# Frozen v1 audit reference. Never imported by live analysis.
from .models import Setup, Config
from .levels import atr, detect_zones


class Strategy:
    def __init__(self, config=None):
        self.config = config or Config()

    def analyze(self, candles, as_of=None):
        # Filter first. Neither pivots nor ATR ever see a bar after as_of.
        history = [c for c in candles if as_of is None or c.time <= as_of]
        history = history[-self.config.lookback:]
        if len(history) < 40:
            return Setup(reasons=["At least 40 closed candles are required."]), []
        intervals = [b.time-a.time for a,b in zip(history,history[1:])]
        if min(intervals) <= 0 or len(set(intervals)) != 1:
            return Setup(reasons=["Candle history has gaps or is not chronological; refresh complete data before analysis."]), []
        # Levels are frozen BEFORE the confirmation candle.
        zones = detect_zones(history[:-1], self.config)
        return self.evaluate(history, zones), zones

    def evaluate(self, history, zones):
        c, prev = history[-1], history[-2]
        v = atr(history[:-1])
        major = [z for z in zones if z.touches >= self.config.min_touches]
        supports = [z for z in major if z.midpoint <= c.close]
        resistances = [z for z in major if z.midpoint > c.close]
        long_zone = max(supports, key=lambda z: z.midpoint, default=None)
        short_zone = min(resistances, key=lambda z: z.midpoint, default=None)
        idle = Setup(signal_time=c.time, long_zone=long_zone, short_zone=short_zone,
                     reasons=["No confirmed historical-zone rejection with acceptable reward/risk."])
        candidates = []
        for direction, z in [("LONG", long_zone), ("SHORT", short_zone)]:
            if z is None or v <= 0:
                continue
            long = direction == "LONG"
            touched = c.low <= z.high and c.high >= z.low
            rejection = (c.close > z.high and c.close > c.open and c.close-c.low >= .6*(c.high-c.low)
                         if long else c.close < z.low and c.close < c.open and c.high-c.close >= .6*(c.high-c.low))
            failed = (c.low < z.low and c.close > z.high if long else c.high > z.high and c.close < z.low)
            if not touched or not rejection or abs(c.close-z.midpoint) > 1.5*v:
                continue
            targets = [a for a in major if a.low > max(z.high, c.close)] if long else [a for a in major if a.high < min(z.low, c.close)]
            target_zone = (min(targets, key=lambda a: a.low) if long else max(targets, key=lambda a: a.high)) if targets else None
            if target_zone is None:
                idle.reasons.append(f"{direction}: no opposing historical zone for a target.")
                continue
            entry = z.midpoint
            stop = min(z.low, c.low, prev.low)-v*self.config.stop_atr if long else max(z.high, c.high, prev.high)+v*self.config.stop_atr
            target = target_zone.low if long else target_zone.high
            risk, reward = abs(entry-stop), abs(target-entry)
            rr = reward/risk
            if stop <= 0 or rr < self.config.min_rr:
                idle.reasons.append(f"{direction}: R:R {rr:.2f} below required {self.config.min_rr:.2f}, or invalid stop.")
                continue
            reasons = [f"Historical zone {z.low:.5f}–{z.high:.5f}; {z.touches} distinct pivot touches.",
                f"Median completed reaction {z.median_reaction:.2f}% ({z.reaction_atr:.2f} ATR).",
                "Failed breakout and close back through zone." if failed else "Directional rejection closes beyond zone; close lies in outer 40% of candle.",
                f"Limit entry at historical zone midpoint {entry:.5f}; valid for the next candle only.",
                f"Stop beyond zone and two-bar extreme, plus {self.config.stop_atr:.2f} ATR.",
                f"One target at nearest opposing zone edge {target:.5f}; gross R:R {rr:.2f}."]
            candidates.append(Setup(direction,c.time,z.low,z.high,entry,stop,target,rr,reasons,z,long_zone,short_zone,
                                    "Failed breakout" if failed else "Zone rejection"))
        return max(candidates, key=lambda s: (s.zone.strength, s.rr), default=idle)
