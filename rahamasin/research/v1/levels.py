# Frozen v1 audit reference. Never imported by live analysis.
"""Causal pivots: a pivot is usable only after span right-hand bars close."""
from statistics import mean, median
from .models import Zone


def atr(candles, period=14):
    if len(candles) < 2:
        return 0.0
    return mean(max(c.high-c.low, abs(c.high-p.close), abs(c.low-p.close))
                for p, c in list(zip(candles, candles[1:]))[-period:])


def pivots(candles, span=3):
    points = []
    for i in range(span, len(candles)-span):
        c = candles[i]
        neighbors = candles[i-span:i] + candles[i+1:i+span+1]
        if c.low < min(x.low for x in neighbors):
            points.append((i, c.low, "support"))
        if c.high > max(x.high for x in neighbors):
            points.append((i, c.high, "resistance"))
    return points


def detect_zones(candles, config):
    candles = candles[-config.lookback:]
    volatility = atr(candles)
    if volatility <= 0:
        return []
    width = volatility * config.zone_atr
    clusters = []
    # Bounded diameter prevents chaining an entire price range into one zone.
    for point in sorted(pivots(candles, config.pivot_span), key=lambda p: p[1]):
        if clusters and point[1] - clusters[-1][0][1] <= width:
            clusters[-1].append(point)
        else:
            clusters.append([point])
    zones = []
    for cluster in clusters:
        ordered = sorted(cluster)
        # Separate touch episodes by pivot span; adjacent bars aren't extra tests.
        distinct = []
        for p in ordered:
            if not distinct or p[0] - distinct[-1][0] > config.pivot_span:
                distinct.append(p)
        reactions, normalized, sides = [], [], []
        for i, price, side in distinct:
            future = candles[i+1:i+config.pivot_span+1]
            move = (max(c.high for c in future)-price if side == "support"
                    else price-min(c.low for c in future))
            local_atr = atr(candles[:i+1]) or volatility
            reactions.append(move/price*100)
            normalized.append(move/local_atr)
            sides.append(side)
        if not distinct:
            continue
        success = sum(r >= 1 for r in normalized)
        recency = len(candles)-1-distinct[-1][0]
        flips = sum(a != b for a, b in zip(sides, sides[1:]))
        # Each component is displayed/documented; no opaque trained score.
        strength = (min(len(distinct), 8)*5 + success/len(distinct)*20
                    + min(median(normalized), 3)*10 + 10/(1+recency/50))
        prices = [p[1] for p in cluster]
        zones.append(Zone(min(prices)-width*.15, max(prices)+width*.15,
            len(distinct), success, mean(reactions), median(reactions),
            median(normalized), candles[distinct[-1][0]].time,
            candles[distinct[0][0]].time,
            sum(s == "support" and r >= 1 for s, r in zip(sides, normalized)),
            sum(s == "resistance" and r >= 1 for s, r in zip(sides, normalized)),
            flips, strength, len(candles)-1-distinct[0][0], recency))
    # Merge overlap by retaining the stronger zone; bounded, readable output.
    selected = []
    for z in sorted(zones, key=lambda z: (-z.strength, z.midpoint)):
        if not any(z.low <= a.high and z.high >= a.low for a in selected):
            selected.append(z)
    return sorted(selected[:24], key=lambda z: z.midpoint)
