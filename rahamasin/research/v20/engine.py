# Frozen structure-v2.0 reference; audit only.
"""Rahamasin structure v2. Live and historical callers use this exact engine."""
from ...models import Setup, Config
from .levels import atr, detect_zones, pivots
from .context import market_context, alignment
from ...strategy.trace import Frame

VERSION = 'structure-v2.0'


def confirmation(candle, zone, direction, volatility, threshold):
    long = direction == 'LONG'
    span = candle.high-candle.low
    wick = min(candle.open,candle.close)-candle.low if long else candle.high-max(candle.open,candle.close)
    directional = candle.close > candle.open if long else candle.close < candle.open
    reclaimed = candle.close > zone.high if long else candle.close < zone.low
    close_position = candle.close-candle.low if long else candle.high-candle.close
    return (span > 0 and candle.low <= zone.high and candle.high >= zone.low
            and directional and reclaimed and wick >= max(.35*span,threshold*volatility)
            and close_position >= .65*span)


def eligible_zone(zone, volatility, config):
    return (zone.displacement_atr >= config.min_displacement and zone.departure_efficiency >= .6
            and zone.role_retests <= config.max_tests and zone.retests <= config.max_tests+1
            and zone.role_failed_holds == 0 and zone.flips <= 1
            and zone.age_bars <= config.lookback/2
            and zone.high-zone.low <= config.zone_atr*volatility*1.5)


def structural_stop(history, zone, direction, volatility, buffer, span):
    long = direction == 'LONG'
    recent = history[-(span*4+1):]
    points = [p[1] for p in pivots(recent[:-1],span)
              if p[2] == ('support' if long else 'resistance')]
    values = [zone.low,history[-1].low,history[-2].low] if long else [zone.high,history[-1].high,history[-2].high]
    if points:
        values.append(points[-1])
    return min(values)-buffer*volatility if long else max(values)+buffer*volatility


