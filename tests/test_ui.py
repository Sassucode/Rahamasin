import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6 import QtWidgets
from rahamasin.ui.window import Window
from rahamasin.storage import Repository
from rahamasin.strategy.engine import Strategy
from rahamasin.backtest.engine import Backtester
from rahamasin.models import Config
from test_core import wave, Once


def test_populated_desktop_and_inspector(tmp_path):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    repo = Repository(tmp_path/'ui.sqlite3')
    w = Window(repo)
    candles = wave()
    setup,zones = Strategy().analyze(candles)
    w.show_market((candles,'Test fixture','Synthetic test data',setup,zones,'1h'))
    result = Backtester(Config(),Once()).run(candles,'1h',0,160*3600,'fixture')
    repo.save_run(result)
    w.show_result((result,candles,'Test fixture'))
    w.show(); app.processEvents()
    assert w.tabs.count() == 5
    assert w.levels.rowCount() == len(zones)
    assert w.trade_table.rowCount() == len(result.trades) > 0
    w.trade_table.selectRow(0); w.inspect_trade()
    assert 'net R' in w.trade_reasons.toPlainText()
    assert w.grab().save(str(tmp_path/'populated.png'))
    w.restore_run()
    from rahamasin.backtest.evaluation import evaluate
    split=evaluate(candles,'1h',40*3600,160*3600,Config(),'fixture')
    repo.save_run(split)
    w.show_result((split,candles,'Independent split test'))
    assert w.split_table.rowCount()==3
    w.diagnostic_segment.setCurrentText('Evaluation 30%')
    assert w.diagnostic_table.rowCount()>0
    assert 'insufficient evidence' in w.evidence_note.text()
    w.close()


def test_rejected_candidate_inspector_is_cutoff_safe(tmp_path):
    from dataclasses import replace
    from test_pipeline import fixture
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    repo=Repository(tmp_path/'rejected.sqlite3');w=Window(repo)
    candles,zones=fixture()
    setup=Strategy().evaluate(candles,[replace(zones[0],age_bars=400),zones[1]])
    record=setup.pipeline['rejected_candidates'][0]
    result=Backtester(Config()).run(wave(100),'1h',40*3600,100*3600)
    result.pipeline['rejected_candidates']=[record]
    w.show_result((result,candles,'Rejected fixture'))
    assert w.rejected_table.rowCount()==1
    assert 'candles_evaluated' in w.pipeline_view.toPlainText()
    seen=[]
    w.inspector.draw=lambda cs,*args:seen.extend(cs)
    w.open_rejected(0)
    w.at_signal.setChecked(False)
    assert 'NOT A TRADE' in w.trade_reasons.toPlainText()
    assert seen and max(c.time for c in seen)<=record['timestamp']
    w.close()
