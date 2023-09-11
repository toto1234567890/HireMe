#!/usr/bin/env python
# coding:utf-8

from collections import deque
from socketserver import ThreadingTCPServer, StreamRequestHandler

# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.Notifie.notifie import Notifie
from common.Helpers.network_helpers import SafeSocket

NOTIF_SERVER_NAME = "notif_server"

send_notif = None

class NotifsStreamHandler(StreamRequestHandler):

    def handle(self):
        NotifSocket = SafeSocket(self.connection)    
        while True:     
            data = NotifSocket.receive_data()
            if not data:
                break
            while True:
                if len(send_notif) > 0:
                    send_notif_ptr = send_notif.pop()
                    send_notif_ptr(data[0], data[1], data[2])
                    send_notif.append(send_notif_ptr)
                    break
                #time.sleep(config.MAIN_QUEUE_BEAT)
                     
            # Queue.queue mode
            #notif_serv_obj.queue.put((obj[0], obj[1], obj[2]))
            # deque mode
            # notif_serv_obj.append((obj[0], obj[1], obj[2]))

class NotifSocketReceiver(ThreadingTCPServer):
    """ Notif server..."""
    allow_reuse_address = True
    def __init__(self, config:Config, port:int=None, handler=NotifsStreamHandler):
        host = config.NT_IP
        if port == None:
            port = int(config.NT_PORT)
        ThreadingTCPServer.__init__(self, (host, port), handler)
        self.port = port 
        self.abort = 0
        self.timeout = 1

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

def NotifServer(config:Config, port:int=None):
    tcpserver = NotifSocketReceiver(config, port)
    tcpserver.serve_until_stopped()



#================================================================
if __name__ == "__main__":
    from sys import argv

    send_notif = deque()
    notif_serv_obj = Notifie(True)
    send_notif.append(notif_serv_obj.send_notification)

    if len(argv) > 1:
        from common.Helpers.helpers import init_logger
        try :
            if len(argv) == 3:
                config = Config(config_file_path=str(argv[1]), name=NOTIF_SERVER_NAME)
                NotifServer(config=config, port=int(argv[2]))
            if len(argv) == 2:
                config = Config(config_file_path=str(argv[1]), name=NOTIF_SERVER_NAME)
                NotifServer(config=config)
            else:
                _, logger = init_logger(name=NOTIF_SERVER_NAME, config="common")
                logger.error("Notifs server : error while trying to launch the service, {0} parameter(s) provided : {1}, expected : 1 'config file' -{2}".format("too much" if len(argv) > 2 else "not enough", len(argv)-1, str(argv)))
        except Exception as e:
            _, logger = init_logger(name=NOTIF_SERVER_NAME, config="common")
            logger.error("Notifs server : error while trying to launch the service, wrong parameter(s) provided : {0} => {1}".format(str(argv), e))
    else:
        # if process launched via vscode....
        from common.Helpers.os_helpers import nb_process_running
        nb_running, pidList = nb_process_running(NOTIF_SERVER_NAME, getPid=True)
        if nb_running > 2:
            # 2 -> current process + vscode process...
            from common.Helpers.helpers import init_logger
            _, logger = init_logger(name="{0}_2".format(NOTIF_SERVER_NAME))
            logger.error("Config server : error while trying to start process : process already running ! (pid:{0})".format(pidList))
            exit(0)
        config = Config(name="notif_server")  # change it depending from where you launch it !!
        #config = Config(config_file_path="trading/trading.cfg")
        NotifServer(config=config)

#    send_notif = deque()
#    notif_serv_obj = Notifie(True)
#    send_notif.append(notif_serv_obj.send_notification)
#
#    if len(argv) > 1:
#        config = Config(config_file_path=argv[1])
#    else:
#        config = Config()
#
#    NotifServer(config)

