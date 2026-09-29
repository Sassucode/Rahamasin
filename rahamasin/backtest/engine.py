from ..models import Result, Trade, SECONDS
from ..strategy.engine import Strategy, VERSION, next_open_fill
from ..strategy.trace import Accumulator


def exit_fill(setup, candle, entry_candle=False, entry_at_open=False):
    """Stop first. Credit an entry-bar target only when ordering is established."""
    long = setup.state == 'LONG'
    stopped = candle.low <= setup.stop if long else candle.high >= setup.stop
    targeted = candle.high >= setup.target if long else candle.low <= setup.target
    if stopped:
        price = setup.stop
        if not entry_candle:
            price = min(price,candle.open) if long else max(price,candle.open)
        return price,'Stop (stop-first if ambiguous)'
    target_after_fill = candle.close >= setup.target if long else candle.close <= setup.target
    if targeted and (not entry_candle or entry_at_open or target_after_fill):
        return setup.target,'Target'
    return None


def limit_fill(setup, candle):
    long = setup.state == 'LONG'
    if (candle.open <= setup.stop if long else candle.open >= setup.stop):
        return None  # documented cancellation on an invalidating opening gap
    marketable = candle.open <= setup.entry if long else candle.open >= setup.entry
    if marketable:
        return candle.open,True
    touched = candle.low <= setup.entry if long else candle.high >= setup.entry
    return (setup.entry,False) if touched else None


def planned_limit_step(setup,candle):
    """Decide using frozen order; ambiguous target-before-entry bars cancel."""
    long=setup.state=='LONG'
    if candle.time>=setup.features['expires_at']:return None,'expired'
    if candle.open<=setup.stop if long else candle.open>=setup.stop:
        return None,'invalidated_open'
    if candle.open>=setup.target if long else candle.open<=setup.target:
        return None,'target_before_entry'
    fill=limit_fill(setup,candle)
    target_touched=candle.high>=setup.target if long else candle.low<=setup.target
    # Opening fills have known sequencing. Intrabar entry vs target is unknown:
    # conservatively cancel, never assume a profitable entry then target.
    stop_touched=candle.low<=setup.stop if long else candle.high>=setup.stop
    if fill and stop_touched:return fill,'filled'  # ambiguous path: retain the stop loss
    if target_touched and not (fill and fill[1]):return None,'target_before_entry'
    return (fill,'filled') if fill else (None,None)


def metrics(trades, equity):
    rs = [t.r for t in trades]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r < 0]
    peak = equity[0][1]
    drawdown = 0
    streak = longest = 0
    for _, value in equity:
        peak = max(peak,value)
        drawdown = max(drawdown,(peak-value)/peak*100)
    for r in rs:
        streak = streak+1 if r < 0 else 0
        longest = max(longest,streak)
    average = sum(rs)/len(rs) if rs else 0
    return dict(total_trades=len(rs),wins=len(wins),losses=len(losses),breakeven=sum(r == 0 for r in rs),
        win_rate=100*len(wins)/len(rs) if rs else 0,
        average_win=sum(wins)/len(wins) if wins else 0,
        average_loss=sum(losses)/len(losses) if losses else 0,
        average_R=average,total_R=sum(rs),expectancy=average,
        profit_factor=sum(wins)/abs(sum(losses)) if losses else ('∞' if wins else '—'),
        maximum_drawdown_pct=drawdown,longest_losing_streak=longest)


