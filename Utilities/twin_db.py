#!/usr/bin/env python
# coding:utf-8

from os import getcwd as osGetcwd
from os.path import join as osPathJoin, dirname as osPathDirname, basename as osPathBasename
from json import dumps as jsonDumps
from time import sleep

# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.MyLogger.my_logger import MyLogger
from common.ThreadQs.thread_Qs import SubsQ
from common.Helpers.os_helpers import is_process_running, launch_TCP_database
from common.Helpers.network_helpers import is_service_listen
from common.Helpers.datas_helpers import load_schema_from_file   
from common.Utilities.tcp_feeder import TCPFeeder


DEFAULT_CONFIG_WAIT = 0.5

def reload_Twin_config(name, config, prefix, logger):
    global DEFAULT_CONFIG_WAIT
    while True:
        try:
            sleep(DEFAULT_CONFIG_WAIT)
            config.reload_config(name=name)
            if config.parser.has_option(name.upper(), "{0}_DB_SERVER".format(prefix)) and config.parser.has_option(name.upper(), "{0}_DB_PORT".format(prefix)):
                return config.parser[name.upper()]["{0}_DB_SERVER".format(prefix)], config.parser[name.upper()]["{0}_DB_PORT".format(prefix)]
        except Exception as e:
            logger.error("{0} : error while trying to reload config of TCP Database : {1}".format(name, e))
            continue


###########################################################################################################


class TwinDB(TCPFeeder):
    """
    Contains 2 databases, one in memory, which is the main database,
    and another one as backup and saved dabase in case of problem or used while restarting app...
    Datas load first in memory databases and then forwarded to fileSystem Database
    """
    Name="TwinDB"
    def __init__(self, logger:MyLogger, config: Config, user:str="TwinDB", TwinName:str=None, 
                        uri:str="", enableInMemory=True,
                            engine:str="sqlite", namespace:str=None, db_sslcert:bool=False, 
                                db_dir:str=osPathDirname(__file__), db_reset:bool=False, config_prefix:str=None, 
                                    db_name:str="TwinDB", inMemory:bool=False, shareable:bool=False,
                                        AppBaseSchemaPath:str=osPathJoin(osGetcwd(), "common", "Utilities", "mds_interface.py"), SocketReceiver=True, 
                                            stream_func=None, DBStreamHandler=None):

        if not TwinName is None:
            self.Name = TwinName.capitalize()

        self.user = user
        self.logger = logger
        self.config = config
        self.namespace = namespace
        self.config_prefix = config_prefix
        self.AppBaseSchemaPath = AppBaseSchemaPath

        try:
            model = load_schema_from_file(AppBaseSchemaPath)
            self.model = model
        except Exception as e:
            self.logger.error("{0}: error while trying to load schema from file, '{1}' : {2}".format(self.Name, AppBaseSchemaPath, e))
            exit(1)

        if uri == "":
            uri = model.DbInterface.default_uri
            self.uri = uri
            
        db_name="{0}.db".format(self.Name.lower())
        JsonDump = {'user':self.user, 'uri':uri, 'engine':engine, 
                    'namespace':namespace, 'db_name':db_name, 'config_prefix':config_prefix,
                    'db_dir':db_dir, 'db_reset':db_reset, 'db_sslcert':db_sslcert,
                    'AppBaseSchemaPath':AppBaseSchemaPath, 'SocketReceiver':True,  
                    'stream_func':stream_func, 'DBStreamHandler':DBStreamHandler}
        self.kwargs = jsonDumps(JsonDump)

        self.logger.info("{0} : Twin Databases (Independant Process Mode) are starting.. .  . ".format(self.Name))
        
        # start TCP Database if not already running...
        TCP_Database = osPathBasename(AppBaseSchemaPath).split('.')[0]
        if not is_process_running(TCP_Database):
            _ = launch_TCP_database(name=self.Name, conf=self.config.COMMON_FILE_PATH, JsonDump=self.kwargs, DBScriptPath=AppBaseSchemaPath)
            self.logger.info("Main Database service : {0} 'TCP Database' is starting.. .  . ".format(self.Name.capitalize()))
            self.TCP_Database_IP, self.TCP_Database_PORT = reload_Twin_config(name=self.Name, config=config, prefix=config_prefix, logger=self.logger)
            while not is_service_listen(server=self.TCP_Database_IP, port=self.TCP_Database_PORT, timeout=1):
                sleep(config.MAIN_QUEUE_BEAT)
                self.TCP_Database_IP, self.TCP_Database_PORT = reload_Twin_config(name=self.Name, config=config, prefix=config_prefix, logger=self.logger)

        if enableInMemory: 
            try:
                # linked mem database...
                self.In_MemoryDB = model.DbInterface(logger=self.logger, config=config, user=user, uri=uri, 
                                                        engine="file:{0}?mode=memory&cache=shared".format(self.Name), namespace=namespace,
                                                            db_name="{0}.db".format(self.Name.lower()), config_prefix=config_prefix, inMemory=True, shareable=True,
                                                                AppBaseSchema=model.Schema, SocketReceiver=False)
            except Exception as e:
                self.logger.error("{0} : error while trying to start 'inMemory' database : {1}".format(self.Name, e))
                exit(1)

        try:
            TCPFeeder.__init__(self, logger=logger, config=config, name=self.Name)
        except Exception as e:
            self.logger.error("{0} : error while trying to start 'TCP Feeder' : {1}".format(self.Name, e))
            exit(1)

        self.logger.info("{0} : Twin Databases have been started !".format(self.Name))


