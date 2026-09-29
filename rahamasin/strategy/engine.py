"""Structure v2.1: independent confirmation paths and an observable causal pipeline."""
import math
from ..models import Setup, Config
from .levels import atr, detect_zones, pivots
from .context import market_context, alignment
from .trace import Frame

VERSION='structure-v2.2'


def previous_tests(zone):
    """Formation is not a retest; an unfinished current episode is not previous."""
    return max(0,zone.role_retests-int(zone.in_touch))


def freshness_reason(zone, now, step, config):
    role_age=(now-zone.breakout_time)//step if zone.breakout_time else zone.age_bars
    if role_age>config.lookback/2:return 'rejected_zone_too_old'
    if previous_tests(zone)>config.max_tests:return 'rejected_too_many_touches'
    if zone.flips>1:return 'rejected_repeated_flips'
    return None


def quality_reason(zone, volatility, config):
    if zone.displacement_atr<config.min_displacement:return 'rejected_weak_displacement'
    if zone.departure_efficiency<.6:return 'rejected_unclean_departure'
    if zone.high-zone.low>config.zone_atr*volatility*1.5:return 'rejected_zone_width'
    return None


def eligible_zone(zone, volatility, config):
    # Convenience for UI/tests. Full evaluation uses actual role age in seconds.
    return previous_tests(zone)<=config.max_tests and zone.flips<=1 and quality_reason(zone,volatility,config) is None


def confirmation_paths(history, zone, direction, volatility, config):
    c=history[-1];long=direction=='LONG';span=c.high-c.low
    if volatility<=0 or span<=0:return []
    recent=history[-(config.pivot_span+1):]
    interaction=any(b.low<=zone.high and b.high>=zone.low for b in recent)
    if not interaction:return []
    wick=min(c.open,c.close)-c.low if long else c.high-max(c.open,c.close)
    position=c.close-c.low if long else c.high-c.close
    body=c.close-c.open if long else c.open-c.close
    midpoint_hold=c.close>zone.midpoint if long else c.close<zone.midpoint
    far_reclaim=c.close>zone.high if long else c.close<zone.low
    current_touch=c.low<=zone.high and c.high>=zone.low
    earlier=history[-(config.pivot_span+1):-1]
    # A one-close breach is a reclaim opportunity, not permanent invalidation.
    breached=any(b.close<zone.low if long else b.close>zone.high for b in earlier)
    paths=[]
    if current_touch and midpoint_hold and position>=.6*span and wick>=max(.35*span,config.confirmation_atr*volatility):
        paths.append('Rejection')
    if breached and far_reclaim and body>=config.confirmation_atr*volatility:
        paths.append('Reclaim')
    if (zone.breakout_time and zone.breakout_time<c.time and previous_tests(zone)==0
            and current_touch and far_reclaim and body>=config.confirmation_atr*volatility):
        paths.append('Breakout-retest')
    return paths


def structural_stop(history,zone,direction,volatility,buffer,span):
    long=direction=='LONG';recent=history[-(span*4+1):]
    points=[p[1] for p in pivots(recent[:-1],span) if p[2]==('support' if long else 'resistance')]
    values=[zone.low,history[-1].low,history[-2].low] if long else [zone.high,history[-1].high,history[-2].high]
    if points:values.append(points[-1])
    return min(values)-buffer*volatility if long else max(values)+buffer*volatility


def target_zone(zones,zone,direction,entry,config):
    long=direction=='LONG'
    opposing=[z for z in zones if z.role==('resistance' if long else 'support')
              and z.displacement_atr>=config.min_displacement and z.departure_efficiency>=.6
              and (z.low>max(entry,zone.high) if long else z.high<min(entry,zone.low))]
    # Distance first: never skip a meaningful intermediate obstacle to get more R.
    return min(opposing,key=lambda z:(abs((z.low if long else z.high)-entry),-z.strength,z.recency_bars)) if opposing else None


def geometry(direction,entry,stop,target,volatility,config):
    sign=1 if direction=='LONG' else -1
    risk=sign*(entry-stop);reward=sign*(target-entry) if target is not None else None
    if not all(math.isfinite(x) for x in (entry,stop,volatility)) or stop<=0 or risk<.75*volatility:
        return None,None,'rejected_stop_invalid'
    if target is None:return None,None,'rejected_no_opposing_target'
    if not math.isfinite(target) or reward<volatility:return None,None,'rejected_target_geometry'
    fee,slip=config.fee_bps/10000,config.slippage_bps/10000
    rr=reward/risk
    stop_fill=stop*(1-sign*slip)
    net_rr=(reward-fee*(entry+target))/(risk+abs(stop_fill-stop)+fee*(entry+stop_fill))
    if rr<config.min_rr or net_rr<config.min_rr:return rr,net_rr,'rejected_rr'
    return rr,net_rr,None