class Backtester:
    def __init__(self, config, strategy=None):
        self.config = config
        self.strategy = strategy or Strategy(config)

    def run(self, candles, timeframe, start, end, source='', progress=None):
        step = SECONDS[timeframe]
        candles = [c for c in candles if c.time+step <= end]
        if not candles:
            raise ValueError('No closed candles in test period')
        if any(b.time-a.time != step for a,b in zip(candles,candles[1:])):
            raise ValueError('Backtest requires continuous candles: data gaps found. Choose a different period/provider.')
        trades, equity = [], [(start,10000.0)]
        trace=Accumulator()
        order_events=[]
        def record_order(s,event,when):
            from dataclasses import asdict
            order_events.append(dict(created=s.signal_time,time=when,event=event,setup=asdict(s)))
        balance = 10000.0
        pending = position = None
        slip = self.config.slippage_bps/10000
        fee = self.config.fee_bps/10000
        for i,c in enumerate(candles):
            if c.time < start:
                continue
            # Analyze every historical closed candle, including while occupied.
            # Its signal cannot be used until the following iteration/open.
            setup,_=self.strategy.analyze(candles[max(0,i+1-self.config.lookback):i+1])
            trace.add(getattr(setup,'pipeline',{}))
            if progress and i % 25 == 0:
                progress(int(i/len(candles)*100))
            new_entry = False
            entry_at_open = False
            if pending and position is None:
                s = pending
                planned=getattr(s,'features',{}).get('execution')=='planned_limit'
                terminal=None
                if planned:
                    entry_fill,terminal=planned_limit_step(s,c)
                elif getattr(s,'features',{}).get('execution')=='next_open':
                    entry_price,rejection=next_open_fill(s,c.open,self.config)
                    entry_fill=(entry_price,True) if entry_price is not None else None
                    if rejection:trace.rejections[rejection]+=1
                else:
                    entry_fill = limit_fill(s,c)
                if entry_fill:
                    trace.funnel['orders_actually_filled']+=1
                    sign = 1 if s.state == 'LONG' else -1
                    entry,entry_at_open = entry_fill
                    risk = abs(entry-s.stop)
                    size = balance*self.config.risk_pct/100/risk
                    position = (s,c.time,entry,risk,size)
                    new_entry = True
                    if planned:record_order(s,'filled',c.time)
                elif not planned or terminal:
                    trace.funnel['orders_unfilled_or_cancelled']+=1
                    if planned:
                        trace.rejections['planned_'+terminal]+=1
                        record_order(s,terminal,c.time)
                if entry_fill or not planned or terminal:pending = None
            if position:
                s,opened,entry,risk,size = position
                sign = 1 if s.state == 'LONG' else -1
                fill = exit_fill(s,c,new_entry,entry_at_open)
                if fill is None and (c.time+step-opened >= self.config.max_hold_days*86400 or i == len(candles)-1):
                    fill = (c.close,'Time exit' if i < len(candles)-1 else 'End of test')
                mark = c.close*(1-sign*slip)
                if fill:
                    raw, reason = fill
                    # Target is a limit; stop/time exits receive adverse slippage.
                    price = raw if reason == 'Target' else raw*(1-sign*slip)
                    pnl_unit = sign*(price-entry)-fee*(entry+price)
                    r = pnl_unit/risk
                    gross_r = sign*(raw-entry)/risk
                    fees_r = fee*(entry+price)/risk
                    slippage_r = sign*(raw-price)/risk
                    balance += size*pnl_unit
                    trades.append(Trade(s,opened,entry,c.time+step,price,'WIN' if r > 0 else 'LOSS' if r < 0 else 'BREAKEVEN',r,pnl_unit/entry*100,reason,gross_r,fees_r,slippage_r))
                    position = None
                    equity.append((c.time+step,balance))
                else:
                    equity.append((c.time+step,balance+size*(sign*(mark-entry)-fee*(entry+mark))))
            else:
                equity.append((c.time+step,balance))
            if position is None and pending is None and i < len(candles)-1 and balance > 0:
                if setup.state != 'NO TRADE':
                    pending = setup
                    trace.funnel['orders_submitted']+=1
                    if getattr(setup,'features',{}).get('execution')=='planned_limit':record_order(setup,'submitted',c.time+step)
            elif position is not None and setup.state!='NO TRADE':
                trace.funnel['signals_blocked_by_open_position']+=1
        if pending is not None:
            trace.funnel['orders_unfilled_or_cancelled']+=1
            if pending.features.get('execution')=='planned_limit':record_order(pending,'end_of_test',end)
        trace.funnel['completed_trades']=len(trades)
        for key in ('orders_submitted','orders_actually_filled','orders_unfilled_or_cancelled'):
            trace.funnel.setdefault(key,0)
        result=Result(trades,metrics(trades,equity),equity,self.config,timeframe,start,end,source,VERSION)
        result.pipeline=trace.result()
        result.pipeline['entry_mode']=self.config.entry_mode
        result.pipeline['order_events']=order_events
        return result
