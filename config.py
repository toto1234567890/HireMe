#!/usr/bin/env python
# coding:utf-8


import configparser
from os import environ as osEnviron, name as osname
from os.path import isfile as osPathIsFile, join as osPathJoin, basename as osPathBaseName
from time import sleep
from threading import Thread
from retry import retry
from logging import getLogger

# relative import
from sys import path;path.extend("..")
from common.Helpers.helpers import getOrDefault, getUnusedPort, load_config_files, ConfigException
from common.Helpers.os_helpers import get_executed_script_dir, is_process_running, launch_config_server
from common.Helpers.network_helpers import is_service_listen, MySocket

updateFunc = None

class RequiredCommonConf:
    NAME = None
    MAIN_QUEUE_BEAT = None
    CF_SERVER = None
    CF_PORT = None
    CF_REFRESH = None

    NT_IP = None
    NT_PORT = None
    NT_URI = None

    TB_TOKEN = None
    TB_CHATID = None
    TB_IP = None
    TB_PORT = None

    DB_URI = None
    DB_PORT = None
    DB_ENDPOINT = None
    DB_NAMESPACE = None
    DB_SSLCERT = None  

    FS_TEMP = None
    FS_DATA = None

    JP_SERVER = None
    JP_PORT = None
    JP_ENV = None

    RESET = None
    def __init__(self)->None:
        pass


