#!/usr/bin/env python
# coding:utf-8

import platform
from subprocess import Popen, DEVNULL, PIPE

DEBUG = False

####################################################################
####################### Config Exception ###########################
from os import environ as osEnviron
def get_shell():
    return osEnviron.get("SHELL")
####################### Config Exception ###########################
####################################################################
############## Prevent the system from idle sleeping ###############
from os import name as osName
def caffeinate(pid=None, cmd=None, check=False, getExe=False):
    if check:
        return "caffein"
    if osName != 'nt':
        if not pid is None:
            start_independant_process("caffein", "-w", str(pid))
        elif getExe:
            return "caffeinate"
        else:
            return "caffeinate -i {0}".format(cmd)
    else:
        # windows, caffeine software have to be installed
        try:
            if not pid is None:
                keeps_network_activity = "-allowss"
                start_independant_process("caffein", "-w", keeps_network_activity, "&&", cmd)
            elif getExe:
                return "caffeine"
            else:
                raise("Caffeine : windows pid caffeination is not yet implemented...")                
                #return "caffeinate -i {0}".format(cmd)
        except Exception as e:
            raise("Caffeinate : error while trying to caffeine windows : {0}".format(e)) 
############## Prevent the system from idle sleeping ###############
####################################################################
########## Check if process / service is running by name ###########
from psutil import process_iter, NoSuchProcess, AccessDenied, ZombieProcess
def is_process_running(cmdlinePatt:str, processName:str="python", argvPatt=None, getPid:bool=False):
    for proc in process_iter():
        try:
            #file_path = osPathJoin(osPathDirname(__file__), "is_process_running.log")
            #with open(file_path, 'a') as log:
            #    log.write(str(proc.name()) + "      =>       " + str(proc.cmdline())+"\n\n\n-----------------------------------------------------------------------\n")
            if processName.lower() in proc.name().lower():
                if len(proc.cmdline()) >= 14:
                    # launched from vscode...
                    cmdLineList = [cmdLine.lower() for cmdLine in proc.cmdline()]
                    if any(cmdlinePatt.lower() in arg for arg in cmdLineList):
                        if not argvPatt is None:
                            if any(argvPatt.lower() in arg for arg in cmdLineList):
                                if getPid:return True, proc.pid
                                else:return True
                        else:
                            if getPid: return True, proc.pid
                            else:return True
                if cmdlinePatt.lower() in proc.cmdline()[1].lower():
                    if not argvPatt is None:
                        if argvPatt.lower() in proc.cmdline()[2].lower():
                            if getPid:return True, proc.pid
                            else:return True
                    else:
                        if getPid: return True, proc.pid
                        else:return True
        except (NoSuchProcess, AccessDenied, ZombieProcess) as e:
            #file_path = osPathJoin(osPathDirname(__file__), "is_process_running_err.log")
            #with open(file_path, 'a') as log:
            #    log.write(str(e)+"\n\n\n-----------------------------------------------------------------------\n")
            pass
    if getPid:return False, -1
    else:return False
########## Check if process / service is running by name ###########
####################################################################
########## Check if process / service is running by name ###########
def nb_process_running(cmdlinePatt:str, processName:str="python", argvPatt=None, getPid:bool=False):
    # function only used while scripts launched via vscode...
    nb_proc = 0 ; pidLits = []
    for proc in process_iter():
        try:
            if processName.lower() in proc.name().lower():
                cmdLineList = [cmdLine.lower() for cmdLine in proc.cmdline()]
                if any(cmdlinePatt.lower() in arg for arg in cmdLineList):
                    if not argvPatt is None:
                        if any(argvPatt.lower() in arg for arg in cmdLineList):
                            if getPid:pidLits.append(proc.pid)
                            nb_proc+=1
                    else:
                        if getPid:pidLits.append(proc.pid)
                        nb_proc+=1
        except (NoSuchProcess, AccessDenied, ZombieProcess) as e:
            pass
    if getPid:return nb_proc, pidLits
    else:return nb_proc  
########## Check if process / service is running by name ###########
####################################################################
########### Class object to interact between loggers  ##############
def create_loggers_msg(name, msg, levelname, levelno, args=None, ):
    """
    #{'name': 'ThreadQs', 'msg': "StarQs : message id '304de7ba-51be-4211-98e9-a00456e09d09' received from 'SwissquoteAPI' to 'SwissQ'", 
    # 'args': None, 'levelname': 'INFO', 'levelno': 20, 'pathname': '/Users/imac/Desktop/Scrapy/common/ThreadQs/thread_Qs.py', 'filename': 'thread_Qs.py', 
    # 'module': 'thread_Qs', 'exc_info': None, 'exc_text': None, 'stack_info': None, 'lineno': 161, 'funcName': 'starQ_msg_in', 'created': 1660337120.1185641, 
    # 'msecs': 118.56412887573242, 'relativeCreated': 11734.132051467896, 'thread': 123145613979648, 'threadName': 'Thread-7', 'processName': 'MainProcess', 
    # 'process': 1265, 'asctime': '2022-08-12 22:45:20'}
    """
    logger_dict = {}
    logger_dict['name'] = name
    logger_dict['msg'] = msg
    logger_dict['levelname'] = levelname
    logger_dict['levelno'] = levelno
    logger_dict['levelno'] = levelno
    logger_dict['levelno'] = levelno