###########################################################################################################


class TwinDBSubsQ(SubsQ, TCPFeeder):
    """
    Contains 2 databases, one in memory, which is the main database,
    and another one as backup and saved dabase in case of problem or used while restarting app...
    Datas load first in memory databases and then forwarded to fileSystem Database
    """
    Name="TwinDBSubsQ"
    def __init__(self, mainQueue, logger:MyLogger, config: Config, user:str="TwinDB", TwinName:str=None, 
                        uri:str="",  enableInMemory=True,
                            engine:str="sqlite", namespace:str=None, db_sslcert:bool=False, 
                                db_dir:str=osPathDirname(__file__), db_reset:bool=False, config_prefix:str=None, 
                                    db_name:str="TwinDB", inMemory:bool=False, shareable:bool=False,
                                        AppBaseSchemaPath:str=osPathJoin(osGetcwd(), "common", "Utilities", "mds_interface.py"), SocketReceiver=True, 
                                            stream_func=None, DBStreamHandler=None,
                                                default_recv=None, ChildProc=None, **kwargs):

        if not TwinName is None:
            self.Name = TwinName.capitalize()

        self.user = user
        self.logger = logger
        self.config = config

        self.logger.info("{0} : Twin Databases (Subscriber Mode) are starting.. .  . ".format(self.Name))
        SubsQ.__init__(self, name=self.Name, mainQueue=mainQueue, default_recv=default_recv, ChildProc=ChildProc, **kwargs)

        try:
            from threading import Thread
            Thread(target=self.start_TCP_Database, args=(enableInMemory, 
                logger, config, 
                    user, uri, engine, 
                        namespace, db_sslcert,
                            db_name, config_prefix,
                                db_dir, db_reset, 
                                    inMemory, shareable,
                                        AppBaseSchemaPath, SocketReceiver, 
                                            stream_func, DBStreamHandler,
                )).start()
        except Exception as e:
            self.logger.error("{0} : error while trying to start 'TCP Database' : {1}".format(self.Name, e))
            exit(1)

        try:
            TCPFeeder.__init__(self, logger=logger, config=config, name=self.Name)
        except Exception as e:
            self.logger.error("{0} : error while trying to start 'TCP Feeder' : {1}".format(self.Name, e))
            exit(1)


    def start_TCP_Database(self, enableInMemory, logger, config, user, uri, engine, namespace, db_sslcert, db_name, config_prefix, db_dir, db_reset, inMemory, shareable, AppBaseSchemaPath, SocketReceiver, stream_func, DBStreamHandler):
        try:
            model = load_schema_from_file(AppBaseSchemaPath)
        except Exception as e:
            self.logger.error("{0}: error while trying to load schema from file, '{1}' : {2}".format(self.Name, AppBaseSchemaPath, e))
            exit(1)

        if uri == "":
            uri = model.DbInterface.default_uri

        db_name="{0}.db".format(self.Name.lower())
        JsonDump = {'user':self.user, 'uri':uri, 'engine':engine, 
                    'namespace':namespace, 'db_name':db_name, 'config_prefix':config_prefix,
                    'db_dir':db_dir, 'db_reset':db_reset, 'db_sslcert':db_sslcert,
                    'AppBaseSchemaPath':AppBaseSchemaPath, 'SocketReceiver':True, 
                    'stream_func':stream_func, 'DBStreamHandler':DBStreamHandler}
        self.kwargs = jsonDumps(JsonDump)
        
        # start TCP Database if not already running...
        TCP_Database = osPathBasename(AppBaseSchemaPath).split('.')[0]
        if not is_process_running(TCP_Database):
            _ = launch_TCP_database(name=self.Name, conf=self.config.COMMON_FILE_PATH, JsonDump=self.kwargs, DBScriptPath=AppBaseSchemaPath)
            self.logger.info("Main Database service : {0} 'TCP Database' is starting.. .  . ".format(self.Name.capitalize()))
            self.TCP_Database_IP, self.TCP_Database_PORT = reload_Twin_config(name=self.Name, config=config, prefix=config_prefix, logger=self.logger)
            while not is_service_listen(server=self.TCP_Database_IP, port=self.TCP_Database_PORT, timeout=1):
                sleep(config.MAIN_QUEUE_BEAT)
                self.TCP_Database_IP, self.TCP_Database_PORT = reload_Twin_config(name=self.Name, config=config, prefix=config_prefix, logger=self.logger)

        if enableInMemory: 
            try:
                # linked mem database...
                self.In_MemoryDB = model.DbInterface(logger=self.logger, config=config, user=user, uri=uri, 
                                                        engine="file:{0}?mode=memory&cache=shared".format(self.Name), namespace=namespace,
                                                            db_name="{0}.db".format(self.Name.lower()), config_prefix=config_prefix, inMemory=True, shareable=True,
                                                                AppBaseSchema=model.Schema, SocketReceiver=False)
            except Exception as e:
                self.logger.error("{0} : error while trying to start 'inMemory' database : {1}".format(self.Name, e))
                exit(1)

        self.logger.info("{0} : Twin databases have been started !".format(self.Name))




