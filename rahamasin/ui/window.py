from dataclasses import asdict
from datetime import datetime, timezone
import json
import time
import traceback
from html import escape
from PySide6 import QtCore, QtGui, QtWidgets as W
import pyqtgraph as pg
from ..models import Config, SECONDS, Setup, Zone
from ..strategy.engine import Strategy
from ..data.providers import MarketData
from ..backtest.evaluation import evaluate
from .chart import Chart
from .live_quotes import QuotePoller


def stamp(t):
    return datetime.fromtimestamp(t,timezone.utc).strftime('%Y-%m-%d %H:%M UTC')


def price(v):
    return '—' if v is None else f'{v:.5f}'


class Worker(QtCore.QThread):
    done = QtCore.Signal(object)
    failed = QtCore.Signal(str)
    progress = QtCore.Signal(int)
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
    def run(self):
        try:
            self.done.emit(self.fn(self.progress.emit))
        except Exception as exc:
            traceback.print_exc()
            self.failed.emit(str(exc))


class Window(W.QMainWindow):
    def __init__(self, repository):
        super().__init__()
        self.repo = repository
        self.config = repository.config()
        self.candles = []
        self.result = None
        self.rejected_record = None
        self.active_rejections = []
        self.worker = None
        self.market_data = None
        self.quote = None
        self.quote_error = ''
        self.live_started = False
        self.quote_poller = QuotePoller(self)
        self.quote_poller.updated.connect(self.receive_quote)
        self.quote_poller.failed.connect(self.quote_failed)
        self.quote_age_timer = QtCore.QTimer(self)
        self.quote_age_timer.setInterval(1000)
        self.quote_age_timer.timeout.connect(self.render_market_card)
        self.history_timer = QtCore.QTimer(self)
        self.history_timer.setInterval(60000)
        self.history_timer.timeout.connect(self.auto_refresh_history)
        self.setWindowTitle('RAHAMASIN · ONDO structure research')
        self.resize(1440,940)
        root = W.QWidget()
        self.setCentralWidget(root)
        layout = W.QVBoxLayout(root)
        header = W.QHBoxLayout()
        title = W.QLabel('RAHAMASIN  /  ONDO')
        title.setObjectName('brand')
        header.addWidget(title)
        header.addStretch()
        header.addWidget(W.QLabel('MARKET STRUCTURE  ·  MANUAL EXECUTION'))
        layout.addLayout(header)
        controls = W.QHBoxLayout()
        self.timeframe = W.QComboBox(); self.timeframe.addItems(SECONDS)
        self.timeframe.setCurrentText('4h')
        self.offline = W.QCheckBox('Use local cache only')
        self.offline.toggled.connect(self.toggle_quote_connection)
        self.refresh = W.QPushButton('Refresh ONDO')
        self.refresh.clicked.connect(self.load_market)
        self.timeframe.activated.connect(self.load_market)
        controls.addWidget(W.QLabel('Timeframe')); controls.addWidget(self.timeframe)
        controls.addWidget(self.offline); controls.addStretch(); controls.addWidget(self.refresh)
        layout.addLayout(controls)
        self.tabs = W.QTabWidget(); layout.addWidget(self.tabs)
        market = W.QWidget(); ml = W.QHBoxLayout(market)
        self.chart = Chart(); ml.addWidget(self.chart,3)
        self.card = W.QTextBrowser(); self.card.setMinimumWidth(330); self.card.setMaximumWidth(430)
        self.card.setLineWrapMode(W.QTextEdit.LineWrapMode.WidgetWidth)
        self.card.setWordWrapMode(QtGui.QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.card.setHtml('<h1>ONDO</h1><h2>Ready to analyze</h2><p>Refresh to download public closed candles. No account or API key required.</p>')
        ml.addWidget(self.card,1); self.tabs.addTab(market,'MARKET')
        self.build_backtest(); self.build_trades(); self.build_levels(); self.build_settings()
        self.status = W.QLabel('Ready · All dates UTC · No automatic trade execution')
        self.status.setWordWrap(True); layout.addWidget(self.status)
        self.bar = W.QProgressBar(); self.bar.setVisible(False); layout.addWidget(self.bar)
        self.setStyleSheet('''
            QMainWindow,QWidget {background:#0c121c;color:#dce5ef;font-family:"Arial";font-size:13px;}
            QLabel#brand {font-size:24px;font-weight:700;padding:14px 0;color:#f2f6fc;}
            QTabWidget::pane {border:1px solid #263244;}
            QTabBar::tab {padding:14px 24px;color:#8f9fb5;background:#101722;}
            QTabBar::tab:selected {color:#67d4bc;border-bottom:2px solid #67d4bc;}
            QPushButton {background:#223449;border:1px solid #38516d;padding:10px 18px;border-radius:5px;}
            QPushButton:hover {background:#304963;} QPushButton:disabled {color:#607087;}
            QComboBox,QSpinBox,QDoubleSpinBox,QDateEdit {padding:7px;background:#172131;border:1px solid #2d3b50;}
            QTextBrowser,QTableWidget {background:#101722;border:0;padding:10px;selection-background-color:#29445a;}
            QHeaderView::section {background:#182334;padding:9px;border:0;color:#a9bacf;}
            QProgressBar {border:0;background:#172131;height:5px;} QProgressBar::chunk {background:#49c8ac;}
        ''')
        self.refresh_runs()

    def build_backtest(self):
        page = W.QWidget(); l = W.QVBoxLayout(page)
        row = W.QHBoxLayout()
        self.start = W.QDateEdit(QtCore.QDate.currentDate().addMonths(-6)); self.start.setCalendarPopup(True)
        self.end = W.QDateEdit(QtCore.QDate.currentDate()); self.end.setCalendarPopup(True)
        self.entry_mode = W.QComboBox()
        self.entry_mode.addItem('Confirmation Entry','confirmation'); self.entry_mode.addItem('Planned Limit Entry','planned_limit'); self.entry_mode.addItem('Both entry modes','both')
        self.entry_mode.setCurrentIndex(self.entry_mode.findData(self.config.entry_mode))
        self.rr = W.QDoubleSpinBox(); self.rr.setRange(.1,20); self.rr.setValue(self.config.min_rr)
        self.risk = W.QDoubleSpinBox(); self.risk.setRange(.01,10); self.risk.setValue(self.config.risk_pct)
        self.run_button = W.QPushButton('Run chronological backtest'); self.run_button.clicked.connect(self.run_backtest)
        for label,widget in [('Start UTC',self.start),('End UTC (exclusive)',self.end),('Minimum R:R',self.rr),('Risk %',self.risk),('Entry mode',self.entry_mode)]:
            row.addWidget(W.QLabel(label)); row.addWidget(widget)
        row.addWidget(self.run_button); l.addLayout(row)
        history = W.QHBoxLayout(); self.runs = W.QComboBox()
        load = W.QPushButton('Open saved run'); load.clicked.connect(self.restore_run)
        history.addWidget(W.QLabel('Saved research')); history.addWidget(self.runs,1); history.addWidget(load); l.addLayout(history)
        self.metrics = W.QLabel('Run a test to measure this exact strategy. Fees and slippage are included.'); self.metrics.setWordWrap(True)
        l.addWidget(self.metrics)
        self.split_table = W.QTableWidget(0,7)
        self.split_table.setHorizontalHeaderLabels(['Period','Trades','Win %','Expectancy R','Total R','PF','Max DD %'])
        self.split_table.setFixedHeight(150)
        self.split_table.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
        l.addWidget(self.split_table)
        self.evidence_note = W.QLabel('Evaluation is chronological; repeatedly viewing/tuning it removes its holdout value.')
        self.evidence_note.setWordWrap(True)
        l.addWidget(self.evidence_note)
        self.equity = pg.PlotWidget(axisItems={'bottom':pg.DateAxisItem(utcOffset=0)},background='#101722')
        self.equity.setLabel('left','Equity',units='USD'); self.equity.showGrid(x=True,y=True,alpha=.15)
        l.addWidget(self.equity)
        diagnostic_row = W.QHBoxLayout()
        diagnostic_row.addWidget(W.QLabel('Setup diagnostics · same rules, independent 70/30 runs'))
        self.diagnostic_segment = W.QComboBox()
        self.diagnostic_segment.addItems(['Full','Development 70%','Evaluation 30%'])
        self.diagnostic_segment.currentTextChanged.connect(self.show_diagnostics)
        diagnostic_row.addWidget(self.diagnostic_segment); l.addLayout(diagnostic_row)
        self.diagnostic_table = W.QTableWidget(0,5)
        self.diagnostic_table.setHorizontalHeaderLabels(['Setup group','Trades','Win %','Expectancy R','PF'])
        self.diagnostic_table.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.diagnostic_tabs = W.QTabWidget()
        self.diagnostic_tabs.setMaximumHeight(190)
        self.diagnostic_tabs.addTab(self.diagnostic_table,'Groups')
        self.pipeline_view = W.QTextBrowser()
        self.diagnostic_tabs.addTab(self.pipeline_view,'Signal pipeline')
        self.rejected_table = W.QTableWidget(0,8)
        self.rejected_table.setHorizontalHeaderLabels(['UTC','Direction','Entry reference','Stop','Target','R:R','Confirmation','Primary rejection'])
        self.rejected_table.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rejected_table.setSelectionBehavior(W.QAbstractItemView.SelectionBehavior.SelectRows)
        self.rejected_table.cellDoubleClicked.connect(self.open_rejected)
        self.rejected_table.setToolTip('Double-click to inspect a rejected candidate. These are not trades.')
        self.diagnostic_tabs.addTab(self.rejected_table,'Rejected · double-click to inspect')
        l.addWidget(self.diagnostic_tabs)
        note = W.QLabel('Starting equity $10,000 · one position · confirmation: next-open · planned: frozen expiring limit · stop first if ambiguous\nDrawdown uses candle-close equity. Older saved runs retain their original execution model. Shorts omit borrowing/funding.')
        note.setWordWrap(True); l.addWidget(note); self.tabs.addTab(page,'BACKTEST')

    def build_trades(self):
        page = W.QWidget(); l = W.QVBoxLayout(page)
        self.trade_table = W.QTableWidget(0,8)
        self.trade_table.setHorizontalHeaderLabels(['Direction','Signal UTC','Entry','Stop','Target','Exit','Net R','Outcome'])
        self.trade_table.setSelectionBehavior(W.QAbstractItemView.SelectionBehavior.SelectRows)
        self.trade_table.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.trade_table.itemSelectionChanged.connect(self.select_trade)
        self.trade_table.setMaximumHeight(230)
        l.addWidget(self.trade_table)
        self.at_signal = W.QCheckBox('At signal: hide candles that were not yet available')
        self.at_signal.setChecked(True)
        self.at_signal.toggled.connect(self.inspect_trade)
        l.addWidget(self.at_signal)
        self.inspector = Chart(); l.addWidget(self.inspector)
        self.trade_reasons = W.QTextBrowser(); self.trade_reasons.setMaximumHeight(170); l.addWidget(self.trade_reasons)
        self.tabs.addTab(page,'TRADES')

    def build_levels(self):
        self.levels = W.QTableWidget(0,16)
        self.levels.setHorizontalHeaderLabels(['Low','High','Mid','Touches','Successes','Avg reaction %','Median %','Median ATR','Support','Resistance','Flips','Age bars','Recency bars','Strength','First touch UTC','Last touch UTC'])
        self.levels.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabs.addTab(self.levels,'LEVELS')

    def build_settings(self):
        page = W.QWidget(); form = W.QFormLayout(page)
        self.settings = {}
        labels = dict(entry_mode='Entry mode',plan_max_distance_atr='Maximum plan distance (ATR)',plan_expiry_bars='Limit expiry (candles)',min_rr='Minimum gross and net reward/risk',risk_pct='Risk per trade (%)',pivot_span='Pivot confirmation bars',lookback='Level lookback (bars)',zone_atr='Fixed zone width (creation ATR)',stop_atr='Stop buffer (ATR)',min_displacement='Minimum departure (ATR)',max_tests='Maximum role retests',confirmation_atr='Minimum rejection wick (ATR)',max_hold_days='Maximum holding days',fee_bps='Fee per side (basis points)',slippage_bps='Market exit slippage (basis points)')
        for key,value in asdict(self.config).items():
            if key=='entry_mode':
                widget=W.QComboBox();widget.addItem('Confirmation Entry','confirmation');widget.addItem('Planned Limit Entry','planned_limit')
                widget.setCurrentIndex(widget.findData(value));self.settings[key]=widget;form.addRow(labels[key],widget);continue
            widget = W.QSpinBox() if isinstance(value,int) else W.QDoubleSpinBox()
            limits = {'plan_max_distance_atr':(.1,20),'plan_expiry_bars':(1,100),'pivot_span':(1,20),'lookback':(50,2000),'min_displacement':(.5,6),'max_tests':(0,5),'confirmation_atr':(.1,1),'max_hold_days':(1,30),'risk_pct':(.01,10),'min_rr':(.1,20),'zone_atr':(.05,3),'stop_atr':(.01,3),'fee_bps':(0,100),'slippage_bps':(0,100)}
            widget.setRange(*limits[key]); widget.setValue(value)
            self.settings[key] = widget; form.addRow(labels[key],widget)
        save = W.QPushButton('Save settings'); save.clicked.connect(self.save_settings); form.addRow(save)
        form.addRow(W.QLabel('Changes apply to the next refresh/backtest. Each saved run retains its own configuration.\nSignals are research output, not evidence of future profitability.'))
        self.tabs.addTab(page,'SETTINGS')

    def save_settings(self):
        self.config = Config(**{key:(w.currentData() if key=='entry_mode' else w.value()) for key,w in self.settings.items()})
        self.repo.save_config(self.config)
        self.rr.setValue(self.config.min_rr); self.risk.setValue(self.config.risk_pct)
        self.entry_mode.setCurrentIndex(self.entry_mode.findData(self.config.entry_mode))
        self.status.setText('Settings saved. Refresh market analysis to apply.')

    def launch(self, fn, callback):
        if self.worker and self.worker.isRunning():
            return
        self.refresh.setEnabled(False); self.run_button.setEnabled(False)
        self.bar.setVisible(True); self.bar.setRange(0,0)
        self.status.setText('Working · downloading / evaluating closed candles…')
        self.worker = Worker(fn)
        self.worker.done.connect(callback)
        self.worker.failed.connect(lambda message:self.status.setText('Could not complete: '+message))
        self.worker.progress.connect(self.progress)
        self.worker.finished.connect(self.finished)
        self.worker.start()

    def progress(self, value):
        self.bar.setRange(0,100); self.bar.setValue(value)

    def finished(self):
        self.refresh.setEnabled(True); self.run_button.setEnabled(True); self.bar.setVisible(False)

    def load_market(self):
        tf, cfg, offline = self.timeframe.currentText(), self.config, self.offline.isChecked()
        end = int(time.time()); start = end-(cfg.lookback+20)*SECONDS[tf]
        def task(progress):
            candles,source,note = MarketData(self.repo).load(tf,start,end,offline)
            setup,zones = Strategy(cfg).market(candles)
            return candles,source,note,setup,zones,tf
        self.launch(task,self.show_market)

    def show_market(self, data):
        candles,source,note,setup,zones,tf = data
        self.candles = candles
        self.chart.draw(candles[-180:],SECONDS[tf],zones,setup)
        self.market_data=data
        if self.quote is not None and self.quote.source!=source:
            self.quote=None;self.quote_error=''
        self.quote_poller.set_source(source)
        self.render_market_card()
        self.status.setText(source+' · '+note+' · '+tf)
        self.levels.setRowCount(len(zones))
        for i,z in enumerate(zones):
            values = [z.low,z.high,z.midpoint,z.touches,z.successes,z.average_reaction,z.median_reaction,z.reaction_atr,z.support_reactions,z.resistance_reactions,z.flips,z.age_bars,z.recency_bars,z.strength]
            for j,v in enumerate(values):
                self.levels.setItem(i,j,W.QTableWidgetItem(str(v) if isinstance(v,int) else f'{v:.5f}'))
            self.levels.setItem(i,14,W.QTableWidgetItem(stamp(z.first_time)))
            self.levels.setItem(i,15,W.QTableWidgetItem(stamp(z.last_time)))
        self.levels.resizeColumnsToContents()

    def start_live(self):
        self.live_started=True
        self.quote_age_timer.start();self.history_timer.start()
        self.quote_poller.set_enabled(not self.offline.isChecked())
        self.load_market()

    def toggle_quote_connection(self,offline):
        self.quote_error=''
        if self.live_started:self.quote_poller.set_enabled(not offline)
        self.render_market_card()

    def receive_quote(self,quote):
        if self.offline.isChecked() or quote.source!=self.quote_poller.source:return
        self.quote=quote;self.quote_error='';self.render_market_card()

    def quote_failed(self,message):
        self.quote_error=message;self.render_market_card()

    def auto_refresh_history(self):
        if self.offline.isChecked() or self.tabs.currentIndex()!=0:return
        if self.worker and self.worker.isRunning():return
        tf=self.timeframe.currentText();step=SECONDS[tf]
        if not self.market_data or self.market_data[-1]!=tf or self.candles[-1].time+step<int(time.time())//step*step:
            self.load_market()

    def render_market_card(self):
        if not self.market_data:
            if self.live_started:
                quote=self.quote
                fresh=bool(quote and quote.fresh(time.time()) and not self.quote_error and not self.offline.isChecked())
                self.card.setHtml(f'<h2>{"LIVE PRICE · refresh every 5s" if fresh else "LIVE PRICE UNAVAILABLE / STALE"}</h2><h1>{quote.price if quote else "—"}</h1><p>{escape(self.quote_poller.source)}</p><p>{escape(self.quote_error)}</p><p>Loading closed-candle analysis…</p>')
            return
        candles,source,note,setup,zones,tf=self.market_data
        color = {'LONG':'#49c8ac','SHORT':'#ed7786','NO TRADE':'#d8b471'}[setup.state]
        planned=setup.features.get('setup_kind')=='PLANNED'
        label=('PLANNED ' if planned else 'ACTIVE ')+setup.state if setup.state!='NO TRADE' else 'NO VALID SETUP'
        quote=self.quote if self.quote and self.quote.source==source else None
        fresh=bool(quote and quote.fresh(time.time()) and not self.quote_error and not self.offline.isChecked())
        live_label='LIVE PRICE · refresh every 5s' if fresh else ('OFFLINE · live price disabled' if self.offline.isChecked() else 'LIVE PRICE UNAVAILABLE / STALE')
        live_price=f'{quote.price:.5f}' if quote else '—'
        detail=(f'Last received {datetime.fromtimestamp(quote.received_at,timezone.utc).strftime("%H:%M:%S UTC")} · data age {quote.age(time.time()):.0f}s<br>Bid {quote.bid:.5f} · Ask {quote.ask:.5f}' if quote else 'Waiting for a fresh exchange quote')
        if self.quote_error:detail+='<br>'+escape(self.quote_error)
        unit='USDT' if source.startswith('Binance') else 'USD' if source.startswith('Coinbase') else ''
        html = f'<p>{source} · {tf}</p><p style="color:{"#49c8ac" if fresh else "#d8b471"}">{live_label}</p><h1>{live_price} {unit}</h1><p>{detail}</p><p>Last closed {tf} candle: <b>{candles[-1].close:.5f}</b><br>Closed {stamp(candles[-1].time+SECONDS[tf])}<br>Strategy uses closed candles; live price is separate.</p><h1 style="color:{color}">{label}</h1>'
        self.chart.set_live_price(quote.price if fresh else None)
        if candles[-1].time+2*SECONDS[tf] <= int(time.time()):
            html = '<h3 style="color:#ed7786">STALE HISTORY · not current analysis</h3>'+html
        if setup.entry is not None:
            html += f'<p>HISTORICAL ZONE<br><b>{price(setup.entry_low)} – {price(setup.entry_high)}</b></p><p>Entry reference <b>{price(setup.entry)}</b></p><p>Stop <b>{price(setup.stop)}</b></p><p>Take profit <b>{price(setup.target)}</b></p><h2>{setup.rr:.2f} R:R</h2>'
            if planned:
                rule='Wait for directional rejection/reclaim; this is not a confirmed entry.' if self.config.entry_mode=='confirmation' else f'Resting limit at {setup.entry:.5f}; no confirmation required. Expires after {self.config.plan_expiry_bars} candles.'
                html += f'<p><b>{setup.features["status"]}</b><br>Confirmation: NOT YET CONFIRMED<br>Preferred entry: {setup.entry:.5f}<br>Distance to entry: {setup.features["distance_pct"]:+.2f}% / {setup.features["zone_distance_atr"]:.2f} ATR<br>{rule}</p>'
            else:
                html += '<p>Confirmation: CONFIRMED · next-open execution subject to geometry recheck.</p>'
            html += f'<p>Risk distance {price(setup.risk_distance)}<br>Reward distance {price(setup.reward_distance)}</p>'
        else:
            html += '<p>No nearby historical zone passes the planned stop, target, quality, freshness and R:R requirements.</p>'
        html += '<ul>'+''.join(f'<li>{r}</li>' for r in setup.reasons)+'</ul>'
        if setup.entry is not None and fresh:
            html += f'<p>Distance from live price to entry: {(setup.entry/quote.price-1)*100:+.2f}%</p>'
            crossed=(quote.price<=setup.stop or quote.price>=setup.target) if setup.state=='LONG' else (quote.price>=setup.stop or quote.price<=setup.target)
            if crossed:html += '<p style="color:#ed7786"><b>Live price has crossed the displayed stop or target. This closed-candle setup needs reassessment.</b></p>'
        scroll=self.card.verticalScrollBar().value()
        self.card.setHtml(html)
        self.card.verticalScrollBar().setValue(scroll)

    def run_backtest(self):
        tf, offline = self.timeframe.currentText(), self.offline.isChecked()
        start = int(datetime.combine(self.start.date().toPython(),datetime.min.time(),timezone.utc).timestamp())
        end = int(datetime.combine(self.end.date().toPython(),datetime.min.time(),timezone.utc).timestamp())
        if start >= end:
            self.status.setText('Choose an end date after the start date.'); return
        selected_mode=self.entry_mode.currentData()
        cfg = Config(**(asdict(self.config)|dict(min_rr=self.rr.value(),risk_pct=self.risk.value(),entry_mode=self.config.entry_mode if selected_mode=='both' else selected_mode)))
        def task(progress):
            candles,source,note = MarketData(self.repo).load(tf,start-cfg.lookback*SECONDS[tf],end,offline)
            if not any(c.time >= start for c in candles):
                raise ValueError('No candles in requested test period')
            if candles[-1].time+SECONDS[tf] < min(end,int(time.time())//SECONDS[tf]*SECONDS[tf]):
                raise ValueError('Cache does not cover test end; download data first')
            if selected_mode=='both':
                from ..backtest.evaluation import evaluate_modes
                results=evaluate_modes(candles,tf,start,end,cfg,source,progress)
                ids={mode:self.repo.save_run(r) for mode,r in results.items()}
                result=results[cfg.entry_mode];run_id=ids[cfg.entry_mode]
                note+=' · Separate mode runs '+str(ids)
            else:
                result = evaluate(candles,tf,start,end,cfg,source,progress)
                run_id = self.repo.save_run(result)
            return result,candles,f'Run #{run_id} · {source} · {note}'
        self.launch(task,self.show_result)

    def show_result(self, data):
        self.rejected_record=None
        self.result,self.test_candles,note = data
        result = self.result
        summaries={**result.mode_comparison,**result.evaluation}
        self.split_table.setRowCount(len(summaries))
        for i,(name,data) in enumerate(summaries.items()):
            m=data['metrics']
            n=m['total_trades']
            for j,v in enumerate([name,n,m['win_rate'] if n else '—',m['expectancy'] if n else '—',m['total_R'],m['profit_factor'],m['maximum_drawdown_pct']]):
                item=W.QTableWidgetItem(f'{v:.3f}' if isinstance(v,float) else str(v))
                item.setToolTip(f'{stamp(data["start"])} to {stamp(data["end"])} (exclusive)')
                self.split_table.setItem(i,j,item)
        self.split_table.resizeColumnsToContents()
        self.show_diagnostics()
        count=result.metrics['total_trades']
        self.evidence_note.setText(f'{count} trades: '+('insufficient evidence of an edge. Zero trades do not establish zero risk or positive expectancy.' if count<10 else 'historical results, not proof of an edge.')+' Development/evaluation restart flat; hover a period for its dates.')
        self.start.setDate(QtCore.QDate.fromString(stamp(result.start)[:10],'yyyy-MM-dd'))
        self.end.setDate(QtCore.QDate.fromString(stamp(result.end)[:10],'yyyy-MM-dd'))
        self.rr.setValue(result.config.min_rr); self.risk.setValue(result.config.risk_pct)
        self.timeframe.setCurrentText(result.timeframe)
        self.entry_mode.setCurrentIndex(self.entry_mode.findData(result.config.entry_mode))
        mode_name='Planned Limit Entry' if result.config.entry_mode=='planned_limit' else 'Confirmation Entry'
        self.metrics.setText(mode_name+'    |    '+'    |    '.join(f'{k.replace("_"," ")}: {v:.2f}' if isinstance(v,float) else f'{k.replace("_"," ")}: {v}' for k,v in result.metrics.items()))
        self.equity.clear(); self.equity.plot([p[0] for p in result.equity],[p[1] for p in result.equity],pen=pg.mkPen('#49c8ac',width=2))
        self.trade_table.setRowCount(0); self.trade_table.setRowCount(len(result.trades))
        for i,t in enumerate(result.trades):
            values = [t.setup.state,stamp(t.setup.signal_time),price(t.entry_price),price(t.setup.stop),price(t.setup.target),price(t.exit_price),f'{t.r:.2f}',t.outcome]
            for j,v in enumerate(values):
                self.trade_table.setItem(i,j,W.QTableWidgetItem(v))
        self.trade_table.resizeColumnsToContents()
        self.inspector.clear(); self.trade_reasons.clear()
        if result.trades:
            self.trade_table.selectRow(0)
        self.status.setText(f'{note} · {result.strategy_version} · Split periods restart positions; historical evaluation is not a pristine forward test.'); self.refresh_runs()

    def show_diagnostics(self):
        if not self.result:
            return
        name=self.diagnostic_segment.currentText()
        groups=self.result.evaluation.get(name,{}).get('diagnostics',self.result.diagnostics if name=='Full' else {})
        self.diagnostic_table.setRowCount(len(groups))
        for i,(label,m) in enumerate(groups.items()):
            n=m['trades']
            for j,v in enumerate([label,n,m['win_rate'] if n else '—',m['expectancy'] if n else '—',m['profit_factor']]):
                self.diagnostic_table.setItem(i,j,W.QTableWidgetItem(f'{v:.3f}' if isinstance(v,float) else str(v)))
        self.diagnostic_table.resizeColumnsToContents()
        pipeline=self.result.evaluation.get(name,{}).get('pipeline',self.result.pipeline if name=='Full' else {})
        if pipeline:
            lines=['SIGNAL FUNNEL (zone-candle candidates, not independent trades)']
            lines += [f'{key}: {value}' for key,value in pipeline.get('funnel',{}).items()]
            lines += ['', 'PRIMARY REJECTIONS (descending frequency)']
            lines += [f'{key}: {value}' for key,value in sorted(pipeline.get('rejections',{}).items(),key=lambda item:-item[1])]
            lines += ['',pipeline.get('counting_note','')]
            self.pipeline_view.setPlainText('\n'.join(lines))
        else:
            self.pipeline_view.setPlainText('No pipeline trace in this legacy run. Run a new backtest to collect it.')
        self.active_rejections=pipeline.get('rejected_candidates',[])
        self.rejected_table.setRowCount(len(self.active_rejections))
        for i,r in enumerate(self.active_rejections):
            values=[stamp(r['timestamp']),r['direction'],price(r.get('entry_candidate')),price(r.get('stop_candidate')),price(r.get('target_candidate')),price(r.get('rr')),r.get('confirmation_type','None'),r['primary_rejection_reason']]
            for j,value in enumerate(values):self.rejected_table.setItem(i,j,W.QTableWidgetItem(str(value)))
        self.rejected_table.resizeColumnsToContents()

    def select_trade(self):
        self.rejected_record=None
        self.inspect_trade()

    def open_rejected(self,row,column=0):
        if not 0<=row<len(self.active_rejections):return
        self.rejected_record=self.active_rejections[row]
        self.tabs.setCurrentIndex(2)
        self.inspect_trade()

    def inspect_rejected(self):
        r=self.rejected_record;z=Zone(**r['zone']);step=SECONDS[self.result.timeframe]
        cutoff=r.get('information_cutoff',r['timestamp'])
        # Always cutoff-safe for rejected candidates, even in outcome mode.
        candles=[c for c in self.test_candles if cutoff-40*step<=c.time<=cutoff]
        overlay=Setup(entry_low=z.low,entry_high=z.high,entry=r.get('entry_candidate'),stop=r.get('stop_candidate'),target=r.get('target_candidate'))
        self.inspector.draw(candles,step,[z],overlay)
        self.trade_reasons.setPlainText(f'REJECTED CANDIDATE — NOT A TRADE · {r["direction"]}\n{stamp(r["timestamp"])} · {r["primary_rejection_reason"]}\nStructure: {r["market_structure"]} · Confirmation: {r["confirmation_type"]}\nZone midpoint {z.midpoint:.5f} · confirmation close {r["confirmation_close"]:.5f} · distance {r["distance_atr"]:.2f} ATR\nProjected R:R {r.get("rr")} · net R:R {r.get("net_rr")}\nAll chart candles and the zone snapshot were available at the rejection. Select a trade row to return to completed trades.')

    def inspect_trade(self):
        if self.rejected_record is not None:
            self.inspect_rejected();return
        row = self.trade_table.currentRow()
        if not self.result or not 0 <= row < len(self.result.trades):
            return
        trade = self.result.trades[row]; step = SECONDS[self.result.timeframe]
        last = trade.setup.signal_time if self.at_signal.isChecked() else trade.exit_time+10*step
        candles = [c for c in self.test_candles if trade.setup.signal_time-40*step <= c.time <= last]
        zones=[z for z in (trade.setup.zone,trade.setup.target_zone) if z]
        self.inspector.draw(candles,step,zones,trade.setup,None if self.at_signal.isChecked() else trade)
        self.trade_reasons.setPlainText(f'{trade.outcome} · {trade.r:.2f} net R · {trade.return_pct:.2f}% price return · {trade.exit_reason}\nEntry {stamp(trade.entry_time)} · Exit {stamp(trade.exit_time)} · {trade.setup.market_state}\n'+'\n'.join(trade.setup.reasons))
        if trade.gross_r is not None:
            self.trade_reasons.append(f'Gross {trade.gross_r:.3f} R − fees {trade.fees_r:.3f} R − slippage {trade.slippage_r:.3f} R = net {trade.r:.3f} R. Zone/target snapshots frozen at signal.')

    def refresh_runs(self):
        previous=self.runs.currentData()
        self.runs.clear()
        for run_id,created,payload in self.repo.runs():
            p = json.loads(payload)
            self.runs.addItem(f'#{run_id} · {created} · {p["timeframe"]} · {p.get("config",{}).get("entry_mode","legacy confirmation")} · {p["source"]}',run_id)
        index=self.runs.findData(previous)
        if index>=0:
            self.runs.setCurrentIndex(index)

    def restore_run(self):
        run_id = self.runs.currentData()
        if run_id is None:
            return
        result = self.repo.load_run(run_id)
        candles = self.repo.candles(result.source,result.timeframe,result.start-result.config.lookback*SECONDS[result.timeframe],result.end)
        self.show_result((result,candles,f'Saved run #{run_id} · {result.source} · {result.timeframe}'))
        self.runs.setCurrentIndex(self.runs.findData(run_id))

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            self.status.setText('Please wait for the active download/backtest before closing.'); event.ignore()
        else:
            self.quote_poller.set_enabled(False)
            self.quote_age_timer.stop();self.history_timer.stop()
            event.accept()
