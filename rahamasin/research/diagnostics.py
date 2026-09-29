"""Features are computed only from information closed BEFORE entry."""
import csv
from dataclasses import asdict
from statistics import mean
from ..strategy.context import market_context, alignment
from ..strategy.levels import atr


def touch_history(candles, zone, span, direction):
    # v1 did not store retest episodes. Reconstruct against its SIGNAL-TIME
    # bounds, explicitly a retrospective diagnostic, not historical zone identity.
    seq = [c for c in candles if c.time > zone.first_time]
    seq = seq[span:]
    outside = 2
    tests = penetrations = failed = 0
    in_episode = False
    episode_penetrated = episode_failed = False
    for c in seq:
        overlap = c.low <= zone.high and c.high >= zone.low
        if overlap and outside >= 2:
            tests += 1; in_episode = True
            episode_penetrated = episode_failed = False
        if overlap:
            outside = 0
        else:
            outside += 1
            if outside >= 2:
                in_episode = False
        if in_episode:
            penetration = c.low < zone.low if direction == 'LONG' else c.high > zone.high
            failure = c.close < zone.low if direction == 'LONG' else c.close > zone.high
            if penetration and not episode_penetrated:
                penetrations += 1; episode_penetrated = True
            if failure and not episode_failed:
                failed += 1; episode_failed = True
    return tests,penetrations,failed


def trade_rows(result, candles):
    indices = {c.time:i for i,c in enumerate(candles)}
    rows = []
    for ordinal,t in enumerate(result.trades):
        s,z = t.setup,t.setup.zone
        i = indices[s.signal_time]
        history = candles[max(0,i+1-result.config.lookback):i+1]
        before = history[:-1]
        v = atr(history)  # available at next-bar entry, not entry bar's final OHLC
        context = market_context(before,result.config.pivot_span)
        features = getattr(s,'features',{})
        if 'previous_tests' in features:
            tests = features['previous_tests']
            penetrations,failed = z.penetrations,z.failed_holds
            origin = 'Causal zone event ledger'
        else:
            tests,penetrations,failed = touch_history(before,z,result.config.pivot_span,s.state)
            origin = 'v1 reconstructed against signal-time bounds'
        sign = 1 if s.state == 'LONG' else -1
        risk = abs(t.entry_price-s.stop)
        gross = getattr(t,'gross_r',None)
        raw_exit = t.exit_price if t.exit_reason=='Target' else t.exit_price/(1-sign*result.config.slippage_bps/10000)
        gross = sign*(raw_exit-t.entry_price)/risk if gross is None else gross
        fees_r = result.config.fee_bps/10000*(t.entry_price+t.exit_price)/risk
        slippage_r = sign*(raw_exit-t.exit_price)/risk
        pattern = features.get('confirmation','Rejection')
        row = dict(trade=ordinal+1,direction=s.state,signal_time=s.signal_time,entry_time=t.entry_time,
            exit_time=t.exit_time,entry=t.entry_price,exit_price=t.exit_price,stop=s.stop,target=s.target,zone_low=z.low,zone_high=z.high,
            zone_strength=z.strength,zone_age_bars=z.age_bars,pivot_touches=z.touches,
            previous_tests=tests,retest_number=tests+1,first_retest=tests==0,
            penetrations=penetrations,failed_holds=failed,weakened=tests>=3 or failed>=1,
            entry_center_distance=abs(t.entry_price-z.midpoint),atr_at_entry=v,
            stop_atr=risk/v,target_atr=abs(s.target-t.entry_price)/v,zone_width_atr=(z.high-z.low)/v,
            rr=s.rr,executed_rr=sign*(s.target-t.entry_price)/risk,confirmation=pattern,context=context,alignment=alignment(s.state,context),
            displacement_atr=getattr(z,'displacement_atr',0) or z.reaction_atr,
            departure_efficiency=getattr(z,'departure_efficiency',None),
            gross_r=gross,net_r=t.r,fees_r=fees_r,slippage_r=slippage_r,cost_r=gross-t.r,result=t.outcome,exit_reason=t.exit_reason,
            feature_provenance=origin)
        rows.append(row)
    return rows


def summary(rows):
    rs = [r['net_r'] for r in rows]
    wins = [r for r in rs if r > 0]; losses = [r for r in rs if r < 0]
    return dict(trades=len(rs),win_rate=100*len(wins)/len(rs) if rs else 0,
        expectancy=mean(rs) if rs else 0,total_r=sum(rs),
        profit_factor=sum(wins)/-sum(losses) if losses else ('∞' if wins else '—'))


def groups(rows):
    predicates = {
        'LONG':lambda r:r['direction']=='LONG','SHORT':lambda r:r['direction']=='SHORT',
        'Fresh zones':lambda r:r['previous_tests']==0,'Retested zones':lambda r:r['previous_tests']>0,
        'First retest':lambda r:r['retest_number']==1,'Second/third retest':lambda r:2<=r['retest_number']<=3,
        'Fourth+ retest':lambda r:r['retest_number']>=4,
        'Trend aligned':lambda r:r['alignment']=='Trend aligned','Countertrend':lambda r:r['alignment']=='Countertrend',
        'Range':lambda r:r['alignment']=='Range','Rejection':lambda r:r['confirmation']=='Rejection',
        'Breakout-retest':lambda r:r['confirmation']=='Breakout-retest',
        'Reclaim':lambda r:r['confirmation']=='Reclaim',
        'Strong (>=65)':lambda r:r['zone_strength']>=65,'Weak (<65)':lambda r:r['zone_strength']<65,
        'Recent (<=100 bars)':lambda r:r['zone_age_bars']<=100,'Old (>100 bars)':lambda r:r['zone_age_bars']>100,
        'Narrow (<=0.5 ATR)':lambda r:r['zone_width_atr']<=.5,'Wide (>0.5 ATR)':lambda r:r['zone_width_atr']>.5,
        'Stop <0.75 ATR':lambda r:r['stop_atr']<.75,'Stop 0.75–1.5 ATR':lambda r:.75<=r['stop_atr']<=1.5,
        'Stop >1.5 ATR':lambda r:r['stop_atr']>1.5,
        'Previously failed hold':lambda r:r['failed_holds']>0,'No failed holds':lambda r:r['failed_holds']==0,
        'Impulse >=3 ATR':lambda r:r['displacement_atr']>=3,'Impulse <3 ATR':lambda r:r['displacement_atr']<3,
    }
    return {name:summary([r for r in rows if predicate(r)]) for name,predicate in predicates.items()}


def markdown_groups(grouped):
    text = '| Characteristic | Trades | Win % | Expectancy R | Total R | PF |\n|---|---:|---:|---:|---:|---:|\n'
    for name,m in grouped.items():
        pf = f'{m["profit_factor"]:.2f}' if isinstance(m['profit_factor'],float) else m['profit_factor']
        text += f'| {name} | {m["trades"]} | {m["win_rate"]:.1f} | {m["expectancy"]:.3f} | {m["total_r"]:.2f} | {pf} |\n'
    return text


def export_rows(path, rows):
    if not rows:
        path.write_text('No trades\n'); return
    with path.open('w',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
