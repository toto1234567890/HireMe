#!/usr/bin/env python
# coding:utf-8


from time import sleep
from os import getpid as osGetpid
from os.path import join as osPathJoin, basename as osPathBasename
from datetime import datetime
from socket import socket, AF_INET, SOCK_STREAM, SOL_TCP, SOL_SOCKET, SO_REUSEADDR
from logging.handlers import DEFAULT_TCP_LOGGING_PORT
from retry import retry
from threading import Thread, Lock as threadingLock
from asyncio import get_running_loop as asyncioGet_running_loop, run as asyncioRun


# relative import
from sys import path;path.extend("..")
from common.Notifie.notifie import LightNotifie
from common.Scheduler.job_loops import runTaskSyncWaitEnd
from common.TeleRemote.tele_command import Telecommand
from common.Helpers.helpers import Singleton, ThreadQKill, default_arguments, getOrDefault, init_logger, create_logger_msg
from common.Helpers.os_helpers import get_executed_script_dir, launch_tri_watch_dog_watcher, launch_tri_watch_dog, is_process_running, \
                                      launch_config_server, launch_notif_server, launch_log_server, launch_teleremote_server, getEnv, get_executed_script_dir
from common.Helpers.network_helpers import SSL_client_context, SSL_server_context, SSL_test_context, is_service_listen, MySocket, SafeSocket




LOG_LEVEL = 20
SPECIFIC_ARGS = ["--lock_file_path"]

TRI_MONITORING = {
                    "config_server":{"config_prefix":"CF", "func":launch_config_server, "params": {"port":"3306", "log_level":LOG_LEVEL, "conf":"current"}, "index":3},
                    "notif_server":{"config_prefix":"NT", "func":launch_notif_server, "params": {"port":"10080", "log_level":LOG_LEVEL, "conf":"current"}, "index":4},
                    "log_server":{"config_prefix":"LG", "func":launch_log_server, "params": {"log_level":LOG_LEVEL, "conf":"current"}, "index":5},
                    "tele_remote":{"config_prefix":"TB", "func":launch_teleremote_server, "params": {"port":"22128", "log_level":LOG_LEVEL, "only_logger":"True", "conf":"current"}, "index":6}
                  }

LOCK_FILE_PATH = osPathJoin(get_executed_script_dir(file_path=__file__), "tri.Lock")
WATCHDOG_PATT = osPathBasename(__file__).replace(".py", '')

##############################################################################################################################################################################################


WatchDogConnected = False
sharedWatchDogState = threadingLock()

def tri_watch_dog_connection_state(_set=None):
    global WatchDogConnected
    with sharedWatchDogState:
        if not _set is None: WatchDogConnected = _set
        else: return WatchDogConnected

