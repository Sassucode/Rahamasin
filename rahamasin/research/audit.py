"""Fixed-rule comparison; no optimizer. Run from project root after download."""
import gc
import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from ..storage import Repository
from ..models import Config, SECONDS
from ..strategy.engine import Strategy
from ..backtest.engine import Backtester
from ..backtest.evaluation import MemoizedStrategy, boundaries
from .v1.models import Config as V1Config
from .v1.engine import Strategy as V1Strategy
from .v1.backtest import Backtester as V1Backtester
from .diagnostics import trade_rows, groups, markdown_groups, export_rows


def iso(t):
    return datetime.fromtimestamp(t,timezone.utc).isoformat()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--coinbase-daily',action='store_true')
    args=parser.parse_args()
    out=Path('reports/coinbase') if args.coinbase_daily else Path('reports')
    out.mkdir(parents=True,exist_ok=True)
    repo=Repository(Path('reports/research.sqlite3'))
    source='Coinbase · ONDO/USD' if args.coinbase_daily else 'Binance · ONDO/USDT'
    end=int(datetime(2026,9,21,tzinfo=timezone.utc).timestamp())
    sample=int(datetime(2026,3,21,tzinfo=timezone.utc).timestamp())
    files=[Path('rahamasin')/p for p in ['models.py','strategy/engine.py','strategy/levels.py','strategy/context.py','backtest/engine.py']]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (out/'evaluation-manifest.json').write_text(json.dumps({'config':asdict(Config()),'code_sha256':hashes,'holdout_policy':'Frozen before v2 market evaluation. Retrospective holdout, previously seen v1 sample overlaps.'},indent=2))
    aggregate={}
    for tf in (['1d'] if args.coinbase_daily else ['4h','1h','1d']):
        cs=repo.candles(source,tf,0,end)[1:]  # conservatively omit listing's partial first candle
        if len(cs)<50:
            raise ValueError(f'Insufficient {tf} history')
        start=cs[40].time
        cuts=boundaries(cs,tf,start,end)
        usable=[c for c in cs if c.time>=start]
        a,b=usable[len(usable)//3].time,usable[2*len(usable)//3].time
        cuts.update({'First third':(start,a),'Middle third':(a,b),'Latest third':(b,end),'User six months':(sample,end)})
        entry={'source':source,'data_first':iso(cs[0].time),'data_last':iso(cs[-1].time),
               'candles':len(cs),'warmup_bars':40,'data_sha256':hashlib.sha256(json.dumps([asdict(c) for c in cs]).encode()).hexdigest(),'variants':{}}
        variants=[('original',V1Config(),V1Strategy(V1Config()),V1Backtester),
                  ('execution_fixed',Config.from_dict(asdict(V1Config())),V1Strategy(V1Config()),Backtester),
                  ('v2',Config(),Strategy(Config()),Backtester)]
        for name,cfg,engine,runner in variants:
            print(f'{tf} {name}: evaluating fixed rules',flush=True)
            memo=MemoizedStrategy(engine); segment_results={}; results={}
            for label,(lo,hi) in cuts.items():
                r=runner(cfg,memo).run(cs,tf,lo,hi,source)
                rows=trade_rows(r,cs)
                segment_results[label]=dict(start=iso(lo),end=iso(hi),metrics=r.metrics,diagnostics=groups(rows))
                results[label]=r
                if label=='Full':
                    export_rows(out/f'{tf}-{name}-trades.csv',rows)
                    export_rows(out/f'{tf}-{name}-losses.csv',[row for row in rows if row['net_r']<0])
                    (out/f'{tf}-{name}-diagnostics.md').write_text(f'# {tf} {name}\n\n'+markdown_groups(groups(rows)))
                print(f'  {label}: n={len(r.trades)} R={r.metrics["total_R"]:.3f} PF={r.metrics["profit_factor"]}',flush=True)
            if name=='v2':
                full=results['Full']
                full.diagnostics=segment_results['Full']['diagnostics']
                full.evaluation={label:dict(start=results[label].start,end=results[label].end,
                    metrics=results[label].metrics,diagnostics=segment_results[label]['diagnostics'])
                    for label in ('Full','Development 70%','Evaluation 30%')}
                entry['v2_saved_run_id']=repo.save_run(full)
            entry['variants'][name]=segment_results
            del memo,results,segment_results
            gc.collect()
            aggregate[tf]=entry
            (out/'comparison.json').write_text(json.dumps(aggregate,indent=2))
    text='# Fixed-rule multi-period comparison\n\nNo periods or losing trades were discarded. Each segment starts flat, is independently risk-sized, and force-closes at its end; segment totals need not sum to full-run totals. Forty initial bars warm up each timeframe; subsequent prefixes expand to 500. First listing candle omitted as potentially partial.\n\n'
    for tf,entry in aggregate.items():
        text+=f'## {tf} · {entry["candles"]} candles · {entry["data_first"]} to {entry["data_last"]}\n\n'
        text+='| Model | Period | Trades | Win % | Expectancy R | Total R | PF | Max DD % |\n|---|---|---:|---:|---:|---:|---:|---:|\n'
        for name,segments in entry['variants'].items():
            for label,p in segments.items():
                m=p['metrics']; pf=m['profit_factor']; pf=f'{pf:.2f}' if isinstance(pf,float) else pf
                text+=f'| {name} | {label} | {m["total_trades"]} | {m["win_rate"]:.1f} | {m["expectancy"]:.3f} | {m["total_R"]:.2f} | {pf} | {m["maximum_drawdown_pct"]:.2f} |\n'
        text+='\n'
    (out/'COMPARISON.md').write_text(text)

if __name__=='__main__':
    main()
