#!/usr/bin/env python
# coding:utf-8


CONFIG_SERVER_TYPE = "ASYNC" # or THREAD
CONFIG_SERVER_NAME = "config_server"
LOG_LEVEL = 10
DEFAULT_CONFIG_SERVER_PORT = 3306 # default port for MySQL (not used by me at least !)
SPECIFIC_ARGS = ["--config_server_type", "--bot_type"]


from os.path import sep as osPathSep, join as osPathJoin, dirname as osPathDirname, exists as osPathExists
from datetime import datetime
from sqlite3 import connect as sqlite3Connect, threadsafety as sqlite3Threadsafety

# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.Helpers.helpers import init_logger, load_config_files, default_arguments
from common.Helpers.network_helpers import SafeAsyncSocket


current_logger = None 
OriginelDB = None
InMemoryDbUri = None   
connected_listeners = {}


if CONFIG_SERVER_TYPE.lower() == "async":
    from asyncio import run as asyncioRun, get_running_loop as asyncioGet_running_loop, start_server as asyncioStart_server, \
                        Lock as asyncioLock, Queue as asyncioQueue, sleep as asyncioSleep
    from common.Helpers.network_helpers import SafeAsyncSocket

    asyncConfigLoop = None
    current_config = None
    config_file_path = None
    config_last_hash = None 

    asyncLockQueue = None
    asyncListenerLock = None 
    
else:
    from time import sleep
    from collections import deque
    from socketserver import ThreadingTCPServer, StreamRequestHandler
    from common.Helpers.helpers import threadIt
    from common.Helpers.network_helpers import SafeSocket

    DEFAULT_TIME_SLEEP = 0.01
    current_config = deque()



def pop_global_conf():
    global current_config
    while True:
        if len(current_config) > 0:
            conf:Config = current_config.pop()
            break
        sleep(DEFAULT_TIME_SLEEP)
    return conf       

def safe_append_global_conf(conf):
    global current_config
    if len(current_config) == 0:
        current_config.append(conf)

def tListeners(key, add=None, remove=False, propagate=False, conf=None, mem_conf=None):
    global connected_listeners
    while True:
        if len(ConfigReceiver.Receiver_listeners) > 0:
            listner_dict:dict = ConfigReceiver.Receiver_listeners.pop()
            break
        sleep(DEFAULT_TIME_SLEEP)
    if propagate:
        if len(listner_dict) > 0:
            for func_key, func in listner_dict.items():
                if func_key != key:
                    func(conf, func_key)
    elif not add is None:
        listner_dict[key] = add
    elif remove:
        if key in listner_dict:
            listner_dict.pop(key)
    ConfigReceiver.Receiver_listeners.append(listner_dict)

async def aListeners(key, add=None, remove=False, propagate=False, conf=None):
    async with asyncListenerLock:
        global connected_listeners
        if propagate:
            if len(connected_listeners) > 0:
                died_socket = []
                for func_key, funcAndArgs in connected_listeners.items():
                    if func_key != key:
                        funcPtr, configSock, port, clientName = funcAndArgs
                        try:
                            await funcPtr(conf=conf, configSock=configSock, port=port, clientName=clientName)
                        except Exception as e:
                            if e.errno == 54: # connection reset by peer
                                died_socket.append(func_key)
                                continue
                            else: raise(e)
                for key in died_socket:
                    connected_listeners.pop(key)
        if not add is None:
            connected_listeners[key] = add
        elif remove:
            if key in connected_listeners:
                connected_listeners.pop(key)

listeners = None
if CONFIG_SERVER_TYPE.lower() == "async": listeners = aListeners
else: listeners = tListeners

##########################################################################

