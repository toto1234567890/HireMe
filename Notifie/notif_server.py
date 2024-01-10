#!/usr/bin/env python
# coding:utf-8

from collections import deque
from socketserver import ThreadingTCPServer, StreamRequestHandler

# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.Notifie.notifie import Notifie
from common.Helpers.helpers import default_arguments, load_config_files
from common.Helpers.network_helpers import SafeSocket

NOTIF_SERVER_NAME = "notif_server"
LOG_LEVEL = 10

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
        else:
            config.update(section="COMMON", configPath=config.COMMON_FILE_PATH, params={"NT_PORT":port})
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
    from platform import system as platformSystem

    log_level = LOG_LEVEL
    configStr = "current"

    send_notif = deque()
    notif_serv_obj = Notifie(True)
    send_notif.append(notif_serv_obj.send_notification)

    if len(argv) > 1:
        from common.Helpers.helpers import init_logger
        try :
            argsAndVal, defaultArgs = default_arguments(argv=argv)
            if argsAndVal:

                if "name" in argsAndVal: NOTIF_SERVER_NAME = argsAndVal.pop("name")
                if "log_level" in argsAndVal: log_level = argsAndVal.pop("log_level")
                if "host" in argsAndVal: argsAndVal.pop("host") # FIXME teleportation !

                if "conf" in argsAndVal: 
                    config_path = load_config_files()[argsAndVal.get("conf")] 
                    argsAndVal.pop("conf")              
                if not "conf" in argsAndVal: config_path = load_config_files()[configStr]
                
                config = Config(config_file_path=config_path, name=NOTIF_SERVER_NAME)
                argsAndVal["config"] = config
                NotifServer(**argsAndVal)
            else:
                cmdLineInfo = """
                Authorized arguments : \n \
                    default optional arguments :\n \
                        --name \n \
                        --host \n \
                        --port \n \
                        --conf \n \
                """.format(argv)
                _, logger = init_logger(name=NOTIF_SERVER_NAME, config="common", log_level=log_level)
                logger.error("{0} : error while trying to launch the service, wrong parameter(s) provided : {1}\n {2}".format(NOTIF_SERVER_NAME, str(argv), cmdLineInfo))
        except Exception as e:
            _, logger = init_logger(name=NOTIF_SERVER_NAME, config="common", log_level=log_level)
            logger.error("{0} : unexpected error while trying to launch the service, parameter(s) provided : {1} => {2}".format(NOTIF_SERVER_NAME, str(argv), e))
    else:
        # if process launched via vscode....
        from common.Helpers.os_helpers import nb_process_running
        nb_running, pidList = nb_process_running(NOTIF_SERVER_NAME, getPid=True)
        launch_vscode = 4 if platformSystem() == "Windows" else 2
        if nb_running > launch_vscode:
            # 2 -> current process + vscode process...
            from common.Helpers.helpers import init_logger
            _, logger = init_logger(name="{0}_2".format(NOTIF_SERVER_NAME), log_level=log_level)
            logger.error("Config server : error while trying to start process : process already running ! (pid:{0})".format(pidList))
            exit(0)
        config = Config(name=NOTIF_SERVER_NAME, config_file_path=load_config_files()[configStr])  # change it depending from where you launch it !!
        # config = Config(config_file_path="trading/trading.cfg")
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

