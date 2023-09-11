#!/usr/bin/env python
# coding:utf-8

from os import getpid as osGetpid
from time import sleep
from threading import Thread
from socketserver import ThreadingTCPServer, StreamRequestHandler
from collections import deque
from telebot import TeleBot


# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.MyLogger.my_logger import MyLogger
from common.Database.database import Database
from common.ThreadQs.thread_Qs import Qmsg
from common.Helpers.helpers import threadIt, getUnusedPort, load_config_files
from common.Helpers.network_helpers import SafeSocket
from common.TeleRemote.tele_funcs import init_bot, create_bot


TELE_REMOTE_SERVER_NAME="tele_remote"

Shared_send_msg_in = deque()
Shared_recv_msg_in = deque()

##############################################################################################################################################################################################

class ClientsInfo(object):
    StartQsLists = {}
    def __init__(self):
        self.count = 0
    def __call__(self, name, host, port, send_func_Ptr, safe_sock_Ptr):
        self.StartQsLists[name] = host, port, send_func_Ptr, safe_sock_Ptr
    def send_msg_too(self, msg:str, too:str):
        _, _, send_func, safe_sock = self.StartQsLists[too]
        send_func(safe_sock, msg)
    def __len__(self):
        return len(self.StartQsLists)
    
##############################################################################################################################################################################################

def start_bot(name, logger:MyLogger, config:Config):
    Bot = init_bot(config=config, logger=logger)

    class TeleRemote:
        Name = "TeleRemote"
        def __init__(self, name, logger:MyLogger, config:Config, Bot:TeleBot):
            self.Name = name
            self.logger = logger
            self.config = config
            self.Bot = Bot
            Thread(target=self.recv_msg_in).start()
            self.start_polling()

        @threadIt   
        def start_polling(self):
            self.Bot.infinity_polling()

        @threadIt
        def send_msg_in(self, msg, too:str=None):
            global Shared_send_msg_in
            try:
                TeleChacheInfo = Shared_send_msg_in.pop()
                if len(TeleChacheInfo) == 0:
                    # no messages
                    self.Bot.send_message(self.config.TB_CHATID, "🏛 no broker linked !")
                    Shared_send_msg_in.append(TeleChacheInfo)
                else:
                    # to one particular 'TeleThreadInterface' connected
                    if not too is None:
                        TeleChacheInfo.send_msg_too(msg, too)
                        TeleChacheInfo.StartQsLists.pop(too)
                    # to all 'TeleThreadInterface' connected
                    else:
                        for que in TeleChacheInfo.StartQsLists.keys():
                            TeleChacheInfo.send_msg_too(msg, too=que)
                        TeleChacheInfo.StartQsLists.clear()
                    Shared_send_msg_in.append(TeleChacheInfo)
            except Exception as e:
                if len(Shared_send_msg_in) == 0:
                    self.Bot.send_message(self.config.TB_CHATID, "Error while sending command to StarQs : {0}".format(e))
                    self.logger.error("Telecommand : error while sending command to StarQs : 'Shared_send_msg_in empty !!!'")
                    pass
                else:
                    self.Bot.send_message(self.config.TB_CHATID, "Error while sending command to StarQs : {0}".format(e))
                    self.logger.error("Telecommand : error while sending command to StarQs : {0}".format(e))

        def recv_msg_in(self):
            global Shared_recv_msg_in
            while self.Bot is None:
                sleep(self.config.MAIN_QUEUE_BEAT)
            while True:
                try:
                    if len(Shared_recv_msg_in) > 0:
                        starQ_msg = Shared_recv_msg_in.popleft()
                        if isinstance(starQ_msg, list):
                            self.Bot.send_message(self.config.TB_CHATID, "{0}=>{1}".format(starQ_msg[1], starQ_msg[0]))         
                        #elif isinstance(starQ_msg, list):
                        #    self.Bot.send_message(self.config.TB_CHATID, "{0}=>{1}".format(starQ_msg[1], starQ_msg[0]))                     
                        else:
                            self.Bot.send_message(self.config.TB_CHATID, "{0}".format(starQ_msg))
                except Exception as e:
                    self.Bot.send_message(self.config.TB_CHATID, "Error while receiving message '{0}' : {1}".format(starQ_msg[0], e))
                    self.logger.error("Telecommad : error while receiving message '{0}' : {1}".format(starQ_msg[0], e))
                    pass
                sleep(self.config.MAIN_QUEUE_BEAT)
                
    TeleCommand = TeleRemote(name, logger, config, Bot)
    TeleCommand = create_bot(TeleCommand=TeleCommand, Bot=Bot)
    return TeleCommand

##############################################################################################################################################################################################

