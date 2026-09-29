"""Render real saved planned entry orders and exact user's current example."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import json
from pathlib import Path
from dataclasses import replace
from PySide6 import QtWidgets
from rahamasin.storage import Repository
from rahamasin.strategy.engine import Strategy
from rahamasin.models import Config,Candle
from rahamasin.ui.window import Window
app=QtWidgets.QApplication([]);repo=Repository('reports/research.sqlite3')
out=Path('reports/planned/ui');out.mkdir(exist_ok=True)
w=Window(repo);w.show()
raw=json.loads(Path('tests/fixtures/planned_real.json').read_text())
cs=[Candle(**c) for c in raw['candles']]
s,z=Strategy(Config(entry_mode='planned_limit')).analyze(cs)
w.show_market((cs,'Binance · ONDO/USDT','Historical planned order',s,z,'4h'))
app.processEvents();w.grab().save(str(out/'historical-plan.png'))
summary=json.loads(Path('reports/planned/results.json').read_text())
event=next(e for e in summary['planned_limit']['pipeline']['order_events'] if e['event']=='submitted' and e['setup']['state']=='SHORT')
cs=repo.candles('Binance · ONDO/USDT','4h',0,event['created']+14400)[-500:]
s,z=Strategy(Config(entry_mode='planned_limit')).analyze(cs)
w.config=replace(w.config,entry_mode='planned_limit')
w.show_market((cs,'Binance · ONDO/USDT','Historical planned short',s,z,'4h'))
app.processEvents();w.grab().save(str(out/'historical-short.png'))
w.config=replace(w.config,entry_mode='confirmation')
cs=repo.candles('Binance · ONDO/USDT','4h',0,2000000000)[-500:]
s,z=Strategy().market(cs);w.show_market((cs,'Binance · ONDO/USDT','Exact requested cached example',s,z,'4h'))
app.processEvents();w.grab().save(str(out/'current-example.png'))
summary=json.loads(Path('reports/planned/results.json').read_text())
for mode,m in summary.items():
    r=repo.load_run(m['run_id']);cs=repo.candles(r.source,'4h',r.start-500*14400,r.end)
    w.show_result((r,cs,'Independent '+mode+' results'));w.tabs.setCurrentIndex(1)
    app.processEvents();w.grab().save(str(out/(mode+'-results.png')))
w.close()
