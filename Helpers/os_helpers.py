#!/usr/bin/env python
# coding:utf-8

from platform import system as platformSystem
from subprocess import Popen, DEVNULL, PIPE



####################################################################
################ Config to Environment variable ####################
from os import environ as osEnviron
from json import loads as jsonLoads, dumps as jsonDumps
def setEnv(key, val, envSection="AMATRIXQS"):
        fixedConf = osEnviron.get(envSection)
        if fixedConf: osConf = jsonLoads(fixedConf)
        else: osConf = {}
        osConf[key] = val
        if osName != "nt":
            print('export {0}={1}'.format(envSection, jsonDumps(osConf)))
        else:
            osEnviron[envSection] = jsonDumps(osConf)
def getEnv(key, envSection="AMATRIXQS"):
    fixedConf = osEnviron.get(envSection)
    if fixedConf:
        osConf = jsonLoads(fixedConf)
        return osConf[key]
    else:
        return None
################ Config to Environment variable ####################
####################################################################
####################### Config Exception ###########################
def get_shell():
    return osEnviron.get("SHELL")
####################### Config Exception ###########################
####################################################################
####################### Get conf section ###########################
from os.path import basename as osPathBasename
def getConfSec(conf, cmdline):
    try:
        from common.Helpers.helpers import load_config_files
        if not conf is None:
            if osSep in conf:
                conf = ({value: key for key, value in load_config_files().items()}).get(conf)
        #else:
        #    conf = load_config_files(dirFilters= osPathBasename(osPathDirname(cmdline)))
        #    conf.pop("current", None)
    except Exception as e:
        raise(e)
    return conf
####################### Get conf section ###########################
####################################################################
####################### Get conf section ###########################
def load_default_args(port:str=None, conf:str=None, host:str=None, name:str=None, log_level:str=None):
    args = []
    if not port is None: args+= ["--port", str(port)]
    if not conf is None: args+= ["--conf", str(conf)]
    if not name is None: args+= ["--name", str(name)]
    if not host is None: args+= ["--host", str(host)]
    if not log_level is None: args+= ["--log_level", str(log_level)]
    return args
####################### Get conf section ###########################
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
########## Check if process/service is running by name #############
from psutil import process_iter as psutilProcess_iter, Process as psutilProcess, NoSuchProcess as psutilNoSuchProcess, \
                   AccessDenied as psutilAccessDenied, ZombieProcess as psutilZombieProcess
def is_process_running(cmdlinePatt:str, processName:str="python", argvPatt=None, getPid:bool=False):
    for proc in psutilProcess_iter():
        try:
            #file_path = osPathJoin(osPathDirname(__file__), "is_process_running.log")
            #with open(file_path, 'a') as log:
            #    log.write(str(proc.name()) + "      =>       " + str(proc.cmdline())+"\n\n\n-----------------------------------------------------------------------\n")
            if processName.lower() in proc.name().lower():
                cmdLineList = [cmdLine.lower() for cmdLine in proc.cmdline()]
                if any(cmdlinePatt.lower() in arg for arg in cmdLineList):
                    if not argvPatt is None:
                        if argvPatt.lower() in " ".join(cmdLineList):
                            if getPid:return True, proc.pid
                            else:return True
                    else:
                        if getPid: return True, proc.pid
                        else:return True
        except (psutilNoSuchProcess, psutilAccessDenied, psutilZombieProcess) as e:
            #file_path = osPathJoin(osPathDirname(__file__), "is_process_running_err.log")
            #with open(file_path, 'a') as log:
            #    log.write(str(e)+"\n\n\n-----------------------------------------------------------------------\n")
            pass
    if getPid:return False, -1
    else:return False
########## Check if process/service is running by name #############
####################################################################
############### Count nb process currently running #################
def nb_process_running(cmdlinePatt:str, processName:str="python", argvPatt=None, getPid:bool=False):
    # function only used while scripts launched via vscode...
    nb_proc = 0 ; pidLits = []
    for proc in psutilProcess_iter():
        try:
            if processName.lower() in proc.name().lower():
                cmdLineList = [cmdLine.lower() for cmdLine in proc.cmdline()]
                if any(cmdlinePatt.lower() in arg for arg in cmdLineList):
                    if not argvPatt is None:
                        if argvPatt.lower() in " ".join(cmdLineList):
                            if getPid:pidLits.append(proc.pid)
                            nb_proc+=1
                    else:
                        if getPid:pidLits.append(proc.pid)
                        nb_proc+=1
        except (psutilNoSuchProcess, psutilAccessDenied, psutilZombieProcess) as e:
            pass
    if getPid:return nb_proc, pidLits
    else:return nb_proc  