class MemConfig:
    Name = "MemConfig"
    db_backup = osPathJoin(osPathDirname(__file__), "memConf.db")
    commonConfig = """CREATE TABLE IF NOT EXISTS [#TABLENAME] 
    (key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    file_path TEXT DEFAULT '[#DEFAULT]') WITHOUT ROWID"""
    # Should be Thread Safe
    threadsafety = False if sqlite3Threadsafety == 3 else True
    def __init__(self, logger, config_file_path, InMemoryDbUri:str="file:memdb?mode=memory&cache=shared"):
        self.logger = logger 
        if InMemoryDbUri != "file:memdb?mode=memory&cache=shared":
            InMemoryDbUri = "file:{0}?mode=memory&cache=shared".format(InMemoryDbUri)

        # create database or Attach database if exist
        if osPathExists(MemConfig.db_backup):
            db_file = sqlite3Connect(MemConfig.db_backup)
            db_file.backup(sqlite3Connect(InMemoryDbUri, uri=True, check_same_thread=self.threadsafety))
            db_file.close()
        
        self.conn = sqlite3Connect(InMemoryDbUri, uri=True, check_same_thread=self.threadsafety)
        self.conn.row_factory = self.dict_factory

        # default config required
        self.conn.execute(self.commonConfig.replace("[#DEFAULT]", config_file_path).replace("[#TABLENAME]", "config"))
        self.conn.execute(self.commonConfig.replace("[#DEFAULT]", config_file_path).replace("[#TABLENAME]", "arbitre"))

    def _cast(self, val):
        try: return int(val) 
        except ValueError: pass
        try: return float(val) 
        except ValueError: pass
        return val
    def get(self, section, keys:list=[]):
        try:
            sql_statement = """SELECT key, value FROM {0} WHERE """.format(section.upper()) ; ret = {}
            if len(keys) > 0:
                # need some keys...
                for key in keys:
                    sql_statement += """key = '{0}' OR """.format(key)
                sql_statement = "{0};".format(sql_statement[:-4])
            else:
                # need all table config
                sql_statement = sql_statement[:-7] 
            for row in self.conn.execute(sql_statement):
                ret[row["key"]]=self._cast(row["value"])
            return {section:ret}
        except Exception as e:
            self.logger.error("{0} : error while trying to get params from config server : '{1}'".format(self.Name, e))
            return None
        
    def all_mem_conf(self):
        try:
            cursor = self.conn.cursor() ; all_ret = {} ; ret = {}
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            table_names = cursor.fetchall()
            for table in table_names:
                for row in self.conn.execute("SELECT * FROM {0};".format(table['name'])):
                    ret[row["key"]]=self._cast(row["value"])
                all_ret[table['name']] = ret
                ret = {}
            return all_ret
        except Exception as e:
            self.logger.error("{0} : error while trying to get_tele_config params from config server : '{1}'".format(self.Name, e))
            return None

    def update(self, section, kwargs:dict):
        try:
            data = [(key, val) for key, val in kwargs.items()]
            sql_statement = """INSERT OR REPLACE INTO {0} (key, value) VALUES (?, ?)""".format(section.upper())
            cursor = self.conn.cursor()
            cursor.execute(self.commonConfig.replace("[#DEFAULT]", "inMemory").replace("[#TABLENAME]", section))
            cursor.executemany(sql_statement, data)
            self.conn.commit()
            self.logger.info("{0} : config section '{1}' have been updated -> {2}".format(self.Name, section, data))
            return "done"
        except Exception as e:
            self.conn.rollback()
            self.logger.error("{0} : error while trying to get params from config server : '{1}', transaction rollbacked...".format(self.Name, e))
            return None

    def dump(self, fileName=None):
        try:
            if fileName == None: fileName = MemConfig.db_backup
            dump_file = sqlite3Connect(fileName)
            self.conn.backup(dump_file)
            dump_file.close()
            return "done"
        except Exception as e:
            self.conn.rollback()
            self.logger.error("{0} : error while trying to dump inMemory DB into '{1}' : {2}, transaction rollbacked...".format(self.Name, fileName, e))
            return None

    def dict_factory(self, cursor, row):
        fields = [column[0] for column in cursor.description]
        return {key: value for key, value in zip(fields, row)}

    def close(self):
        try:self.dump()
        except:pass
        try:self.conn.close()
        except:pass


##############################################################################################################################################################################################
##############################################################################################################################################################################################


