#!/usr/bin/env python
# coding:utf-8

from os import system as osSystem, getcwd as osGetcwd
from os.path import join as osPathJoin
from time import sleep
from random import uniform as randomUniform
from telnetlib import Telnet

# relative import
from sys import path;path.extend("..")
from common.TeleRemote.tele_funcs import POWER_OFF, CLOSE_ALL_POSITION_CONFIRMATION

# Stolen from retry module

####################################################################
############ ping and telnet for external connection ###############
def ping_error(hostname="google.com"):
    # if response == 0: pingstatus = "Network Active" else: pingstatus = "Network Error"
    return osSystem("ping -c 1 {0}".format(hostname))

def telnet_error(host, port, timeout=5, logger=None):
    try:
        with Telnet(host, int(port)) as tn:
            tn.open(host, int(port), timeout)
            tn.close()
            return False
    except:
        if not logger is None:
            logger.error("Broker : Broker connection lost, telneting '{0}:{1}'...".format(host, port))
        return True
############ ping and telnet for external connection ###############
####################################################################

####################################################################
##################### Retry for coroutines #########################
# thank you chatGPT
from random import uniform
from functools import partial, wraps
from re import findall as reFindall
from asyncio import sleep as asyncioSleep
async def __retry_internal(f, exceptions=Exception, tries=-1, delay=0, max_delay=None, backoff=1, jitter=0, logger=None, name=None):
    """
    Executes an asynchronous function and retries it if it failed.
    :param f: the function to execute.
    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param tries: the maximum number of attempts. default: -1 (infinite).
    :param delay: initial delay between attempts. default: 0.
    :param max_delay: the maximum value of delay. default: None (no limit).
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :returns: the result of the f function.
    """
    _tries, _delay = tries, delay
    while _tries:
        try:
            return await f()
        except exceptions as e:
            _tries -= 1
            if not _tries:
                raise
            if not logger is None:
                await logger.asyncWarning("{0} : {1}, retrying in {2} seconds...".format(name, e, _delay))
                # FIXME find a solution for IPtables... or not does VPS are powerfull enougth ?
                #if check_ipt:
                #    from common.Helpers.os_helpers import start_independant_process
                #    domain = (reFindall(r'https:\/\/\S+', "{0}".format(e))[0]).replace("https://", '').split('/')[0]
                #    if not domain is None:
                #        cmdline = "{0}".format(osPathJoin(osGetcwd(), "common", "Helpers", "ipt_helpers.py"))
                #        start_independant_process(cmdline, name, 1, domain)
            await asyncioSleep(float(_delay))
            _delay *= backoff
            if isinstance(jitter, tuple):
                _delay += uniform(*jitter)
            else:
                _delay += jitter
            if not max_delay is None:
                _delay = min(_delay, max_delay)

def asyncRetry(exceptions=Exception, tries=-1, delay=0, max_delay=None, backoff=1, jitter=0, logger=None, name=None):
    """Returns a retry decorator.
    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param tries: the maximum number of attempts. default: -1 (infinite).
    :param delay: initial delay between attempts. default: 0.
    :param max_delay: the maximum value of delay. default: None (no limit).
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :returns: a retry decorator.
    """
    def retry_decorator(f):
        @wraps(f)
        async def retry_wrapper(*args, **kwargs):
            if f.__name__ == "watch_broker": 
                return await __retry_internal(partial(f, *args, **kwargs), exceptions, tries, delay, max_delay, backoff, jitter, logger=kwargs["logger"], name=kwargs["name"])
            else: return await __retry_internal(partial(f, *args, **kwargs), exceptions, tries, delay, max_delay, backoff, jitter)
        return retry_wrapper
    return retry_decorator
##################### Retry for coroutines #########################
####################################################################

####################################################################
################## Retry for stickyTelecommand #####################
# only with local address : 127.0.0.1 (localhost)
def Tele_retry(f, exceptions=Exception, tries=-1, delay=0, max_delay=None, backoff=1, jitter=0, clsPtr=None):
    cause = "Telecommand is probably down..."
    _tries, _delay = tries, delay
    first_occurence = _tries
    while _tries:
        try:
            if clsPtr.state != CLOSE_ALL_POSITION_CONFIRMATION.starQs_message and clsPtr.state != POWER_OFF.starQs_message:
                return f()
            else:
                return
        except exceptions as e:
            if first_occurence==_tries:
                if not clsPtr is None:
                    clsPtr.logger.error("{0} : '{1}' while trying to connect to : '{2}', {3}".format(clsPtr.Name, e, "{0}:{1}".format(clsPtr.config.TB_IP, clsPtr.config.TB_PORT), cause))
                    clsPtr.config.reload_config(name=clsPtr.Name)
            _tries -= 1
            if not _tries:                    
                raise
            if not clsPtr is None:
                clsPtr.logger.sqlinfo("{0} : '{1}', retrying '{2}' in {3} seconds...".format(clsPtr.Name, e, "{0}:{1}".format(clsPtr.config.TB_IP, clsPtr.config.TB_PORT), _delay))
                clsPtr.config.reload_config(name=clsPtr.Name)
            sleep(_delay)
            _delay *= backoff
            if isinstance(jitter, tuple):
                _delay += randomUniform(*jitter)
            else:
                _delay += jitter
            if max_delay is not None:
                _delay = min(_delay, max_delay)
