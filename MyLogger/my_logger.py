#!/usr/bin/env python
# coding:utf-8

import logging
from os import mkdir as osMkdir, getcwd as osGetcwd
from os.path import join as osPathJoin, normcase as osPathNormcase
from time import sleep
from logging.handlers import RotatingFileHandler
from genericpath import exists
from collections import deque
from threading import Thread

# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.Notifie.notifie import Notifie
from common.Helpers.helpers import getUnusedPort
from common.Helpers.os_helpers import is_process_running, launch_notif_server, launch_log_server, launch_teleremote_server
from common.Helpers.network_helpers import is_service_listen, MySocketObj
from common.MyLogger.my_cwe312_url import my_cwe312_url, load_sensitive_data



class DEFAULT_LOGGER_FORMAT:
    LOG="%(asctime)s.%(msecs)03d %(levelname)-8s %(filename)-23s %(funcName)-20s %(lineno)-4s  %(message)s"
    DATEFMT="%Y-%m-%d %H:%M:%S"
    LOG_SERVER="%(asctime)s.%(msecs)03d %(name)-23s %(levelname)-8s %(filename)-23s %(funcName)-20s %(lineno)-4s  %(message)s"

####################################################################
######## Patch to get right filename and line in logs ##############

#https://stackoverflow.com/questions/19615876/showing-the-right-funcname-when-wrapping-logger-functionality-in-a-custom-class/58532960#58532960

import sys, io, traceback
if hasattr(sys, '_getframe'): currentframe = lambda: sys._getframe(3)
# done filching
#
# _srcfile is used when walking the stack to check when we've got the first
# caller stack frame.
#
_srcfile = osPathNormcase(currentframe.__code__.co_filename)
def findCallerPatch(stack_info=False, stacklevel=1):
        """
        Find the stack frame of the caller so that we can note the source
        file name, line number and function name.
        """
        f = currentframe()
        #On some versions of IronPython, currentframe() returns None if
        #IronPython isn't run with -X:Frames.
        if f is not None:
            f = f.f_back
        orig_f = f
        while f and stacklevel > 1:
            f = f.f_back
            stacklevel -= 1
        if not f:
            f = orig_f
        rv = "(unknown file)", 0, "(unknown function)", None
        while hasattr(f, "f_code"):
            co = f.f_code
            filename = osPathNormcase(co.co_filename)
            if filename == _srcfile:
                f = f.f_back
                continue
            sinfo = None
            if stack_info:
                sio = io.StringIO()
                sio.write('Stack (most recent call last):\n')
                traceback.print_stack(f, file=sio)
                sinfo = sio.getvalue()
                if sinfo[-1] == '\n':
                    sinfo = sinfo[:-1]
                sio.close()
            rv = (co.co_filename, f.f_lineno, co.co_name, sinfo)
            break
        return rv
######## Patch to get right filename and line in logs ##############
####################################################################
##### Patch to get record formatted on error and put in in DB ######
# Not Good but it's works....
#              logger __init__.py file modified 
#     directy in Logging / __init__.py => class Logger / method Error...
#     directy in Logging / __init__.py => class Logger  / method Warning...
#     directy in Logging / __init__.py => class Logger  / method Critical...
# Not Good but it's works....
##### Patch to get record formatted on error and put in in DB ######
####################################################################