############### Count nb process currently running #################
####################################################################
################ Get command line and args from PID ################
def get_command_line_from_pid(pid):
    try:
        process = psutilProcess(pid)
        command_line = process.cmdline()
        return command_line
    except psutilNoSuchProcess:
        return None
################ Get command line and args from PID ################
####################################################################
################# Get PID arborescence in a list ###################
def get_linked_PID(parent_PID):
    linkedProc = psutilProcess(parent_PID)
    procChilds = linkedProc.children(recursive=True)
    if osName != 'nt':
        pidList = str(parent_PID)
        for procChild in procChilds:
            pidList+=" "+str(procChild.pid)
    else:
        pidList = [int(parent_PID)]
        if not procChilds is None:
            for procChild in procChilds:
                pidList.append(procChild.pid)
    return pidList
################# Get PID arborescence in a list ###################
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
    if platformSystem() == 'Windows':
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
############## Launch CONFIG server if not exist... ################
def launch_config_server(port:str, conf:str=None, host:str=None, name:str=None, log_level:str=None, curDir:str=osGetcwd()):
    cmdline = "{0}".format(osPathJoin(curDir, "common", "config_server.py"))
    conf = getConfSec(conf=conf, cmdline=cmdline)
    args = load_default_args(port=port, conf=conf, host=host, name=name, log_level=log_level)
    return start_independant_process(cmdline, *args)
############## Launch CONFIG server if not exist... ################
####################################################################
############## Launch NOTIF server if not exist... #################
def launch_notif_server(curDir:str=osGetcwd(), port:str=None, conf:str=None, host:str=None, name:str=None, log_level:str=None):
    cmdline = "{0}".format(osPathJoin(curDir, "common", "Notifie", "notif_server.py"))
    conf = getConfSec(conf=conf, cmdline=cmdline)
    args = load_default_args(port=port, conf=conf, host=host, name=name, log_level=log_level)
    if len(args) > 0:
        return start_independant_process(cmdline, *args)
    else:
        return start_independant_process(cmdline)
############## Launch NOTIF server if not exist... #################
####################################################################
############### Launch LOG server if not exist... ##################
def launch_log_server(curDir:str=osGetcwd(), port:str=None, conf:str=None, host:str=None, name:str=None, log_level:str=None):
    cmdline = "{0}".format(osPathJoin(curDir, "common", "MyLogger", "log_server.py"))
    conf = getConfSec(conf=conf, cmdline=cmdline)
    args = load_default_args(port=port, conf=conf, host=host, name=name, log_level=log_level)
    if len(args) > 0:
        return start_independant_process(cmdline, *args)
    else:
        return start_independant_process(cmdline)
############### Launch LOG server if not exist... ##################
####################################################################
####### Launch TRIWATCHDOGWATCHER, if not already running... #######
def launch_tri_watch_dog_watcher(lock_file_path, curDir:str=osGetcwd(), port:str=None, conf:str=None, host:str=None, name:str=None, log_level:str=None):
    cmdline = "{0}".format(osPathJoin(curDir, "common", "WatchDog", "tri_watch_dog.py"))
    args = load_default_args(port=port, conf=conf, host=host, name=name, log_level=log_level)
    args += ["--lock_file_path", lock_file_path]
    return start_independant_process(cmdline, *args)
####### Launch TRIWATCHDOGWATCHER, if not already running... #######
####################################################################
###### Launch TRIWATCHDOG server, if not already running... ########
def launch_tri_watch_dog(lock_file_path, curDir:str=osGetcwd(), port:str=None, conf:str=None, host:str=None, name:str=None, log_level:str=None):
    cmdline = "{0}".format(osPathJoin(curDir, "common", "WatchDog", "tri_watch_dog.py"))
    args = load_default_args(port=port, conf=conf, host=host, name=name, log_level=log_level)
    args += ["--lock_file_path", lock_file_path]
    return start_independant_process(cmdline, *args)
###### Launch TRIWATCHDOG server, if not already running... ########
####################################################################
############ Launch TELEREMOTE server if not exist... ##############
def launch_teleremote_server(curDir:str=osGetcwd(), port:str=None, conf:str=None, host:str=None, name:str=None, log_level:str=None, only_logger:str=None):
    cmdline = "{0}".format(osPathJoin(curDir, "common", "TeleRemote", "tele_remote.py"))
    conf = getConfSec(conf=conf, cmdline=cmdline)
    args = load_default_args(port=port, conf=conf, host=host, name=name, log_level=log_level)
    if not only_logger is None: args+= ["--only_logger", (str(only_logger)).capitalize()]
    return start_independant_process(cmdline, *args)
