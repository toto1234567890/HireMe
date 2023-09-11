#!/usr/bin/env python
# coding:utf-8

import logging
from socketserver import ThreadingTCPServer, StreamRequestHandler
from os import mkdir as osMkdir, getcwd as osGetcwd
from os.path import join as osPathJoin
from logging.handlers import RotatingFileHandler, DEFAULT_TCP_LOGGING_PORT
from genericpath import exists


# relative import
from sys import path;path.extend("..")
from common.Helpers.network_helpers import SafeSocket
from common.MyLogger.my_logger import DEFAULT_LOGGER_FORMAT



LOG_SERVER_NAME = "log_server"

class LogRecordStreamHandler(StreamRequestHandler):
    def handle(self):
        while True:    
            LogRecordSocket = SafeSocket(self.connection)
            obj = LogRecordSocket.receive_data()
            if not obj:
                break            
            record = logging.makeLogRecord(obj)
            self.handleLogRecord(record)               

    def handleLogRecord(self, record):
        if self.server.logname is not None:
            name = self.server.logname
        else:
            name = record.name
        logger = logging.getLogger(name)
        logger.handle(record)


class LogRecordSocketReceiver(ThreadingTCPServer):
    """ Log server..."""
    allow_reuse_address = True
    def __init__(self, host="127.0.0.1", port=DEFAULT_TCP_LOGGING_PORT, handler=LogRecordStreamHandler):
        ThreadingTCPServer.__init__(self, (host, port), handler)
        self.port = port
        self.abort = 0
        self.timeout = 1
        self.logname = None

    def serve_until_stopped(self):
        import select
        abort = 0
        while not abort:
            rd, wr, ex = select.select([self.socket.fileno()],
                                       [], [],
                                       self.timeout)
            if rd:
                self.handle_request()
            abort = self.abort


def LogServer(log_dir=osPathJoin(osGetcwd(), "logs"), log_level=logging.DEBUG):
    # Logger setup
    if not exists(log_dir):
        osMkdir(log_dir)
    logging.basicConfig(
        handlers=[#logging.StreamHandler(), #enable it for testing purposes
                    RotatingFileHandler("{0}.log".format(osPathJoin(log_dir, "_main")), maxBytes=2097152, backupCount=50)],
        encoding="utf-8", 
        format=DEFAULT_LOGGER_FORMAT.LOG_SERVER,
        datefmt=DEFAULT_LOGGER_FORMAT.DATEFMT, 
        level=log_level
        )
    tcpserver = LogRecordSocketReceiver()
    tcpserver.serve_until_stopped()

#================================================================
if __name__ == "__main__":
    from sys import argv
    if len(argv) > 3:
        print("Too much argument sent to log_server !\n \
        first argument should be :\n \
            - 'log directory path'\n \
        second argument should be the logger 'level':\n \
            - CRITICAL = 50 (FATAL = CRITICAL)\n \
            - ERROR = 40 \n \
            - WARNING = 30 \n \
            - WARN = WARNING \n \
            - DEBUG = 10 \n \
            - NOTSET = 0") 

    if len(argv) > 1:
        # argv[2] = externalCall = True
        LogServer()
    else:
        # if process launched via vscode....
        from common.Helpers.os_helpers import nb_process_running
        nb_running, pidList = nb_process_running(LOG_SERVER_NAME, getPid=True)
        if nb_running > 2:
            # 2 -> current process + vscode process...
            from common.Helpers.helpers import init_logger
            _, logger = init_logger(name="{0}_2".format(LOG_SERVER_NAME))
            logger.error("Log server : error while trying to start process : process already running ! (pid:{0})".format(pidList))
            exit(0)

        LogServer()