class Strategy:
    def __init__(self, config=None):
        self.config = config or Config()

    def analyze(self, candles, as_of=None):
        history = [c for c in candles if as_of is None or c.time <= as_of][-self.config.lookback:]
        if len(history) < 40:
            return Setup(reasons=['At least 40 closed candles are required.']),[]
        intervals = [b.time-a.time for a,b in zip(history,history[1:])]
        if min(intervals) <= 0 or len(set(intervals)) != 1:
            return Setup(reasons=['Candle history has gaps or is not chronological.']),[]
        zones = detect_zones(history[:-1],self.config)
        return self.evaluate(history,zones),zones

    def evaluate(self, history, zones):
        cfg = self.config
        frame=Frame(history[-1].time,VERSION)
        frame.hit("historical_zones_available",len(zones))
        frame.hit("swing_candidates",len(pivots(history[:-1],cfg.pivot_span)))
        c = history[-1]; v = atr(history[:-1])
        context = market_context(history[:-1],cfg.pivot_span)
        for z in zones:
            near=history[-1].low<=z.high and history[-1].high>=z.low
            if not near: continue
            frame.hit('price_near_zone')
            direction='LONG' if z.role=='support' else 'SHORT'
            frame.candidate(direction,z,z.midpoint,v,context,c.close)
            if z.age_bars>cfg.lookback/2: frame.reject('rejected_zone_too_old')
            elif z.role_retests>cfg.max_tests or z.retests>cfg.max_tests+1: frame.reject('rejected_too_many_touches')
            elif z.role_failed_holds: frame.reject('rejected_previous_failed_hold')
            elif z.flips>1: frame.reject('rejected_repeated_flips')
            else:
                frame.hit('fresh_enough_zone')
                if z.displacement_atr<cfg.min_displacement: frame.reject('rejected_weak_displacement')
                elif z.departure_efficiency<.6: frame.reject('rejected_unclean_departure')
                elif z.high-z.low>cfg.zone_atr*v*1.5: frame.reject('rejected_zone_width')
                else: frame.hit('zone_strength_passed')
            frame.record=None
        available = [z for z in zones if v > 0 and eligible_zone(z,v,cfg)]
        supports = [z for z in available if z.role == 'support' and z.midpoint < c.close]
        resistances = [z for z in available if z.role == 'resistance' and z.midpoint > c.close]
        long_zone = max(supports,key=lambda z:z.midpoint,default=None)
        short_zone = min(resistances,key=lambda z:z.midpoint,default=None)
        idle = Setup(signal_time=c.time,long_zone=long_zone,short_zone=short_zone,market_state=context,
                     reasons=['No fresh, clean historical-zone confirmation with sufficient net reward/risk.'])
        candidates = []
        for direction,z in [('LONG',long_zone),('SHORT',short_zone)]:
            if z is None:
                continue
            long = direction == 'LONG'
            frame.hit('selected_candidates')
            frame.candidate(direction,z,z.midpoint,v,context,c.close)
            def reject(reason):
                idle.reasons.append(f'{direction}: {reason}')
                mapping={'needs a significant':'rejected_confirmation','confirmation is more':'rejected_entry_too_late','confirmation arrived':'rejected_prolonged_overlap','too many earlier':'rejected_too_many_touches','countertrend needs':'rejected_market_structure','no meaningful':'rejected_no_opposing_target','structural stop':'rejected_stop_invalid','nearest opposing':'rejected_target_geometry','nearest target':'rejected_rr','only the first':'rejected_later_flip_retest'}
                frame.reject(next((code for prefix,code in mapping.items() if reason.startswith(prefix)),reason))
            if not confirmation(c,z,direction,v,cfg.confirmation_atr):
                reject('needs a significant directional wick and close beyond the zone'); continue
            frame.hit('confirmation_passed')
            if abs(c.close-z.midpoint) > v:
                reject('confirmation is more than 1 ATR from the zone; do not chase'); continue
            # Repeated adjacent candles are one episode; reject confirmation after
            # more than one earlier candle in the current episode (chop).
            step = c.time-history[-2].time
            if z.in_touch and c.time-z.last_touch_time > step:
                reject('confirmation arrived after prolonged overlap/chop'); continue
            previous_tests = max(0,z.role_retests-int(z.in_touch))
            if previous_tests > cfg.max_tests:
                reject('too many earlier retests'); continue
            frame.hit('entry_timing_passed')
            relation = alignment(direction,context)
            if relation == 'Countertrend':
                sweep = c.low < z.low if long else c.high > z.high
                if not (z.displacement_atr >= 3 and z.departure_efficiency >= .8
                        and previous_tests == 0 and sweep
                        and confirmation(c,z,direction,v,max(.5,cfg.confirmation_atr))):
                    reject('countertrend needs a fresh 3 ATR impulse zone and stronger failed-break rejection'); continue
            frame.hit('market_structure_passed')
            # Even used/aged zones can block a target. Do not skip an intermediate
            # meaningful opposing level merely to manufacture a higher R:R.
            opposing = [a for a in zones if a.role == ('resistance' if long else 'support')
                        and a.displacement_atr >= cfg.min_displacement and a.role_failed_holds == 0
                        and (a.low > z.high if long else a.high < z.low)]
            target_zone = (min(opposing,key=lambda a:a.low) if long else max(opposing,key=lambda a:a.high)) if opposing else None
            if target_zone is None:
                reject('no meaningful opposing zone'); continue
            entry = z.midpoint
            stop = structural_stop(history,z,direction,v,cfg.stop_atr,cfg.pivot_span)
            target = target_zone.low if long else target_zone.high
            frame.record.update(stop_candidate=stop,target_candidate=target,confirmation_type='Wick AND far-edge reclaim')
            risk = entry-stop if long else stop-entry
            reward = target-entry if long else entry-target
            if stop <= 0 or risk < .75*v:
                reject('structural stop is under 0.75 ATR; reject rather than arbitrarily widen'); continue
            frame.hit('valid_stop_found')
            if reward < v or (c.close >= target if long else c.close <= target):
                reject('nearest opposing structure is too close or already crossed'); continue
            frame.hit('valid_target_found')
            rr = reward/risk
            frame.record['rr']=rr
            # Expected net target reward / net normal-stop loss, including both
            # fees and market-stop slippage. Reported R remains structural gross R.
            fee,slip = cfg.fee_bps/10000,cfg.slippage_bps/10000
            estimated_reward = reward-fee*(entry+target)
            estimated_risk = risk+fee*(entry+stop)+stop*slip
            frame.record['net_rr']=estimated_reward/estimated_risk
            if rr < cfg.min_rr or estimated_reward/estimated_risk < cfg.min_rr:
                reject('nearest target fails minimum R:R after modeled costs'); continue
            frame.hit('minimum_rr_passed')
            pattern = 'Breakout-retest' if z.breakout_time and z.breakout_time < c.time else 'Rejection'
            if pattern == 'Breakout-retest' and z.role_retests > 1:
                reject('only the first held retest after a two-close break is allowed'); continue
            features = dict(previous_tests=previous_tests,atr_at_signal=v,confirmation=pattern,
                            context=context,alignment=relation,net_rr=estimated_reward/estimated_risk,
                            strategy_version=VERSION)
            reasons = [f'{pattern}: {z.role} zone {z.low:.5f}–{z.high:.5f}, fixed at confirmed pivot.',
                f'Creation impulse {z.displacement_atr:.2f} ATR; departure efficiency {z.departure_efficiency:.2f}.',
                f'{previous_tests} previous role retests; {z.penetrations} penetrations; {z.failed_holds} historical failed holds.',
                f'{context} structure · {relation}; directional wick clears both range and ATR thresholds.',
                f'Stop beyond zone, rejection and relevant confirmed local swing + {cfg.stop_atr:.2f} ATR; risk {risk/v:.2f} ATR.',
                f'Nearest meaningful opposing zone target {target:.5f}; gross R:R {rr:.2f}, estimated net R:R {features["net_rr"]:.2f}.',
                'Next-candle midpoint limit only; no late chase or target stretching.']
            s = Setup(direction,c.time,z.low,z.high,entry,stop,target,rr,reasons,z,long_zone,short_zone,context,features,target_zone)
            candidates.append(s)
        result=max(candidates,key=lambda s:(s.zone.strength,s.rr),default=idle)
        if result.state!='NO TRADE':frame.hit('final_'+result.state+'_signals')
        result.pipeline=frame.output()
        return result
