"""Compare independent entry modes on the same cached ONDO 4h history."""
from pathlib import Path
from dataclasses import asdict
from datetime import datetime,timezone
import json,hashlib
from ..models import Config
from ..storage import Repository
from ..strategy.engine import Strategy
from ..backtest.evaluation import evaluate_modes
from .diagnostics import trade_rows,export_rows

def main():
    repo=Repository('reports/research.sqlite3');out=Path('reports/planned');out.mkdir(exist_ok=True)
    start=int(datetime(2026,3,22,tzinfo=timezone.utc).timestamp());end=int(datetime(2026,9,22,tzinfo=timezone.utc).timestamp())
    cs=repo.candles('Binance · ONDO/USDT','4h',start-500*14400,end)
    (out/'manifest.json').write_text(json.dumps(dict(config=asdict(Config()),start=start,end=end,hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('rahamasin').rglob('*.py')}),indent=2))
    results=evaluate_modes(cs,'4h',start,end,Config(),'Binance · ONDO/USDT')
    summary={}
    for mode,r in results.items():
        rid=repo.save_run(r)
        summary[mode]=dict(run_id=rid,metrics=r.metrics,evaluation=r.evaluation,config=asdict(r.config),pipeline=r.pipeline)
        export_rows(out/(mode+'-trades.csv'),trade_rows(r,cs))
        print(mode,rid,r.metrics,flush=True)
    (out/'results.json').write_text(json.dumps(summary,indent=2))
    latest=repo.candles('Binance · ONDO/USDT','4h',0,2000000000)[-500:]
    setup,zones=Strategy().market(latest)
    (out/'current-example.json').write_text(json.dumps(dict(candle=asdict(latest[-1]),setup=asdict(setup)),indent=2))
    # Preserve a real planned order snapshot as a causal regression fixture.
    events=results['planned_limit'].pipeline['order_events']
    if events:
        e=events[0];cut=e['created'];prefix=[c for c in cs if c.time<=cut][-500:]
        Path('tests/fixtures/planned_real.json').write_text(json.dumps(dict(candles=[asdict(c) for c in prefix],setup=e['setup']),indent=2))
if __name__=='__main__':main()
