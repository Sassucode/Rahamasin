from dataclasses import asdict, replace
import math
import pytest
from rahamasin.models import Candle, Config, Zone, Setup
from rahamasin.strategy.levels import pivots, detect_zones, atr
from rahamasin.strategy.engine import Strategy
from rahamasin.backtest.engine import Backtester, exit_fill
from rahamasin.storage import Repository
from rahamasin.data.providers import MarketData, validate


def wave(n=160):
    return [Candle(i*3600,10+math.sin(i*.3),10.3+math.sin(i*.3),9.7+math.sin(i*.3),10+math.sin(i*.3)) for i in range(n)]


def zone(low,high):
    return Zone(low,high,5,4,5,4,2,100,0,4,0,0,70,80,3)


def long_fixture():
    h = [Candle(i*3600,11,11.5,10.5,11) for i in range(40)]
    h[-1] = Candle(39*3600,10.1,10.9,9.8,10.8)
    return h,[zone(9.9,10.1),zone(13,13.2)]


def test_pivot_confirmation_does_not_repaint():
    cs = [Candle(i, p,p+.1,p-.1,p) for i,p in enumerate([3,2,1,2,3])]
    assert pivots(cs[:3],2) == []
    assert pivots(cs,2) == [(2,.9,'support')]
    assert pivots(cs+[Candle(5,1,1.1,.8,1)],2)[0] == (2,.9,'support')


def test_clustering_strength_and_reactions():
    from rahamasin.research.v1.engine import Strategy
    from rahamasin.research.v1.levels import detect_zones
    from rahamasin.research.v1.models import Config
    zones = detect_zones(wave(),Config(pivot_span=2))
    assert 2 <= len(zones) <= 4
    assert all(0 < z.strength <= 100 for z in zones)
    assert all(z.touches >= 3 for z in zones)
    assert all(z.successes <= z.touches and z.median_reaction > 0 for z in zones)
    z = zones[0]
    expected = min(z.touches,8)*5+z.successes/z.touches*20+min(z.reaction_atr,3)*10+10/(1+z.recency_bars/50)
    assert z.strength == pytest.approx(expected)
    assert all(a.high < b.low for a,b in zip(zones,zones[1:]))


def test_long_structural_stop_target_and_rr():
    from rahamasin.research.v1.engine import Strategy
    from rahamasin.research.v1.levels import detect_zones
    from rahamasin.research.v1.models import Config
    history,zones = long_fixture()
    s = Strategy().evaluate(history,zones)
    assert s.state == 'LONG'
    assert s.entry == 10
    assert s.stop == pytest.approx(9.8-atr(history[:-1])*.2)
    assert s.target == 13
    assert s.rr == pytest.approx((13-10)/(10-s.stop))
    assert s.reasons and s.zone == zones[0]


def test_short_is_symmetric():
    from rahamasin.research.v1.engine import Strategy
    from rahamasin.research.v1.levels import detect_zones
    from rahamasin.research.v1.models import Config
    history,zones = long_fixture()
    reflected = [Candle(c.time,30-c.open,30-c.low,30-c.high,30-c.close) for c in history]
    s = Strategy().evaluate(reflected,[zone(30-z.high,30-z.low) for z in zones])
    assert s.state == 'SHORT'
    assert s.entry == 20 and s.target == 17
    assert s.stop > 20.2


def test_rr_rejection_and_no_touch_only_entry():
    from rahamasin.research.v1.engine import Strategy
    from rahamasin.research.v1.levels import detect_zones
    from rahamasin.research.v1.models import Config
    h,z = long_fixture()
    assert Strategy(Config(min_rr=20)).evaluate(h,z).state == 'NO TRADE'
    h[-1] = replace(h[-1],close=10.05)
    assert Strategy().evaluate(h,z).state == 'NO TRADE'


def test_future_candles_cannot_change_historical_signal():
    cs = wave()
    strategy = Strategy()
    cutoff = cs[100].time
    original = strategy.analyze(cs[:101])
    altered = cs[:101]+[Candle(c.time,1000,2000,.001,1500) for c in cs[101:]]
    assert strategy.analyze(altered,as_of=cutoff) == original
    assert strategy.analyze(cs,as_of=cutoff) == original


def test_analysis_matches_every_prefix():
    cs = wave(110)
    engine = Strategy()
    for i in range(40,110):
        assert engine.analyze(cs,as_of=cs[i].time) == engine.analyze(cs[:i+1])


def active():
    return Setup('LONG',0,9.9,10.1,10,9,12,2,['fixture'],zone(9.9,10.1))


def test_same_candle_stop_target_and_gap():
    s = active()
    assert exit_fill(s,Candle(1,10,13,8,11))[0] == 9
    assert exit_fill(s,Candle(1,8,13,7,11))[0] == 8
    assert exit_fill(s,Candle(1,10,13,9.5,11),entry_candle=True) is None


