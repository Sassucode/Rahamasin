import pyqtgraph as pg
from PySide6 import QtCore, QtGui


class Candlesticks(pg.GraphicsObject):
    def __init__(self, candles, step):
        super().__init__()
        self.picture = QtGui.QPicture()
        painter = QtGui.QPainter(self.picture)
        for c in candles:
            color = '#49c8ac' if c.close >= c.open else '#ed7786'
            painter.setPen(pg.mkPen(color))
            painter.setBrush(pg.mkBrush(color))
            painter.drawLine(QtCore.QPointF(c.time,c.low),QtCore.QPointF(c.time,c.high))
            painter.drawRect(QtCore.QRectF(c.time-step*.32,min(c.open,c.close),step*.64,max(abs(c.close-c.open),c.close*.0001)))
        painter.end()

    def paint(self, painter, *args):
        painter.drawPicture(0,0,self.picture)

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())


class Chart(pg.PlotWidget):
    def __init__(self):
        super().__init__(axisItems={'bottom':pg.DateAxisItem(utcOffset=0)},background='#101722')
        self.showGrid(x=True,y=True,alpha=.12)
        self.setLabel('left','Price')
        self.getAxis('left').enableAutoSIPrefix(False)
        self.setLabel('bottom','UTC')
        self.setMinimumHeight(280)
        self.setMenuEnabled(False)

    def draw(self, candles, step, zones=(), setup=None, trade=None):
        self.clear()
        self.live_line=None
        if not candles:
            return
        self.addItem(Candlesticks(candles,step))
        price = candles[-1].close
        for z in zones:
            color = (73,200,172,24) if z.midpoint <= price else (237,119,134,24)
            band = pg.LinearRegionItem((z.low,z.high),orientation='horizontal',brush=color,
                pen=pg.mkPen(color[:3]+(65,)),movable=False)
            self.addItem(band)
        if setup and setup.entry is not None:
            self.addItem(pg.LinearRegionItem((setup.entry_low,setup.entry_high),orientation='horizontal',
                brush=(120,155,245,50),pen=pg.mkPen('#789bf5'),movable=False))
            for value,label,color in [(setup.entry,'ENTRY','#789bf5'),(setup.stop,'STOP','#ed7786'),(setup.target,'TARGET','#49c8ac')]:
                if value is not None:
                    self.addItem(pg.InfiniteLine(value,angle=0,pen=pg.mkPen(color,width=1.5),label=f'{label} {value:.5f}',labelOpts={'position':.85,'color':color}))
        if trade:
            self.addItem(pg.InfiniteLine(trade.entry_time,angle=90,pen=pg.mkPen('#789bf5',style=QtCore.Qt.PenStyle.DashLine)))
            self.addItem(pg.InfiniteLine(trade.exit_time,angle=90,pen=pg.mkPen('#d8b471',style=QtCore.Qt.PenStyle.DashLine)))
        self.setXRange(candles[0].time-step,candles[-1].time+step,padding=.02)
        values = [c.low for c in candles]+[c.high for c in candles]
        if setup and setup.entry is not None:
            values += [v for v in (setup.stop,setup.target) if v is not None]
        self.setYRange(min(values),max(values),padding=.08)

    def set_live_price(self,value):
        if getattr(self,'live_line',None) is not None:
            self.removeItem(self.live_line);self.live_line=None
        if value is not None:
            self.live_line=pg.InfiniteLine(value,angle=0,pen=pg.mkPen('#f2ce76',style=QtCore.Qt.PenStyle.DashLine),
                label=f'LIVE {value:.5f}',labelOpts={'position':.1,'color':'#f2ce76'})
            self.addItem(self.live_line,ignoreBounds=True)
