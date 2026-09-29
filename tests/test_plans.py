from dataclasses import replace
import json
import pytest
from rahamasin.models import Candle,Config
from rahamasin.strategy.engine import Strategy
from rahamasin.backtest.engine import Backtester,planned_limit_step
from rahamasin.backtest.evaluation import evaluate_modes
from rahamasin.storage import Repository
from test_strategy_v2 import fixture,zone
from test_core import wave


def planned_fixture(monkeypatch):
    cs,zs=fixture()
    cs[-1]=Candle(cs[-1].time,11,11.5,10.8,11)
    monkeypatch.setattr('rahamasin.strategy.engine.pivots',lambda *args:[(20,9.2,'support'),(21,15,'resistance')])
    return cs,zs


def test_planned_long_and_short_geometry_without_confirmation(monkeypatch):
    cs,zs=planned_fixture(monkeypatch)
    p=Strategy().plans(cs,zs)[0]
    assert p.state=='LONG' and p.entry==10 and p.stop<9.2 and p.target==14
    assert p.features['confirmation']=='Not yet confirmed'
    assert p.rr==(p.target-p.entry)/(p.entry-p.stop)
    assert p.features['setup_kind']=='PLANNED'
    cs=[replace(c,open=30-c.open,high=30-c.low,low=30-c.high,close=30-c.close) for c in cs]
    zs=[zone(19.8,20.2,'resistance'),zone(15.6,16,'support')]
    monkeypatch.setattr('rahamasin.strategy.engine.pivots',lambda *args:[(20,20.8,'resistance')])
    p=Strategy().plans(cs,zs)[0]
    assert p.state=='SHORT' and p.entry==20 and p.stop>20.8 and p.target==16


def test_plans_reject_rr_distance_overused_future_and_no_target(monkeypatch):
    cs,zs=planned_fixture(monkeypatch)
    assert not Strategy(Config(min_rr=10)).plans(cs,zs)
    assert not Strategy(Config(plan_max_distance_atr=.1)).plans(cs,zs)
    assert not Strategy().plans(cs,[replace(zs[0],role_retests=8),zs[1]])
    assert not Strategy().plans(cs,[replace(zs[0],created_time=cs[-1].time),zs[1]])
    assert not Strategy().plans(cs,[zs[0]])


def test_limit_expiry_fill_never_fill_invalidation_and_target(monkeypatch):
    cs,zs=planned_fixture(monkeypatch);p=Strategy(Config(entry_mode='planned_limit')).plans(cs,zs)[0]
    t=cs[-1].time+3600
    assert planned_limit_step(p,Candle(t,11,11.2,10.5,11))==(None,None)
    assert planned_limit_step(p,Candle(t,11,11.2,9.9,10.2))==((10,False),'filled')
    assert planned_limit_step(p,Candle(t,9.8,10.2,9.5,10))==((9.8,True),'filled')
    assert planned_limit_step(p,Candle(p.features['expires_at'],11,11.2,9,10))==(None,'expired')
    assert planned_limit_step(p,Candle(t,p.stop-.1,10,8,9))==(None,'invalidated_open')
    assert planned_limit_step(p,Candle(t,11,14.1,10.5,12))==(None,'target_before_entry')
    # Both entry and target touched, unknowable ordering: conservative cancellation.
    assert planned_limit_step(p,Candle(t,11,14.1,9.9,12))==(None,'target_before_entry')


class FrozenOnce:
    def __init__(self,p):self.p=p
    def analyze(self,cs):
        from rahamasin.models import Setup
        return (self.p if cs[-1].time==self.p.signal_time else Setup()),[]


def test_pending_order_persists_frozen_then_expires(monkeypatch):
    cs,zs=planned_fixture(monkeypatch);cfg=Config(entry_mode='planned_limit',plan_expiry_bars=2)
    p=Strategy(cfg).plans(cs,zs)[0]
    tail=[Candle(cs[-1].time+i*3600,11,11.1,10.5,11) for i in range(1,5)]
    r=Backtester(cfg,FrozenOnce(p)).run(cs+tail,'1h',cs[-1].time,tail[-1].time+3600)
    assert not r.trades
    assert [e['event'] for e in r.pipeline['order_events']]==['submitted','expired']
    assert r.pipeline['funnel']['orders_submitted']==1
    assert r.pipeline['funnel']['orders_unfilled_or_cancelled']==1
    assert all(e['setup']['entry']==p.entry for e in r.pipeline['order_events'])


