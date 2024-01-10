#!/usr/bin/env python
# coding:utf-8


from platform import system as platformSystem
from logging import getLogger

# relative import
from sys import path;path.extend("..")
from common.Helpers.helpers import init_logger, getOrDefault


####################################################################
###################### Configure IpTables ##########################
iptable_managed = True
from time import sleep
from subprocess import run as subprocessRun
from re import findall as reFindall
def change_ipt_rules(name, logger, IP, add=True, input=True):
    rule ="/sbin/iptables -t filter {0} INPUT -s {1} -j ACCEPT".format(("-A" if add else "-D"), IP) if input else "/sbin/iptables -t filter {0} OUTPUT -d {1} -j ACCEPT".format(("-A" if add else "-D"), IP)
    check = "ACCEPT     all  --  {0}".format(IP) if input else "ACCEPT     all  --  anywhere             {0}".format(IP)
    ret = subprocessRun("/sbin/iptables -L | grep '{0}'".format(check), shell=True, text=True, capture_output=True)
    
    if ret.returncode == -1:
        logger.error("{0} : enable to check iptables rule for IP '{1}' : {2}".format(name, IP, ret.stderr.encode('utf-8')))
    elif ret.returncode == 0 and len(ret.stdout) > 0 and add:
        logger.info("{0} : rule for IP '{1}' already exists : {2}".format(name, IP, rule))
    elif ret.returncode == 1 and len(ret.stdout) == 0 and (not add):
        logger.info("{0} : rule for IP '{1}' already removed : {2}".format(name, IP, rule))
    else:
        nbTry = 0
        if add:
            ret = subprocessRun(rule, shell=True, text=True, capture_output=True)
            if ret.returncode == -1:
                logger.error("{0} : error while trying to add rule for IP '{1}', {2} : {3}".format(name, IP, rule, ret))
            else:
                ret = subprocessRun("/sbin/iptables -L | grep '{0}'".format(check), shell=True, text=True, capture_output=True)
                if ret.returncode == 0 and len(ret.stdout) > 0:
                    logger.info("{0} : iptables rule has been saved for IP '{1}' : {2}".format(name, IP, rule))
                else:      
                    while True:
                        sleep(0.5)
                        _ = subprocessRun(rule, shell=True, text=True, capture_output=True)
                        ret = subprocessRun("/sbin/iptables -L | grep '{0}'".format(check), shell=True, text=True, capture_output=True)
                        if ret.returncode == 0 and len(ret.stdout) > 0:
                            logger.info("{0} : iptables rule has been saved for IP '{1}' : {2}".format(name, IP, rule))
                            break
                        if nbTry > 10:
                            logger.warning("{0} : enable to save iptables rule for IP '{1}' : {2}".format(name, IP, rule))
                            break
                        nbTry += 1
        else: 
            ret = subprocessRun(rule, shell=True, text=True, capture_output=True)
            if ret.returncode == -1:
                logger.error("{0} : error while trying to remove rule for IP '{1}', {2} : {3}".format(name, IP, rule, ret))
            else:
                ret = subprocessRun("/sbin/iptables -L | grep '{0}'".format(check), shell=True, text=True, capture_output=True)
                if ret.returncode == 1 and len(ret.stdout) == 0:
                    logger.info("{0} : iptables rule has been removed for IP '{1}' : {2}".format(name, IP, rule))
                else:
                    while True:
                        sleep(0.5)
                        _ = subprocessRun(rule, shell=True, text=True, capture_output=True)
                        ret = subprocessRun("/sbin/iptables -L | grep '{0}'".format(check), shell=True, text=True, capture_output=True)
                        if ret.returncode == 1 and len(ret.stdout) == 0:
                            logger.info("{0} : iptables rule has been removed for IP '{1}' : {2}".format(name, IP, rule))
                            break
                        if nbTry >= 10:
                            logger.warning("{0} : enable to remove iptables rule for IP '{1}' : {2}".format(name, IP, rule))
                            break
                        nbTry += 1
                        subprocessRun(rule, shell=True, text=True, capture_output=True)
def get_ip_domain(domain):
    ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
    ret = subprocessRun("nslookup {0} 8.8.8.8".format(domain), shell=True, text=True, capture_output=True)
    return reFindall(ip_pattern, ret.stdout.replace('8.8.8.8', '')) 
def configure_iptables(name, logger, add=True, domain=None, IP=None):
    global iptable_managed
    if not iptable_managed:
        pass
    if platformSystem() == "Linux": 
        if not domain is None:
            IP = get_ip_domain(domain)
        if add:
            change_ipt_rules(name=name, logger=logger, IP=IP)
            change_ipt_rules(name=name, logger=logger, IP=IP, input=False)
        else:
            change_ipt_rules(name=name, logger=logger, IP=IP, add=False)
            change_ipt_rules(name=name, logger=logger, IP=IP, add=False, input=False)
    else:
        iptable_managed = False
        logger.warning("{0} : iptables rules are not usable on this plateform : '{1}', firewall won't be managed for {0}...".format(name, platformSystem()))
    return
###################### Configure IpTables ##########################
####################################################################
########### Is Process host has running /sbin/iptables ? ###########
running_ipt = False
def host_has_ipt():
    """
        ***************************************
        For the moment only works with iptables
        ***************************************
    """
    if platformSystem() == "Linux": 
        global running_ipt
        #if not running_ipt:
        #    ret = subprocessRun("/usr/bin/which /sbin/iptables")
        #    print("{}".format(ret))
        #    if ret.returncode == 1:
        #        running_ipt = True
        #        return True  
        #    else: return False
        #else:
        #    print("ici")
        #    return True
        running_ipt = True
        return True
    else:
        return False
########### Is Process host has running /sbin/iptables ? ###########
####################################################################


#================================================================
# used for asyncio, asyncio time out, the function didn't reach the end...
if __name__ == "__main__":
    from sys import argv

    name = "ipt_helpers"
    configStr = "current"
    if len(argv) == 4: 
        name = argv[1]
        add = argv[2]
        domain = getOrDefault(value=argv, default=None, key=3)
        IP = getOrDefault(value=argv, default=None, key=3)
    else:
        config, logger = init_logger(name=name, config=configStr)
        logger.error("{0} : error while trying to manage iptables : 3 parameters expected (name, add and (domain or IP)) : {1} parameters received => '{2}'".format(name, len(argv), argv))
        exit(1)

    name = name.lower()

    # loading config and logger
    logger = getLogger(name=name)

    # change iptables config
    configure_iptables(name=name, logger=logger, 
                       add=True if add == "True" else False, 
                       domain=domain, IP=IP)