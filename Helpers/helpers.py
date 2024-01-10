#!/usr/bin/env python
# coding:utf-8

MainAppList=("common", "trading", "scrapyt", "analyst", "backtest", "MT5")

####################################################################
###################### Default argParser ###########################
def default_arguments(argv, specificArgs=None):
    args = argv[1:] # args[0] = script path
    defaultArgs = ("--name", "--host", "--port", "--conf", "--log_level")
    if len(args) > 0:
        cmdArgs = {}
        i = 0 
        while i < len(argv)-1:
            if (args[i]).lower() in defaultArgs:
                cmdArgs[args[i].replace("--", '').lower()]=args[i+1]
            elif not specificArgs is None:
                if (args[i]).lower() in specificArgs:
                    cmdArgs[args[i].replace("--", '').lower()]=args[i+1]
                else:
                    return False, defaultArgs
            else:
                return False, defaultArgs
            i+=2
        if "port" in cmdArgs:
            cmdArgs["port"] = int(cmdArgs.get("port")) 
        if "log_level" in cmdArgs:
            cmdArgs["log_level"] = int(cmdArgs.get("log_level")) 
        return cmdArgs, defaultArgs
    return True, defaultArgs
###################### Default argParser ###########################
####################################################################
####################### Config Exception ###########################
class ConfigException(Exception):
    def __init__(self, message="Unusable configuration"):
        super().__init__(message)
