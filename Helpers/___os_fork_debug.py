#!/usr/bin/env python
# coding:utf-8


####################################################################
# /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\  #
#                                                                  #
#                   only used for debugging !!!                    #
#                                                                  #
# /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\  #
####################################################################



####################################################################
########## Start independant process (PSEUDO not child) ############
import os, sys
def start_independant_process(command:str, argv:str=None):
    """
    For multiple arguments send one string separated by one space character
    """
    try:
        if os.name != 'nt':
            pid = os.fork()
            if pid == 0:
                os.setsid()
                os.umask(0) 
                if not argv is None:
                    os.system("{0} {1}".format(command, argv))
                else:
                    os.system(command)
            return pid
        else:
            import subprocess
            if not argv is None:
                proc = subprocess.Popen([sys.executable, command, argv], shell=True)
            else:
                proc = subprocess.Popen([sys.executable, command], shell=True)
            return proc.pid
    except Exception as e:
        return e
########## Start independant process (PSEUDO not child) ############
####################################################################
############### Launch LOG server if not exist... ##################
def launch_log_server(curDir:str=os.getcwd()):
    if os.name != 'nt':
        cmdline =  "cd / ; \
                    cd {0}/bin ; \
                    source activate ; \
                    cd .. ; \
                    ./bin/python {1} \
                    ".format(curDir, os.path.join(curDir, "common", "MyLogger", "log_server.py"))
    else:
        cmdline = "{0}".format(os.path.join(curDir, "common", "MyLogger", "log_server.py"))
    return start_independant_process(cmdline)
############### Launch LOG server if not exist... ##################
####################################################################
########### Launch TELECOMMAND server if not exist... ##############
def launch_telecommand_server(curDir:str=os.getcwd(), path_conf:str=None, externalCall:str="True"):
    if os.name != 'nt':
        cmdline =  "cd / ; \
                    cd {0}/bin ; \
                    source activate ; \
                    cd .. ; \
                    ./bin/python {1} \
                    ".format(curDir, os.path.join(curDir, "common", "TeleRemote", "tele_remote.py"))
    else:
        cmdline = "{0}".format(os.path.join(curDir, "common", "TeleRemote", "tele_remote.py"))
    if not path_conf is None:
        return start_independant_process(cmdline, "{0} {1}".format(path_conf, externalCall))
    else:
        return start_independant_process(cmdline, externalCall)
########### Launch TELECOMMAND server if not exist... ##############
####################################################################
############## Launch NOTIF server if not exist... #################
def launch_notif_server(curDir:str=os.getcwd(), path_conf:str=None):
    if os.name != 'nt':
        cmdline =  "cd / ; \
                    cd {0}/bin ; \
                    source activate ; \
                    cd .. ; \
                    ./bin/python {1} \
                    ".format(curDir, os.path.join(curDir, "common", "Notifie", "notif_server.py"))
    else:
        cmdline = "{0}".format(os.path.join(curDir, "common", "Notifie", "notif_server.py"))
    if not path_conf is None:
        return start_independant_process(cmdline, path_conf)
    else:
        return start_independant_process(cmdline)
############## Launch NOTIF server if not exist... #################
####################################################################
########### Launch independant server (if not exist)  ##############
def launch_independant_process(path_from_cwd, file, param=None, curDir=os.getcwd()):
    if os.name != 'nt':
        cmdline =  "cd / ; \
                    cd {0}/bin ; \
                    source activate ; \
                    cd .. ; \
                    ./bin/python {1} \
                    ".format(curDir, os.path.join(curDir, path_from_cwd, file))      
    else:    
        cmdline = "{0}".format(os.path.join(curDir, path_from_cwd, file))     
    if not param is None:
        return start_independant_process(cmdline, param)
    else:
        return start_independant_process(cmdline)
########### Launch independant server (if not exist)  ##############
####################################################################