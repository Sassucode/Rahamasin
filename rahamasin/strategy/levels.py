"""Causal fixed-width zones with an event ledger after pivot confirmation."""
from statistics import mean
from ..models import Zone


def atr(candles, period=14):
    if len(candles) < 2:
        return 0.0
    start = max(1,len(candles)-period)
    return mean(max(candles[i].high-candles[i].low,
                    abs(candles[i].high-candles[i-1].close),
                    abs(candles[i].low-candles[i-1].close)) for i in range(start,len(candles)))


def pivots(candles, span=3):
    points = []
    for i in range(span,len(candles)-span):
        c = candles[i]
        neighbors = candles[i-span:i]+candles[i+1:i+span+1]
        if c.low < min(x.low for x in neighbors):
            points.append((i,c.low,'support'))
        if c.high > max(x.high for x in neighbors):
            points.append((i,c.high,'resistance'))
    return points


def strength(displacement, efficiency, tests, penetrations, failed_holds, age, lookback, flips):
    # Quality rewards impulse, NOT repeated touch count. All penalties monotonic.
    quality = 45*min(displacement/6,1)+25*efficiency+20+(10 if flips == 1 else 0)
    decay = (1/(1+.45*tests+.25*penetrations+.8*failed_holds)
             * max(.25,1-age/(lookback*1.25)))
    return max(0,min(100,quality*decay))


def track_zone(candles, seed_index, price, role, config):
    """Bounds and formation quality use only data through seed confirmation."""
    span = config.pivot_span
    confirmed = seed_index+span
    v = atr(candles[:seed_index+1])
    if seed_index < 14 or v <= 0 or confirmed >= len(candles):
        return None
    low,high = price-v*config.zone_atr/2,price+v*config.zone_atr/2
    if low <= 0:
        return None
    departure = candles[seed_index+1:confirmed+1]
    sign = 1 if role == 'support' else -1
    displacement = max(sign*(c.close-price) for c in departure)/v
    path = sum(abs(b.close-a.close) for a,b in zip(candles[seed_index:confirmed],departure))
    efficiency = max(0,sign*(departure[-1].close-candles[seed_index].close))/path if path else 0
    if displacement < config.min_displacement or efficiency < .6:
        return None
    origin_role = role
    tests = role_tests = penetrations = failures = role_failures = flips = 0
    breakout_time = 0
    last_touch = candles[seed_index].time
    # A departure must spend two complete bars outside before a new touch episode.
    outside = 0
    for c in candles[seed_index+1:confirmed+1]:
        outside = outside+1 if c.low > high or c.high < low else 0
    inside = episode_penetrated = episode_failed = False
    break_count = 0
    for c in candles[confirmed+1:]:
        overlap = c.low <= high and c.high >= low
        if overlap and outside >= 2:
            tests += 1; role_tests += 1
            inside = True; episode_penetrated = episode_failed = False
            last_touch = c.time
        if overlap:
            outside = 0
        else:
            outside += 1
            if outside >= 2:
                inside = False
        penetrated = c.low < low if role == 'support' else c.high > high
        failed = c.close < low-.25*v if role == 'support' else c.close > high+.25*v
        if inside and penetrated and not episode_penetrated:
            penetrations += 1; episode_penetrated = True
        if failed and not episode_failed:
            failures += 1; role_failures += 1; episode_failed = True
        break_count = break_count+1 if failed else 0
        if break_count == 2:
            role = 'resistance' if role == 'support' else 'support'
            flips += 1; breakout_time = c.time
            role_tests = role_failures = 0
            break_count = 0; inside = False
            episode_penetrated = episode_failed = False
            # The breakout itself isn't a retest of its newly established role.
            outside = 2
    age = len(candles)-1-confirmed
    recency = sum(c.time > last_touch for c in candles)
    score = strength(displacement,efficiency,tests,penetrations,failures,age,config.lookback,flips)
    reaction_pct = displacement*v/price*100
    return Zone(low,high,1+tests,1,reaction_pct,reaction_pct,displacement,
        last_touch,candles[seed_index].time,int(origin_role=='support'),int(origin_role=='resistance'),
        flips,score,age,recency,role,origin_role,candles[confirmed].time,breakout_time,
        tests,role_tests,penetrations,failures,role_failures,displacement,efficiency,v,inside,last_touch)


def detect_zones(candles, config):
    candles = candles[-config.lookback:]
    if len(candles) < 2*config.pivot_span+1:
        return []
    zones = []
    # Chronological clustering: first qualified seed fixes bounds. Later overlapping
    # pivots cannot widen it or reset freshness. Old seeds expire with the lookback.
    for i,price,role in pivots(candles,config.pivot_span):
        if any(z.low <= price <= z.high for z in zones):
            continue
        z = track_zone(candles,i,price,role,config)
        if z and not any(z.low <= a.high and z.high >= a.low for a in zones):
            zones.append(z)
    return sorted(zones,key=lambda z:z.midpoint)
