"""Optional offscreen audit UI check using the locally generated research database."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import json
from pathlib import Path
from PySide6 import QtWidgets
from rahamasin.storage import Repository
from rahamasin.ui.window import Window
from rahamasin.strategy.engine import Strategy

app=QtWidgets.QApplication([])
repo=Repository('reports/research.sqlite3')
comparison=json.loads(Path('reports/comparison.json').read_text())
out=Path('reports/ui');out.mkdir(exist_ok=True)
w=Window(repo)
r=repo.load_run(comparison['4h']['v2_saved_run_id'])
cs=repo.candles(r.source,r.timeframe,0,r.end)
s,zs=Strategy(r.config).analyze(cs)
w.show_market((cs,r.source,'Actual cached ONDO; frozen v2',s,zs,r.timeframe))
w.show_result((r,cs,'Audit validation'));w.show()
for i in [0,1,3,4]:
    w.tabs.setCurrentIndex(i);app.processEvents();w.grab().save(str(out/f'tab-{i}.png'))
r=repo.load_run(comparison['1h']['v2_saved_run_id'])
cs=repo.candles(r.source,r.timeframe,0,r.end)
w.show_result((r,cs,'Only observed v2 trade; not enough evidence'));w.tabs.setCurrentIndex(2)
for causal in [True,False]:
    w.at_signal.setChecked(causal);w.inspect_trade();app.processEvents()
    w.grab().save(str(out/('v2-signal.png' if causal else 'v2-outcome.png')))
w.close()
