"""Render actual audit results and causally frozen rejected candidates."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import json
from pathlib import Path
from PySide6 import QtWidgets
from rahamasin.storage import Repository
from rahamasin.ui.window import Window
app=QtWidgets.QApplication([]);repo=Repository('reports/research.sqlite3')
out=Path('reports/pipeline/ui');out.mkdir(exist_ok=True)
summary=json.loads(Path('reports/pipeline/results.json').read_text())
r=repo.load_run(summary['4h']['Current six months']['run_id']);cs=repo.candles(r.source,'4h',0,r.end)
w=Window(repo);w.show_result((r,cs,'Actual Binance ONDO/USDT · structure-v2.1'));w.show()
for tab in [1,2]:
    w.tabs.setCurrentIndex(1);w.diagnostic_tabs.setCurrentIndex(tab);app.processEvents();w.grab().save(str(out/f'diagnostics-{tab}.png'))
w.tabs.setCurrentIndex(2)
for i in range(len(r.trades)):
    w.trade_table.selectRow(i);w.select_trade()
    for at_signal in [True,False]:
        w.at_signal.setChecked(at_signal);w.inspect_trade();app.processEvents()
        w.grab().save(str(out/(f'trade-{i+1}-'+('signal.png' if at_signal else 'outcome.png'))))
for i,record in enumerate(json.loads(Path('reports/pipeline/before.json').read_text())['late_stage_examples']):
    w.rejected_record=record;w.inspect_rejected();app.processEvents();w.grab().save(str(out/f'before-rejected-{i+1}.png'))
if w.active_rejections:
    w.open_rejected(len(w.active_rejections)-1);app.processEvents();w.grab().save(str(out/'after-rejected.png'))
w.close()
