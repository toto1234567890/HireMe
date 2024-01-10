#!/usr/bin/env python
# coding:utf-8

from os import getpid as osGetpid

# relative import
from sys import path;path.extend("..")
from common.ThreadQs.thread_Qs import Qmsg
from common.Helpers.helpers import getUnusedPort, init_logger, threadIt


TELE_REMOTE_SERVER_TYPE = "ASYNC" # THREAD or ASYNC
TELE_REMOTE_SERVER_NAME = "tele_remote"
LOG_LEVEL = 10
SPECIFIC_ARGS = ["--only_logger"]


TeleCommand = None
if TELE_REMOTE_SERVER_TYPE.lower() == "async":
    from os.path import sep as osPathSep
    from datetime import datetime
    from asyncio import run as asyncioRun, get_running_loop as asyncioGet_running_loop, start_server as asyncioStart_server, \
                        Lock as asyncioLock

    # relative import
    from sys import path;path.extend("..")
    from common.ThreadQs.thread_Qs import Qmsg
    from common.Helpers.helpers import Singleton, getUnusedPort, init_logger, threadIt
    from common.Helpers.network_helpers import SafeAsyncSocket
    from common.TeleRemote.tele_funcs import init_bot, create_bot

    class TeleRemote(metaclass=Singleton):
        Name = "TeleRemote"
        StartQsLists = {}
        config = None
        logger = None
        asyncLoop = None
        asyncLock = asyncioLock()
        Bot = None

        def __init__(self, config, logger, Bot):
            self.config = config
            self.logger = logger
            self.Bot = Bot 

        async def send_msg_in(self, msg:str, too=False):
            if len(self.StartQsLists) == 0:
                await self.Bot.send_message(self.config.TB_CHATID, "🏛 no broker linked !")
            elif too:
                try:
                    _, _, _, TeleSock = self.StartQsLists[too]
                    await TeleSock.send_data(msg)
                except Exception as e:
                    await self.Bot.send_message(self.config.TB_CHATID, "Error while sending command to '{0}' : {1}".format(too, e))
                    await self.logger.asyncError("{0} : error while trying to send msg '{1}' to '{2}' : '{3}'".format(self.Name, msg, too, e))
            else:
                StartQsLists = self.StartQsLists.values()
                for listener in StartQsLists:
                    try:
                        _, _, _, TeleSock = listener
                        await TeleSock.send_data(msg)                  
                    except Exception as e:
                        await self.Bot.send_message(self.config.TB_CHATID, "Error while sending command to '{0}' : {1}".format(too, e))
                        await self.logger.asyncError("{0} : error while trying to send msg '{1}' to '{2}' : '{3}'".format(self.Name, msg, too, e))
                        continue

        async def recv_msg_in(self, data):
            try:
                if isinstance(data, Qmsg):
                    await self.Bot.send_message(self.config.TB_CHATID, "{0}=>{1}".format(data.msg, data.frome))
                else:
                    await self.Bot.send_message(self.config.TB_CHATID, "{0}".format(data))               
            except Exception as e:
                if isinstance(data, Qmsg):
                    await self.Bot.send_message(self.config.TB_CHATID, "Error while receiving message '{0}' from {1} : {2}".format(data.msg, data.frome, e))
                    await self.logger.asyncError("{0} : error while receiving message '{1}' from {2} : {3}".format(self.Name, data.msg, data.frome, e))
                else:
                    await self.Bot.send_message(self.config.TB_CHATID, "Error while receiving message '{0}' : {1}".format(data, e))
                    await self.logger.asyncError("{0} : error while receiving message '{1}' : {2}".format(self.Name, data, e))                


        async def remove_client(self, key):
            async with self.asyncLock:
                if key in self.StartQsLists:
                    self.StartQsLists.pop(key)
        async def add_client(self, name, host, port, TeleSock):
            async with self.asyncLock:
                if name != "tri_watch_dog":
                    self.StartQsLists[name] = (name, host, port, TeleSock)

    ####################################################################

    async def start_bot(config, logger):
        global TeleCommand 
        Bot = init_bot(config=config, logger=logger, async_mode=True)
        TeleCommand = TeleRemote(config=current_config, logger=current_logger, Bot=Bot)
        TeleCommand, Bot = create_bot(TeleCommand=TeleCommand, Bot=Bot, async_mode=True)
        await Bot.polling(none_stop=True)

    ####################################################################

    async def handle_TCP_client(reader, writer):
        Name = "TeleRemoteHandler"
        global current_logger
        global TeleCommand

        TeleSock = SafeAsyncSocket(reader=reader, writer=writer)
        try:
            data = await TeleSock.receive_data()
        except Exception as e:
            await current_logger.asyncError("{0} : error while trying to initiate connection : {1}".format(Name, e))
            TeleSock.writer.close()
            await TeleSock.writer.wait_closed()
            return

        if not data:
            TeleSock.writer.close()
            await TeleSock.writer.wait_closed()
            return

        clientName, host, port = data.split(':') ; port = int(port)
        await TeleCommand.add_client(name=clientName, host=host, port=port, TeleSock=TeleSock)
        await current_logger.asyncInfo("{0} : '{1}' has established connection without encryption from '{2}' destport '{3}'".format(Name, clientName, host, port))

        while True:
            try:
                data = await TeleSock.receive_data()
            except Exception as e:
                await current_logger.asyncError("{0} : error while trying to received data, closing connection : {1}".format(Name, e))
                break              
            if not data:
                break
            await TeleCommand.recv_msg_in(data=data)

        try:
            await TeleCommand.remove_client(key=clientName)
            TeleSock.writer.close()
            await TeleSock.writer.wait_closed()
        except:
            pass

    async def async_tcp_server(srv_port:str, Name:str="TeleRemoteReceiver"):
        global current_logger
        try:
            async_TCP_IP = '127.0.0.1' ; async_TCP_port = int(srv_port)
            config_tcp_server = await asyncioStart_server(handle_TCP_client, async_TCP_IP, async_TCP_port)
            await current_logger.asyncInfo("{0} : socket async TCP handler is open : '{1}', srcport : '{2}'".format(Name, async_TCP_IP, async_TCP_port))
            async with config_tcp_server:
                await config_tcp_server.serve_forever()
        except Exception as e:
            await current_logger.asyncError("{0} : error while trying to start TCP server : '{1}'".format(Name, e))
            exit(1)

    ####################################################################

    async def run_tasks(srv_port:str, ReceiverName:str="TeleRemoteReceiver"):
        global current_config
        global current_logger
        try:
            asyncTeleLoop = asyncioGet_running_loop()
            asyncTeleLoop.create_task(start_bot(config=current_config, logger=current_logger))
            await asyncTeleLoop.create_task(async_tcp_server(srv_port=srv_port, Name=ReceiverName))
        except KeyboardInterrupt:
            await current_logger.asyncInfo("{0} : socket async TCP handler has been stopped at : {1}".format(ReceiverName, datetime.utcnow()))
        except Exception as e:
            await current_logger.asyncError("{0} : error while trying to start TeleRemote_server : '{1}'".format(ReceiverName, e))
            exit(1)


    def run_TeleRemote(port=int(getUnusedPort()), ReceiverName:str="TeleRemoteReceiver", conf:str="common", log_level=LOG_LEVEL, only_logger:bool=False):
            global TELE_REMOTE_SERVER_NAME
            global current_config
            global current_logger

            if not osPathSep in conf:
                current_config, current_logger = init_logger(name=TELE_REMOTE_SERVER_NAME, config=conf, log_level=log_level, only_logger=only_logger)
            else:
                current_config, current_logger = init_logger(name=TELE_REMOTE_SERVER_NAME, config_path=conf, log_level=log_level, only_logger=only_logger)

            port = int(port)
            if str(current_config.TB_PORT) != str(port):
                current_config.TB_PORT = int(port)
                current_config.update(section="COMMON", configPath=current_config.COMMON_FILE_PATH, params={"TB_PORT":port})
            
            asyncioRun(run_tasks(port, ReceiverName))