########### Class object to interact between loggers  ##############
####################################################################
############# Get current script executed directory ################
from os import getcwd as osGetcwd
from os.path import realpath as osPathRealpath, join as osPathJoin, dirname as osPathDirname
def get_executed_script_dir(file_path):
    return osPathJoin(osGetcwd(),osPathDirname(osPathRealpath(file_path)))
############# Get current script executed directory ################
####################################################################
############# Get current script executed directory ################
def get_real_path(file_path):
    return osPathRealpath(file_path)
############# Get current script executed directory ################
####################################################################


####################################################################
# /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\  #
#                                                                  #
#                   only used for debugging !!!                    #
#                                                                  #
# /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\  #
####################################################################

if DEBUG:
    # relative import
    from sys import path;path.extend("..")
    from common.Helpers.___os_fork_debug import start_independant_process, launch_log_server, launch_telecommand_server, launch_notif_server, launch_independant_process

####################################################################
# /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\  #
#                                                                  #
#                   only used for debugging !!!                    #
#                                                                  #
# /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\  #
####################################################################

else:
    NotPython = "!=python"
####################################################################
############ Start independant process (not a child) ###############
    if osName != 'nt':
        from os import setsid as osSetsid
    from sys import version_info, executable
# https://stackoverflow.com/questions/13243807/popen-waiting-for-child-process-even-when-the-immediate-child-has-terminated/13256908#13256908
    def start_independant_process(command:str, *argv, **kwargs):
        # set system/version dependent "start_new_session" analogs
        # kwargs = {}
        if platform.system() == 'Windows':
            # from msdn [1]
            CREATE_NEW_PROCESS_GROUP = 0x00000200  # note: could get it from subprocess
            DETACHED_PROCESS = 0x00000008          # 0x8 | 0x200 == 0x208
            kwargs.update(creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP)  
            stdin=PIPE; stdout=PIPE; stderr=PIPE
        elif version_info < (3, 2):  # assume posix
            kwargs.update(preexec_fn=osSetsid)
            stdin=DEVNULL; stdout=DEVNULL; stderr=DEVNULL
        else:  # Python 3.2+ and Unix
            kwargs.update(start_new_session=True)
            stdin=DEVNULL; stdout=DEVNULL; stderr=DEVNULL

        #python env : executable 
        if command == caffeinate(check=True): 
            cmdAndArgs = [caffeinate(getExe=True)] ; argv = ("-i", ) + argv
        elif NotPython in argv:
            argv = [item for item in argv if item != NotPython]
            cmdAndArgs = [command]
        else:
            cmdAndArgs = [executable, command]

        #cmdAndArgs = [executable, command]
        if not argv is None:
            for arg in argv:
                cmdAndArgs.append(arg)

        p = Popen(args=cmdAndArgs, stdin=stdin, stdout=stdout, stderr=stderr, **kwargs)
        assert not p.poll()
############ Start independant process (not a child) ###############
####################################################################
############### Launch LOG server if not exist... ##################
    def launch_log_server(curDir:str=osGetcwd(), externalCall:str="True"):
        cmdline = "{0}".format(osPathJoin(curDir, "common", "MyLogger", "log_server.py"))
        return start_independant_process(cmdline, externalCall)
############### Launch LOG server if not exist... ##################
####################################################################
########### Launch TELECOMMAND server if not exist... ##############
    def launch_telecommand_server(curDir:str=osGetcwd(), path_conf:str=None, externalCall:str="True"):
        cmdline = "{0}".format(osPathJoin(curDir, "common", "TeleRemote", "tele_remote.py"))
        if not path_conf is None:
            return start_independant_process(cmdline, path_conf, externalCall)
        else:
            return start_independant_process(cmdline, externalCall)
########### Launch TELECOMMAND server if not exist... ##############
####################################################################
############## Launch NOTIF server if not exist... #################
    def launch_notif_server(curDir:str=osGetcwd(), path_conf:str=None, port:str=None):
        cmdline = "{0}".format(osPathJoin(curDir, "common", "Notifie", "notif_server.py"))
        if not path_conf is None and not port is None:
            return start_independant_process(cmdline, path_conf, port)
        elif not path_conf is None:
            return start_independant_process(cmdline, path_conf)
        else:
            return start_independant_process(cmdline)