################## Retry for stickyTelecommand #####################
####################################################################
################## Retry for astickyTelecommand ####################
# only with local address : 127.0.0.1 (localhost)
async def aTele_retry(f, exceptions=Exception, tries=-1, delay=0, max_delay=None, backoff=1, jitter=0, clsPtr=None):
    cause = "Telecommand is probably down..."
    _tries, _delay = tries, delay
    first_occurence = _tries
    while _tries:
        try:
            if clsPtr.state != CLOSE_ALL_POSITION_CONFIRMATION.starQs_message and clsPtr.state != POWER_OFF.starQs_message:
                return await f()
            else:
                return
        except exceptions as e:
            if first_occurence==_tries:
                if not clsPtr.logger is None:
                    await clsPtr.logger.asyncError("{0} : '{1}' while trying to connect to : '{2}', {3}".format(clsPtr.Name, e, "{0}:{1}".format(clsPtr.config.TB_IP, clsPtr.config.TB_PORT), cause))
                if not clsPtr.config is None:
                    clsPtr.config.reload_config(name=clsPtr.Name)
            _tries -= 1
            if not _tries:                    
                raise
            if not clsPtr.logger is None:
                await clsPtr.logger.asyncSqlinfo("{0} : '{1}', retrying '{2}' in {3} seconds...".format(clsPtr.Name, e, "{0}:{1}".format(clsPtr.config.TB_IP, clsPtr.config.TB_PORT), _delay))
            if not clsPtr.config is None:
                clsPtr.config.reload_config(name=clsPtr.Name)
            await asyncioSleep(float(_delay))
            _delay *= backoff
            if isinstance(jitter, tuple):
                _delay += randomUniform(*jitter)
            else:
                _delay += jitter
            if max_delay is not None:
                _delay = min(_delay, max_delay)
################## Retry for astickyTelecommand ####################
####################################################################

####################################################################
############# Refresh socket configuration (if changed) ############
def Refresh_Feeded_Port(instanceObj, config, sectionName):
    notFound=True
    config.reload_config(name=instanceObj.Name)
    for analystName, conf in config.parser.items():
        if analystName == sectionName:
            try:
                server="" ; port="" ; mem_port="" 
                prefixe = analystName.split('_')[0]
                for name_sec, conf_sec in conf.items(): 
                    if name_sec == "{0}_SERVER".format(prefixe):
                        server = conf_sec
                    if name_sec == "{0}_DB_PORT".format(prefixe):
                        port = conf_sec
                    if name_sec == "{0}_DB_MEM_PORT".format(prefixe):
                        mem_port = conf_sec
                    if server != "" and port != "" and mem_port != "":
                        notFound = False
                        break
                if port == "" or port == "" or mem_port == "":
                    instanceObj.logger.info("{0} : missing address or port for section '{1}', this section will not be load as an Analyst...".format(sectionName, analystName))
                    return config, notFound
            except Exception as e:
                instanceObj.logger.error("{0} : error while trying to load address/port for Analyst '{1}', please check config file... (analyst format) : {2}".format(sectionName, analystName, e))
                return config, notFound
    return config, notFound
############# Refresh socket configuration (if changed) ############
####################################################################

