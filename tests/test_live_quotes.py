import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace
import pytest
from PySide6 import QtWidgets
from rahamasin.data.quotes import parse_quote,Quote,BINANCE,COINBASE
from rahamasin.ui.live_quotes import QuotePoller
from rahamasin.ui.window import Window
from rahamasin.storage import Repository
from rahamasin.strategy.engine import Strategy
from test_core import wave


def payload():
    return dict(symbol='ONDOUSDT',lastPrice='.45',bidPrice='.4499',askPrice='.4501',closeTime=1000000)


def test_quotes_validate_source_prices_and_age():
    q=parse_quote(BINANCE,payload(),1001)
    assert q.price==.45 and q.fresh(1019) and not q.fresh(1021)
    assert not parse_quote(BINANCE,payload(),2000).fresh(2000)
    for patch in [dict(lastPrice='NaN'),dict(bidPrice='.46'),dict(lastPrice='-1'),dict(symbol='BTCUSDT'),dict(closeTime=999999999)]:
        with pytest.raises(ValueError):parse_quote(BINANCE,payload()|patch,1001)
    c=parse_quote(COINBASE,dict(price='.45',bid='.44',ask='.46',time='1970-01-01T00:16:40Z'),1001)
    assert c.source==COINBASE and c.provider_time==1000


def test_ui_never_labels_closed_candle_as_live(monkeypatch,tmp_path):
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr('rahamasin.ui.window.time.time',lambda:1001)
    w=Window(Repository(tmp_path/'live.sqlite3'));cs=wave();setup,zones=Strategy().market(cs)
    w.show_market((cs,BINANCE,'cached',setup,zones,'4h'))
    assert 'LIVE PRICE UNAVAILABLE' in w.card.toPlainText()
    original=list(w.candles)
    w.receive_quote(parse_quote(BINANCE,payload(),1001))
    assert 'LIVE PRICE · refresh every 5s' in w.card.toPlainText()
    assert '0.45000 USDT' in w.card.toPlainText()
    assert 'Last closed 4h candle' in w.card.toPlainText()
    assert w.chart.live_line is not None and w.candles==original
    monkeypatch.setattr('rahamasin.ui.window.time.time',lambda:1022)
    w.render_market_card()
    assert 'UNAVAILABLE / STALE' in w.card.toPlainText() and w.chart.live_line is None
    w.quote_failed('connection lost')
    assert 'connection lost' in w.card.toPlainText()
    w.offline.setChecked(True)
    assert 'OFFLINE · live price disabled' in w.card.toPlainText()
    w.show_market((cs,COINBASE,'changed source',setup,zones,'4h'))
    assert w.quote is None and '0.45000 USDT' not in w.card.toPlainText()
    w.close()


def test_source_change_aborts_previous_request_and_offline_stops_timer(monkeypatch):
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    poller=QuotePoller();calls=[]
    monkeypatch.setattr(poller,'poll',lambda:calls.append(poller.source))
    class Reply:
        def abort(self):calls.append('aborted')
    poller.set_enabled(True);poller.reply=Reply();poller.set_source(COINBASE)
    assert calls==[BINANCE,'aborted',COINBASE] and poller.reply is None
    poller.set_enabled(False)
    assert not poller.timer.isActive()


def test_auto_history_refresh_waits_for_new_closed_bar(monkeypatch,tmp_path):
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w=Window(Repository(tmp_path/'history.sqlite3'));cs=wave();setup,zones=Strategy().market(cs)
    w.show_market((cs,BINANCE,'fixture',setup,zones,'1h'));w.timeframe.setCurrentText('1h')
    calls=[];monkeypatch.setattr(w,'load_market',lambda:calls.append(True))
    monkeypatch.setattr('rahamasin.ui.window.time.time',lambda:cs[-1].time+3601)
    w.auto_refresh_history();assert not calls
    monkeypatch.setattr('rahamasin.ui.window.time.time',lambda:cs[-1].time+7201)
    w.auto_refresh_history();assert calls==[True]
    w.offline.setChecked(True);w.auto_refresh_history();assert calls==[True]
    w.close()
