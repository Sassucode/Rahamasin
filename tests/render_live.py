"""Render all desktop tabs against the optional integration check's cached data."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6 import QtWidgets
from rahamasin.storage import Repository
from rahamasin.ui.window import Window
from rahamasin.strategy.engine import Strategy

app = QtWidgets.QApplication([])
repo = Repository('/tmp/rahamasin-live.sqlite3')
result = repo.load_run(repo.runs()[0][0])
cs = repo.candles(result.source,result.timeframe,0,result.end)
setup,zones = Strategy(result.config).analyze(cs)
w = Window(repo)
w.show_market((cs,result.source,'Integration check: actual cached exchange data',setup,zones,result.timeframe))
w.show_result((result,cs,'Integration check'))
w.show()
for i in range(5):
    w.tabs.setCurrentIndex(i)
    app.processEvents()
    w.grab().save(f'/tmp/rahamasin-tab-{i}.png')
w.close()
