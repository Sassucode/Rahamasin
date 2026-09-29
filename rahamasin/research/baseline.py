from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from ..storage import Repository
from .v1.backtest import Backtester
from .v1.models import Config
from .diagnostics import trade_rows, groups, markdown_groups, export_rows

if __name__ == '__main__':
    source = 'Binance · ONDO/USDT'
    start = int(datetime(2026,3,21,tzinfo=timezone.utc).timestamp())
    end = int(datetime(2026,9,21,tzinfo=timezone.utc).timestamp())
    # Read user cache without creating or migrating their active database.
    db = sqlite3.connect(f'file:{Path.home()}/.rahamasin/rahamasin.sqlite3?mode=ro',uri=True)
    from ..models import Candle
    cs = [Candle(*r) for r in db.execute('SELECT time,open,high,low,close,volume FROM candles WHERE source=? AND timeframe=? AND time<? ORDER BY time',(source,'4h',end))]
    db.close()
    result = Backtester(Config()).run(cs,'4h',start,end,source)
    rows = trade_rows(result,cs)
    export_rows(Path('reports/original-six-month-trades.csv'),rows)
    export_rows(Path('reports/original-six-month-losses.csv'),[r for r in rows if r['net_r']<0])
    Path('reports/ORIGINAL_DIAGNOSTICS.md').write_text('# Original six-month diagnostics\n\n'+str(result.metrics)+'\n\n'+markdown_groups(groups(rows)))
    print(result.metrics,flush=True)