def test_backtest_limit_available_only_next_bar_and_fills_later(monkeypatch):
    cs,zs=planned_fixture(monkeypatch);cfg=Config(entry_mode='planned_limit')
    p=Strategy(cfg).plans(cs,zs)[0]
    tail=[Candle(cs[-1].time+3600,11,11.2,10.5,11),Candle(cs[-1].time+7200,11,11.2,9.9,10.1),Candle(cs[-1].time+10800,10.1,14.2,10,14)]
    r=Backtester(cfg,FrozenOnce(p)).run(cs+tail,'1h',cs[-1].time,tail[-1].time+3600)
    assert len(r.trades)==1 and r.trades[0].entry_time==tail[1].time
    assert r.trades[0].entry_price==10 and r.trades[0].setup==p
    assert r.trades[0].exit_reason=='Target'


def test_separate_modes_and_storage(tmp_path):
    results=evaluate_modes(wave(100),'1h',40*3600,100*3600,Config())
    assert set(results)=={'confirmation','planned_limit'}
    repo=Repository(tmp_path/'modes.sqlite3')
    for mode,r in results.items():
        assert r.config.entry_mode==mode and r.pipeline['entry_mode']==mode
        assert set(r.mode_comparison)=={'Confirmation Entry','Planned Limit Entry'}
        assert repo.load_run(repo.save_run(r)).mode_comparison==r.mode_comparison


def test_plan_future_data_independence(monkeypatch):
    cs,zs=planned_fixture(monkeypatch)
    monkeypatch.setattr('rahamasin.strategy.engine.detect_zones',lambda *args:zs)
    engine=Strategy(Config(entry_mode='planned_limit'))
    expected,_=engine.analyze(cs)
    assert expected.state=='LONG'
    future=cs+[Candle(cs[-1].time+3600,100,200,.01,150)]
    assert engine.analyze(future,as_of=cs[-1].time)==engine.analyze(cs)
    # Market card also cannot turn a plan into an active signal without confirmation.
    shown,_=engine.market(cs)
    assert shown.features['setup_kind']=='PLANNED'


def test_short_limit_and_stop_first_after_touch(monkeypatch):
    cs,zs=planned_fixture(monkeypatch);p=Strategy().plans(cs,zs)[0]
    p=replace(p,state='SHORT',entry=20,stop=21,target=16)
    t=p.signal_time+3600
    assert planned_limit_step(p,Candle(t,19,20.2,18.5,20))==((20,False),'filled')
    assert planned_limit_step(p,Candle(t,21.1,22,20,21))==(None,'invalidated_open')
    assert planned_limit_step(p,Candle(t,19,19.5,15.9,16))==(None,'target_before_entry')
    from rahamasin.backtest.engine import exit_fill
    assert exit_fill(p,Candle(t,19,21.2,18,20),True,False)[0]==21


def test_plan_ui_shows_full_geometry_and_mode_choice(monkeypatch,tmp_path):
    import os
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6 import QtWidgets
    from rahamasin.ui.window import Window
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    cs,zs=planned_fixture(monkeypatch);p=Strategy().plans(cs,zs)[0]
    w=Window(Repository(tmp_path/'ui.sqlite3'))
    w.show_market((cs,'Synthetic fixture','test',p,zs,'1h'))
    card=w.card.toPlainText()
    assert 'PLANNED LONG' in card and 'NOT YET CONFIRMED' in card
    assert 'Preferred entry' in card and 'Take profit' in card and 'Distance to entry' in card
    assert w.entry_mode.findData('both')>=0
    w.settings['entry_mode'].setCurrentIndex(1);w.save_settings()
    assert w.repo.config().entry_mode=='planned_limit'
    w.close()


def test_real_historical_plan_is_nonvacuous_and_future_safe():
    from pathlib import Path
    raw=json.loads(Path('tests/fixtures/planned_real.json').read_text())
    cs=[Candle(**c) for c in raw['candles']]
    engine=Strategy(Config(entry_mode='planned_limit'))
    plan,zones=engine.analyze(cs)
    assert plan.state==raw['setup']['state']!='NO TRADE'
    assert plan.features['setup_kind']=='PLANNED'
    for key in ('entry','stop','target','rr'):assert getattr(plan,key)==raw['setup'][key]
    future=cs+[Candle(cs[-1].time+14400,100,200,.01,150)]
    assert engine.analyze(future,as_of=cs[-1].time)==(plan,zones)


def test_ambiguous_entry_target_stop_does_not_erase_loss(monkeypatch):
    cs,zs=planned_fixture(monkeypatch);p=Strategy().plans(cs,zs)[0]
    bar=Candle(p.signal_time+3600,11,14.5,p.stop-.1,10)
    fill,event=planned_limit_step(p,bar)
    assert fill==(p.entry,False) and event=='filled'
    from rahamasin.backtest.engine import exit_fill
    assert exit_fill(p,bar,True,False)[0]==p.stop
