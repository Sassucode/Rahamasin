"""Independent chronological segments; same immutable config and core strategy."""
from .engine import Backtester
from ..strategy.engine import Strategy
from ..models import SECONDS


class MemoizedStrategy:
    """Cache exact immutable history tuples, never timestamp-only or full-data pivots."""
    def __init__(self, strategy):
        self.strategy = strategy
        self.cache = {}

    def analyze(self, history):
        key = tuple(history)
        if key not in self.cache:
            setup,_ = self.strategy.analyze(history)
            self.cache[key] = (setup,[])
        return self.cache[key]


def boundaries(candles, timeframe, start, end):
    test = [c for c in candles if start <= c.time and c.time+SECONDS[timeframe] <= end]
    if len(test) < 10:
        raise ValueError('At least 10 candles required for a 70/30 evaluation split')
    split = test[int(len(test)*.7)].time
    return {'Full':(test[0].time,test[-1].time+SECONDS[timeframe]),
            'Development 70%':(test[0].time,split),
            'Evaluation 30%':(split,test[-1].time+SECONDS[timeframe])}


def evaluate(candles, timeframe, start, end, config, source='', progress=None):
    from ..research.diagnostics import trade_rows, groups
    strategy = MemoizedStrategy(Strategy(config))
    results = {}
    for name,(a,b) in boundaries(candles,timeframe,start,end).items():
        result = Backtester(config,strategy).run(candles,timeframe,a,b,source,progress)
        rows = trade_rows(result,candles)
        result.diagnostics = groups(rows)
        results[name] = result
    full = results['Full']
    full.evaluation = {name:dict(start=r.start,end=r.end,metrics=r.metrics,diagnostics=r.diagnostics,pipeline=r.pipeline)
                       for name,r in results.items()}
    return full


def evaluate_modes(candles,timeframe,start,end,config,source='',progress=None):
    """Independent portfolios and chronological splits; never pool their trades."""
    from dataclasses import replace
    results={mode:evaluate(candles,timeframe,start,end,replace(config,entry_mode=mode),source,progress)
             for mode in ('confirmation','planned_limit')}
    comparison={('Confirmation Entry' if mode=='confirmation' else 'Planned Limit Entry'):
                dict(start=r.start,end=r.end,metrics=r.metrics) for mode,r in results.items()}
    for r in results.values():r.mode_comparison=comparison
    return results
