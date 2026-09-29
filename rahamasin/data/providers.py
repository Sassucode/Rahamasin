from datetime import datetime, timezone
from typing import Protocol
import time
import math
import httpx
from ..models import Candle, SECONDS


class Provider(Protocol):
    name: str
    def fetch(self, timeframe: str, start: int, end: int) -> list[Candle]: ...


def get(client, url, params):
    for attempt in range(4):
        response = client.get(url, params=params)
        if response.status_code not in (429, 500, 502, 503, 504):
            response.raise_for_status()
            return response.json()
        time.sleep(min(2**attempt, 8))
    response.raise_for_status()


class Binance:
    name = 'Binance · ONDO/USDT'
    def fetch(self, timeframe, start, end):
        result = []
        with httpx.Client(timeout=25) as client:
            cursor = start
            while cursor < end:
                rows = get(client, 'https://api.binance.com/api/v3/klines',
                    dict(symbol='ONDOUSDT',interval=timeframe,startTime=cursor*1000,endTime=end*1000-1,limit=1000))
                if not rows:
                    break
                result.extend(Candle(int(r[0])//1000,*map(float,r[1:6])) for r in rows)
                next_cursor = int(rows[-1][0])//1000+SECONDS[timeframe]
                if next_cursor <= cursor:
                    raise ValueError('Provider pagination did not advance')
                cursor = next_cursor
                time.sleep(.12)
        return result


class Coinbase:
    name = 'Coinbase · ONDO/USD'
    def fetch(self, timeframe, start, end):
        step = 3600 if timeframe == '4h' else SECONDS[timeframe]
        result = []
        iso = lambda t: datetime.fromtimestamp(t,timezone.utc).isoformat()
        with httpx.Client(timeout=25) as client:
            for cursor in range(start, end, step*299):
                rows = get(client,'https://api.exchange.coinbase.com/products/ONDO-USD/candles',
                    dict(granularity=step,start=iso(cursor),end=iso(min(cursor+step*299,end))))
                result.extend(Candle(int(r[0]),float(r[3]),float(r[2]),float(r[1]),float(r[4]),float(r[5])) for r in rows)
                time.sleep(.15)
        result = sorted({c.time:c for c in result if start <= c.time < end}.values(),key=lambda c:c.time)
        if timeframe == '4h':
            groups = {}
            for c in result:
                groups.setdefault(c.time//14400*14400,[]).append(c)
            result = [Candle(t,g[0].open,max(c.high for c in g),min(c.low for c in g),g[-1].close,sum(c.volume for c in g))
                      for t,g in groups.items() if [c.time for c in g] == [t+i*3600 for i in range(4)]]
        return result


def validate(candles, timeframe, start, end):
    step = SECONDS[timeframe]
    candles = sorted({c.time:c for c in candles if start <= c.time and c.time+step <= end}.values(),key=lambda c:c.time)
    for c in candles:
        if not all(math.isfinite(v) for v in (c.open,c.high,c.low,c.close,c.volume)) or not (0 < c.low <= min(c.open,c.close) <= max(c.open,c.close) <= c.high) or c.volume < 0:
            raise ValueError('Invalid OHLCV from provider')
    return candles


class MarketData:
    def __init__(self, repository, providers=None):
        self.repository = repository
        self.providers = providers or [Binance(), Coinbase()]

    def load(self, timeframe, start, end, offline=False):
        step = SECONDS[timeframe]
        start = start//step*step
        end = min(end, int(time.time()))//step*step
        errors = []
        cached_options = []
        for provider in self.providers:
            cached = self.repository.candles(provider.name,timeframe,start,end)
            if cached:
                cached_options.append((cached,provider.name))
            if offline:
                continue
            try:
                present = {c.time for c in cached}
                missing = [t for t in range(start,end,step) if t not in present]
                ranges = []
                for t in missing:
                    if ranges and ranges[-1][1] == t:
                        ranges[-1] = (ranges[-1][0],t+step)
                    else:
                        ranges.append((t,t+step))
                fresh = []
                for a,b in ranges:
                    fresh.extend(provider.fetch(timeframe,a,b))
                fresh = validate(fresh,timeframe,start,end)
                self.repository.save_candles(provider.name,timeframe,fresh)
                candles = validate(cached+fresh,timeframe,start,end)
                if not candles:
                    raise ValueError('No ONDO candles in selected period')
                gaps = sum(b.time-a.time != step for a,b in zip(candles,candles[1:]))
                note = f'{len(candles)} closed candles; {gaps} gaps'
                if candles[0].time > start:
                    note += '; history starts after requested date'
                if candles[-1].time+step < end:
                    note += '; STALE: latest requested candles unavailable'
                return candles,provider.name,note
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                errors.append(f'{provider.name}: {exc}')
        if cached_options:
            candles, source = max(cached_options,key=lambda item:item[0][-1].time)
            return candles,source,'OFFLINE / cached data only; may be stale. '+ ' | '.join(errors)
        raise ValueError('No cached data. '+ ' | '.join(errors))