############## Launch NOTIF server if not exist... #################
####################################################################
############## Launch Config server if not exist... #################
    def launch_config_server(port:str, path_conf:str=None, curDir:str=osGetcwd()):
        cmdline = "{0}".format(osPathJoin(curDir, "common", "config_server.py"))
        if not path_conf is None:
            return start_independant_process(cmdline, port, path_conf)
        else:
            return start_independant_process(cmdline, port)
############## Launch Config server if not exist... #################
####################################################################
############# Launch ARBITRE server if not exist... ################
    def launch_arbitre(name:str, curDir:str=osGetcwd(), path_conf:str=None, arbitreScript:str="arbitre.py"):
        if not arbitreScript.endswith(".py"): arbitreScript+=".py"
        cmdline = "{0}".format(osPathJoin(curDir, "trading", "Arbitre", arbitreScript))
        if not path_conf is None:
            return start_independant_process(cmdline, name, path_conf)
        else:
            return start_independant_process(cmdline)
############# Launch ARBITRE server if not exist... ################
####################################################################
############# Launch ANALYST server if not exist... ################
    def launch_analyst(curDir:str=osGetcwd(), path_conf:str=None, analystScript:str="analyst_server.py"):
        if not analystScript.endswith(".py"): analystScript+=".py"
        cmdline = "{0}".format(osPathJoin(curDir, "analyst", analystScript))
        if not path_conf is None:
            return start_independant_process(cmdline, path_conf)
        else:
            return start_independant_process(cmdline)
############# Launch ANALYST server if not exist... ################
####################################################################
############# Launch JUPYTER server if not exist... ################
    def launch_JUPYTER_server(jp_env, jp_server="127.0.0.1", jp_port=8888):
        if jp_server != "127.0.0.1":
            # paramiko
            raise("Running jupyter server on a remote machine is not implemented yet... ")
        else:
            if osName != 'nt':
                cmdline = "source"
                args = [NotPython, osPathJoin(jp_env, "bin", "activate"), "&&", "jupyter server", "--notebook-dir={0}".format(jp_env), "--port={0}".format(jp_port)]         
            else:
                cmdline = osPathJoin(jp_env, "Scripts", "activate.bat")
                args = [NotPython, "&&", "jupyter server", "--notebook-dir={0}".format(jp_env), "--port={0}".format(jp_port)]
            return start_independant_process(cmdline, *args)            
############# Launch JUPYTER server if not exist... ################
####################################################################
########### Launch independant server (if not exist)  ##############
    def launch_independant_process(path_from_cwd, file, param=None, curDir=osGetcwd()):
        cmdline = "{0}".format(osPathJoin(curDir, path_from_cwd, file))         
        if not param is None:
            return start_independant_process(cmdline, param)
        else:
            return start_independant_process(cmdline)
########### Launch independant server (if not exist)  ##############
####################################################################
############# Launch TCP-DB server if not exist... #################
    from os import sep as osSep
    def launch_TCP_database(curDir:str=osGetcwd(), DBScript:str="database.py", name:str=None, conf:str=None, JsonDump=None, DBScriptPath:str=None):
        if not DBScript.endswith(".py"): DBScript+=".py"
        if osSep in conf:
            from common.Helpers.helpers import load_config_files
            x = load_config_files()
            for key, val in x.items(): 
                if val == conf: conf = key ; break
        cmdline = "{0}".format(osPathJoin(curDir, "common", "Database", DBScript))
        if not DBScriptPath is None:
            cmdline = "{0}".format(DBScriptPath)
        if not conf is None:
            return start_independant_process(cmdline, name, conf, JsonDump)
        else:
            return start_independant_process(cmdline, name, conf)
############# Launch TCP-DB server if not exist... #################
####################################################################
############# Exec function on SIGKILL, SIGTERM... #################
from signal import signal, SIGTERM, SIGTERM, SIGKILL, SIGQUIT
def cleanup_function(cleanup_function, *args, **kwargs):
    if osName != 'nt':
        def signal_handler(signum, frame):
            cleanup_function(*args, **kwargs)
        signal(SIGTERM, signal_handler)
        signal(SIGTERM, signal_handler)
        signal(SIGKILL, signal_handler)
        signal(SIGQUIT, signal_handler)
    else:
        from win32api import SetConsoleCtrlHandler
        def win32_signal_handler(signum, frame):
            cleanup_function()
        SetConsoleCtrlHandler(win32_signal_handler, True)
############# Exec function on SIGKILL, SIGTERM... #################
####################################################################