class Once:
    def __init__(self): self.calls=[]
    def analyze(self, history):
        self.calls.append(history[:])
        return (replace(active(),signal_time=history[-1].time) if len(self.calls)==1 else Setup()),[]


def test_backtest_next_bar_costs_and_shared_engine():
    cs = [Candle(i*3600,10,10.5,9.5,10) for i in range(5)]
    cs[2] = Candle(7200,10,13,8,10)
    strategy = Once()
    result = Backtester(Config(fee_bps=0,slippage_bps=0),strategy).run(cs,'1h',0,18000)
    assert len(result.trades) == 1
    t = result.trades[0]
    assert t.entry_time == 3600 and t.setup.signal_time == 0
    assert t.r == -1 and t.exit_price == 9
    assert result.metrics['maximum_drawdown_pct'] == pytest.approx(1)
    assert isinstance(Backtester(Config()).strategy,Strategy)
    assert all(h[-1].time < 18000 for h in strategy.calls)


def test_pending_expires_and_gap_cancels():
    cs = [Candle(0,10,10.5,9.5,10),Candle(3600,8,11,7,10),Candle(7200,10,13,9.5,12)]
    assert Backtester(Config(),Once()).run(cs,'1h',0,10800).trades == []


def test_backtest_rejects_missing_bars():
    with pytest.raises(ValueError,match='gaps'):
        Backtester(Config()).run(wave(5)[::2],'1h',0,18000)


def test_repository_roundtrip(tmp_path):
    repo = Repository(tmp_path/'test.sqlite3')
    cs = wave(5); repo.save_candles('test','1h',cs)
    assert repo.candles('test','1h',0,18000) == cs
    repo.save_config(Config(min_rr=2)); assert repo.config().min_rr == 2
    result = Backtester(Config(),Once()).run(cs,'1h',0,18000,'test')
    run_id = repo.save_run(result)
    loaded = repo.load_run(run_id)
    assert asdict(loaded)['trades'] == asdict(result)['trades']
    assert loaded.config == result.config


def test_closed_candle_filter_and_invalid_data():
    assert len(validate(wave(5),'1h',0,4*3600+100)) == 4
    with pytest.raises(ValueError):
        validate([Candle(0,10,9,11,10)],'1h',0,3600)


def test_provider_fallback_and_cache(tmp_path):
    class Broken:
        name = 'broken'
        def fetch(self,*args): raise ValueError('unavailable')
    class Good:
        name = 'good'
        def fetch(self,tf,start,end): return wave(5)
    repo = Repository(tmp_path/'data.sqlite3')
    service = MarketData(repo,[Broken(),Good()])
    cs,source,note = service.load('1h',0,18000)
    assert source == 'good' and len(cs) == 5
    cs2,source,note = service.load('1h',0,18000,offline=True)
    assert cs2 == cs and 'OFFLINE' in note


def test_backtest_future_rows_cannot_affect_completed_period():
    cs = wave(120)
    engine = Backtester(Config())
    cutoff = cs[100].time
    expected = engine.run(cs[:100],'1h',40*3600,cutoff)
    changed = cs[:100]+[Candle(c.time,500,900,.1,800) for c in cs[100:]]
    actual = engine.run(changed,'1h',40*3600,cutoff)
    assert asdict(actual) == asdict(expected)


def test_short_stop_target_and_target_fill():
    s = replace(active(),state='SHORT',stop=11,target=8)
    assert exit_fill(s,Candle(1,10,12,7,9))[0] == 11
    assert exit_fill(s,Candle(1,12,13,7,9))[0] == 12
    assert exit_fill(s,Candle(1,10,10.5,7,9)) == (8,'Target')


def test_setup_refuses_gapped_history():
    cs = wave()
    s,_ = Strategy().analyze(cs[:80]+cs[81:])
    assert s.state == 'NO TRADE' and 'gaps' in s.reasons[0]


def test_coinbase_four_hour_requires_complete_groups(monkeypatch):
    from rahamasin.data import providers
    # First UTC group is complete; second misses one hourly candle.
    rows = [[i*3600,9,11,10,10.5,2] for i in (0,1,2,3,4,5,7)]
    monkeypatch.setattr(providers,'get',lambda *a:rows)
    monkeypatch.setattr(providers.time,'sleep',lambda _:None)
    candles = providers.Coinbase().fetch('4h',0,8*3600)
    assert candles == [Candle(0,10,11,9,10.5,8)]


def test_binance_pagination_advances(monkeypatch):
    from rahamasin.data import providers
    calls = []
    def fetch(client,url,params):
        calls.append(params['startTime'])
        times = [0,3600] if params['startTime'] == 0 else [7200]
        return [[t*1000,'10','11','9','10.5','2'] for t in times]
    monkeypatch.setattr(providers,'get',fetch)
    monkeypatch.setattr(providers.time,'sleep',lambda _:None)
    candles = providers.Binance().fetch('1h',0,10800)
    assert calls == [0,7200000]
    assert [c.time for c in candles] == [0,3600,7200]
