"""Reproduce zero-trade diagnosis and fixed-rule evaluation without parameter fitting."""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import asdict,replace
import argparse,hashlib,json
from ..models import Config
from ..storage import Repository
from ..data.providers import MarketData
from ..strategy.engine import Strategy,VERSION
from ..backtest.engine import Backtester
from ..backtest.evaluation import MemoizedStrategy,boundaries
from .diagnostics import trade_rows,groups,export_rows
from .v20.engine import Strategy as OldStrategy

START=int(datetime(2026,3,22,tzinfo=timezone.utc).timestamp())
END=int(datetime(2026,9,22,tzinfo=timezone.utc).timestamp())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--download',action='store_true');parser.add_argument('--only',choices=['4h','1h']);args=parser.parse_args()
    repo=Repository('reports/research.sqlite3');out=Path('reports/pipeline');out.mkdir(exist_ok=True)
    source='Binance · ONDO/USDT'
    if args.download:
        for tf in ['4h','1h']:
            cs,src,note=MarketData(repo).load(tf,int(datetime(2025,4,11,tzinfo=timezone.utc).timestamp()),END)
            print(tf,src,note,flush=True)
        return
    manifest=dict(version=VERSION,config=asdict(Config()),end=END,
        hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path('rahamasin/strategy/engine.py'),Path('rahamasin/strategy/levels.py'),Path('rahamasin/backtest/engine.py')]})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    summary=json.loads((out/'results.json').read_text()) if (out/'results.json').exists() else {}
    for tf in ([args.only] if args.only else ['4h','1h']):
        step=14400 if tf=='4h' else 3600
        cs=repo.candles(source,tf,0,END)[1:]
        if cs[-1].time+step<END:raise ValueError(f'{tf}: incomplete coverage, download missing data first')
        cfg=Config();memo=MemoizedStrategy(Strategy(cfg))
        windows=boundaries(cs,tf,cs[40].time,END)
        windows['Current six months']=(START,END)
        results={};summary[tf]={}
        for label,(a,b) in windows.items():
            print(tf,label,'starting',flush=True)
            result=Backtester(cfg,memo).run(cs,tf,a,b,source)
            result.diagnostics=groups(trade_rows(result,cs))
            results[label]=result
            filename=f'{tf}-{label.lower().replace(" ","-").replace("%","")}'
            (out/(filename+'-pipeline.json')).write_text(json.dumps(result.pipeline,indent=2))
            export_rows(out/(filename+'-trades.csv'),trade_rows(result,cs))
            summary[tf][label]=dict(start=a,end=b,metrics=result.metrics,diagnostics=result.diagnostics,
                funnel=result.pipeline['funnel'],rejections=result.pipeline['rejections'])
            print(tf,label,result.metrics,flush=True)
        for label,r in results.items():
            r.evaluation={name:dict(start=t.start,end=t.end,metrics=t.metrics,diagnostics=t.diagnostics,pipeline=t.pipeline)
                          for name,t in results.items() if label=='Full' and name in ('Full','Development 70%','Evaluation 30%')}
            summary[tf][label]['run_id']=repo.save_run(r)
        # Diagnostic R:R sensitivity: same projected candidates, no P&L ranking.
        if tf=='4h':
            sensitivity={}
            for rr in [1.2,1.5,1.8,2.0]:
                if rr==1.8:r=results['Current six months']
                else:
                    r=Backtester(replace(cfg,min_rr=rr)).run(cs,tf,START,END,source)
                f=r.pipeline['funnel']
                sensitivity[str(rr)]=dict(rr_survivors=f['minimum_rr_passed'],long_signals=f['final_LONG_signals'],short_signals=f['final_SHORT_signals'],submitted=f['orders_submitted'],filled=f['orders_actually_filled'],completed=len(r.trades))
                print('RR sensitivity',rr,sensitivity[str(rr)],flush=True)
            summary[tf]['rr_sensitivity']=sensitivity
        (out/'results.json').write_text(json.dumps(summary,indent=2))
if __name__=='__main__':main()