class MyLogger:

    Logger = None
    Notification = None
    NotifQ = None
    Context = None
    DBlog = None
    def __init__(self, name, config:Config, enable_notifications:bool=True, log_server:bool=True, server_notification:bool=True, \
                                        notify_from_log_server:bool=True, \
                                        start_telecommand:bool=True, \
                                        only_logger:bool=False, \
                                        log_level:int=logging.DEBUG, log_dir:str=osPathJoin(osGetcwd(), "logs")):

        # Logger setup
        if not exists(log_dir):
            osMkdir(log_dir)
        
        logging.basicConfig(
        handlers=[logging.StreamHandler(), logging.handlers.SocketHandler("127.0.0.1", logging.handlers.DEFAULT_TCP_LOGGING_PORT)] if not only_logger else [logging.StreamHandler()],                 
        encoding="utf-8", 
        format=DEFAULT_LOGGER_FORMAT.LOG, 
        datefmt=DEFAULT_LOGGER_FORMAT.DATEFMT, 
        level=log_level
        )
        
        # needed for multiprocess...
        self.Logger = logging.getLogger(name)
        fileHandler = RotatingFileHandler("{0}.log".format(osPathJoin(log_dir, name)), maxBytes=2097152, backupCount=10)       
        self.Logger.addHandler(fileHandler)
        fileHandlerformatter = logging.Formatter(DEFAULT_LOGGER_FORMAT.LOG)
        fileHandler.setFormatter(fileHandlerformatter)

        self.config = config
        # DO patch to get right filename of log
        self.Logger.findCaller = findCallerPatch
        # bind config sensitive datas
        self.sensitive_data = load_sensitive_data(config)
        # AppDB
        self.appDB = None

        # notification handler Logger Module modified !
        self.enable_notifications = enable_notifications
        self.server_notification = server_notification
        self.notify_from_log_server = notify_from_log_server

        # recv loop for server notifs
        self.loop = False

        if log_server and (not only_logger):
            log_server = "log_server"
            # check if log_server server already run
            if not is_process_running(log_server):
                _ = launch_log_server(curDir=osGetcwd())
                while not is_service_listen(server=self.config.LG_IP, port=logging.handlers.DEFAULT_TCP_LOGGING_PORT):
                    sleep(self.config.MAIN_QUEUE_BEAT)
                self.Logger.info("Main Logger : Main log_server is starting.. .  . ")

        if enable_notifications and (not only_logger):
            if server_notification:
                notif_server = "notif_server"
                # check if notification server already run
                if not is_process_running(notif_server):
                    self.config.update(section="COMMON", configPath=config.COMMON_FILE_PATH, params={"NT_PORT":str(getUnusedPort())})
                    _ = launch_notif_server(curDir=osGetcwd(), conf=self.config.COMMON_FILE_PATH, port=self.config.NT_PORT)
                    while not is_service_listen(server=self.config.NT_IP, port=self.config.NT_PORT):
                        sleep(self.config.MAIN_QUEUE_BEAT)
                    self.Logger.info("Main Notifier : Main notifs_server is starting.. .  . ")

        if start_telecommand and (not only_logger):
            tele_remote = "tele_remote"
            # check if tele_remote server already run
            if not is_process_running(tele_remote):
                self.config.update(section="COMMON", configPath=config.COMMON_FILE_PATH, params={"TB_PORT":str(getUnusedPort())})
                _ = launch_teleremote_server(curDir=osGetcwd(), conf=self.config.COMMON_FILE_PATH, port=self.config.TB_PORT)
                while not is_service_listen(server=self.config.TB_IP, port=self.config.TB_PORT):
                    sleep(self.config.MAIN_QUEUE_BEAT)
                self.Logger.info("Main Telecommand : Main Telecommand is starting.. .  . ")             
                
        if notify_from_log_server and (not only_logger):
            self.NotifQ = deque() ; self.loop = True
            Thread(target=self.notifie_from_server, daemon=True).start()
            self.notifie = self.server_notifie
            
        if (not notify_from_log_server) or only_logger:
            if enable_notifications:
                self.Notification = Notifie(enable_notifications)
                self.notifie = self.local_notifie


    def local_notifie(self, level, message):
        if level == "error" or level == "critical":
            self.Notification.send_notification(message, tag=["telebot", "desktop", "sms"])
        elif level == "trade" or level == "warning":
            self.Notification.send_notification(message, tag=["telebot", "desktop"])
        elif level == "trade":
            self.Notification.send_notification(message, tag=["telebot"])

    def server_notifie(self, level, message):
        if level == "error" or level == "critical":
            self.NotifQ.append([message, None, ["telebot", "desktop", "sms"]])
        elif level == "trade" or level == "warning":
            self.NotifQ.append([message, None, ["telebot", "desktop"]])
        elif level == "trade":
            self.NotifQ.append([message, None, ["telebot"]])
    
    def notifie(self, level, message):
        # monkey patch regarding local_notif or server_notif  
        pass

    def ends_srv_notif_loop(self):
        self.loop = False

    def notifie_from_server(self):
        def treat_notif(NotifsSocket:MySocketObj):
            msg = ""
            while self.loop: 
                sleep(self.config.MAIN_QUEUE_BEAT)
                if len(self.NotifQ) > 0:
                    msg = self.NotifQ.popleft()
                    try:
                        NotifsSocket.send_data(msg)
                    except Exception as e:
                        self.Logger.info(e)
                        
        with MySocketObj().make_connection(server=self.config.NT_IP, port=int(self.config.NT_PORT)) as NotifsSocket:
            if not NotifsSocket.context is None:
                self.Logger.info("Notifs client SSL : connection established with encryption: '{0}' to '{1}' destport '{2}' srcport '{3}'".format(NotifsSocket.version(), self.config.NT_URI, self.config.NT_PORT, NotifsSocket.getsockname()[1]))
            else:
                self.Logger.info("Notifs client TCP : connection established to '{0}' destport '{1}' srcport '{2}'".format(self.config.NT_IP, self.config.NT_PORT, NotifsSocket.getsockname()[1]))
            treat_notif(NotifsSocket)

    def log(self, message, level="debug", notification=True):
        if level == "debug":
            self.Logger.debug(message)
        elif level == "info":
            self.Logger.info(message)
        elif level == "warning":
            rec = self.Logger.warning(message)
            self.DBlog.db_error(rec.asctime + str(rec.msecs).replace('.', '')[:3], \
                                    rec.levelname, rec.filename, rec.funcName, rec.lineno, rec.msg)
        elif level == "error":          
            rec = self.Logger.error(message)
            self.DBlog.db_error(rec.asctime + str(rec.msecs).replace('.', '')[:3], \
                                    rec.levelname, rec.filename, rec.funcName, rec.lineno, rec.msg)
        elif level == "critical":          
            rec = self.Logger.critical(message)
            self.DBlog.db_error(rec.asctime + str(rec.msecs).replace('.', '')[:3], \
                                    rec.levelname, rec.filename, rec.funcName, rec.lineno, rec.msg)
            # Should stop program ?!
        elif level == "trade":
            log_msg = message.pop("log_msg")
            self.Logger.info(log_msg)
            self.DBlog.db_order(**message)
            message = log_msg
        elif level == "stream":
            self.DBlog.db_fix_message(**message)
            self.Logger.info(message)
        elif level == "dberror":
            self.Logger.error(message)
        elif level == "sqlinfo":
            rec = self.Logger.error(message)
            self.DBlog.db_error(rec.asctime + str(rec.msecs).replace('.', '')[:3], \
                                    rec.levelname, rec.filename, rec.funcName, rec.lineno, rec.msg) 


        if self.enable_notifications and notification:
            self.notifie(level, message)

    def debug(self, message, notification=False):
        self.log(message, "debug", notification)
    def info(self, message, notification=True):
        self.log(message, "info", notification)
    def warning(self, message, notification=True):
        self.log(message, "warning", notification)
    def error(self, message, notification=True):
        self.log(message, "error", notification)
    def critical(self, message, notification=True):
        self.log(message, "critical", notification)

    def logon(self, message, notification=True):
        message = my_cwe312_url(message, self.sensitive_data)
        self.log(message, "trade", notification)
    def stream(self, message, notification=True):
        self.log(message, "stream", notification)
    def trade(self, message, notification=True):
        self.log(message, "trade", notification)

    def dberror(self, message, notification=True):
        self.log(message, "dberror", notification)
    def sqlinfo(self, message, notification=True):
        self.log(message, "sqlinfo", notification)

    async def asyncLog(self, message, level="debug", notification=True):
        if level == "debug":
            self.Logger.debug(message)
        elif level == "info":
            self.Logger.info(message)
        elif level == "warning":
            rec = self.Logger.warning(message)
            self.DBlog.db_error(rec.asctime + str(rec.msecs).replace('.', '')[:3], \
                                    rec.levelname, rec.filename, rec.funcName, rec.lineno, rec.msg)
        elif level == "error":          
            rec = self.Logger.error(message)
            self.DBlog.db_error(rec.asctime + str(rec.msecs).replace('.', '')[:3], \
                                    rec.levelname, rec.filename, rec.funcName, rec.lineno, rec.msg)
        elif level == "critical":          
            rec = self.Logger.critical(message)
            self.DBlog.db_error(rec.asctime + str(rec.msecs).replace('.', '')[:3], \
                                    rec.levelname, rec.filename, rec.funcName, rec.lineno, rec.msg)
            # Should stop program ?!
        elif level == "trade":
            log_msg = message.pop("log_msg")
            self.Logger.info(log_msg)
            self.DBlog.db_order(**message)
            message = log_msg
        elif level == "stream":
            self.Logger.info(message)
            self.DBlog.db_fix_message(message)
        elif level == "dberror":
            self.Logger.error(message)
        elif level == "sqlinfo":
            rec = self.Logger.error(message)
            self.DBlog.db_error(rec.asctime + str(rec.msecs).replace('.', '')[:3], \
                                    rec.levelname, rec.filename, rec.funcName, rec.lineno, rec.msg) 


        if self.enable_notifications and notification:
            self.notifie(level, message)

    async def asyncDebug(self, message, notification=False):
        await self.asyncLog(message, "debug", notification)
    async def asyncInfo(self, message, notification=True):
        await self.asyncLog(message, "info", notification)
    async def asyncWarning(self, message, notification=True):
        await self.asyncLog(message, "warning", notification)
    async def asyncError(self, message, notification=True):
        await self.asyncLog(message, "error", notification)
    async def asyncCritical(self, message, notification=True):
        await self.asyncLog(message, "critical", notification)
    async def asyncDberror(self, message, notification=True):
        await self.asyncLog(message, "dberror", notification)
    async def asyncSqlinfo(self, message, notification=True):
        await self.asyncLog(message, "sqlinfo", notification)

#================================================================
if __name__ == "__main__":
    from common.config import Config
    from common.Database.database import Database
    name = "my_logger"
    #config = Config()
    config = Config(config_file_path='trading/trading.cfg', name=name)
    logger = MyLogger(name=name, config=config)
    dblog = Database(logger=logger, config=config)
    # late binding
    logger.DBlog = dblog

    for x in range(10):
        logger.warning("Warning send from logger!")
        logger.error("Error send from logger!")
    logger.info("Info send from logger!")
    logger.debug("Debug send from logger!")

