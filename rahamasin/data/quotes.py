"""Public last-trade snapshots, deliberately separate from closed OHLCV history."""
from dataclasses import dataclass
from datetime import datetime
import math

BINANCE='Binance · ONDO/USDT'
COINBASE='Coinbase · ONDO/USD'
ENDPOINTS={BINANCE:'https://api.binance.com/api/v3/ticker/24hr?symbol=ONDOUSDT',
           COINBASE:'https://api.exchange.coinbase.com/products/ONDO-USD/ticker'}

@dataclass(frozen=True)
class Quote:
    source: str
    price: float
    bid: float
    ask: float
    received_at: float
    provider_time: float

    def age(self,now):
        return max(0,now-self.received_at,now-self.provider_time)

    def fresh(self,now):
        return self.age(now)<=20


def parse_quote(source,data,received_at):
    if source==BINANCE:
        if data.get('symbol')!='ONDOUSDT':raise ValueError('Unexpected ticker symbol')
        values=[float(data[k]) for k in ('lastPrice','bidPrice','askPrice')]
        timestamp=float(data['closeTime'])/1000
    elif source==COINBASE:
        values=[float(data[k]) for k in ('price','bid','ask')]
        timestamp=datetime.fromisoformat(data['time'].replace('Z','+00:00')).timestamp()
    else:raise ValueError('No live quote provider for this source')
    if not all(math.isfinite(v) and v>0 for v in values) or values[1]>values[2]:
        raise ValueError('Invalid quote prices')
    if not math.isfinite(timestamp) or timestamp<=0 or timestamp>received_at+30:
        raise ValueError('Invalid quote timestamp / clock mismatch')
    return Quote(source,*values,received_at,timestamp)