class WatchTriWatch(metaclass=Singleton):
    Name = "watch_tri_watch"
    WATCH_TRI_WATCH_DOG_PORT = (DEFAULT_TCP_LOGGING_PORT + 1)
    _LOCK_FILE_PATH = LOCK_FILE_PATH
    def __init__(self, argv, lock_file_path=None):
        if not lock_file_path is None: 
            self._LOCK_FILE_PATH = lock_file_path
        
        tri_watch_dog_connection_state(_set=False)
        self.light_notif = LightNotifie()   
        WatchTriWatch.launch_tri_watch_dog() # if not already runnning
        Thread(target=self.listen_tri_watch_dog_service, args=("127.0.0.1", WatchTriWatch.WATCH_TRI_WATCH_DOG_PORT, argv)).start()

    @staticmethod
    def launch_tri_watch_dog(pocessPatt=WATCHDOG_PATT):
        if not is_process_running(cmdlinePatt=pocessPatt, argvPatt="--name {0} --lock_file_path {1}".format(TriWatchDog.Name, TriWatchDog._LOCK_FILE_PATH)):
            _ = launch_tri_watch_dog(name=TriWatchDog.Name, lock_file_path=WatchTriWatch._LOCK_FILE_PATH)
            sleep(1)

    @staticmethod
    def handle_tri_watch_dog(watchDogSocket, watchDogAddress, argv):
        tri_watch_dog_connection_state(_set=True)
        watchDogSock = SafeSocket(watchDogSocket)
        while True:
            data = watchDogSock.receive_data()
            if not data:
                tri_watch_dog_connection_state(_set=False)
                LightNotifie.notifie("{0} : connection lost with '{1}', restart of the service has been triggered.. .  .".format(WatchTriWatch.Name, TriWatchDog.Name))
                break
            # Name, host, port, argv, logFilePath, PID
            watchDogSock.send_data("{0}|{1}|{2}|{3}|{4}|{5}".format(WatchTriWatch.Name, "127.0.0.1", WatchTriWatch.WATCH_TRI_WATCH_DOG_PORT,  " ".join(argv), "#N/A", osGetpid()))
        WatchTriWatch.launch_tri_watch_dog()    

    def listen_tri_watch_dog_service(self, server, port, argv):
        server_socket = socket(AF_INET, SOCK_STREAM, SOL_TCP)
        server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        server_socket.bind((server, port))
        server_socket.listen(1)
        # Wrap the socket with SSL
        ssl_context = (SSL_test_context() 
                       # FIXME if server_context is applicable ?! 
                       if 1 == 1 else
                       SSL_server_context())

        while True:
            tri_watch_dog_connection_state(_set=False)
            client_socket, client_address = server_socket.accept()
            #if client_address == ("127.0.0.1", self.triWatchDogParams[2]):
            self.handle_tri_watch_dog(watchDogSocket=client_socket, watchDogAddress=client_address, argv=argv)

    def sentinelle(self):
        sleep(30)
        Thread(target=lambda : asyncioRun(self.check_tri_watch_dog_state())).start()
    ## Scheduler runTaskSyncWaitEnd job 
    async def check_tri_watch_dog_state(self):
        loop = asyncioGet_running_loop()
        await loop.run_until_complete(runTaskSyncWaitEnd(loop=asyncioGet_running_loop(), interval=10, obj=self))
    def exec_job(self):
        global WATCHDOG_PATT
        connected = tri_watch_dog_connection_state()
        if not connected:
            _, pid = is_process_running(cmdlinePatt="{0}".format(WATCHDOG_PATT), argvPatt="--name {0} --lock_file_path {1}".format(TriWatchDog.Name, TriWatchDog._LOCK_FILE_PATH))
            if pid > 0: 
                ThreadQKill(pidList=[pid])
                self.light_notif.send_message("{0} : '{1}' is not connected to socket server, a 'zombie' process was running and has been killed at : {2} !!!".format(self.Name, TriWatchDog.Name, datetime.utcnow()))
            self.launch_tri_watch_dog()
            self.light_notif.send_message("{0} : '{1}' was not connected to socket server, service restart has been triggered.. .  .".format(self.Name, TriWatchDog.Name))
            

##############################################################################################################################################################################################
      

