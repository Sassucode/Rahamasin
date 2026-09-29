from dataclasses import replace,asdict
import pytest
from rahamasin.models import Candle,Config,Zone
from rahamasin.strategy.engine import (Strategy,confirmation_paths,freshness_reason,
    geometry,next_open_fill,previous_tests)
from rahamasin.strategy.levels import track_zone,pivots
from rahamasin.backtest.engine import Backtester
from rahamasin.storage import Repository
from test_strategy_v2 import fixture,zone,seed_history
from test_core import wave,Once


def test_completed_retests_not_current_episode_or_creation():
    cfg=Config();z=zone(role_retests=3,in_touch=True)
    assert previous_tests(z)==2
    assert freshness_reason(z,100000,3600,cfg) is None
    assert freshness_reason(replace(z,in_touch=False),100000,3600,cfg)=='rejected_too_many_touches'
    assert previous_tests(zone())==0


def test_role_age_after_break_does_not_reset_quality_history():
    z=zone(age_bars=400,breakout_time=90000,flips=1,failed_holds=3)
    assert freshness_reason(z,100000,3600,Config()) is None
    assert z.failed_holds==3
    assert freshness_reason(replace(z,breakout_time=0),100000,3600,Config())=='rejected_zone_too_old'


def test_reclaim_is_separate_from_wick_and_historical_failure():
    cs,zs=fixture()
    cs[-2]=Candle(cs[-2].time,10.1,10.3,9.5,9.6)
    cs[-1]=Candle(cs[-1].time,9.7,10.8,9.6,10.75)
    z=replace(zs[0],role_failed_holds=1,failed_holds=1)
    paths=confirmation_paths(cs,z,'LONG',1,Config())
    assert 'Reclaim' in paths and 'Rejection' not in paths
    s=Strategy().evaluate(cs,[z,zs[1]])
    assert s.state=='LONG' and s.features['confirmation']=='Reclaim'


def test_first_breakout_retest_does_not_require_wick():
    cs,zs=fixture()
    z=replace(zs[0],origin_role='resistance',flips=1,breakout_time=cs[-5].time,role_retests=1,in_touch=True)
    cs[-1]=Candle(cs[-1].time,10.05,10.7,9.98,10.6)
    paths=confirmation_paths(cs,z,'LONG',1,Config())
    assert 'Breakout-retest' in paths and 'Rejection' not in paths
    assert 'Breakout-retest' not in confirmation_paths(cs,replace(z,role_retests=2),'LONG',1,Config())


def test_rejection_midpoint_hold_does_not_require_far_edge():
    cs,zs=fixture()
    cs[-1]=Candle(cs[-1].time,10.1,10.3,9.4,10.15)
    assert 'Rejection' in confirmation_paths(cs,zs[0],'LONG',1,Config())
    assert cs[-1].close<zs[0].high


def test_short_paths_are_symmetric():
    cs,zs=fixture()
    cs[-2]=Candle(cs[-2].time,10.1,10.3,9.5,9.6)
    cs[-1]=Candle(cs[-1].time,9.7,10.8,9.6,10.75)
    mirror=[Candle(c.time,30-c.open,30-c.low,30-c.high,30-c.close) for c in cs]
    z=replace(zs[0],low=30-zs[0].high,high=30-zs[0].low,role='resistance')
    assert confirmation_paths(mirror,z,'SHORT',1,Config())==confirmation_paths(cs,zs[0],'LONG',1,Config())


def test_consecutive_overlap_not_episode_age():
    cs,zs=fixture()
    z=replace(zs[0],in_touch=True,last_touch_time=cs[-3].time,role_retests=1)
    s=Strategy().evaluate(cs,[z,zs[1]])
    assert 'rejected_prolonged_overlap' not in s.pipeline['rejections']
    assert s.state=='LONG'
    for j in range(-5,-1):cs[j]=Candle(cs[j].time,10.3,10.9,9.9,10.4)
    s=Strategy().evaluate(cs,[z,zs[1]])
    assert s.pipeline['rejections'].get('rejected_prolonged_overlap',0)>0


def test_old_recovered_target_is_not_discarded():
    cs,zs=fixture()
    zs[1]=replace(zs[1],age_bars=400,role_failed_holds=2)
    s=Strategy().evaluate(cs,zs)
    assert s.state=='LONG' and s.target==zs[1].low
    blocked=Strategy().evaluate(cs,zs+[zone(11.8,12.1,'resistance')])
    assert blocked.state=='NO TRADE'  # don't stretch target to farther zone