############ Launch TELEREMOTE server if not exist... ##############
####################################################################
###### Launch MONITORING server, if not already running... #########
def launch_monitoring_server(curDir:str=osGetcwd(), port:str=None, conf:str=None, host:str=None, name:str=None, log_level:str=None):
    cmdline = "{0}".format(osPathJoin(curDir, "common", "WatchDog", "monitoring.py"))
    conf = getConfSec(conf=conf, cmdline=cmdline)
    args = load_default_args(port=port, conf=conf, host=host, name=name, log_level=log_level)
    return start_independant_process(cmdline, *args)
###### Launch MONITORING server, if not already running... #########
####################################################################
####### Launch WATCHDOG server, if not already running... ##########
def launch_watch_dog_server(curDir:str=osGetcwd(), port:str=None, conf:str=None, host:str=None, name:str=None, log_level:str=None):
    cmdline = "{0}".format(osPathJoin(curDir, "common", "WatchDog", "watch_dog.py"))
    conf = getConfSec(conf=conf, cmdline=cmdline)
    args = load_default_args(port=port, conf=conf, host=host, name=name, log_level=log_level)
    return start_independant_process(cmdline, *args)
####### Launch WATCHDOG server, if not already running... ##########
####################################################################
############# Launch ANALYST server if not exist... ################
def launch_analyst_server(curDir:str=osGetcwd(), port:str=None, conf:str=None, host:str=None, name:str=None, log_level:str=None, mode:str=None):
    cmdline = "{0}".format(osPathJoin(curDir, "analyst", "analyst_server.py"))
    conf = getConfSec(conf=conf, cmdline=cmdline)
    args = load_default_args(port=port, conf=conf, host=host, name=name, log_level=log_level)
    if not mode is None: args+= ["--mode", (str(mode)).capitalize()]
    return start_independant_process(cmdline, *args)
############# Launch ANALYST server if not exist... ################
####################################################################
############# Launch AMATRIXQ server if not exist... ###############
def launch_amatrixq_server(curDir:str=osGetcwd(), port:str=None, conf:str=None, host:str=None, name:str=None, log_level:str=None, mode:str=None):
    cmdline = "{0}".format(osPathJoin(curDir, "common", "ThreadQs", "aMatrixQ.py"))
    return start_independant_process(cmdline)
############# Launch AMATRIXQ server if not exist... ###############
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
########## Launch MT5 server if not already running... #############
def launch_MT5_server(curDir:str=osGetcwd(), MT5_server:str="MT5_server.py", name:str=None, conf:str=None, ssl:str='False'):
    if not MT5_server.endswith(".py"): MT5_server+=".py"
    conf = getConfSec(conf=conf, cmdline=cmdline)
    cmdline = "{0}".format(osPathJoin(curDir, "MT5", MT5_server))
    return start_independant_process(cmdline, name, conf, ssl)
########## Launch MT5 server if not already running... #############
####################################################################
############# Launch JUPYTER server if not exist... ################
def launch_jupyter_server(jp_env, jp_server="127.0.0.1", jp_port=8888):
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
    conf = getConfSec(conf=conf, cmdline=cmdline)
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
#FIXME SIGKILL SIGQUIT
from signal import signal, SIGTERM, SIGTERM#, SIGKILL, SIGQUIT
def cleanup_function(cleanup_function, *args, **kwargs):
    if osName != 'nt':
        def signal_handler(signum, frame):
            cleanup_function(*args, **kwargs)
        signal(SIGTERM, signal_handler)
        signal(SIGTERM, signal_handler)
        #signal(SIGKILL, signal_handler)
        #signal(SIGQUIT, signal_handler)
    else:
        from win32api import SetConsoleCtrlHandler
        def win32_signal_handler(signum, frame):
            cleanup_function()
        SetConsoleCtrlHandler(win32_signal_handler, True)
############# Exec function on SIGKILL, SIGTERM... #################
####################################################################
############### Is Process host has running proxy ? ################
running_proxy = []
def host_has_proxy():
    """
        ************************************
        For the moment only works with Nginx
        ************************************
    """
    global running_proxy
    known_proxy = {"nginx":"/usr/sbin/nginx",}
    if len(running_proxy) == 0:
        for proxy, proc in known_proxy.items():
            if is_process_running(processName=proxy, cmdlinePatt=proc):
                running_proxy.append(proxy)
    if len(running_proxy) == 0: return False, None
    else:                       return True, running_proxy
############### Is Process host has running proxy ? ################
####################################################################
########### Is Process host has running supervisord ? ##############
def host_has_supervisor():
    if is_process_running(cmdlinePatt="supervisord"):
        return True
    return False
########### Is Process host has running supervisord ? ##############
####################################################################
