from dataclasses import replace, asdict
import pytest
from rahamasin.models import Candle, Config, Zone, Setup
from rahamasin.research.v20.levels import strength, track_zone, detect_zones, pivots
from rahamasin.research.v20.engine import Strategy, confirmation, eligible_zone, structural_stop
from rahamasin.research.v20.context import market_context
from rahamasin.backtest.engine import Backtester, limit_fill, exit_fill
from rahamasin.backtest.evaluation import evaluate, boundaries, MemoizedStrategy
from test_core import wave, active, Once


def zone(low=9.8,high=10.2,role='support',**kwargs):
    z = Zone(low,high,1,1,20,20,3,0,0,1,0,0,70,20,10,
             role,role,1,0,0,0,0,0,0,3,.9,1,False,0)
    return replace(z,**kwargs)


def fixture():
    cs = [Candle(i*3600,11,11.5,10.5,11) for i in range(40)]
    cs[-1] = Candle(39*3600,10.4,10.9,9.45,10.85)
    return cs,[zone(),zone(14,14.4,'resistance')]


def test_decay_is_monotonic_and_impulse_is_rewarded():
    base = strength(3,.9,0,0,0,0,500,0)
    for tests,penetrations,failed,age in [(1,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,100)]:
        assert strength(3,.9,tests,penetrations,failed,age,500,0)<base
    assert strength(6,.9,0,0,0,0,500,0)>base>strength(.5,.9,0,0,0,0,500,0)


def test_significant_wick_required_and_symmetric():
    cs,zs = fixture(); c=cs[-1]; z=zs[0]
    assert confirmation(c,z,'LONG',1,.25)
    assert not confirmation(replace(c,open=9.5),z,'LONG',1,.25)
    assert not confirmation(replace(c,close=10.1),z,'LONG',1,.25)
    mirror = Candle(c.time,30-c.open,30-c.low,30-c.high,30-c.close)
    assert confirmation(mirror,zone(30-z.high,30-z.low,'resistance'),'SHORT',1,.25)


def test_v2_structural_trade_and_nearest_target():
    cs,zs = fixture(); s = Strategy().evaluate(cs,zs)
    assert s.state == 'LONG' and s.target == 14
    assert s.stop == pytest.approx(9.2)
    assert s.features['confirmation']=='Rejection'
    assert s.target_zone == zs[1]
    # Nearer structure is never skipped in order to achieve minimum R:R.
    assert Strategy().evaluate(cs,zs+[zone(11.2,11.5,'resistance')]).state=='NO TRADE'


def test_v2_short_symmetry():
    cs,zs = fixture()
    reflected = [Candle(c.time,30-c.open,30-c.low,30-c.high,30-c.close) for c in cs]
    reflected_z = [replace(z,low=30-z.high,high=30-z.low,role='resistance' if z.role=='support' else 'support') for z in zs]
    s = Strategy().evaluate(reflected,reflected_z)
    assert s.state=='SHORT' and s.stop==pytest.approx(20.8) and s.target==16


def test_freshness_failure_age_width_filters():
    z=zone(); cfg=Config()
    assert eligible_zone(z,1,cfg)
    for changed in [replace(z,role_retests=3),replace(z,retests=4),replace(z,role_failed_holds=1),
                    replace(z,age_bars=251),replace(z,high=11),replace(z,flips=2),
                    replace(z,displacement_atr=.5),replace(z,departure_efficiency=.3)]:
        assert not eligible_zone(changed,1,cfg)


def test_no_chase_no_prolonged_chop():
    cs,zs=fixture()
    cs[-1]=Candle(cs[-1].time,10.4,11.7,9.45,11.6)
    assert Strategy().evaluate(cs,zs).state=='NO TRADE'
    cs,zs=fixture()
    zs[0]=replace(zs[0],in_touch=True,last_touch_time=cs[-3].time,role_retests=1)
    assert Strategy().evaluate(cs,zs).state=='NO TRADE'


def test_tight_stops_rejected_not_widened():
    cs,zs=fixture()
    cs[-1]=Candle(cs[-1].time,10.3,10.7,9.8,10.6)
    assert Strategy().evaluate(cs,zs).state=='NO TRADE'


def test_countertrend_exception_requires_stronger_first_retest(monkeypatch):
    import rahamasin.research.v20.engine as engine
    monkeypatch.setattr(engine,'market_context',lambda *a:'BEARISH')
    cs,zs=fixture()
    assert Strategy().evaluate(cs,zs).state=='LONG'
    for z in [replace(zs[0],displacement_atr=2),replace(zs[0],role_retests=1),replace(zs[0],departure_efficiency=.7)]:
        assert Strategy().evaluate(cs,[z,zs[1]]).state=='NO TRADE'


