#!/usr/bin/env python
# coding:utf-8

from time import sleep
from os.path import sep as osPathSep, join as osPathJoin, dirname as osPathDirname, exists as osPathExists
from datetime import datetime
from collections import deque
from socketserver import ThreadingTCPServer, StreamRequestHandler
from sqlite3 import connect as sqlite3Connect, threadsafety as sqlite3Threadsafety


# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.Helpers.helpers import init_logger, threadIt, load_config_files
from common.Helpers.network_helpers import SafeSocket

CONFIG_SERVER_NAME = "config_server"
DEFAULT_CONFIG_SERVER_PORT = 3306 # default port for MySQL (not used by me at least !)

DEFAULT_TIME_SLEEP = 0.01
current_logger = None
connected_listeners = {}
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

def listeners(key, add=None, remove=False, propagate=False, conf=None, mem_conf=None):
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
        listner_dict.pop(key)
    ConfigReceiver.Receiver_listeners.append(listner_dict)

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
        self.conn.execute(self.commonConfig.replace("[#DEFAULT]", config_file_path).replace("[#TABLENAME]", "config"))

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

##########################################################################

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
        self.add_listener(key=port)

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
    def __init__(self, srv_port:str, conf="common", handler=ConfigHandler):
        global CONFIG_SERVER_NAME
        global connected_listeners ; self.Receiver_listeners.append(connected_listeners)
        global current_logger ; self.port = int(srv_port)

        if not osPathSep in conf:
            config, current_logger = init_logger(name=CONFIG_SERVER_NAME, config=conf)
        else:
            config, current_logger = init_logger(name=CONFIG_SERVER_NAME, config_path=conf)

        config.update(section="COMMON", configPath=config.COMMON_FILE_PATH, params={"CF_PORT":srv_port})
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
    port = DEFAULT_CONFIG_SERVER_PORT

    if len(argv) > 1:
        conf = None
        try:
            if len(argv) == 2:
                conf = argv[1]
                tcpserver = ConfigReceiver(srv_port=port, conf=conf)
                tcpserver.serve_until_stopped()
            elif len(argv) == 3:
                port = argv[1]
                conf = argv[2]
                tcpserver = ConfigReceiver(srv_port=port, conf=conf)
                tcpserver.serve_until_stopped()
            else:
                if not conf is None:
                    _, logger = init_logger(name=CONFIG_SERVER_NAME, config_path=conf)
                else:
                    _, logger = init_logger(name=CONFIG_SERVER_NAME)
                logger.error("Config server : error while trying to launch the service, {0} parameter(s) provided : {1}, expected : 2 or 3 'config server path, port optional=conf' -{2}".format("too much" if len(argv) > 3 else "not enough", len(argv)-1, str(argv)))
        except Exception as e:
            if not conf is None:
                _, logger = init_logger(name=CONFIG_SERVER_NAME, config_path=conf)
            else:
                _, logger = init_logger(name=CONFIG_SERVER_NAME)
            logger.error("Config server : error while trying to launch the service, wrong parameter(s) provided : {0} => {1}".format(str(argv), e))
    else:
        # if process launched via vscode....
        from common.Helpers.os_helpers import nb_process_running
        nb_process_running, pidList = nb_process_running(CONFIG_SERVER_NAME, getPid=True)
        if nb_process_running > 2:
            # 2 -> current process + vscode process...
            _, logger = init_logger(name="{0}_2".format(CONFIG_SERVER_NAME))
            logger.error("Config server : error while trying to start process : process already running ! (pid:{0})".format(pidList))
            exit(0)
        print("Starting Config Server, on port {0}...".format(port))

        ## with common.cfg
        #tcpserver = ConfigReceiver(srv_port=port)
        tcpserver = ConfigReceiver(srv_port=port, conf=load_config_files()["current"])
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

 