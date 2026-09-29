from pathlib import Path
from datetime import datetime,timezone
from statistics import median
from collections import Counter
from dataclasses import asdict
import json
from ..storage import Repository
from ..models import Config
from .v20.engine import Strategy
from .v20.levels import detect_zones,pivots,atr
from ..strategy.trace import Accumulator

def main():
    start=int(datetime(2026,3,22,tzinfo=timezone.utc).timestamp());end=start+184*86400
    repo=Repository('reports/research.sqlite3')
    cs=repo.candles('Binance · ONDO/USDT','4h',start-500*14400,end)
    strategy=Strategy(Config());total=Accumulator();inventory={};examples=[]
    for i,c in enumerate(cs):
        if c.time<start:continue
        h=cs[max(0,i-499):i+1];s,zs=strategy.analyze(h)
        total.add(s.pipeline)
        for z in zs:inventory.setdefault((z.first_time,z.origin_role),z)
        examples.extend(r for r in s.pipeline.get('rejected_candidates',[]) if r['primary_rejection_reason'] not in ('rejected_confirmation','rejected_zone_too_old','rejected_too_many_touches','rejected_previous_failed_hold','rejected_repeated_flips','rejected_zone_width'))
    zs=list(inventory.values());points=pivots(cs,3)
    stats=dict(loaded_candles=len(cs),warmup_candles=sum(c.time<start for c in cs),test_candles=sum(c.time>=start for c in cs),
        confirmed_highs=sum(p[2]=='resistance' for p in points),confirmed_lows=sum(p[2]=='support' for p in points),
        distinct_zone_identities=len(zs),support_zones=sum(z.role=='support' for z in zs),resistance_zones=sum(z.role=='resistance' for z in zs),
        polarity_flip_zones=sum(z.flips>0 for z in zs),median_width_creation_atr=median((z.high-z.low)/z.seed_atr for z in zs),
        median_age_bars=median(z.age_bars for z in detect_zones(cs[-500:-1],Config())),
        latest_touch_distribution=dict(Counter(z.role_retests for z in detect_zones(cs[-500:-1],Config()))))
    # Distinct identity roles use first observation; also provide final-snapshot roles.
    latest=detect_zones(cs[-500:-1],Config())
    stats['latest_snapshot']=dict(support=sum(z.role=='support' for z in latest),resistance=sum(z.role=='resistance' for z in latest),flipped=sum(z.flips>0 for z in latest),width_current_atr=median((z.high-z.low)/atr(cs[-500:-1]) for z in latest))
    out=total.result();out['inventory']=stats;out['late_stage_examples']=examples
    Path('reports/pipeline/before.json').write_text(json.dumps(out,indent=2))
    print(json.dumps({'funnel':out['funnel'],'rejections':out['rejections'],'inventory':stats},indent=2),flush=True)
if __name__=='__main__':main()
