"""Optional network integration: production Qt poller, two quotes, no candle writes."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json,time
from pathlib import Path
from dataclasses import asdict
from PySide6 import QtWidgets,QtCore
from rahamasin.ui.live_quotes import QuotePoller
app=QtWidgets.QApplication([]);poller=QuotePoller();received=[];errors=[]
def done(q):
    received.append(asdict(q));print(q.source,q.price,'fresh',q.fresh(time.time()),flush=True)
    if len(received)>=2:poller.set_enabled(False);app.quit()
def fail(message):
    errors.append(message);print(message,flush=True)
poller.updated.connect(done);poller.failed.connect(fail)
QtCore.QTimer.singleShot(22000,app.quit);poller.set_enabled(True);app.exec();poller.set_enabled(False)
if received:
    from rahamasin.ui.window import Window
    from rahamasin.storage import Repository
    from rahamasin.strategy.engine import Strategy
    from rahamasin.data.quotes import Quote
    repo=Repository('reports/research.sqlite3')
    cs=repo.candles(poller.source,'4h',0,2000000000)[-500:]
    if cs:
        w=Window(repo);setup,zones=Strategy().market(cs)
        w.show_market((cs,poller.source,'Cached history · independent current quote',setup,zones,'4h'))
        w.receive_quote(Quote(**received[-1]));w.show();app.processEvents()
        w.grab().save('reports/live/live-price.png');w.close()
Path('reports/live/network-check.json').write_text(json.dumps(dict(quotes=received,errors=errors),indent=2))
if len(received)<2:raise SystemExit('Did not obtain two public quote snapshots')