class Config:  # pylint: disable=too-few-public-methods,too-many-instance-attributes
    configObj={} 
    Name = "Config"
    COMMON_FILE_PATH = None
    CF_SERVER = None
    CF_PORT = None
    CONFIG_SERVER = False
    # configparser patch...
    def my_optionxform(self, optionstr):
        return optionstr.upper()

    def __init__(self, config_file_path:str=None, config_file_list:list=None, server_mode:bool=False, name:str=None, ignore_config_server:bool=False):
        self.mem_config = None

        if not name is None:
            self.Name = name
        section = "COMMON"

        # Init config
        self.parser = configparser.ConfigParser()
        self.parser.optionxform = self.my_optionxform

        if not config_file_path is None and not config_file_list is None:
            print("\nYou should provide either config_file_path, either config_file_list... not both !")
            print("Exit program...\n")
            exit(1)
        if config_file_path == None and config_file_list == None:
            default_conf = load_config_files()
            if "common" in default_conf:
                self.COMMON_FILE_PATH = default_conf["common"]
            else:
                config_file_path = "In Memory!"
        # CF_PORT = 3306 = IANA This port is listed as "My SQL"
        # NT_PORT = 10080 = IANA This port is listed as "Amanda Backup"
        cfg_str = """
        [COMMON]
        # Config name
        NAME = common
        MAIN_QUEUE_BEAT = 0.01
        CF_SERVER = 127.0.0.1
        CF_PORT = 3306
        CF_REFRESH = 300
        # Telegram Emergency (unexpected error?!)
        # Telegram_Api = 10037566
        # Telegram_Hash = ce435c2033146088eef68dabb1ffb1df
        # Telegram_Session = MyTelegram.session
        # Log server
        LG_IP = 127.0.0.1
        # Telegram Notifs
        NT_IP = 127.0.0.1
        NT_PORT = 10080
        NT_URI = None for the moment
        # Remote control
        TB_TOKEN = 5346907063:AAHjF-7pTIlJsMj3t_84Ddb1v_gy-G4XAF0
        TB_CHATID = 1995178465
        TB_IP = 127.0.0.1
        TB_PORT = 22123
        # Database
        DB_URI = Database/backend.db
        DB_PORT = 5123
        DB_ENDPOINT = http://db:5123
        DB_NAMESPACE = DEFAULT
        DB_SSLCERT = False
        # datas on file system
        FS_TEMP = None
        FS_DATA = None
        # Reset True, remove database/history
        RESET = False
        # Jupyter Lab Server
        JP_SERVER = 127.0.0.1
        JP_PORT = 8888
        JP_ENV = /Users/imac/Desktop/Jupyt
        # Config file path 
        COMMON_FILE_PATH = ""
        """
        if not config_file_list is None:
            self.merge(config_file_list=config_file_list)
            if "common" in config_file_list:
                self.COMMON_FILE_PATH = config_file_list["common"]
            else:
                self.COMMON_FILE_PATH = "{0}.cfg".format(osPathJoin(get_executed_script_dir(__file__), osPathBaseName(get_executed_script_dir(__file__))))
            self.write_config_file(self.COMMON_FILE_PATH)
        elif config_file_path != "In Memory!":
            if not self.COMMON_FILE_PATH is None:
                # common.cfg found !
                self.load_config_file(self.COMMON_FILE_PATH)
            else:
                # other *.cfg file...
                self.COMMON_FILE_PATH = config_file_path
                self.load_config_file(self.COMMON_FILE_PATH)
        else:
            # load config file with default params in "Memory"
            self.parser.read_string(cfg_str)
            print("No Configuration file (*.cfg) found ! default '{0}' configuration has been loaded !".format(config_file_path))
            # write config file with default params in "Memory"
            conf_path = get_executed_script_dir(__file__)
            self.update(section, conf_path)
        
        self.load_config_object(server_mode=server_mode, ignore_config_server=ignore_config_server)

    def load_config_object(self, server_mode=False, section="COMMON", ignore_config_server=False):
        conf = RequiredCommonConf()
        if not self.COMMON_FILE_PATH is None:
            try:
                # main common config 
                self.parser[section]["NAME"] = conf.NAME = getOrDefault(osEnviron.get("NAME"), self.parser[section]["NAME"])
                self.parser[section]["COMMON_FILE_PATH"] = conf.COMMON_FILE_PATH = self.COMMON_FILE_PATH
                self.parser[section]["MAIN_QUEUE_BEAT"] = getOrDefault(osEnviron.get("MAIN_QUEUE_BEAT"), self.parser[section]["MAIN_QUEUE_BEAT"]) ; \
                    self.MAIN_QUEUE_BEAT = conf.MAIN_QUEUE_BEAT = float(self.parser[section]["MAIN_QUEUE_BEAT"])
                # main config config
                self.parser[section]["CF_SERVER"] = conf.CF_SERVER = getOrDefault(osEnviron.get("CF_SERVER"), self.parser[section]["CF_SERVER"]) ; \
                    self.CF_SERVER = self.parser[section]["CF_SERVER"]
                self.parser[section]["CF_PORT"] = getOrDefault(osEnviron.get("CF_PORT"), self.parser[section]["CF_PORT"]) ; \
                    conf.CF_PORT = self.CF_PORT = int(self.parser[section]["CF_PORT"])
                self.parser[section]["CF_REFRESH"] = getOrDefault(osEnviron.get("CF_REFRESH"), self.parser[section]["CF_REFRESH"]) ; \
                    conf.CF_REFRESH = self.CF_REFRESH = float(self.parser[section]["CF_REFRESH"])
                # main data config 
                self.parser[section]["FS_DATA"] = conf.FS_DATA = getOrDefault(osEnviron.get("FS_DATA"), self.parser[section]["FS_DATA"]) ; \
                    self.FS_DATA = self.parser[section]["FS_DATA"]
                self.parser[section]["FS_TEMP"] = conf.FS_TEMP = getOrDefault(osEnviron.get("FS_TEMP"), self.parser[section]["FS_TEMP"]) ; \
                    self.FS_TEMP = self.parser[section]["FS_TEMP"]
                # main jupyter server lab config 
                self.parser[section]["JP_SERVER"] = conf.JP_SERVER = getOrDefault(osEnviron.get("JP_SERVER"), self.parser[section]["JP_SERVER"]) ; \
                    self.JP_SERVER = self.parser[section]["JP_SERVER"]
                self.parser[section]["JP_PORT"] = getOrDefault(osEnviron.get("JP_PORT"), self.parser[section]["JP_PORT"]) ; \
                    conf.JP_PORT = self.JP_PORT = int(self.parser[section]["JP_PORT"])
                self.parser[section]["JP_ENV"] = conf.JP_ENV = getOrDefault(osEnviron.get("JP_ENV"), self.parser[section]["JP_ENV"]) ; \
                    self.JP_ENV = self.parser[section]["JP_ENV"]
                
                if server_mode:
                    # service mode is only callable with in Shell...
                    config_server = "config_server" 
                    if not is_process_running(config_server):
                        self.CF_PORT = self.parser["COMMON"]["CF_PORT"] = conf.CF_PORT = str(getUnusedPort())
                        self.update(section="COMMON", configPath=conf.COMMON_FILE_PATH, params={"CF_PORT":conf.CF_PORT}, server_starting=True)
                        Thread(target=self.start_server, args=(conf.COMMON_FILE_PATH, conf.CF_PORT, self.CF_SERVER, conf.MAIN_QUEUE_BEAT,), daemon=False).start()

                # if server is already running
                if is_service_listen(server=self.CF_SERVER, port=conf.CF_PORT) and not ignore_config_server:
                    self.CONFIG_SERVER = True
                    try:
                        load_conf = self.get_config(server=self.CF_SERVER, port=self.CF_PORT, name="{0} config.__init__".format(self.Name))
                        for section_name, section in self.parser.items():
                            if not load_conf.parser.has_section(section_name) and (section_name not in ("COMMON", "DEFAULT")):
                                load_conf.parser.add_section(section_name)
                                for key, value in section.items():
                                    load_conf.parser.set(section_name, key, value)
                        self.__dict__.update(load_conf.__dict__)
                        self.update()
                        self.mem_config = self.get_mem_config(section_key_list=None)
                    except Exception as e:
                        print("\nError while trying to load config from config_server :\n{0}".format(e))
                        print("Exit program...\n")
                        exit(1)
                    Thread(target=self.config_listener, args=(self.CF_SERVER, self.CF_PORT), daemon=True).start()
                else:
                    # Telegram
                    # self.TELEGRAM_HASH = getOrDefault(osEnviron.get("TELEGRAM_HASH"), config.get(self.USER_section, "Telegram_Hash"))
                    # self.TELEGRAM_API = getOrDefault(osEnviron.get("TELEGRAM_API"), config.get(self.USER_section, "Telegram_Api"))

                    # Log server
                    self.parser[section]["LG_IP"] = conf.LG_IP = getOrDefault(osEnviron.get("LG_IP"), self.parser[section]["LG_IP"]) 

                    # Telegram Notifs
                    self.parser[section]["NT_IP"] = conf.NT_IP = getOrDefault(osEnviron.get("NT_IP"), self.parser[section]["NT_IP"])            
                    self.parser[section]["NT_PORT"] = conf.NT_PORT = getOrDefault(osEnviron.get("NT_PORT"), self.parser[section]["NT_PORT"])
                    self.parser[section]["NT_URI"] = conf.NT_URI = getOrDefault(osEnviron.get("NT_URI"), self.parser[section]["NT_URI"])

                    # Remote Control
                    self.parser[section]["TB_TOKEN"] = conf.TB_TOKEN = getOrDefault(osEnviron.get("TB_TOKEN"), self.parser[section]["TB_TOKEN"])
                    self.parser[section]["TB_CHATID"] = conf.TB_CHATID = getOrDefault(osEnviron.get("TB_CHATID"), self.parser[section]["TB_CHATID"])
                    self.parser[section]["TB_IP"] = conf.TB_IP = getOrDefault(osEnviron.get("TB_IP"), self.parser[section]["TB_IP"])            
                    self.parser[section]["TB_PORT"] = conf.TB_PORT = getOrDefault(osEnviron.get("TB_PORT"), self.parser[section]["TB_PORT"])

                    # Database
                    self.parser[section]["DB_URI"] = conf.DB_URI = getOrDefault(osEnviron.get("DB_URI"), self.parser[section]["DB_URI"])
                    self.parser[section]["DB_PORT"] = conf.DB_PORT = getOrDefault(osEnviron.get("DB_PORT"), self.parser[section]["DB_PORT"])
                    self.parser[section]["DB_ENDPOINT"] = conf.DB_ENDPOINT = getOrDefault(osEnviron.get("DB_ENDPOINT"), self.parser[section]["DB_ENDPOINT"])
                    self.parser[section]["DB_NAMESPACE"] = conf.DB_NAMESPACE = getOrDefault(osEnviron.get("DB_NAMESPACE"), self.parser[section]["DB_NAMESPACE"])
                    self.parser[section]["DB_SSLCERT"] = conf.DB_SSLCERT = getOrDefault(osEnviron.get("DB_SSLCERT"), self.parser[section]["DB_SSLCERT"])

                    # FileSystem Datas
                    self.parser[section]["FS_TEMP"] = conf.FS_TEMP = getOrDefault(osEnviron.get("FS_TEMP"), self.parser[section]["FS_TEMP"])
                    self.parser[section]["FS_DATA"] = conf.FS_DATA = getOrDefault(osEnviron.get("FS_DATA"), self.parser[section]["FS_DATA"])

                    # Jupyter Lab Server
                    self.parser[section]["JP_SERVER"] = conf.JP_SERVER = getOrDefault(osEnviron.get("JP_SERVER"), self.parser[section]["JP_SERVER"])
                    self.parser[section]["JP_PORT"] = conf.JP_PORT = getOrDefault(osEnviron.get("JP_PORT"), self.parser[section]["JP_PORT"])
                    self.parser[section]["JP_ENV"] = conf.JP_ENV = getOrDefault(osEnviron.get("JP_ENV"), self.parser[section]["JP_ENV"])

                    # Reset
                    self.parser[section]["RESET"] = conf.RESET = getOrDefault(osEnviron.get("RESET"), self.parser[section]["RESET"])

                    # easier to manipulate from other script..
                    self.configObj[section] = conf
                    self.__dict__.update(conf.__dict__)

            except Exception as e:
                print("\nProblem while loading configuration :\n{0}".format(e))
                print("Exit program...\n")
                exit(1)
         
    def load_config_file(self, config_file_path):
        if osname == 'nt':
            config_file_path = str(config_file_path)
        if not osPathIsFile(config_file_path):
            print("\nNo configuration file (*.cfg) found ! File : '{0}' doesn't exist...".format(config_file_path))
            print("Exit program...\n")
            exit(1)
        else:
            self.parser.read(config_file_path)
            try:
                print("Configuration file (*.cfg) found ! '{0}' has been loaded !".format(config_file_path))
            except:
                # Windows c'est de la merde ! (la merde, ça au moins, ça fonctionne à tous les niveaux !/!\!)
                pass

    def merge(self, logger=None, config_file_path:str=None, config_file_list:list=None, str_config:str=None):
        # do not use with config server...
        try :
            if not str_config is None:
                self.parser.read_string(str_config)
                logger.info("Config : string config has been loaded !")
            if not config_file_path is None:
                self._merge(logger, config_file_path)
            if not config_file_list is None:
                for conf in config_file_list.values():
                    self._merge(logger, conf)        
        except Exception as e:
            if not logger is None:
                logger.error("Config : error while trying to merge config file {0}... : '{1}'\n                                  /!\ Exit program... \n".format(config_file_path, e))
            else:
                print("Config : error while trying to merge config file {0}... : '{1}'\n                                  /!\ Exit program... \n".format(config_file_path, e))
            exit(1)

    def _merge(self, logger, config_file_path:str):
        if not osPathIsFile(config_file_path):
            if not logger is None:
                logger.error("Config : no configuration file (*.cfg) found ! '{0}' doesn't exist...".format(config_file_path))
            else:
                print(("Config : no configuration file (*.cfg) found ! '{0}' doesn't exist...".format(config_file_path)))
        else:
            self.parser.read(config_file_path)
            if not logger is None:
                logger.info("Config : configuration file (*.cfg) found ! '{0}' has been loaded !".format(config_file_path))
            else:
                print("Config : configuration file (*.cfg) found ! '{0}' has been loaded !".format(config_file_path))

    def update(self, section:str=None, configPath:str=None, params:dict=None, name:str=None, server_starting:bool=False):
        logger = getLogger(__name__)
        if not params is None:
            # update key:value
            self.parser.read_dict({section:params})
        if not configPath is None:
            if not configPath.endswith(".cfg"):
                # common in Memory !
                configPath = osPathJoin(configPath, "{0}.cfg".format(section.lower()))
        if self.CONFIG_SERVER and (not server_starting):
            # while load external components with config_server, write config file from config server...
            try:
                if name == None: name = "{0} config.update".format(self.Name)
                with MySocket(server=self.CF_SERVER, port=self.CF_PORT) as configSock:
                    configSock.send_data("{0}:{1}:{2}".format(name, "127.0.0.1", configSock.conn.getsockname()[1]))
                    configSock.send_data(self)
                    _ = configSock.receive_data()
                if not logger is None:
                    logger.info("Config : configuration file '{0}' has been updated with new parameters".format(configPath))
                else:
                    print("Configuration file '{0}' has been updated with new parameters".format(configPath))
            except Exception as e:
                logger.info("Config : error while trying to write *.cfg file '{0}' : {1}".format(configPath, e))
        else:
            self.write_config_file(configPath, logger)
            self.reload_config(ignore_config_server=True)

    def write_config_file(self, configPath, logger=None):
            try:
                with open(configPath, 'w') as configfile:
                    self.parser.write(configfile)
                if not logger is None:
                    logger.info("Config : configuration file '{0}' has been updated with new parameters".format(configPath))
                else:
                    print("Configuration file '{0}' has been updated with new parameters".format(configPath))
            except Exception as e:
                if not logger is None:
                    logger.info("Config : error while trying to write *.cfg file '{0}' : {1}".format(configPath, e))
                else:
                    print("Config : error while trying to write *.cfg file '{0}' : {1}".format(configPath, e))                   

    def start_server(self, path_conf, port, server, wait):
        logger = getLogger(__name__)
        if server == "127.0.0.1" or server.lower() == "localhost":
            _ = launch_config_server(port=port, path_conf=path_conf)
            while not is_service_listen(server, port):
                sleep(wait)
            logger.info("Main Config : Main Config is starting.. .  . ")
            print("Main Config : Main Config is starting.. .  . ")
        else:
            raise Exception("Config server on external server is not implemented yet...")

    def get_config(self, server=None, port=None, name=None):
        if self.CONFIG_SERVER:
            if name == None: name = "{0} config.get_server_config".format(self.Name)
            if server == None: server=self.CF_SERVER
            if port == None: port = self.CF_PORT
            with MySocket(name=name, server=server, port=port) as configSock:
                configSock.send_data("{0}:{1}:{2}".format(name, server, configSock.conn.getsockname()[1]))
                configSock.send_data("get_config_object")
                return configSock.receive_data()
        else:
            return self

    def get_mem_config(self, server=None, port=None, name=None, section_key_list:list=None):
        if self.CONFIG_SERVER:
            if name == None: name = "{0} config.get_mem_config".format(self.Name)
            if server == None: server=self.CF_SERVER
            if port == None: port = self.CF_PORT
            with MySocket(name=name, server=server, port=port) as configSock:
                configSock.send_data("{0}:{1}:{2}".format(name, server, configSock.conn.getsockname()[1]))
                configSock.send_data({"get_mem_config":section_key_list})
                return configSock.receive_data()
        else:
            raise ConfigException("invalid 'config.get_mem_config' call, the current config object is not linked to the 'config_server', check if the 'config_server' is started...")

    def update_mem_config(self, server=None, port=None, name=None, section_key_val_dict:dict=None):
        if self.CONFIG_SERVER:
            if name == None: name = "{0} config.update_mem_config".format(self.Name)
            if server == None: server=self.CF_SERVER
            if port == None: port = self.CF_PORT
            with MySocket(name=name, server=server, port=port) as configSock:
                configSock.send_data("{0}:{1}:{2}".format(name, server, configSock.conn.getsockname()[1]))
                configSock.send_data({"update_mem_config":section_key_val_dict})
                return configSock.receive_data()
        else:
            raise ConfigException("invalid 'config.update_mem_config' call, the current config object is not linked to the 'config_server', check if the 'config_server' is started...")

    def dump_mem_config(self, server=None, port=None, name=None):
        if self.CONFIG_SERVER:
            if name == None: name = "{0} config.dump_mem_config".format(self.Name)
            if server == None: server=self.CF_SERVER
            if port == None: port = self.CF_PORT
            with MySocket(name=name, server=server, port=port, timeout=5) as configSock:
                configSock.send_data("{0}:{1}:{2}".format(name, server, configSock.conn.getsockname()[1]))
                configSock.send_data("dump_mem_config")
                return configSock.receive_data()
        else:
            raise ConfigException("invalid 'config.update_mem_config' call, the current config object is not linked to the 'config_server', check if the 'config_server' is started...")

    def reload_config(self, server=None, port=None, name=None, ignore_config_server=False):
        if self.CONFIG_SERVER and not ignore_config_server:
            if name == None: name = "{0} config.reload_config".format(self.Name)
            reloaded_conf = self.get_config(server=server, port=port, name=name)
            self.__dict__.update(reloaded_conf.__dict__)           
        else:
            self.load_config_file(self.COMMON_FILE_PATH)
            self.load_config_object(ignore_config_server=ignore_config_server)
 
    def update_self(self, config_updated):
        if type(config_updated) == Config:
            self.__dict__.update(config_updated.__dict__)
        else:
            self.mem_config = config_updated

    @retry(delay=5) 
    def config_listener(self, server, port, delayed_start=30):
        global updateFunc
        try:
            name = "{0} listener".format(self.Name)
            with MySocket(name=name, server=server, port=port) as listenerSock:
                listenerSock.send_data("{0}:{1}:{2}".format(name, server, listenerSock.conn.getsockname()[1]))
                listenerSock.send_data("add config listener")
                while True:
                    config_updated = listenerSock.receive_data()
                    if not config_updated:
                        break
                    if not updateFunc is None : updateFunc(config_updated)
                    else : self.update_self(config_updated)
        except Exception as e:
            print("Config listener : '{0}:{1}' error while trying to upgrade configuration : {2}".format(name, port, e))

    @staticmethod
    def set_updateFunc(update_func):
        global updateFunc 
        updateFunc = update_func