def test_breakout_retest_is_explicit_and_first_only():
    cs,zs=fixture()
    z=replace(zs[0],origin_role='resistance',flips=1,breakout_time=cs[-5].time,role_retests=0)
    assert Strategy().evaluate(cs,[z,zs[1]]).features['confirmation']=='Breakout-retest'
    assert Strategy().evaluate(cs,[replace(z,role_retests=2),zs[1]]).state=='NO TRADE'


def seed_history():
    prices = [12,11.7,11.4,10,10.9,11.7,12.2]
    return [Candle(i*3600,p,p+.2,p-.2,p) for i,p in enumerate(prices)]


def test_seed_confirmation_displacement_fixed_width():
    cs=seed_history(); cfg=Config()
    assert track_zone(cs[:6],3,9.8,'support',cfg) is None
    z=track_zone(cs,3,9.8,'support',cfg)
    assert z is not None and z.created_time==cs[6].time
    later=cs+[Candle(7*3600,12,12.2,11.8,12)]
    z2=track_zone(later,3,9.8,'support',cfg)
    assert (z.low,z.high)==(z2.low,z2.high)
    assert z.high-z.low==pytest.approx(cfg.zone_atr*z.seed_atr)
    assert track_zone(cs,3,9.8,'support',Config(min_displacement=9)) is None


def test_two_closes_change_role_no_immediate_retest():
    cs=seed_history(); cfg=Config()
    seq=cs+[Candle(7*3600,9,9.1,8.8,9),Candle(8*3600,9,9.1,8.8,9)]
    first=track_zone(seq[:-1],3,9.8,'support',cfg)
    second=track_zone(seq,3,9.8,'support',cfg)
    assert first.role=='support' and first.flips==0
    assert second.role=='resistance' and second.flips==1
    assert second.role_retests==0 and second.breakout_time==seq[-1].time
    assert second.failed_holds>=1 and second.role_failed_holds==0


def test_touch_episodes_require_clean_separation():
    cs=seed_history(); cfg=Config()
    cs += [Candle(7*3600,10,10.1,9.7,10),Candle(8*3600,10,10.1,9.7,10)]
    z=track_zone(cs,3,9.8,'support',cfg)
    assert z.retests==1 and z.penetrations<=1
    cs += [Candle(9*3600,12,12.1,11.9,12),Candle(10*3600,12,12.1,11.9,12),Candle(11*3600,10,10.1,9.7,10)]
    assert track_zone(cs,3,9.8,'support',cfg).retests==2


def test_marketable_limits_fill_even_without_trading_back_to_limit():
    s=active()
    assert limit_fill(s,Candle(1,9.5,9.8,9.2,9.6))==(9.5,True)
    assert limit_fill(s,Candle(1,8.5,10,8,9)) is None
    short=replace(s,state='SHORT',stop=11,target=8)
    assert limit_fill(short,Candle(1,10.5,10.8,10.2,10.4))==(10.5,True)


def test_known_entry_bar_target_order_and_ambiguity():
    s=active()
    assert exit_fill(s,Candle(1,10,13,9.5,11),True,True)==(12,'Target')
    assert exit_fill(s,Candle(1,11,13,9.5,11),True,False) is None
    assert exit_fill(s,Candle(1,11,13,9.5,12.5),True,False)==(12,'Target')
    assert exit_fill(s,Candle(1,10,13,8,12.5),True,True)[0]==9


def test_r_decomposition_long_and_short():
    cs=[Candle(i*3600,10,10.5,9.5,10) for i in range(4)]
    cs[2]=Candle(7200,10,13,8,10)
    result=Backtester(Config(),Once()).run(cs,'1h',0,14400)
    t=result.trades[0]
    assert t.gross_r==-1
    assert t.r==pytest.approx(t.gross_r-t.fees_r-t.slippage_r)
    assert t.fees_r>0 and t.slippage_r>0


def test_net_rr_can_reject_a_gross_rr_pass():
    cs,zs=fixture()
    zs[1]=replace(zs[1],low=11.55,high=11.9)
    assert Strategy().evaluate(cs,zs).state=='LONG'
    assert Strategy(Config(fee_bps=100)).evaluate(cs,zs).state=='NO TRADE'