####################################################################
################## Common retry for safeSocket #####################
def Feeder_retry(f, exceptions=Exception, tries=-1, delay=0, max_delay=None, backoff=1, jitter=0, clsPtr=None, curSock=None, sockName=None, server=None, port=None):
    _tries, _delay = tries, delay
    first_occurence = _tries
    while _tries:
        try:
            return f()
        except exceptions as e:
            if first_occurence==_tries:
                if not clsPtr is None:
                    clsPtr.logger.error("{0} : error while trying to connect to '{1} {2}:{3}' : {4}".format(clsPtr.Name, sockName, server, port, e))
                    clsPtr.config, notFound = Refresh_Feeded_Port(clsPtr, clsPtr.config, sockName)
                if notFound:
                    try :
                        (clsPtr.Sock_Sender[curSock]).conn.close()
                        clsPtr.Sock_Sender.pop(curSock, None)
                    except:
                        clsPtr.Sock_Sender.pop(curSock, None)
                        pass
                    clsPtr.logger.error("{0} : '{1}' configuration not found, socket '{2}' has been closed.".format(clsPtr.Name, sockName, clsPtr.sock.getsocketname()))
                    return
            _tries -= 1

            if not _tries:                    
                raise
            if not clsPtr is None:
                clsPtr.logger.sqlinfo("{0} : '{1}', retrying connection to '{2} {3}:{4}' in {5} seconds...".format(clsPtr.Name, e, sockName, server, port, _delay))
                clsPtr.config, notFound = Refresh_Feeded_Port(clsPtr, clsPtr.config, sockName)
            if notFound:
                try :
                    (clsPtr.Sock_Sender[curSock]).conn.close()
                    clsPtr.Sock_Sender.pop(curSock, None)
                except:
                    clsPtr.Sock_Sender.pop(curSock, None)
                    pass
                clsPtr.logger.error("{0} : '{1}' configuration not found, socket '{2}' has been closed.".format(clsPtr.Name, sockName, clsPtr.sock.getsocketname()))
                return
            sleep(_delay)
            _delay *= backoff
            if isinstance(jitter, tuple):
                _delay += randomUniform(*jitter)
            else:
                _delay += jitter
            if max_delay is not None:
                _delay = min(_delay, max_delay)
################## Common retry for safeSocket #####################
####################################################################

####################################################################
####################### Retry for SslTunnel ########################

DEFAULT_WAIT_CONNECTION_LOST=30
connection_lost_at = None
def SslTunnel_retry():
    pass
# External connection with Broker
#def broker_conn_state(logger, uri, port, connection_lost_at):
#    if ping_error() != 0: 
#        logger.error("Network : Internet connection lost, loop until connection comes back...")
#    while ping_error() != 0:
#        sleep(DEFAULT_WAIT_CONNECTION_LOST)
#        logger.error("Network : Internet connection lost, pinging 'google.com'...")
#
#    if telnet_error(uri, port, timeout=5, logger=logger):  
#        logger.error("Broker : Broker connection lost, loop until Broker connection comes back...")
#        while telnet_error(uri, port, timeout=5, logger=logger):
#            sleep(DEFAULT_WAIT_CONNECTION_LOST)  
#    connection_restored_at = datetime.now()
#    logger.warning("Network : Connection with broker restored, interrupted while '{0}' from '{1}' to '{2}'".format(connection_restored_at-connection_lost_at, connection_lost_at, connection_restored_at))  
#    #FIXME : ré-init account state....
#
#def SslTunnel_retry(f, exceptions=Exception, tries=-1, delay=0, max_delay=None, backoff=1, jitter=0, clsPtr=None):
#    cause = "Broker probably shutdown connection..."
#    _tries, _delay = tries, delay
#    first_occurence = _tries
#    while _tries:
#        try:
#            if clsPtr.state != CLOSE_ALL_POSITION_CONFIRMATION.starQs_message and clsPtr.state != POWER_OFF.starQs_message:
#                return f()
#            else:
#                return
#        except exceptions as e:
#            if first_occurence==_tries:
#                if not clsPtr is None:
#                    clsPtr.logger.error("{0} : '{1}' while trying to connect to : '{2}', {3}".format(clsPtr.Name, e, "{0}:{1}".format(clsPtr.config.BR_IP, clsPtr.config.BR_PORT), cause))
#                    clsPtr.config.reload_config(name=clsPtr.Name)
#            _tries -= 1
#            if not _tries:                    
#                raise
#            if not clsPtr is None:
#                clsPtr.logger.sqlinfo("{0} : '{1}', retrying '{2}' in {3} seconds...".format(clsPtr.Name, e, "{0}:{1}".format(clsPtr.config.BR_IP, clsPtr.config.BR_PORT), _delay))
#                clsPtr.config.reload_config(name=clsPtr.Name)
#            sleep(_delay)
#            _delay *= backoff
#            if isinstance(jitter, tuple):
#                _delay += randomUniform(*jitter)
#            else:
#                _delay += jitter
#            if max_delay is not None:
#                _delay = min(_delay, max_delay)
####################### Retry for SslTunnel ########################
####################################################################