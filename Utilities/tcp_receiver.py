#!/usr/bin/env python
# coding:utf-8

from socketserver import ThreadingTCPServer, StreamRequestHandler

# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.MyLogger.my_logger import MyLogger
from common.Helpers.network_helpers import SafeSocket



class StreamHandlerMixin(StreamRequestHandler):
    """ 
    overide the 'def stream_func(self, data):' or pass it to the SocketReceiverMixin __init__()
    """
    Name="StreamHandlerMixin"
    current_logger = None
    stream_func = None
    SessionMaker = None
    def handle(self):
        MySocket = SafeSocket(self.connection)
        msg = MySocket.receive_data()
        if not msg:
            return

        self.clientName, self.clientHost, port = msg.split(':') ; self.clientPort = int(port)
        self.current_logger.info("{0} : '{1}' has established connection without encryption from '{2}' destport '{3}'".format(self.Name, self.clientName, self.clientHost, self.clientPort))#srcport '{3}'
        
        while True:
            data = MySocket.receive_data()
            if not data:
                break
            try:
                self.current_logger.debug("{0} : data received from '{1}' : {2}".format(self.Name, self.clientName, data))
                self.stream_func(handlerName=self.Name, clientName=self.clientName, data=data)
            except Exception as e:
                self.current_logger.error("{0} : error while trying to receive data from '{1}' : {2}".format(self.Name, self.clientName, e))

    def stream_func(self, handlerName, clientName, data):
        self.current_logger.info("{0} : stream_func data received from {1} : {2}".format(handlerName, clientName, str(data)))


class SocketReceiverMixin(ThreadingTCPServer):
    """ 
    Override the '__init__(self, logger:MyLogger, config:Config, name=None, stream_func=None, handler=StreamHandlerMixin)' \n
    And add 'self.init_mixin(self, name, stream_func, handler)' at the end
    """
    allow_reuse_address = True
    Name = "SocketReceiverMixin"
    def __init__(self, logger:MyLogger, config:Config, name=None, stream_func=None, handler=StreamHandlerMixin, SocketReceiverMixinOnly=False):
        try:
            if not name is None:
                self.Name = name.capitalize()
            self.config = config 
            self.logger = handler.current_logger = logger
            self.config = config
        except Exception as e:
            self.logger.error("{0} : error while trying to initialize 'SocketReceiver' object : {1}".format(self.Name, e))

        # without inheritance
        if SocketReceiverMixinOnly:
            from common.Helpers.helpers import getUnusedPort
            self.host = '127.0.0.1'
            self.port = int(getUnusedPort())

        handler.Name = name
        if not stream_func is None:
            handler.stream_func = stream_func

        ThreadingTCPServer.__init__(self, (self.host, int(self.port)), handler)
        self.abort = 0
        self.timeout = 1
        self.logname = None


    def serve_until_stopped(self):
        import select
        abort = 0
        self.logger.info("{0} : socket stream handler is open : '{1}', srcport : '{2}'".format(self.Name, self.host, int(self.port)))
        while not abort:
            rd, wr, ex = select.select([self.socket.fileno()],
                                       [], [],
                                       self.timeout)
            if rd:
                self.handle_request()
            abort = self.abort

#================================================================
if __name__ == "__main__":
    from common.Helpers.helpers import init_logger
    name = "SocketReceiverMixin"
    configStr = "common"

    config, logger = init_logger(name=name, config=configStr)
    streamHandler = SocketReceiverMixin(name=name, config=config, logger=logger)
    streamHandler.serve_until_stopped()

## test
#from common.Helpers.network_helpers import MySocket
#def test_con():
#    with MySocket(port=50452) as sock:
#        sock.send_data("client:local:1234")
#test_con()