class TeleThreadInterface(StreamRequestHandler):
    QAddress = None
    logger = None
    waite = None
    def handle(self):
        global Shared_recv_msg_in
        TeleSocket = SafeSocket(self.connection)
        msg = TeleSocket.receive_data()
        if not msg:
            return
        name, host, port = msg.split(':') ; port = int(port)
        
        while True:
            # get broker address
            if len(self.QAddress) == 1:
                TeleChacheInfo = self.QAddress.pop()
                TeleChacheInfo(name, host, port, self.send_msg, TeleSocket)
                self.QAddress.append(TeleChacheInfo)
                break
        self.logger.info("TeleCommand : StarQs '{0}' has established connection without encryption from '{1}' destport '{2}'".format(name, host, port))#srcport '{3}' , self.server[0]
        while True:
            data = TeleSocket.receive_data()
            if not data:
                break
            try:
                if isinstance(data, Qmsg):
                    recv_msg = data.msg
                    # pop bot.send_message func in deque ??
                    Shared_recv_msg_in.append([recv_msg, data.frome])
                else:
                    Shared_recv_msg_in.append(data)
            except Exception as e:
                self.logger.error("TeleCommand : error while trying to read Qmsg '{0}' : '{1}'".format(msg, e))

    @threadIt
    def send_msg(self, TeleSocket:SafeSocket, msg:str):
        try:
            TeleSocket.send_data(msg)
        except Exception as e:
            self.logger.error("TeleCommand : error while trying to send msg '{0}' : '{1}'".format(msg, e))

##############################################################################################################################################################################################

class TelecommandSocketServer(ThreadingTCPServer):
    """ Telecommand server..."""
    Name = "telecommand"
    SocketServer = None
    Bot = None
    allow_reuse_address = True
    waite = None

    def __init__(self, config:Config, handler=TeleThreadInterface, externalCall=False): 
        global Shared_send_msg_in ; Shared_send_msg_in.append(ClientsInfo())

        self.config = config
        if not externalCall:
            self.config.update(section="COMMON", configPath=config.COMMON_FILE_PATH, params={"TB_PORT": str(getUnusedPort())})

        self.logger = MyLogger(self.Name, config, start_telecommand=False)
        dblog = Database(self.logger, config)  
        ## late binding
        self.logger.DBlog = dblog
        self.waite = self.config.MAIN_QUEUE_BEAT

        handler.QAddress = Shared_send_msg_in
        handler.logger = self.logger
        handler.waite = self.config.MAIN_QUEUE_BEAT

        ThreadingTCPServer.__init__(self, (self.config.TB_IP, int(self.config.TB_PORT)), handler)
        self.port = int(self.config.TB_PORT)
        self.abort = 0
        self.timeout = 1

        self.run_bot("TeleCommand", self.logger, self.config)
        self.logger.info("Telecommand : Telecommand TCP server is starting.. .  . ")
        self.serve_until_stopped()
        
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

    @threadIt
    def run_bot(self, name, logger, config):
        global Shared_send_msg_in
        while len(Shared_send_msg_in) == 0:
            sleep(self.waite)
        self.Bot = start_bot(name, logger, config)

#================================================================
if __name__ == "__main__":
    from sys import argv
    from common.Helpers.helpers import init_logger, caffeinMe

    caffeinMe(pid=osGetpid())

    configStr = "common"     
    if len(argv) > 1:
        try :
            if len(argv) == 3:
                config = Config(config_file_path=argv[1], name=TELE_REMOTE_SERVER_NAME)
                Shared_Telecommande = TelecommandSocketServer(config, externalCall=argv[2])
            else:
                _, logger = init_logger(name=TELE_REMOTE_SERVER_NAME, config=configStr)
                logger.error("Telecommand : error while trying to launch the service, {0} parameter(s) provided : {1}, expected : 2 'config path and externalCall' -{2}".format("too much" if len(argv) > 3 else "not enough", len(argv)-1, str(argv)))
        except Exception as e:
            _, logger = init_logger(name=TELE_REMOTE_SERVER_NAME, config=configStr)
            logger.error("Telecommand : error while trying to launch the service, wrong parameter(s) provided : {0} => {1}".format(str(argv), e))
    else:
        # if process launched via vscode....
        from common.Helpers.os_helpers import nb_process_running
        nb_running, pidList = nb_process_running(TELE_REMOTE_SERVER_NAME, getPid=True)
        if nb_running > 2:
            # 2 -> current process + vscode process...
            _, logger = init_logger(name="{0}_2".format(TELE_REMOTE_SERVER_NAME))
            logger.error("Tele Remote : error while trying to start process : process already running ! (pid:{0})".format(pidList))
            exit(0)

        configStr = "trading"
        configPath = load_config_files()[configStr]
        #config=Config(name=TELE_REMOTE_SERVER_NAME)
        config = Config(config_file_path=configPath, name=TELE_REMOTE_SERVER_NAME)
        Shared_Telecommande = TelecommandSocketServer(config)


    #config = Config(name="tele_remote")
    #logger = MyLogger("tele_command", config, start_telecommand=False)
    #dblog = Database(logger, config)    

    ### late binding
    #logger.DBlog = dblog   
    #"TeleCommand", logger, config)

    ## starting MainQ
    #MainQ = StarQs(logger, config)  

    #toto2 = SubsQ("receiver1", MainQ, "TeleCommand2")
    #toto3 = SubsQ("receiver", MainQ, "TeleCommand2")

    #TeleCommand = start_bot("TeleCommand2", MainQ, logger, config)

    #for x in range(10):
    #    toto2.send_msg_in("did you recieved my message (toto2)")
    #    sleep(0.5)
    #    toto3.send_msg_in(" !!!! did you recieved my message (toto3)")

    