##############################################################################################################################################################################################
##############################################################################################################################################################################################


else:


    from time import sleep
    from threading import Thread, Lock as threadingLock
    from socketserver import ThreadingTCPServer, StreamRequestHandler
    from collections import deque


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
    threadLock = threadingLock()

    Shared_send_msg_in = deque()
    Shared_recv_msg_in = deque()

    ####################################################################

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

    ####################################################################

    def start_bot(name, logger:MyLogger, config:Config):
        Bot = init_bot(config=config, logger=logger)

        class TeleRemote:
            Name = "TeleRemote"
            def __init__(self, name, logger:MyLogger, config:Config, Bot):
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
                with threadLock:
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
                            self.logger.error("{0} : error while sending command to StarQs : 'Shared_send_msg_in empty !!!'".format(self.Name))
                            pass
                        else:
                            self.Bot.send_message(self.config.TB_CHATID, "Error while sending command to StarQs : {0}".format(e))
                            self.logger.error("{0} : error while sending command to StarQs : {1}".format(self.Name, e))

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
                            else:
                                self.Bot.send_message(self.config.TB_CHATID, "{0}".format(starQ_msg))
                    except Exception as e:
                        self.Bot.send_message(self.config.TB_CHATID, "Error while receiving message '{0}' : {1}".format(starQ_msg[0], e))
                        self.logger.error("{0} : error while receiving message '{1}' : {2}".format(self.Name, starQ_msg[0], e))
                        pass
                    sleep(self.config.MAIN_QUEUE_BEAT)

        TeleCommand = TeleRemote(name, logger, config, Bot)
        TeleCommand = create_bot(TeleCommand=TeleCommand, Bot=Bot)
        return TeleCommand

    ####################################################################

    class TeleThreadInterface(StreamRequestHandler):
        Name = "TeleThreadInterface"
        QAddress = None
        logger = None
        waite = None
        def handle(self):
            global Shared_recv_msg_in
            TeleSocket = SafeSocket(self.connection)

            try:
                msg = TeleSocket.receive_data()
            except Exception as e:
                self.logger.error("{0} : error while trying to initiate connection : {1}".format(self.Name, e))
                if not TeleSocket.conn._closed:
                    TeleSocket.conn.close()
                return
            
            if not msg:
                if not TeleSocket.conn._closed:
                    TeleSocket.conn.close()
                return
            name, host, port = msg.split(':') ; port = int(port)

            while True:
                # get broker address
                if len(self.QAddress) == 1:
                    TeleChacheInfo = self.QAddress.pop()
                    if name != "tri_watch_dog":
                        TeleChacheInfo(name, host, port, self.send_msg, TeleSocket)
                    self.QAddress.append(TeleChacheInfo)
                    break
            self.logger.info("{0} : '{1}' has established connection without encryption from '{2}' destport '{3}'".format(self.Name, name, host, port))

            while True:
                try:
                    data = TeleSocket.receive_data()
                except Exception as e:
                    self.logger.error("{0} : error while trying to received data, closing connection : {1}".format(self.Name, e))
                    if not TeleSocket.conn._closed:
                        TeleSocket.conn.close()
                    break

                if not data:
                    if not TeleSocket.conn._closed:
                        TeleSocket.conn.close()
                    break
                
                try:
                    if isinstance(data, Qmsg):
                        recv_msg = data.msg
                        # pop bot.send_message func in deque ??
                        Shared_recv_msg_in.append([recv_msg, data.frome])
                    else:
                        Shared_recv_msg_in.append(data)
                except Exception as e:
                    self.logger.error("{0} : error while trying to read Qmsg '{1}' : '{2}'".format(self.Name, msg, e))

        @threadIt
        def send_msg(self, TeleSocket:SafeSocket, msg:str):
            try:
                TeleSocket.send_data(msg)
            except Exception as e:
                self.logger.error("{0} : error while trying to send msg '{1}' : '{2}'".format(self.Name, msg, e))

    ####################################################################

    class TelecommandSocketServer(ThreadingTCPServer):
        """ Telecommand server..."""
        Name = "TeleRemoteSocketServer"
        SocketServer = None
        Bot = None
        allow_reuse_address = True
        waite = None

        def __init__(self, config:Config, handler=TeleThreadInterface, port=int(getUnusedPort()), log_level:int=LOG_LEVEL, only_logger:bool=False): 
            global Shared_send_msg_in ; Shared_send_msg_in.append(ClientsInfo())
            
            self.config = config
            if str(self.config.TB_PORT) != str(port):
                self.config.TB_PORT = int(port)
                self.config.update(section="COMMON", configPath=config.COMMON_FILE_PATH, params={"TB_PORT": str(port)})

            self.logger = MyLogger(TELE_REMOTE_SERVER_NAME, config, start_telecommand=False, log_level=log_level, only_logger=only_logger)
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
            self.logger.info("{0} : Telecommand TCP server is starting.. .  . ".format(TELE_REMOTE_SERVER_NAME))
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
    from platform import system as platformSystem
    from common.Helpers.helpers import caffeinMe, default_arguments

    if platformSystem() != "Windows":
        caffeinMe(pid=osGetpid())
    log_level = LOG_LEVEL
    configStr="current"

    if len(argv) > 1:
        from common.Helpers.helpers import init_logger
        try :
            argsAndVal, defaultArgs = default_arguments(argv=argv, specificArgs=SPECIFIC_ARGS)
            if argsAndVal:

                if "name" in argsAndVal: TELE_REMOTE_SERVER_NAME = argsAndVal.pop("name")
                if "log_level" in argsAndVal: log_level = argsAndVal["log_level"]
                if "host" in argsAndVal: argsAndVal.pop("host") # FIXME teleportation !
                if not "conf" in argsAndVal: argsAndVal["conf"] = configStr
                if "only_logger" in argsAndVal: argsAndVal["only_logger"] = eval(argsAndVal["only_logger"])

                if TELE_REMOTE_SERVER_TYPE.lower() == "async":
                    run_TeleRemote(**argsAndVal)
                else:
                    if "conf" in argsAndVal: config_path = load_config_files()[argsAndVal.pop("conf")]
                    config = Config(config_file_path=config_path, name=TELE_REMOTE_SERVER_NAME)
                    argsAndVal["config"] = config
                    Shared_Telecommande = TelecommandSocketServer(**argsAndVal)
            else:
                cmdLineInfo = """
                Authorized arguments : \n \
                    default optional arguments :\n \
                        --name \n \
                        --host \n \
                        --port \n \
                        --conf \n \
                        --log_level \n \
                specific optional arguments :\n \
                        --only_logger \n \
                """.format(argv)
                _, logger = init_logger(name=TELE_REMOTE_SERVER_NAME, config="common", log_level=log_level)
                logger.error("{0} : error while trying to launch the service, wrong parameter(s) provided : {1}\n {2}".format(TELE_REMOTE_SERVER_NAME, str(argv), cmdLineInfo))
        except Exception as e:
            _, logger = init_logger(name=TELE_REMOTE_SERVER_NAME, config="common", log_level=log_level)
            logger.error("{0} : unexpected error while trying to launch the service, parameter(s) provided : {1} => {2}".format(TELE_REMOTE_SERVER_NAME, str(argv), e))
    else:
        # if process launched via vscode....
        from common.Helpers.os_helpers import nb_process_running
        nb_running, pidList = nb_process_running(TELE_REMOTE_SERVER_NAME, getPid=True)
        launch_vscode = 4 if platformSystem() == "Windows" else 2
        if nb_running > launch_vscode:
            # 2 -> current process + vscode process...
            _, logger = init_logger(name="{0}_2".format(TELE_REMOTE_SERVER_NAME), log_level=log_level)
            logger.error("{0} : error while trying to start process : process already running ! (pid:{1})".format(TELE_REMOTE_SERVER_NAME, pidList))
            exit(0)

        if TELE_REMOTE_SERVER_TYPE.lower() == "async":
            run_TeleRemote(conf=configStr)
        else:
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
    #    toto3.send_msg_in(" !!!! did you received my message (toto3)")

 