class TriWatchDog(metaclass=Singleton):
    """ \n
        ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        +++   Do not forget to configure supervisord, os schedule or task that launch this script at machine startup...    +++
        ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    """
    Name = "tri_watch_dog"
    NB_TRY_LOOP = 10
    WRITE_LOCK_FILE= threadingLock() 
    _LOCK_FILE_PATH = LOCK_FILE_PATH
    def __init__(self, argv, conf, log_level=LOG_LEVEL, lock_file_path=None):
        global TRI_MONITORING 

        if not lock_file_path is None: 
            self._LOCK_FILE_PATH = lock_file_path
        self.light_notif = LightNotifie()

        self.config, self.logger = init_logger(name=self.Name, config=conf, only_logger=True, log_level=log_level, enable_notifications=False)
        self.logger.info(TriWatchDog.__doc__)
        # Name, host, port, argv, logFilePath, PID
        Thread(target=self.write_lock_file, args=(self.Name, "127.0.0.1", "#N/A", [arg.replace("--", '') for arg in argv[1:]], self.logger.Logger.handlers[0].baseFilename, osGetpid())).start()
        for service in TRI_MONITORING:
            # order for port parameter : command line param, environment variable, config current.cfg, then config common.cfg...
            server = getOrDefault(
                        value=self.config.__dict__, key="{0}_IP".format(TRI_MONITORING.get(service).get("config_prefix")), 
                        default=getOrDefault(
                            value=self.config.__dict__, key="{0}_IP".format(TRI_MONITORING.get(service).get("config_prefix")),
                            default="127.0.0.1"))
            port = int(getOrDefault(
                        value=self.config.__dict__, 
                        key="{0}_PORT".format(TRI_MONITORING.get(service).get("config_prefix")),
                        default=DEFAULT_TCP_LOGGING_PORT))
            Thread(target=self.watch, args=(server, port, service, TRI_MONITORING.get(service).get("func"), TRI_MONITORING.get(service).get("params"))).start()
        Thread(target=self.watch, args=("127.0.0.1", WatchTriWatch.WATCH_TRI_WATCH_DOG_PORT, WatchTriWatch.Name, launch_tri_watch_dog_watcher, {"name":WatchTriWatch.Name, "lock_file_path":TriWatchDog._LOCK_FILE_PATH})).start()


    @retry(delay=10, backoff=1, tries=-1) 
    @retry(delay=1, backoff=1, tries=10, jitter=1)
    def watch(self, server, port, service, launcherPtr, launcherArgs):
        global TRI_MONITORING

        service_pid = self.check_run_process(server, port, service, launcherPtr, launcherArgs, init=True)
        if service_pid < 1 : 
            service_pid = self.check_run_process(server, port, service, launcherPtr, launcherArgs)
        self.write_lock_file(service=service, server=server, port=port, launcherArgs=launcherArgs, log_path="#N/A", service_pid=service_pid)

        with MySocket(server=server, port=port) as TriSock:
            if port == DEFAULT_TCP_LOGGING_PORT : msg = create_logger_msg(name=self.Name, funcName="watch", filename="tri_watch_dog.py", msg="LogServer : '{0}' has established connection without encryption from '127.0.0.1' destport '{1}'".format(self.Name, TriSock.conn.getsockname()[1]))
            else : msg = "{0}:{1}:{2}".format(self.Name, "127.0.0.1", TriSock.conn.getsockname()[1])

            TriSock.send_data(msg)
            while True:
                data = TriSock.receive_data()
                if not data:
                    error_msg = "{0} : connection lost with '{1}' service, restart will be triggered.. .  .".format(self.Name, service)
                    self.logger.error(error_msg)
                    self.light_notif.send_message(error_msg)
                    break
            
        service_pid = self.check_run_process(server, port, service, launcherPtr, launcherArgs)
        self.write_lock_file(service=service, server=server, port=port, launcherArgs=launcherArgs, log_path="#N/A", service_pid=service_pid)

        error_msg = "{0} : connection lost with {1}, service has been re-launched at : {2}".format(self.Name, service, datetime.utcnow())
        self.logger.error(error_msg)
        self.light_notif.send_message(error_msg)
        raise Exception(error_msg)
    

    def write_lock_file(self, service, server, port, launcherArgs, log_path, service_pid):
        global TRI_MONITORING
        with TriWatchDog.WRITE_LOCK_FILE:
            try:
                with open(TriWatchDog._LOCK_FILE_PATH, "r+") as lockFile:
                    # Name, host, port, argv, logFilePath, PID
                    TriWatchDog.write_file_index(fso_object=lockFile, 
                                                       index=TRI_MONITORING.get(service).get("index") if service in TRI_MONITORING else 1 if port==WatchTriWatch.WATCH_TRI_WATCH_DOG_PORT else 2, 
                                                       line="{0}|{1}|{2}|{3}|{4}|{5}".format(service, server, port, 
                                                                                             " ".join(["{0} {1}".format(key, val) for key, val in launcherArgs.items()] if type(launcherArgs) == dict else launcherArgs)
                                                                                             , log_path, service_pid))
            except Exception as e: 
                error_msg = "{0} : error while trying to write tri.Lock file '{1}' : {2}".format(self.Name, TriWatchDog._LOCK_FILE_PATH, e)
                self.logger.error(error_msg)
                self.light_notif.send_message(error_msg)
                raise Exception(error_msg)

    def check_run_process(self, server, port, service, launcherPtr, launcherArgs, init=False):
        global WATCHDOG_PATT
        if service != WatchTriWatch.Name: service_running, service_pid = is_process_running(cmdlinePatt=service, getPid=True) 
        else :                            service_running, service_pid = is_process_running(cmdlinePatt=WATCHDOG_PATT, argvPatt="--name {0} --lock_file_path {1}".format(WatchTriWatch.Name, WatchTriWatch._LOCK_FILE_PATH), getPid=True) 

        if init:
            return service_pid
        else:
            # service is running but client socket closed unexpectedly...
            if service_running:
                ThreadQKill(pidList=service_pid)
                error_msg = "{0} : service '{1}' is running but not listenning, pid {2} has been killed at : {3} !!!".format(self.Name, service, service_pid, datetime.utcnow())
                self.logger.error(error_msg)
                self.light_notif.send_message(error_msg)
                sleep(1)
            _ = launcherPtr(**launcherArgs)
            error_msg = "{0} : service '{1}' has been re-started.. .  .".format(self.Name, service)
            self.logger.error(error_msg)
            self.light_notif.send_message(error_msg)

            nb_try = 0
            while True:
                if is_service_listen(server=server, port=port):
                    if service != WatchTriWatch.Name: _, service_pid = is_process_running(cmdlinePatt=service, getPid=True) 
                    else :                            _, service_pid = is_process_running(cmdlinePatt=WATCHDOG_PATT, argvPatt="--name {0} --lock_file_path {1}".format(WatchTriWatch.Name, WatchTriWatch._LOCK_FILE_PATH), getPid=True) 
                    error_msg = "{0} : service '{1}' is up and running at : {2} !".format(self.Name, service, datetime.utcnow())
                    self.logger.error(error_msg)
                    self.light_notif.send_message(error_msg)
                    break
                if nb_try > TriWatchDog.NB_TRY_LOOP:
                    error_msg = "{0} : service '{1}' is yet not listenning : trying to re-init socket.. .  .".format(self.Name, service)
                    self.logger.error(error_msg)
                    self.light_notif.send_message(error_msg)
                    sleep(5)
                nb_try += 1
                sleep(1)
            return service_pid

    @staticmethod
    def write_file_index(fso_object, index, line):
        contents = fso_object.readlines()
        i = len(contents)
        if i <= index-1:
            while True:
                contents.insert(i, '\n')
                if i >= index-1:
                    break
                i += 1
            contents.insert(index-1, "{0}\n".format(line))
        else:
            contents[index-1] = "{0}\n".format(line) 
        fso_object.seek(0)
        fso_object.truncate()
        fso_object.writelines(contents)

