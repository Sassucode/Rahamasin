"""Nonblocking polling: one request at a time; source changes discard old replies."""
import json,time
from PySide6 import QtCore,QtNetwork
from ..data.quotes import ENDPOINTS,BINANCE,parse_quote

class QuotePoller(QtCore.QObject):
    updated=QtCore.Signal(object)
    failed=QtCore.Signal(str)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.source=BINANCE;self.enabled=False;self.reply=None
        self.network=QtNetwork.QNetworkAccessManager(self)
        self.timer=QtCore.QTimer(self);self.timer.setInterval(5000)
        self.timer.timeout.connect(self.poll)

    def set_source(self,source):
        if source==self.source:return
        self.cancel();self.source=source
        if self.enabled:self.poll()

    def cancel(self):
        old=self.reply;self.reply=None
        if old is not None:old.abort()

    def set_enabled(self,enabled):
        self.enabled=enabled
        if enabled:self.timer.start();self.poll()
        else:self.timer.stop();self.cancel()

    def poll(self):
        if not self.enabled or self.reply is not None:return
        if self.source not in ENDPOINTS:
            self.failed.emit('Live quotes unavailable for this data source');return
        source=self.source
        request=QtNetwork.QNetworkRequest(QtCore.QUrl(ENDPOINTS[source]))
        request.setTransferTimeout(8000)
        request.setRawHeader(b'User-Agent',b'Rahamasin/2.2')
        request.setAttribute(QtNetwork.QNetworkRequest.Attribute.CacheLoadControlAttribute,QtNetwork.QNetworkRequest.CacheLoadControl.AlwaysNetwork)
        reply=self.network.get(request);self.reply=reply
        reply.finished.connect(lambda:self.complete(reply,source))

    def complete(self,reply,source):
        try:
            if reply is not self.reply or not self.enabled or source!=self.source:return
            self.reply=None
            if reply.error()!=QtNetwork.QNetworkReply.NetworkError.NoError:
                raise ValueError(reply.errorString())
            quote=parse_quote(source,json.loads(bytes(reply.readAll())),time.time())
            self.updated.emit(quote)
        except (ValueError,KeyError,TypeError,OverflowError) as exc:
            self.failed.emit(str(exc))
        finally:reply.deleteLater()
