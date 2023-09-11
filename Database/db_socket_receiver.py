#!/usr/bin/env python
# coding:utf-8


# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.MyLogger.my_logger import MyLogger
from common.Helpers.helpers import getUnusedPort
from common.Utilities.tcp_receiver import SocketReceiverMixin, StreamHandlerMixin


def stream_func(self, handlerName, clientName, data):
    self.current_logger.info("{0} : data received from {1} : {2}".format(handlerName, clientName, str(data)))



class DBStreamHandler(StreamHandlerMixin):
    Name="DatabaseStreamHandler"

class DBSocketReceiver(SocketReceiverMixin):
    """ 
    Database TCP socket receiver...
    Provide DB_FeedFunc or DatabaseStreamHandler or even both...
    by default the default DatabaseStreamHandler is loaded and only DB_FeedFunc is needed
    For complex connection use DatabaseStreamHandler and DB_FeedFunc (can use multiple DBSocketReceiver)
    """
    Name = "DBSocketReceiver"
    logger = None
    allow_reuse_address = True
    def __init__(self, name, logger:MyLogger, config:Config, stream_func=stream_func, DBStreamHandler=DBStreamHandler, prefixe=None, inMemory=None, UpdatePort:bool=True):  
        if not name is None:
            self.Name = "DBSockRecv_{0}".format(name.capitalize())
        if prefixe is None:
            prefixe = name
        self.prefixe = prefixe.upper()

        try:
            if UpdatePort:
                db_port = str(getUnusedPort()) #; mem_db_port = str(getUnusedPort())
                config.update(section=name.upper(), configPath=config.COMMON_FILE_PATH, 
                params={
                        "{0}_DB_PORT".format(self.prefixe):db_port, 
                        #"{0}_DB_MEM_PORT".format(self.prefixe):mem_db_port,
                        "{0}_DB_ENDPOINT".format(self.prefixe):"http://db:{0}".format(db_port), 
                        #"{0}_DB_MEM_ENDPOINT".format(self.prefixe):"http://db:{0}".format(mem_db_port),
                        }, 
                        name=name.capitalize())
            config = dict(config.parser.items(name.upper()))

            self.host = config["{0}_SERVER".format(self.prefixe)]
            self.port = int(config["{0}_DB_PORT".format(self.prefixe)])
        except Exception as e:
            logger.error("{0} : error while trying to initialize 'DBSocketReceiver' object : {1}".format(self.Name, e))

        SocketReceiverMixin.__init__(self, logger=logger, config=config, name=self.Name, stream_func=stream_func, handler=DBStreamHandler)