def next_open_fill(setup,opening_price,config):
    """Only the next bar's opening quote is exposed; no high/low/close knowledge."""
    sign=1 if setup.state=='LONG' else -1
    entry=opening_price*(1+sign*config.slippage_bps/10000)
    v=setup.features['atr_at_signal']
    if abs(entry-setup.zone.midpoint)>v:return None,'rejected_open_too_far'
    rr,net_rr,reason=geometry(setup.state,entry,setup.stop,setup.target,v,config)
    if reason:return None,'open_'+reason
    return entry,None


class Strategy:
    def __init__(self,config=None):self.config=config or Config()

    def analyze(self,candles,as_of=None):
        history=[c for c in candles if as_of is None or c.time<=as_of][-self.config.lookback:]
        if len(history)<40:
            s=Setup(reasons=['At least 40 closed candles are required.'])
            s.pipeline=Frame(history[-1].time if history else 0,VERSION).output();return s,[]
        gaps=[b.time-a.time for a,b in zip(history,history[1:])]
        if min(gaps)<=0 or len(set(gaps))!=1:
            return Setup(reasons=['Candle history has gaps or is not chronological.']),[]
        zones=detect_zones(history[:-1],self.config)
        if self.config.entry_mode=='planned_limit':
            plans=self.plans(history,zones)
            idle=Setup(signal_time=history[-1].time,reasons=['No structurally valid nearby plan.'])
            result=plans[0] if plans else idle;result.pipeline=self.last_plan_pipeline
            return result,zones
        return self.evaluate(history,zones),zones

    def market(self,candles,as_of=None):
        """Display confirmed analysis first, otherwise the best hypothetical plan."""
        from dataclasses import replace
        history=[c for c in candles if as_of is None or c.time<=as_of][-self.config.lookback:]
        active,zones=Strategy(replace(self.config,entry_mode='confirmation')).analyze(history)
        if active.state!='NO TRADE':return active,zones
        plans=self.plans(history,zones) if len(history)>=40 and zones else []
        if plans:return plans[0],zones
        if hasattr(self,'last_plan_pipeline'):
            active.pipeline=self.last_plan_pipeline
            active.reasons=['No structurally valid nearby planned setup.']
            records=active.pipeline.get('rejected_candidates',[])
            for r in sorted(records,key=lambda r:r['distance_atr'])[:3]:
                z=r['zone']
                reason={'rejected_rr':f'R:R below required {self.config.min_rr:.2f}',
                    'rejected_stop_invalid':'Structural stop is too narrow or invalid',
                    'rejected_no_opposing_target':'No meaningful opposing target',
                    'rejected_target_geometry':'Target is too close',
                    'rejected_target_already_passed':'Price has already passed the target'}.get(r['primary_rejection_reason'],r['primary_rejection_reason'])
                value=lambda x: f'{x:.5f}' if x is not None else 'unavailable'
                rr=f"{r['rr']:.2f}" if r.get('rr') is not None else 'unavailable'
                active.reasons.append(f"{r['direction']} {z['low']:.5f}–{z['high']:.5f}: {reason}. Entry {r['entry_candidate']:.5f}, stop {value(r.get('stop_candidate'))}, target {value(r.get('target_candidate'))}, gross R:R {rr}.")
        return active,zones

    def plans(self,history,zones):
        """Frozen hypothetical geometry, no confirmation requirement or future data."""
        cfg=self.config;c=history[-1];v=atr(history);step=c.time-history[-2].time
        frame=Frame(c.time,VERSION);self.last_plan_pipeline=frame.output()
        if not math.isfinite(v) or v<=0:return []
        frame.hit('historical_zones_available',len(zones))
        context=market_context(history,cfg.pivot_span);plans=[]
        points=pivots(history,cfg.pivot_span)
        for z in zones:
            long=z.role=='support';direction='LONG' if long else 'SHORT'
            if z.created_time>=c.time or z.breakout_time>=c.time:continue
            if freshness_reason(z,c.time,step,cfg) or quality_reason(z,v,cfg):continue
            # Only a resting buy below price / sell above price, on the valid side.
            if not (c.close>z.midpoint if long else c.close<z.midpoint):continue
            if abs(c.close-z.midpoint)>cfg.plan_max_distance_atr*v:continue
            relation=alignment(direction,context)
            if relation=='Countertrend' and not(z.displacement_atr>=max(3,cfg.min_displacement) and z.departure_efficiency>=.8):continue
            # Confirmed swings near the zone are structural invalidation anchors.
            anchors=[price for _,price,role in points if role==z.role and z.low-v<=price<=z.high+v]
            boundary=z.low if long else z.high
            anchor=(min([boundary]+anchors) if long else max([boundary]+anchors))
            stop=anchor-cfg.stop_atr*v if long else anchor+cfg.stop_atr*v
            entry=z.midpoint
            target=target_zone(zones,z,direction,entry,cfg)
            tp=(target.low if long else target.high) if target else None
            rr,net_rr,reason=geometry(direction,entry,stop,tp,v,cfg)
            frame.hit('planned_candidates')
            frame.candidate(direction,z,entry,v,context,c.close,stop,tp)
            frame.record.update(rr=rr,net_rr=net_rr,distance_atr=abs(entry-c.close)/v)
            if reason:frame.reject(reason);continue
            if not (c.close<tp if long else c.close>tp):
                frame.reject('rejected_target_already_passed');continue
            status='WAITING FOR PRICE' if (c.close>z.high if long else c.close<z.low) else ('WAITING FOR LIMIT TOUCH' if cfg.entry_mode=='planned_limit' else 'WAITING FOR CONFIRMATION')
            invalidation=f'Cancel before fill on opening gap through stop {stop:.5f}, target reached before entry, or after {cfg.plan_expiry_bars} candles. A stop crossed after entry exits the trade.'
            features=dict(setup_kind='PLANNED',execution='planned_limit',confirmation='Not yet confirmed',
                atr_at_signal=v,previous_tests=previous_tests(z),context=context,alignment=relation,
                net_rr=net_rr,strategy_version=VERSION,zone_distance_atr=abs(entry-c.close)/v,
                distance_pct=(entry/c.close-1)*100,status=status,invalidation=invalidation,
                expires_at=c.time+(cfg.plan_expiry_bars+1)*step)
            reasons=[f'Historical {z.role}, strength {z.strength:.1f}; {previous_tests(z)} completed prior tests.',
                f'Creation departure {z.displacement_atr:.2f} ATR; creation reaction {z.median_reaction:.2f}% (one formation observation, not an expected return).',
                f'Preferred entry is the fixed zone midpoint. Stop beyond nearby confirmed swing/zone plus {cfg.stop_atr:.2f} ATR.',
                f'Nearest meaningful opposing zone target {tp:.5f}; gross R:R {rr:.2f}, net {net_rr:.2f}.',invalidation]
            plans.append(Setup(direction,c.time,z.low,z.high,entry,stop,tp,rr,reasons,z,None,None,context,features,target))
        frame.hit('valid_plans',len(plans));self.last_plan_pipeline=frame.output()
        for plan in plans:plan.pipeline=self.last_plan_pipeline
        return sorted(plans,key=lambda s:(s.features['zone_distance_atr'],-s.zone.strength,-s.rr))

    def evaluate(self,history,zones):
        cfg=self.config;c=history[-1];v=atr(history[:-1]);step=c.time-history[-2].time
        context=market_context(history[:-1],cfg.pivot_span)
        frame=Frame(c.time,VERSION)
        frame.hit('swing_candidates',len(pivots(history[:-1],cfg.pivot_span)))
        frame.hit('historical_zones_available',len(zones))
        idle=Setup(signal_time=c.time,market_state=context,reasons=['No confirmed historical-level setup with valid execution geometry.'])
        if not math.isfinite(v) or v<=0:
            frame.reject('rejected_atr_unavailable');idle.pipeline=frame.output();return idle
        nearby=[];candidates=[]
        for z in zones:
            direction='LONG' if z.role=='support' else 'SHORT';long=direction=='LONG'
            # Recent overlap supports a multi-candle reclaim. Every qualifying
            # nearby zone is examined, rather than a preselected noninteracting one.
            recent=history[-(cfg.pivot_span+1):]
            if not any(b.low<=z.high and b.high>=z.low for b in recent):continue
            frame.hit('price_near_zone')
            entry=c.close  # reference only; actual order executes next open
            stop=structural_stop(history,z,direction,v,cfg.stop_atr,cfg.pivot_span)
            target=target_zone(zones,z,direction,entry,cfg)
            target_price=(target.low if long else target.high) if target else None
            frame.candidate(direction,z,entry,v,context,c.close,stop,target_price)
            record=frame.record
            if z.created_time>=c.time or z.breakout_time>=c.time:
                frame.reject('rejected_zone_not_available');continue
            reason=freshness_reason(z,c.time,step,cfg)
            if reason:frame.reject(reason);continue
            frame.hit('fresh_enough_zone')
            reason=quality_reason(z,v,cfg)
            if reason:frame.reject(reason);continue
            frame.hit('zone_strength_passed');nearby.append(z)
            paths=confirmation_paths(history,z,direction,v,cfg)
            if not paths:frame.reject('rejected_confirmation');continue
            pattern='Breakout-retest' if 'Breakout-retest' in paths else 'Reclaim' if 'Reclaim' in paths else 'Rejection'
            record['confirmation_type']=pattern;frame.hit('confirmation_passed')
            relation=alignment(direction,context)
            # Countertrend retains a stronger creation-zone requirement. The
            # confirmation path is NOT forced to also be a first-retouch wick.
            if relation=='Countertrend' and not(z.displacement_atr>=max(3,cfg.min_displacement) and z.departure_efficiency>=.8):
                frame.reject('rejected_market_structure');continue
            frame.hit('market_structure_passed')
            if abs(entry-z.midpoint)>v:frame.reject('rejected_entry_too_late');continue
            # Consecutive overlap measures chop. Episode age includes outside
            # bars and must not be mistaken for continuous indecision.
            overlap_run=0
            for b in reversed(history):
                if b.low<=z.high and b.high>=z.low:overlap_run+=1
                else:break
            if overlap_run>cfg.pivot_span+1:frame.reject('rejected_prolonged_overlap');continue
            frame.hit('entry_timing_passed')
            rr,net_rr,reason=geometry(direction,entry,stop,target_price,v,cfg)
            record.update(rr=rr,net_rr=net_rr)
            if reason=='rejected_stop_invalid':frame.reject(reason);continue
            frame.hit('valid_stop_found')
            if reason in ('rejected_no_opposing_target','rejected_target_geometry'):frame.reject(reason);continue
            frame.hit('valid_target_found')
            if reason:frame.reject(reason);continue
            frame.hit('minimum_rr_passed')
            features=dict(previous_tests=previous_tests(z),atr_at_signal=v,confirmation=pattern,
                context=context,alignment=relation,net_rr=net_rr,strategy_version=VERSION,execution='next_open',
                zone_distance_atr=abs(entry-z.midpoint)/v)
            reasons=[f'{pattern}: historical {z.role} {z.low:.5f}–{z.high:.5f}; creation known at {z.created_time}.',
                f'Creation departure {z.displacement_atr:.2f} ATR, efficiency {z.departure_efficiency:.2f}; {previous_tests(z)} completed prior role tests.',
                f'{context} / {relation}. Confirmation paths passed: {", ".join(paths)}.',
                f'Entry reference is confirmation close {entry:.5f}; execute next open with adverse slippage only if geometry still passes.',
                f'Stop beyond zone/rejection/local swing plus {cfg.stop_atr:.2f} ATR; nearest meaningful target {target_price:.5f}.',
                f'Projected gross R:R {rr:.2f}; net R:R {net_rr:.2f}. No farther target substituted.']
            candidates.append(Setup(direction,c.time,z.low,z.high,entry,stop,target_price,rr,reasons,z,None,None,context,features,target))
        idle.long_zone=max((z for z in nearby if z.role=='support' and z.midpoint<c.close),key=lambda z:z.midpoint,default=None)
        idle.short_zone=min((z for z in nearby if z.role=='resistance' and z.midpoint>c.close),key=lambda z:z.midpoint,default=None)
        def rank(s):
            multiplier={'Trend aligned':1.1,'Range':1.0,'Countertrend':.85}[s.features['alignment']]
            return s.zone.strength*multiplier,s.rr
        result=max(candidates,key=rank,default=idle)
        if result.state!='NO TRADE':frame.hit('final_'+result.state+'_signals')
        elif frame.rejections:result.reasons += [f'{code}: {n}' for code,n in frame.rejections.most_common(3)]
        result.pipeline=frame.output()
        return result