def change_default_params(service, **params):
    global TRI_MONITORING
    (TRI_MONITORING.get(service)).update(**params)



#================================================================
if __name__ == "__main__":
    from sys import argv

    log_level = LOG_LEVEL    
    configStr = "current"

    if len(argv) > 1:
        argsAndVal, defaultArgs = default_arguments(argv=argv, specificArgs=SPECIFIC_ARGS)
        if argsAndVal:

            if not "lock_file_path" in argsAndVal: 
                raise("Error you must provide the '--lock_file_path' argument with complete file path...")
                #argsAndVal["lock_file_path"] = LOCK_FILE_PATH

            if "log_level" in argsAndVal:
                for item in TRI_MONITORING:
                    TRI_MONITORING[item]["params"]["log_level"] = argsAndVal["log_level"]
                if (not "name" in argsAndVal) or argsAndVal["name"] == WatchTriWatch.Name:
                    raise("Error you must not provide the '--log_level' argument with '{0}' process ...".format(WatchTriWatch.Name))

            # not used
            if "port" in argsAndVal: argsAndVal.pop("port")
            if "host" in argsAndVal: argsAndVal.pop("host") # FIXME teleportation !
            if "log_level" in argsAndVal : argsAndVal.pop("log_level") # not usedAnyMore

            argsAndVal["argv"] = argv
            if not "name" in argsAndVal:
                raise("Error you must provide the '--name' argument either {0}, either {1}...".format(TriWatchDog.Name, WatchTriWatch.Name))
            name = argsAndVal.pop("name")

            if name == WatchTriWatch.Name:
                if "conf" in argsAndVal: argsAndVal.pop("conf")
                _ = WatchTriWatch(**argsAndVal)
            elif name == TriWatchDog.Name:
                if not "conf" in argsAndVal: argsAndVal["conf"] = configStr
                _ = TriWatchDog(**argsAndVal)            
        else:
            print("""
            Authorized arguments : \n \
                default optional arguments :\n \
                    --conf \n \
                    --log_level \n \
                        - CRITICAL = 50 (FATAL = CRITICAL)\n \
                        - ERROR = 40 \n \
                        - WARNING = 30 \n \
                        - WARN = WARNING \n \
                        - DEBUG = 10 \n \
                        - NOTSET = 0
                    --lock_file_path \n \
                        full path from the program root directory... \n \
                arguments provided : \n \ 
                    {0} \n \ 
            """.format(argv))
    else:
        print("""
        Authorized arguments : \n \
            default optional arguments :\n \
                --conf \n \
                --log_level \n \
                    - CRITICAL = 50 (FATAL = CRITICAL)\n \
                    - ERROR = 40 \n \
                    - WARNING = 30 \n \
                    - WARN = WARNING \n \
                    - DEBUG = 10 \n \
                    - NOTSET = 0
                --lock_file_path \n \
                    full path from the program root directory... \n \
            arguments provided : \n \ 
                {0} \n \ 
        """.format(argv))       




    
    
    


