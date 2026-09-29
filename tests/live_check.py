"""Optional network integration check; not part of pytest's offline suite."""
import time
from pathlib import Path
from rahamasin.storage import Repository
from rahamasin.data.providers import MarketData
from rahamasin.models import Config
from rahamasin.strategy.engine import Strategy
from rahamasin.backtest.engine import Backtester

repo = Repository(Path('/tmp/rahamasin-live.sqlite3'))
end = int(time.time())//14400*14400
cs,source,note = MarketData(repo).load('4h',end-14400*1000,end)
setup,zones = Strategy().analyze(cs)
result = Backtester(Config()).run(cs,'4h',cs[500].time,end,source)
repo.save_run(result)
print(source,note)
print('State:',setup.state,'zones:',len(zones),'metrics:',result.metrics)
