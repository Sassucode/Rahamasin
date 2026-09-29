"""Broader confirmed swing structure; no indicator crossover or future pivots."""
from .levels import pivots, atr


def market_context(candles, span=3):
    points = pivots(candles, span*2)
    highs = [p[1] for p in points if p[2] == 'resistance'][-2:]
    lows = [p[1] for p in points if p[2] == 'support'][-2:]
    tolerance = atr(candles)*.1
    if len(highs) < 2 or len(lows) < 2:
        return 'RANGE'
    if highs[1] > highs[0]+tolerance and lows[1] > lows[0]+tolerance:
        return 'BULLISH'
    if highs[1] < highs[0]-tolerance and lows[1] < lows[0]-tolerance:
        return 'BEARISH'
    return 'RANGE'


def alignment(direction, context):
    if context == 'RANGE':
        return 'Range'
    return 'Trend aligned' if (direction == 'LONG') == (context == 'BULLISH') else 'Countertrend'
