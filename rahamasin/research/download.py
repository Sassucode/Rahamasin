"""Download full available primary-exchange ONDO history, never synthetic-fill gaps."""
from pathlib import Path
from datetime import datetime, timezone
from ..data.providers import MarketData
from ..storage import Repository
from ..models import SECONDS
from ..data.providers import Coinbase
import argparse

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--coinbase-daily',action='store_true')
    args=parser.parse_args()
    repo = Repository(Path('reports/research.sqlite3'))
    start = int(datetime(2024,1,1,tzinfo=timezone.utc).timestamp())
    end = int(datetime(2026,9,21,tzinfo=timezone.utc).timestamp())
    for tf in (['1d'] if args.coinbase_daily else SECONDS):
        cs,source,note = MarketData(repo,[Coinbase()] if args.coinbase_daily else None).load(tf,start,end)
        print(tf,source,note,datetime.fromtimestamp(cs[0].time,timezone.utc).isoformat(),flush=True)