#================================================================
if __name__ == "__main__":
    from os import sep as osSep
    from sys import argv
    from common.Helpers.helpers import init_logger, getOrDefault   
    name = "twindb"
    configStr = "common"
    if len(argv) > 1:  
        try:
            if len(argv) == 4:
                from json import loads as jsonLoads
                name = (argv[1]).capitalize()
                configStr = argv[2]
                kwargs = jsonLoads(argv[3])

                config, logger = init_logger(name=name, config_path=configStr)
                model = load_schema_from_file(kwargs["AppBaseSchemaPath"])
                _ = model.DbInterface(logger=logger, config=config, user=getOrDefault(kwargs, "TCP Database", key="user"),
                                uri=getOrDefault(kwargs, model.DbInterface.default_uri, key="uri"), 
                                    engine=getOrDefault(kwargs, "sqlite", key="engine"), namespace=getOrDefault(kwargs, None, key="namespace"), db_sslcert=getOrDefault(kwargs, False, key="db_sslcert"),
                                        db_dir=getOrDefault(kwargs, model.DbInterface.default_db_dir, key="db_dir"), db_reset=getOrDefault(kwargs, False, key="db_reset"), config_prefix=getOrDefault(kwargs, None, key="config_prefix"),
                                            db_name=getOrDefault(kwargs, "Dummy.db", key="db_name"), inMemory=getOrDefault(kwargs, False, key="inMemory"), shareable=getOrDefault(kwargs, False, key="shareable"),
                                                AppBaseSchema=model.Schema, SocketReceiver=getOrDefault(kwargs, True, key="SocketReceiver"), stream_func=getOrDefault(model.stream_func, None), DBStreamHandler=getOrDefault(model.DBStreamHandler, None))          
            else:
                _, logger = init_logger(name=name, config=configStr)
                logger.error("Database : error while trying to launch the service, {0} parameter(s) provided : {1}, expected : 3 'name config_file_path **kwargs' {2}".format("too much" if len(argv) > 4 else "not enough", len(argv)-1, str(argv)))
        except Exception as e:
            _, logger = init_logger(name=name, config=configStr)
            logger.error("Database : error while trying to launch the service, wrong or missing parameter(s) : {0} => {1}".format(str(argv), e))
    else: 
        # Default schema : from common.Utilities.mds_interface import Schema
        config, logger = init_logger(name=name, config=configStr)
        _newTwinDb = TwinDB(TwinName=name, logger=logger, config=config, config_prefix="TW", SocketReceiver=True, uri="sqlite:///{0}{1}twinDb.db".format(osPathDirname(__file__), osSep))

    # Twin Databases subscriber ; default schema : from common.Utilities.mds_interface import Schema
        #from common.ThreadQs.thread_Qs import StarQs
        #config, logger = init_logger(name=name, config=configStr)
        #mainQueue = StarQs(logger, config, "{0}_streamQ".format(name))
        #_newTwinDBSubsQ = TwinDBSubsQ(mainQueue=mainQueue, TwinName=name, logger=logger, config=config, config_prefix="TW", SocketReceiver=True)