if CONFIG_SERVER_TYPE.lower() == "async": 

    ##########################################################################
    # async config server 
    
    async def update_listener(conf, configSock, port, clientName):
        global CONFIG_SERVER_NAME
        global current_logger
        await configSock.send_data(conf)
        await current_logger.asyncInfo("{0} : config update propagated to socket '{1}' (port:{2})".format(CONFIG_SERVER_NAME, clientName, port))
    
    async def add_listener(key, funcAndArgsPtr):
        await listeners(key=key, add=funcAndArgsPtr)
    async def remove_listener(key):
        await listeners(key=key, remove=True)
    async def propagate_listener(key, conf):
        await listeners(key=key, propagate=True, conf=conf)
    
    
    async def handle_TCP_client(reader, writer):
        Name = "ConfigHandler"
        global asyncLockQueue
        global current_logger
        global config_last_hash
    
        configSock = SafeAsyncSocket(reader=reader, writer=writer)
        data = await configSock.receive_data()
        if not data:
            configSock.writer.close()
            await configSock.writer.wait_closed()
            return
    
        clientName, host, port = data.split(':') ; port = int(port)
        await current_logger.asyncInfo("{0} : '{1}' has established connection without encryption from '{2}' destport '{3}'".format(Name, clientName, host, port))
    
        conf = await asyncLockQueue.get()
        MemDB = MemConfig(logger=current_logger, config_file_path=conf.COMMON_FILE_PATH, InMemoryDbUri=InMemoryDbUri)
        asyncLockQueue.put_nowait(conf)
    
        while True:
            try:
                data = await configSock.receive_data()
            except Exception as e:
                await current_logger.asyncError("{0} : error while trying to received data, closing connection : {1}".format(Name, e))
                break   
            if not data:
                MemDB.close()
                break
            
            # classic config get object
            if type(data) == str:
                if data == "get_config_object":
                    try:
                        conf = await asyncLockQueue.get()
                        await configSock.send_data(conf)
                        asyncLockQueue.put_nowait(conf)
                        await current_logger.asyncInfo("{0} : config object sent to '{1}'".format(Name, clientName))
                    except Exception as e:
                        asyncLockQueue.put_nowait(conf)
                        await current_logger.asyncError("{0} : error while trying to send config to '{1}' : {2}".format(Name, clientName, e))
                elif data == "add config listener":
                    await add_listener(key=port, funcAndArgsPtr=(update_listener, configSock, port, clientName))
                elif data == "dump_mem_config":
                    await configSock.send_data(MemDB.dump())
                else:
                    await current_logger.asyncError("{0} : error while trying to send config to '{1}' : unknown config request '{2}'".format(Name, clientName, data))
    
            # config in memory DB
            elif type(data) == dict:
                if "get_mem_config" in data:
                    try:
                        #dict format -> {get_mem_config:{section:[key1,key2]}}
                        donnee = data.get("get_mem_config")
                        if not donnee is None:
                            section = [key for key in donnee.keys()][0]
                            keys = [val for val in donnee.values()][0]
                            if not keys is None : await configSock.send_data(MemDB.get(section=section, keys=keys))
                            else : await configSock.send_data(MemDB.get(section=section))
                        else:
                            await configSock.send_data(MemDB.all_mem_conf())
                    except Exception as e:
                        await current_logger.asyncError("{0} : error while trying to return config to '{1}' : {2}".format(Name, clientName, e))    
    
                elif "update_mem_config" in data:
                    try:
                        #dict format -> {"update_mem_config":{"section":{"key1":12,"key2":14}}}
                        donnee = data.get("update_mem_config")
                        section = [key for key in donnee.keys()][0]
                        mem_conf_updated = MemDB.update(section=section, kwargs=donnee.get(section))
                        await configSock.send_data(mem_conf_updated)
                        await propagate_listener(key=port, conf=MemDB.all_mem_conf())
                        await current_logger.asyncInfo("{0} : config memory has been updated '{1}'".format(Name, clientName))
                    except Exception as e:
                        await current_logger.asyncError("{0} : error while trying to update config from '{1}' : {2}".format(Name, clientName, e))
                else:
                    await current_logger.asyncError("{0} : error while trying to send config to '{1}' : unknown config request '{2}'".format(Name, clientName, data))
    
            # update_config_object or insert_config_object
            elif type(data) == Config:
                try:
                    conf = await asyncLockQueue.get()
                    conf = data
                    with open(conf.COMMON_FILE_PATH, 'w+') as configfile:
                        conf.parser.write(configfile)
                        content = configfile.read() 
                    config_last_hash = content.__hash__()
                    await configSock.send_data(conf)
                    await propagate_listener(key=port, conf=conf)
                    conf.Name = CONFIG_SERVER_NAME
                    asyncLockQueue.put_nowait(conf)
                    await current_logger.asyncInfo("{0} : config file updated from '{1}'".format(Name, clientName))
                except Exception as e:
                    conf.Name = CONFIG_SERVER_NAME
                    asyncLockQueue.put_nowait(conf)
                    await current_logger.asyncError("{0} : error while trying to update/insert config from '{1}' : {2}".format(Name, clientName, e))
                    break
            else:
                await current_logger.asyncError("{0} : error while trying to send config to '{1}' : unknown config request '{2}'".format(Name, clientName, data))
    
        configSock.writer.close()
        await remove_listener(key=port)
        await configSock.writer.wait_closed()
    
    
    async def async_tcp_server(srv_port:str, Name:str="ConfigReceiver"):
        global asyncConfigLoop
        global OriginelDB
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
    
    
    async def config_auto_reload(wait_before_starting=15):
        # in case of config manual modif
        global asyncLockQueue
        global current_logger
        
        global config_file_path
        global config_last_hash
    
        Name = "ConfigAutoReload"
        config_refresh = wait_before_starting
        _conf = None
    
        # get current config
        _current_config = await asyncLockQueue.get()
        config_file_path = _current_config.COMMON_FILE_PATH
        asyncLockQueue.put_nowait(_current_config)
    
        while True:
            await asyncioSleep(float(config_refresh))
    
            _current_config = await asyncLockQueue.get()
            config_refresh = float(_current_config.CF_REFRESH)
            asyncLockQueue.put_nowait(_current_config)
    
            try:
                with open(config_file_path, 'r') as configfile:
                    content = configfile.read() 
            except Exception as e:
                await current_logger.asyncError("{0} : error while trying to reload config file : the 'COMMON_FILE_PATH' has been changed from '{1}' to '{2}', config won't be reloaded until the initial 'COMMON_FILE_PATH' will be restored ...".format(Name, _conf.COMMON_FILE_PATH, current_config.COMMON_FILE_PATH))
                await current_logger.asyncInfo("{0} : auto reload paused for 60 seconds".format(Name))
                config_refresh = 60            
    
            if config_last_hash != content.__hash__():
                _conf = Config(config_file_path=config_file_path, ignore_config_server=True)
                try:
                    _current_config = await asyncLockQueue.get()
                    await propagate_listener(key=-1, conf=_conf)
                    config_last_hash = content.__hash__()
                    asyncLockQueue.put_nowait(_conf)
                    await current_logger.asyncInfo("{0} : config file '{1}' has been reloaded...".format(Name, config_file_path))
                except Exception as e:
                    asyncLockQueue.put_nowait(_current_config)
                    config_refresh = 5 # retry later...
                    await current_logger.asyncError("{0} : error while trying to reload config file : {1}".format(Name, e))
                    continue
                
                
    async def run_tasks(srv_port:str, ReceiverName:str="ConfigReceiver"):
        global asyncConfigLoop
        global asyncLockQueue
        global asyncListenerLock
        global current_config
        try:
            asyncLockQueue = asyncioQueue(maxsize=1)
            asyncLockQueue.put_nowait(current_config)
            asyncListenerLock = asyncioLock()
            asyncConfigLoop = asyncioGet_running_loop()
            asyncConfigLoop.create_task(async_tcp_server(srv_port=srv_port, Name=ReceiverName))
            await asyncConfigLoop.create_task(config_auto_reload())
        except KeyboardInterrupt:
            OriginelDB.close()
            await current_logger.asyncInfo("{0} : config memory database has been closed at {1}".format(ReceiverName, datetime.utcnow()))
            await current_logger.asyncInfo("{0} : socket async TCP handler has been stopped at : {1}".format(ReceiverName, datetime.utcnow()))
        except Exception as e:
            await current_logger.asyncError("{0} : error while trying to start config_server : '{1}'".format(ReceiverName, e))
            exit(1)
    
    
    def run_config_server(port:int, ReceiverName:str="ConfigReceiver", conf:str="common", log_level:int=LOG_LEVEL):
            global CONFIG_SERVER_NAME 
            global current_config
            global current_logger
    
            global OriginelDB
            global InMemoryDbUri
            global config_file_path
    
            if not osPathSep in conf:
                current_config, current_logger = init_logger(name=CONFIG_SERVER_NAME, config=conf, only_logger=True, log_level=log_level)
            else:
                current_config, current_logger = init_logger(name=CONFIG_SERVER_NAME, config_path=conf, only_logger=True, log_level=log_level)
    
            current_config.update(section="COMMON", configPath=current_config.COMMON_FILE_PATH, params={"CF_PORT":port})
            config_file_path = current_config.COMMON_FILE_PATH
            InMemoryDbUri = "{0}DB".format(ReceiverName)
    
            OriginelDB = MemConfig(logger=current_logger, config_file_path=current_config.COMMON_FILE_PATH, InMemoryDbUri=InMemoryDbUri)
            current_logger.info("{0} : config memory database has been created !".format(ReceiverName))
    
            asyncioRun(run_tasks(port, ReceiverName))