def test_next_open_only_realistic_price_and_revalidation():
    cs,zs=fixture();s=Strategy().evaluate(cs,zs)
    assert s.features['execution']=='next_open' and s.entry==cs[-1].close
    entry,error=next_open_fill(s,10.7,Config())
    assert error is None and entry==pytest.approx(10.7*1.0005)
    assert next_open_fill(s,13,Config())[0] is None
    assert next_open_fill(s,9,Config())[0] is None


def test_rr_default_and_geometry_floor_not_relaxed():
    cfg=Config();assert cfg.min_rr==1.8
    assert geometry('LONG',10,9.5,15,1,cfg)[2]=='rejected_stop_invalid'
    assert geometry('LONG',10,9,11.9,1,cfg)[2] is None
    assert geometry('LONG',10,9,11.8,1,cfg)[2]=='rejected_rr'


def test_pivot_available_at_n_right_bars_and_seed_atr_stable():
    cs=[Candle(i*3600,12,12.2,11.8,12) for i in range(20)]
    tail=seed_history()
    cs += [replace(c,time=(20+i)*3600) for i,c in enumerate(tail)]
    cfg=Config();idx=23
    assert (idx,9.8,'support') not in pivots(cs[:-1],3)
    assert (idx,9.8,'support') in pivots(cs,3)
    z=track_zone(cs,idx,9.8,'support',cfg)
    assert z is not None and z.created_time==cs[idx+3].time
    shifted=track_zone(cs[5:],idx-5,9.8,'support',cfg)
    assert (z.low,z.high)==(shifted.low,shifted.high)
    assert track_zone(cs[15:],idx-15,9.8,'support',cfg) is None


def test_trace_and_candidate_records_are_causal_and_serializable():
    cs,zs=fixture();e=Strategy()
    s=e.evaluate(cs,zs)
    assert s.pipeline['funnel']['final_LONG_signals']==1
    assert s.pipeline['funnel']['minimum_rr_passed']>=1
    bad=e.evaluate(cs,[replace(zs[0],age_bars=400),zs[1]])
    r=bad.pipeline['rejected_candidates'][0]
    assert r['primary_rejection_reason']=='rejected_zone_too_old'
    assert r['stop_candidate'] is not None and r['target_candidate'] is not None
    import json;json.dumps(bad.pipeline,allow_nan=False)
    future=e.evaluate(cs,[replace(zs[0],created_time=cs[-1].time),zs[1]])
    assert future.state=='NO TRADE'


def test_funnel_counts_every_test_bar_even_in_position_and_roundtrips(tmp_path):
    cs=wave(100)
    r=Backtester(Config()).run(cs,'1h',40*3600,100*3600)
    assert r.pipeline['funnel']['candles_evaluated']==60
    assert len(r.pipeline['per_candle'])==60
    assert len(r.pipeline['rejected_candidates'])<=50
    assert r.pipeline['funnel']['orders_actually_filled']==len(r.trades)
    repo=Repository(tmp_path/'trace.sqlite3')
    assert repo.load_run(repo.save_run(r)).pipeline==r.pipeline


def test_future_candles_cannot_change_new_signal_or_trace():
    cs=wave(140);cut=cs[95].time;engine=Strategy()
    before=engine.analyze(cs[:96])
    after=cs[:96]+[replace(c,open=100,high=200,low=.01,close=150) for c in cs[96:]]
    assert engine.analyze(after,as_of=cut)==before


def test_real_active_signal_and_executed_trade_regression():
    import json
    from pathlib import Path
    raw=json.loads(Path('tests/fixtures/pipeline_active.json').read_text())
    cs=[Candle(**c) for c in raw['candles']];expected=raw['trade'];cut=expected['setup']['signal_time']
    engine=Strategy();signal,_=engine.analyze(cs,as_of=cut)
    assert signal.state=='SHORT' and signal.features['confirmation']=='Breakout-retest'
    assert signal.entry==expected['setup']['entry']
    changed=[c if c.time<=cut else replace(c,open=100,high=200,low=.01,close=150) for c in cs]
    assert engine.analyze(changed,as_of=cut)==engine.analyze(cs,as_of=cut)
    result=Backtester(Config()).run(cs,'4h',cut,cs[-1].time+14400,raw['source'])
    assert len(result.trades)==1
    trade=result.trades[0]
    assert trade.entry_time==expected['entry_time']
    assert trade.entry_price==expected['entry_price']
    assert trade.r==expected['r']