def test_v2_future_independence_and_memoization():
    cs=wave(100); strategy=Strategy()
    original=strategy.analyze(cs[:80])
    changed=cs[:80]+[replace(c,open=500,high=900,low=.1,close=600) for c in cs[80:]]
    assert strategy.analyze(changed,as_of=cs[79].time)==original
    memo=MemoizedStrategy(strategy)
    assert memo.analyze(cs[:80])[0]==original[0]
    altered=cs[:79]+[replace(cs[79],close=cs[79].close+.01)]
    memo.analyze(altered)
    assert len(memo.cache)==2


def test_independent_evaluation_boundaries_and_persistence(tmp_path):
    from rahamasin.storage import Repository
    cs=wave(100)
    cuts=boundaries(cs,'1h',40*3600,100*3600)
    assert cuts['Development 70%'][1]==cuts['Evaluation 30%'][0]
    result=evaluate(cs,'1h',40*3600,100*3600,Config())
    assert set(result.evaluation)=={'Full','Development 70%','Evaluation 30%'}
    repo=Repository(tmp_path/'v2.sqlite3')
    saved=repo.load_run(repo.save_run(result))
    assert saved.evaluation==result.evaluation and saved.strategy_version=='structure-v2.2'


def test_old_config_migrates():
    assert Config.from_dict({'min_touches':2,'min_rr':2}).min_rr==2


def test_higher_highs_lows_and_lower_highs_lows_context():
    up=[replace(c,open=c.open+i*.02,high=c.high+i*.02,low=c.low+i*.02,close=c.close+i*.02) for i,c in enumerate(wave(150))]
    down=[replace(c,open=c.open-i*.02,high=c.high-i*.02,low=c.low-i*.02,close=c.close-i*.02) for i,c in enumerate(wave(150))]
    assert market_context(up)=='BULLISH'
    assert market_context(down)=='BEARISH'
    assert market_context(wave(150))=='RANGE'


def test_short_r_decomposition_and_gap_loss_exceeds_one():
    class ShortOnce(Once):
        def analyze(self,history):
            setup,zones=super().analyze(history)
            if setup.state=='LONG':
                setup=replace(setup,state='SHORT',stop=11,target=8)
            return setup,zones
    cs=[Candle(i*3600,10,10.5,9.5,10) for i in range(4)]
    cs[2]=Candle(7200,12,13,11.5,12)
    t=Backtester(Config(),ShortOnce()).run(cs,'1h',0,14400).trades[0]
    assert t.gross_r==-2 and t.r<-2
    assert t.r==pytest.approx(t.gross_r-t.fees_r-t.slippage_r)


def test_opposing_target_quality_is_required():
    cs,zs=fixture()
    assert Strategy().evaluate(cs,[zs[0],replace(zs[1],displacement_atr=.5)]).state=='NO TRADE'
    assert Strategy().evaluate(cs,[zs[0],replace(zs[1],role_failed_holds=1)]).state=='NO TRADE'


def test_signal_time_snapshots_do_not_include_confirmation_in_level_ledger(monkeypatch):
    import rahamasin.research.v20.engine as engine
    cs,zs=fixture(); seen=[]
    def detector(history,config):
        seen.extend(history);return zs
    monkeypatch.setattr(engine,'detect_zones',detector)
    result,_=Strategy().analyze(cs)
    assert result.state=='LONG'
    assert seen==cs[:-1]


def test_real_active_v2_signal_is_causal_and_backtests_identically():
    import json
    from pathlib import Path
    d=json.loads((Path(__file__).parent/'fixtures/ondo_v2_signal.json').read_text())
    cs=[Candle(**c) for c in d['candles']]
    engine=Strategy()
    signal,_=engine.analyze(cs,as_of=d['signal_time'])
    assert signal.state=='LONG' and signal.features['alignment']=='Countertrend'
    altered=[c if c.time<=d['signal_time'] else replace(c,open=10,high=20,low=.01,close=15) for c in cs]
    assert engine.analyze(altered,as_of=d['signal_time'])[0]==signal
    assert signal.zone.created_time < signal.signal_time
    assert signal.target_zone.created_time < signal.signal_time
    result=Backtester(Config(),Strategy()).run(cs,'1h',d['signal_time'],d['exit_time'],d['source'])
    assert len(result.trades)==1
    assert result.trades[0].setup==signal
    assert result.trades[0].entry_time==d['entry_time']
    assert result.trades[0].r==pytest.approx(d['expected_net_r'])