else:
    ##########################################################################
    # Threaded config server

    class ConfigHandler(StreamRequestHandler):
        Name="ConfigHandler"
        InMemoryDbUri=None
        Config_DB=None
        ConfigSocket = None
        def handle(self):
            global DEFAULT_TIME_SLEEP
            global current_logger

            self.ConfigSocket = SafeSocket(self.connection)
            msg = self.ConfigSocket.receive_data()
            if not msg:
                return
            name, host, port = msg.split(':') ; port = int(port)

            current_logger.info("{0} : '{1}' has established connection without encryption from '{2}' destport '{3}'".format(self.Name, name, host, port))

            conf = pop_global_conf()
            MemDB = MemConfig(logger=current_logger, config_file_path=conf.COMMON_FILE_PATH, InMemoryDbUri=self.InMemoryDbUri)
            safe_append_global_conf(conf)

            while True:
                data = self.ConfigSocket.receive_data()
                if not data:
                    MemDB.close()
                    break 
                # classic config get object
                if type(data) == str:
                    if data == "get_config_object":
                        try:
                            conf = pop_global_conf()
                            self.ConfigSocket.send_data(conf)
                            safe_append_global_conf(conf)
                            current_logger.info("{0} : config object sent to '{1}'".format(self.Name, name))
                        except Exception as e:
                            safe_append_global_conf(conf)
                            current_logger.error("{0} : error while trying to send config to '{1}' : {2}".format(self.Name, name, e))
                    elif data == "add config listener":
                        self.add_listener(key=port)
                    elif data == "dump_mem_config":
                        self.ConfigSocket.send_data(MemDB.dump())
                    else:
                        current_logger.error("{0} : error while trying to send config to '{1}' : unknown config request '{2}'".format(self.Name, name, data))

                # config in memory DB
                elif type(data) == dict:
                    if "get_mem_config" in data:
                        try:
                            #dict format -> {get_mem_config:{section:[key1,key2]}}
                            donnee = data.get("get_mem_config")
                            if not donnee is None:
                                section = [key for key in donnee.keys()][0]
                                keys = [val for val in donnee.values()][0]
                                if not keys is None : self.ConfigSocket.send_data(MemDB.get(section=section, keys=keys))
                                else : self.ConfigSocket.send_data(MemDB.get(section=section))
                            else:
                                self.ConfigSocket.send_data(MemDB.all_mem_conf())
                        except Exception as e:
                            current_logger.error("{0} : error while trying to return config to '{1}' : {2}".format(self.Name, name, e))   

                    elif "update_mem_config" in data:
                        try:
                            #dict format -> {"update_mem_config":{"section":{"key1":12,"key2":14}}}
                            donnee = data.get("update_mem_config")
                            section = [key for key in donnee.keys()][0]
                            mem_conf_updated = MemDB.update(section=section, kwargs=donnee.get(section))
                            self.ConfigSocket.send_data(mem_conf_updated)
                            self.propagate_listener(key=port, conf=MemDB.all_mem_conf())
                            current_logger.info("{0} : config memory has been updated '{1}'".format(self.Name, name))
                        except Exception as e:
                            current_logger.error("{0} : error while trying to update config from '{1}' : {2}".format(self.Name, name, e))  

                    else:
                        current_logger.error("{0} : error while trying to send config to '{1}' : unknown config request '{2}'".format(self.Name, name, data))

                # update_config_object or insert_config_object
                elif type(data) == Config:
                    try:
                        conf = pop_global_conf()
                        conf = data
                        with open(conf.COMMON_FILE_PATH, 'w+') as configfile:
                            conf.parser.write(configfile)
                            content = configfile.read() 
                        ConfigReceiver.config_last_hash = content.__hash__()
                        self.ConfigSocket.send_data(conf)
                        self.propagate_listener(key=port, conf=conf)
                        safe_append_global_conf(conf)
                        current_logger.info("{0} : config file updated from '{1}'".format(self.Name, name))
                    except Exception as e:
                        safe_append_global_conf(conf)
                        current_logger.error("{0} : error while trying to update/insert config from '{1}' : {2}".format(self.Name, name, e))
                        break
                else:
                    current_logger.error("{0} : error while trying to send config to '{1}' : unknown config request '{2}'".format(self.Name, name, data))

            self.remove_listener(key=port)

        def add_listener(self, key):
            listeners(key=key, add=self.update_listener)
        def remove_listener(self, key):
            listeners(key=key, remove=True)
        def propagate_listener(self, key, conf):
            listeners(key=key, propagate=True, conf=conf)

        def update_listener(self, conf, name):
            self.ConfigSocket.send_data(conf)
            current_logger.info("{0} : config update propagated to socket '{1}'".format(self.Name, name))

    ##########################################################################

    class ConfigReceiver(ThreadingTCPServer):
        Name = "ConfigReceiver"
        Receiver_listeners = deque()
        allow_reuse_address = True
        config_last_hash = None
        def __init__(self, port:str, conf="common", handler=ConfigHandler, log_level:int=LOG_LEVEL):
            global CONFIG_SERVER_NAME 
            global connected_listeners ; self.Receiver_listeners.append(connected_listeners)
            global current_logger ; self.port = int(port)

            if not osPathSep in conf:
                config, current_logger = init_logger(name=CONFIG_SERVER_NAME, config=conf, log_level=log_level)
            else:
                config, current_logger = init_logger(name=CONFIG_SERVER_NAME, config_path=conf, log_level=log_level)

            config.update(section="COMMON", configPath=config.COMMON_FILE_PATH, params={"CF_PORT":port})
            self.config_file_path = config.COMMON_FILE_PATH ; self.config_refresh = float(config.CF_REFRESH)
            safe_append_global_conf(config)

            ConfigHandler.InMemoryDbUri = "{0}DB".format(self.Name)
            ThreadingTCPServer.__init__(self, ("127.0.0.1", self.port), handler)

            self.abort = 0
            self.timeout = 1
            self.logname = None
            self.config_auto_reload()

        @threadIt
        def config_auto_reload(self):
            # in case of config manual modif
            global current_logger 
            global DEFAULT_TIME_SLEEP
            abort = self.abort

            while not abort:
                sleep(self.config_refresh)
                abort = self.abort

                config = pop_global_conf()
                self.config_refresh = float(config.CF_REFRESH)
                safe_append_global_conf(config)
                with open(self.config_file_path, 'r') as configFile:
                    content = configFile.read()

                if self.config_last_hash != content.__hash__():
                    try:
                        conf = pop_global_conf()
                        _conf = Config(config_file_path=conf.COMMON_FILE_PATH, ignore_config_server=True)
                        if conf.COMMON_FILE_PATH != _conf.COMMON_FILE_PATH:
                            safe_append_global_conf(conf)
                            current_logger.error("{0} : error while trying to reload config file : the 'COMMON_FILE_PATH' has been changed from '{1}' to '{2}', config won't be reloaded until the initial 'COMMON_FILE_PATH' will be restored ...".format(self.Name, _conf.COMMON_FILE_PATH, conf.COMMON_FILE_PATH))
                            current_logger.info("{0} : config auto reload paused for 60 seconds".format(self.Name))
                            sleep(60)
                        else:
                            listeners(key=-1, propagate=True, conf=_conf)
                            safe_append_global_conf(_conf)
                            self.config_last_hash = content.__hash__()
                            current_logger.info("{0} : config file {1} has been reloaded...".format(self.Name, self.config_file_path))
                    except Exception as e:
                        safe_append_global_conf(conf)
                        current_logger.error("{0} : error while trying to reload config file : {1}".format(self.Name, e))
                        continue

        def serve_until_stopped(self):
            import select
            abort = 0
            global current_logger 
            # create InMemory database
            config:Config = pop_global_conf()
            OriginelDB = MemConfig(logger=current_logger, config_file_path=config.COMMON_FILE_PATH, InMemoryDbUri=ConfigHandler.InMemoryDbUri)
            safe_append_global_conf(config)
            current_logger.info("{0} : config socket stream handler is open : '{1}', srcport : '{2}'".format(self.Name, "127.0.0.1", self.port))

            while not abort:
                rd, wr, ex = select.select([self.socket.fileno()],
                                           [], [],
                                           self.timeout)
                if rd:
                    self.handle_request()
                abort = self.abort

            OriginelDB.close()
            current_logger.info("{0} : Config memory database has been closed at {1}".format(self.Name, datetime.utcnow()))



