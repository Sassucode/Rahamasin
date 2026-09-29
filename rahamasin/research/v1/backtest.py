# Frozen v1 audit reference. Never imported by live analysis.
from .models import Result, Trade, SECONDS
from .engine import Strategy


def exit_fill(setup, candle, entry_candle=False):
    """Stop first; no favorable target credit on ambiguous limit-entry bars."""
    long = setup.state == 'LONG'
    stopped = candle.low <= setup.stop if long else candle.high >= setup.stop
    targeted = candle.high >= setup.target if long else candle.low <= setup.target
    if stopped:
        price = setup.stop
        if not entry_candle:
            price = min(price,candle.open) if long else max(price,candle.open)
        return price,'Stop (stop-first if ambiguous)'
    if targeted and not entry_candle:
        return setup.target,'Target'
    return None


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
        balance = 10000.0
        pending = position = None
        slip = self.config.slippage_bps/10000
        fee = self.config.fee_bps/10000
        for i,c in enumerate(candles):
            if c.time < start:
                continue
            if progress and i % 25 == 0:
                progress(int(i/len(candles)*100))
            new_entry = False
            if pending and position is None:
                s = pending
                # Cancel a gap through invalidation; limit expires after one bar.
                valid_open = c.open > s.stop if s.state == 'LONG' else c.open < s.stop
                if valid_open and c.low <= s.entry <= c.high:
                    sign = 1 if s.state == 'LONG' else -1
                    entry = s.entry  # limit order never fills worse than its limit
                    risk = abs(entry-s.stop)
                    size = balance*self.config.risk_pct/100/risk
                    position = (s,c.time,entry,risk,size)
                    new_entry = True
                pending = None
            if position:
                s,opened,entry,risk,size = position
                sign = 1 if s.state == 'LONG' else -1
                fill = exit_fill(s,c,new_entry)
                if fill is None and (c.time+step-opened >= self.config.max_hold_days*86400 or i == len(candles)-1):
                    fill = (c.close,'Time exit' if i < len(candles)-1 else 'End of test')
                mark = c.close*(1-sign*slip)
                if fill:
                    raw, reason = fill
                    # Target is a limit; stop/time exits receive adverse slippage.
                    price = raw if reason == 'Target' else raw*(1-sign*slip)
                    pnl_unit = sign*(price-entry)-fee*(entry+price)
                    r = pnl_unit/risk
                    balance += size*pnl_unit
                    trades.append(Trade(s,opened,entry,c.time+step,price,'WIN' if r > 0 else 'LOSS' if r < 0 else 'BREAKEVEN',r,pnl_unit/entry*100,reason))
                    position = None
                    equity.append((c.time+step,balance))
                else:
                    equity.append((c.time+step,balance+size*(sign*(mark-entry)-fee*(entry+mark))))
            else:
                equity.append((c.time+step,balance))
            if position is None and i < len(candles)-1 and balance > 0:
                setup,_ = self.strategy.analyze(candles[max(0,i+1-self.config.lookback):i+1])
                if setup.state != 'NO TRADE':
                    pending = setup
        return Result(trades,metrics(trades,equity),equity,self.config,timeframe,start,end,source)
