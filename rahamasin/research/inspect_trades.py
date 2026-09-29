"""Seeded visual sample; render existing inspector, not a new plotting shortcut."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
import random
from pathlib import Path
from datetime import datetime, timezone
from PySide6 import QtWidgets
from ..storage import Repository
from ..ui.window import Window
from .v1.backtest import Backtester
from .v1.models import Config
from .diagnostics import trade_rows


def main():
    folder=Path('reports/inspection'); folder.mkdir(exist_ok=True)
    repo=Repository('reports/research.sqlite3')
    source='Binance · ONDO/USDT'
    end=int(datetime(2026,9,21,tzinfo=timezone.utc).timestamp())
    start=int(datetime(2026,3,21,tzinfo=timezone.utc).timestamp())
    cs=repo.candles(source,'4h',0,end)
    original=Backtester(Config()).run(cs,'4h',start,end,source)
    result=repo.load_run(repo.save_run(original))  # actual legacy-load compatibility
    rows=trade_rows(original,cs)
    rng=random.Random(20260921)
    selection=[]
    for outcome in ['WIN','LOSS']:
        pool=[i for i,t in enumerate(result.trades) if t.outcome==outcome]
        selection+=rng.sample(pool,min(5,len(pool)))
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window=Window(repo); window.show_result((result,cs,'Audit: frozen original 4h strategy'))
    window.tabs.setCurrentIndex(2); window.show()
    records=[]
    for i in selection:
        t=result.trades[i]
        window.trade_table.selectRow(i)
        for causal in [True,False]:
            window.at_signal.setChecked(causal); window.inspect_trade(); app.processEvents()
            suffix='signal' if causal else 'outcome'
            window.grab().save(str(folder/f'{t.outcome.lower()}-{i+1:02d}-{suffix}.png'))
        records.append(rows[i])
    (folder/'sample.json').write_text(json.dumps(records,indent=2))
    window.close()
    print('Rendered',len(selection),'seeded trades in signal-only and outcome modes.',flush=True)

if __name__=='__main__':
    main()