#================================================================
if __name__ == "__main__":
    from sys import argv
    from platform import system as platformSystem
    
    log_level = LOG_LEVEL
    configStr="current"

    if len(argv) > 1:
        from common.Helpers.helpers import init_logger
        try :
            argsAndVal, defaultArgs = default_arguments(argv=argv)
            if argsAndVal:

                if "name" in argsAndVal: CONFIG_SERVER_NAME = argsAndVal.pop("name")
                if "log_level" in argsAndVal: log_level = argsAndVal["log_level"]
                if "host" in argsAndVal: argsAndVal.pop("host") # FIXME teleportation !
                if not "conf" in argsAndVal: argsAndVal["conf"] = configStr
                if not "port" in argsAndVal: argsAndVal["port"] = DEFAULT_CONFIG_SERVER_PORT

                if CONFIG_SERVER_TYPE.lower() == "async":
                    run_config_server(**argsAndVal)
                else:
                    tcpserver = ConfigReceiver(**argsAndVal)
                    tcpserver.serve_until_stopped()

            else:
                cmdLineInfo = """
                Authorized arguments : \n \
                    default optional arguments :\n \
                        --name \n \
                        --host \n \
                        --port \n \
                        --conf \n \
                        --log_level \n \
                """.format(argv)
                _, logger = init_logger(name=CONFIG_SERVER_NAME, config="common", log_level=log_level)
                logger.error("{0} : error while trying to launch the service, wrong parameter(s) provided : {1}\n {2}".format(CONFIG_SERVER_NAME, str(argv), cmdLineInfo))
        except Exception as e:
            _, logger = init_logger(name=CONFIG_SERVER_NAME, config="common", log_level=log_level)
            logger.error("{0} : unexpected error while trying to launch the service, parameter(s) provided : {1} => {2}".format(CONFIG_SERVER_NAME, str(argv), e))
    else:
        # if process launched via vscode....
        from common.Helpers.os_helpers import nb_process_running
        nb_process_running, pidList = nb_process_running(CONFIG_SERVER_NAME, getPid=True)
        vscode_launch = 4 if platformSystem() == "Windows" else 2
        if nb_process_running > vscode_launch:
            # 2 -> current process + vscode process...
            _, logger = init_logger(name="{0}_2".format(CONFIG_SERVER_NAME), log_level=log_level)
            logger.error("Config server : error while trying to start process : process already running ! (pid:{0})".format(pidList))
            exit(0)
        print("Starting Config Server, on port {0}...".format(DEFAULT_CONFIG_SERVER_PORT))

        ## with common.cfg
        if CONFIG_SERVER_TYPE.lower() == "async":
            #run_config_server(srv_port=port)
            run_config_server(port=DEFAULT_CONFIG_SERVER_PORT, conf=load_config_files()[configStr])
        else:
            #tcpserver = ConfigReceiver(srv_port=port)
            tcpserver = ConfigReceiver(port=DEFAULT_CONFIG_SERVER_PORT, conf=load_config_files()[configStr])
            tcpserver.serve_until_stopped()

        ##add in another *.py file to test
        #from time import sleep
        ## relative import
        #from sys import path;path.extend("..")
        #from common.config import Config
        #from common.Helpers.helpers import load_config_files
        #print("+ + + + + + + + + + + + + + + + + + + + + + +  \n")
        #print("    Do not forget to start config_server !!!   \n")
        #print("  And add break point before common config !!! \n")
        #print("+ + + + + + + + + + + + + + + + + + + + + + +  \n")
        #conf = load_config_files()["trading"]
        #conf1 = Config(config_file_path=conf, name="conf1")
        #conf2 = Config(config_file_path=conf, name="conf2")
        #conf2.update(section="COMMON", configPath=conf, params={"NT_URI":"None for now ?"})    
        #conf3 = Config(config_file_path=conf, name="conf3")
        #conf3.update(section="COMMON", configPath=conf, params={"NT_URI":"coucou !"})
        #conf2.reload_config()
        #conf1.reload_config()
        #conf2.update(section="COMMON", configPath=conf, params={"NT_URI":"trading !"})
        #sleep(1)
        #print(conf1.NT_URI) # should be "trading !"
        #print(conf2.NT_URI) # should be "trading !"
        #print(conf3.NT_URI) # should be "trading !"
        #conf1.reload_config()
        #punaise = conf1.get_config()
        #punaise.Name = "punaise"
        #val = input("change config file manually ('NT_URI') to test config reload, then enter...")
        #punaise.reload_config()
        #conf3.reload_config()
        #conf2.reload_config()
        #conf1.reload_config()
        #sleep(1)
        #print(conf1.NT_URI)
        #print(conf2.NT_URI)
        #print(conf3.NT_URI)
        #print(punaise.NT_URI)
        #val = input("change config file manually ('NT_URI') to test config propagation, then enter...")
        #sleep(1)
        #print(conf1.NT_URI)
        #print(conf2.NT_URI)
        #print(conf3.NT_URI)
        #print(punaise.NT_URI)
        #
        ##config.update(section="COMMON", configPath=conf, params={"NT_URI":"gros mot"})    
        #confDur = Config()
        #confDur.update(section="COMMON", configPath=confDur.COMMON_FILE_PATH, params={"NT_URI":"common ?"})
        #print(confDur.NT_URI)
        #print(confDur.parser["COMMON"]["NT_URI"])
        #conf2Dur = Config()
        #print(conf2Dur.parser["COMMON"]["NT_URI"])
        #confDur.update(section="COMMON", configPath=confDur.COMMON_FILE_PATH, params={"NT_URI":"common !"})
        #conf2Dur.reload_config()
        #print(confDur.parser["COMMON"]["NT_URI"])
        #print(conf2Dur.parser["COMMON"]["NT_URI"])
        #print("ok")

        ##add in another *.py file to test
        ## testing mem_config
        ## relative import
        #from sys import path;path.extend("..")
        #from common.config import Config
        #from common.Helpers.helpers import load_config_files
        #conf = load_config_files()["trading"]
        #config = Config(config_file_path=conf, name="test")
        #config.update_mem_config(section_key_val_dict={'test':{'key1':1, 'key2':2}})
        #data = config.get_mem_config(section_key_list={'test':['key1', 'key2']})
        #print(data)
        #config.update_mem_config(section_key_val_dict={'essai':{'key1':12000, 'key2':40, 'key3':'coucou'}})
        #data = config.get_mem_config(section_key_list={'essai':['key1', 'key2', 'key3']})
        #print(data)
        #config.update_mem_config(section_key_val_dict={'test':{'key1':1, 'key2':2, 'key3':'3'}})
        #data = config.get_mem_config(section_key_list={'test':['key1', 'key2', 'key3']})
        #print(data)
        #config.dump_mem_config()

        # stop server and restart it to check the loading of last in memory config is ok:
        #from sys import path;path.extend("..")
        #from common.config import Config
        #from common.Helpers.helpers import load_config_files
        #conf = load_config_files()["trading"]
        #config = Config(config_file_path=conf, name="test")
        #data = config.get_mem_config(section_key_list={'test':['key1', 'key2', 'key3']})
        #print(data)
        #data = config.get_mem_config(section_key_list={'essai':['key1', 'key2', 'key3']})
        #print(data)

 