#================================================================
if __name__=="__main__":

    print("+ + + + + + + + + + + + + + + + + + + + + + + \n")
    print("    Do not forget to STOP config_server !!!   \n")
    print("+ + + + + + + + + + + + + + + + + + + + + + + \n")
    
    config = Config()

    print("\n******* config common *******")
    for section_name in config.parser.sections():
        print("Section: " + section_name)
        #print("     Options: " + str(config.parser.options(section_name)))
        for name, value in config.parser.items(section_name):
            print("         %s = %s" % (name, value))
    print("******* config common *******\n")
    test = config.configObj["COMMON"]
#
    essai = "34"
#
    config.update(section="COMMON", configPath=config.COMMON_FILE_PATH, params={"TB_PORT":essai}, name="ConfigTest")
    print("\n******* config common modified *******")
    for section_name in config.parser.sections():
        print("Section: " + section_name)
        #print("     Options: " + str(config.parser.options(section_name)))
        for name, value in config.parser.items(section_name):
            print("         %s = %s" % (name, value))
    print("******* config common modified *******\n")
    config.configObj["COMMON"].__dict__["TB_PORT"] = essai 
    test = config.configObj["COMMON"]
    print(test.TB_PORT)
#
    from os import getcwd as osGetcwd
    config_path = osPathJoin(osGetcwd(), "trading/trading.cfg")
    config = Config(config_file_path=config_path, server_mode=True)