####################### Config Exception ###########################
####################################################################
#################### Dynamic module import #########################
from importlib.util import spec_from_file_location, module_from_spec
def module_from_file(module_name, file_path):
    spec = spec_from_file_location(module_name, file_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
#################### Dynamic module import #########################
####################################################################
######################  Singleton class  ###########################
class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
######################  Singleton class  ###########################
####################################################################
#################### Singleton decorator  ##########################
def singleton(cls):
    instances = {}
    def getinstance(*args, **kwargs):
        for arg in args:
            print(arg)
        for key, arg in kwargs.items():
            print(key + "  " + arg)
        if cls not in instances:
            try:
                instances[cls] = cls(*args, **kwargs)
            except:
                try:
                    instances[cls] = cls(*args)
                except:
                    instances[cls] = cls()
        return instances[cls]
    return getinstance
#################### Singleton decorator  ##########################
####################################################################
#################### Threading decorator  ##########################
from threading import Thread
def threadIt(f):
    """ without handle (basically without return)"""
    def wrapper(*args, **kwargs):
        Thread(target=f, args=args, kwargs=kwargs).start()
        # with handle on thread :
        # thread.start()
        # return thread
    return wrapper
#################### Threading decorator  ##########################
####################################################################
################## caffeinate from process  ########################
@threadIt
def caffeinMe(pid):
    from common.Helpers.os_helpers import caffeinate
    caffeinate(pid=pid)
################## caffeinate from process  ########################
####################################################################
################ Get value or return default  ######################
def getOrDefault(value, default, key=None):
    if not key is None:
        try: 
            return value[key]
        except:
            return default      
    else:
        if not value is None:
            return value
        else:
            return default
def safeFloat(value):
    if not type(value) is float:
        return float(value)
    else:
        return None   
################ Get value or return default  ######################
####################################################################
################## Get unused port from OS #########################
from socket import socket
def getUnusedPort():
    sock = socket()
    # OS managed : return free port in the range [1024 - 65535]
    sock.bind(('', 0)) 
    port = sock.getsockname()[1]
    sock.close()
    return port 
################## Get unused port from OS #########################
####################################################################
############### Loads bineary pickle objects #######################
from pickle import loads, dump
def load_pickle_from_file(filePath):
    with open(filePath, "rb") as f:
            rawdata = f.read()
    return loads(rawdata)  
def dump_pickle_to_file(obj, filePath):
    with open(filePath, "wb") as f:
            dump(obj, f)
############### Loads binary pickle objects ########################
####################################################################
################  Kill process from inside #########################
from os import system as osSystem, name as osName
from multiprocessing import Process
def SIGKILL(pidList):
    osSystem("kill {0}".format(pidList))
def NT_SIGKILL(pidList):
    cmdLine = "taskkill "
    for pid in pidList:
        cmdLine += "/pid {0} ".format(pid)
    osSystem("{0}/F".format(cmdLine))
    
def ThreadQKill(pidList, TeleSocket=None, poweroff_msg=None, logger=None, logger_msg=None):
    if osName != 'nt':
        if not logger is None: logger.info(logger_msg)
        if not TeleSocket is None : TeleSocket.send_data(poweroff_msg)
        SIGKILL(pidList)
    else:
        if not logger is None: logger.info(logger_msg)
        if not TeleSocket is None : TeleSocket.send_data(poweroff_msg)
        NT_SIGKILL(pidList)
################  Kill process from inside #########################
####################################################################
#################  Kill async proc from inside #####################
async def asyncThreadQKill(pidList, logger=None, logger_msg=None, TeleSocket=None, poweroff_msg=None):
    if osName != 'nt':
        SigKill = Process(target=SIGKILL, args=(pidList,))
        SigKill.start()
        if not logger is None: await logger.asyncInfo(logger_msg)
        if not TeleSocket is None : await TeleSocket.send_data(poweroff_msg)
        SigKill.join()
    else:
        NT_SigKill = Process(target=NT_SIGKILL, args=(pidList,))
        NT_SigKill.start()
        if not logger is None: await logger.asyncInfo(logger_msg)
        if not TeleSocket is None : await TeleSocket.send_data(poweroff_msg)
        NT_SigKill.join()
#################  Kill async proc from inside #####################
####################################################################
############ Generate instance from dict or params #################
class DynamicInstance:
    """
    init with columns : \n
    x = PreDataFrame("ticker", "exchange")\n
    dataF = pd.DataFrame(x.__dict__)\n
    add function if necessary (every function name should start with "func*") : \n
    x = PreDataFrame("ticker", "exchange", "func0"=toto, "func1"=tata...)
    """
    def __init__(self, *args, **kwargs):  
        for x in args:
            self.__dict__.update({x:[]})
        self.__dict__.update(kwargs)
    def __call__(self, *args, **kwargs):  
        for x in args:
            self.__dict__.update({x:[]})
        self.__dict__.update(kwargs)
############ Generate instance from dict or params #################
####################################################################
################### Search for config files  #######################
from os import getcwd as osGetcwd, walk as osWalk, sep as osSep
from os.path import join as osPathJoin, exists as osPathExists
def load_config_files(root:str=osGetcwd(), dirFilters:list=MainAppList, extFilters:str=(".cfg")):
    config = {}
    if osPathExists(osPathJoin(root, "current.cfg")): config["current"] = osPathJoin(root, "current.cfg")
    for root, dirs, files in osWalk(root):
        dirs[:] = [d for d in dirs if d in dirFilters] 
        for filename in files:
            dirFolder = (root.split(osSep))[-1]
            if filename == "{0}{1}".format(dirFolder, extFilters):
                config[dirFolder] = "{0}".format(osPathJoin(root, filename))
    return config
################### Search for config files  #######################
####################################################################
################ Search for main parent config  ####################
from os.path import dirname as osPathDirname, basename as osBaseName
def default_config_file(filePath:str):
    root = osGetcwd()
    if not filePath.startswith(root):
        raise Exception("File path not in current working directory...")
    dirList = filePath.split(osSep)
    nb_app_related = 0
    for mainApp in MainAppList:
        for dir in dirList:
            if mainApp == dir:
                nb_app_related+=1
    if nb_app_related != 1:
        raise Exception("No main app directory in file path, expected directory : {0}".format(MainAppList))
    # find the most coherent config file from leaf to root
    parentDir = osPathDirname(filePath)
    while True:
        if osBaseName(parentDir) in MainAppList:
            break
        parentDir = osPathDirname(parentDir)
    return osBaseName(parentDir)
################ Search for main parent config  ####################
####################################################################
################### Check if receiver is ready #####################
def receiver_subscribes(star_que, subscriber):
    if "{0}_in".format(subscriber) in star_que.__dict__:
        return True
    else:
        return False
################### Check if receiver is ready #####################
####################################################################
############### Log error while launching process ##################
def init_logger(name="init_logger", config="common", config_path=None, log_level=None, only_logger=False, withOutConfigListener=False, enable_notifications=True):
    logger = None
    try:
        from common.config import Config
        from common.MyLogger.my_logger import MyLogger
        from common.Database.database import Database
        ignore_config_server = only_logger
        if withOutConfigListener:
            ignore_config_server = True
        if config_path is None: 
            config_path = load_config_files()[config]
        config = Config(config_file_path=config_path, name=name, ignore_config_server=ignore_config_server)
        if not log_level is None : logger = MyLogger(name, config, log_level=log_level, only_logger=only_logger, enable_notifications=enable_notifications)
        else : logger = MyLogger(name, config, only_logger=only_logger, enable_notifications=enable_notifications)  
    except:
        config = Config(name=name, ignore_config_server=ignore_config_server)
        try:
            currentConfig = osPathJoin(config_path)
        except: 
            currentConfig = osPathJoin(osGetcwd(), "current.cfg")
        config.merge(logger=logger, config_file_path=currentConfig)
        config.COMMON_FILE_PATH = currentConfig
        config.update(configPath=currentConfig)
        if not log_level is None : logger = MyLogger(name, config, log_level=log_level, only_logger=only_logger, enable_notifications=enable_notifications)
        else : logger = MyLogger(name, config, only_logger=only_logger, enable_notifications=enable_notifications)
    dblog = Database(logger, config)
    # late binding
    logger.DBlog = dblog 
    return config, logger
############### Log error while launching process ##################
####################################################################
################# Get standard formatted string ####################
from re import sub as reSub
def standardStr(input_string):
    cleaned_string = reSub(r'[^a-zA-Z0-9]+', '', input_string)
    return cleaned_string.lower()
################# Get standard formatted string ####################
####################################################################
###################### Get splitted params #########################
def getSplitedParam(line:str):
    """ return one line mulitple configuration parameters into list (from string)"""
    return (line.strip().replace(' ', '').replace(',', '|').replace(';', '|')).split('|')
###################### Get splitted params #########################
####################################################################
######################## TreeNode xPath ############################
class TreeNode:
    def __init__(self, node_name):
        self.node_name = node_name
        self.children = []
        self.parent = None
    def add_child(self, child_node):
        if not child_node in self.children:
            child_node.parent = self
            self.children.append(child_node)
    def drop_child(self, child_node):
        if child_node in self.children:
            child_node.parent = None
            self.children.remove(child_node)
    def drop_my_child(self):
        for child_node in self.children:
            child_node.parent = None
            self.children.remove(child_node)
    def root_add_child(self, path, child_node):
        node = self.get_node(path)
        if node:
            node.add_child(child_node)
    def root_drop_child(self, path):
        node = self.get_node(path)
        if node and node != self:
            parent = self.get_parent_node(node)
            if parent:
                parent.drop_child(node)
    def get_node(self, path):
        keys = path.split("/")
        if not keys[0]:
            return self
        first_key = keys[0]
        path = "/".join(keys[1:])
        for child in self.children:
            if child.node_name == first_key:
                return child.get_node(path)
        return None
    def get_parent_node(self, child_node):
        if child_node.parent:
            return child_node.parent
        return None
    def get_root_node(self):
        if self.get_parent_node(self):
            return self.get_parent_node(self).get_root_node()
        else:
            return self
######################## TreeNode xPath ############################
####################################################################
############## Get source file from running code ###################
from inspect import getsourcefile, currentframe, getsource
def getCurrentSourceCode():
    current_file_path = getsourcefile(currentframe())
    with open(current_file_path, 'r') as file:
        source_code = file.read()
    return str(source_code)
############## Get source file from running code ###################
####################################################################
############## Get source file from running code ###################
def getAlgo(algo):
    source_code = getsource(algo)
    return str(source_code)
############## Get source file from running code ###################
####################################################################
############# Get string content from common module ################
def load_module_string(root:str=osGetcwd(), dirFilters:list=['common'], extFilters:str=(".py")):
    module_str = {}
    for dir in dirFilters:
        for root, dirs, files in osWalk(osPathJoin(root, dir)):
            for filename in files:
                if filename.endswith(extFilters):
                    with open(osPathJoin(root, filename), 'r') as py_file:
                        module_str[filename.replace('py', '')] = py_file.read()
    return module_str
############# Get string content from common module ################
####################################################################
########### Class object to interact between loggers  ##############
from datetime import datetime
def create_logger_msg(name="DemoLogDict", msg="DemoLogDict message", args=None, levelname="INFO", levelno=20, pathname='/fullPath/MyScript.py', filename="MyScript.py", 
                      module="MyModule", exc_info=None, exc_text=None, stack_info=None, lineno=1, funcName="MyFunc",
                      # created=1660337120.1185641,
                      # msecs=118.56412887573242,
                      # relativeCreated=11734.132051467896, 
                      # asctime=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
                      thread=123456789, threadName="MainThread", 
                      processName="MainProcess", process=123456789 ):
    """
    {
        'name': 'DemoLogDict', 
        'msg': "DemoLogDict message", 
        'args': None, 
        'levelname': 'INFO', 
        'levelno': 20, 
        'pathname': '/fullPath/MyScript.py', 
        'filename': 'MyScript.py', 
        'module': 'MyModule', 
        'exc_info': None, 
        'exc_text': None, 
        'stack_info': None, 
        'lineno': 1, 
        'funcName': 'pyFunc', 
        'created': 1660337120.1185641, 
        'msecs': 118.56412887573242, 
        'relativeCreated': 11734.132051467896, 
        'thread': 123456789, 
        'threadName': 'Thread-7' or 'MainThread', 
        'processName': 'MainProcess', 
        'process': 123456789, 
        'asctime': '2022-08-12 22:45:20'
    }
    """
    logger_dict = {}
    
    now = datetime.utcnow()
    created=(now - datetime(1970, 1, 1)).total_seconds()
    msecs=(created%1)*100
    asctime=now.strftime("%Y-%m-%d %H:%M:%S")

    logger_dict['name'] = name 
    logger_dict['msg'] = msg
    logger_dict['args'] = args
    logger_dict['levelname'] = levelname
    logger_dict['levelno'] = levelno
    logger_dict['pathname'] = pathname
    logger_dict['filename'] = filename
    logger_dict['module'] = module
    logger_dict['exc_info'] = exc_info
    logger_dict['exc_text'] = exc_text
    logger_dict['stack_info'] = stack_info
    logger_dict['lineno'] = lineno
    logger_dict['funcName'] = funcName
    logger_dict['created'] = created
    logger_dict['msecs'] = msecs
    logger_dict['thread'] = thread
    logger_dict['threadName'] = threadName
    logger_dict['processName'] = processName
    logger_dict['process'] = process
    logger_dict['asctime'] = asctime
    logger_dict['relativeCreated'] = (datetime.utcnow() - now).total_seconds()
    return logger_dict
########### Class object to interact between loggers  ##############
####################################################################