#
    print("\n******* config common *******")
    for section_name in config.parser.sections():
        print("Section: " + section_name)
        #print("     Options: " + str(config.parser.options(section_name)))
        for name, value in config.parser.items(section_name):
            print("         %s = %s" % (name, value))
    print("******* config common *******\n")

    from common.Helpers.helpers import load_config_files
    config_file_list = load_config_files()
    confs = Config(config_file_list=config_file_list)
#
    print("\n******* configs merged *******")
    for section_name in confs.parser.sections():
        print("Section: " + section_name)
        #print("     Options: " + str(config.parser.options(section_name)))
        for name, value in confs.parser.items(section_name):
            print("         %s = %s" % (name, value))
    print("******* configs merged *******\n")
#
    print("******* common properties after merge *******")
    print("Section: {0}".format(confs.NAME))
    print("         {0}".format(confs.MAIN_QUEUE_BEAT))
    print("         {0}".format(confs.CF_SERVER))
    print("         {0}".format(confs.CF_PORT))
    print("         {0}".format(confs.CF_REFRESH))
    print("         {0}".format(confs.FS_DATA))
    print("         {0}".format(confs.FS_TEMP))
    print("         {0}".format(confs.LG_IP))
    print("         {0}".format(confs.NT_IP))
    print("         {0}".format(confs.NT_PORT))
    print("         {0}".format(confs.NT_URI))
    print("         {0}".format(confs.TB_TOKEN))
    print("         {0}".format(confs.TB_CHATID))
    print("         {0}".format(confs.TB_IP))
    print("         {0}".format(confs.TB_PORT))
    print("         {0}".format(confs.DB_URI))
    print("         {0}".format(confs.DB_PORT))
    print("         {0}".format(confs.DB_NAMESPACE))
    print("         {0}".format(confs.DB_SSLCERT))
    print("         {0}".format(confs.DB_NAMESPACE))
    print("         {0}".format(confs.RESET))
    print("         {0}".format(confs.COMMON_FILE_PATH))
    print("******* common properties after merge *******\n") 
    print("End  ! (service mode is only callable with in Shell...)\n") 
    print("******* The remaining processes launched will quit ! *******\n") 