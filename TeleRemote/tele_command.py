#!/usr/bin/env python
# coding:utf-8

from os import getppid as osGetppid, getpid as osGetpid, name as osName
from time import sleep
from datetime import datetime
from psutil import Process as psutilProcess
from asyncio import sleep as asyncioSleep, all_tasks as asyncioAll_tasks


# relative import
from sys import path;path.extend("..")
from common.Helpers.helpers import asyncThreadQKill, ThreadQKill
from common.Helpers.network_helpers import MyAsyncSocketObj, MySocketObj, stickyTelecommand, aStickyTelecommand
from common.TeleRemote.tele_funcs import POWER_OFF, CLOSE_ALL_POSITION_CONFIRMATION, UNDER_CONSTRUCTION
from common.TeleRemote import tele_funcs

DEFAULT_RETRY_PERIOD = 1




class Telecommand:
    @stickyTelecommand(delay=10, backoff=1, tries=-1) 
    @stickyTelecommand(delay=DEFAULT_RETRY_PERIOD, backoff=1, tries=10, jitter=1)
    def TeleCommand(self):
        self.state = 'started'
        with MySocketObj(name=self.Name).make_connection(server=self.config.TB_IP, port=int(self.config.TB_PORT)) as TeleSocket:
            self.logger.info("{0} : Telecommand sending TCP address to TeleRemote.. .  . ".format(self.Name))
            StarQsPort = int(TeleSocket.getsockname()[1])
            TeleSocket.send_data("{0}:{1}:{2}".format(self.Name, self.config.TB_IP, StarQsPort))
            while True:
                if self.state == POWER_OFF.starQs_message or self.state == CLOSE_ALL_POSITION_CONFIRMATION.starQs_message:
                    break

                try:
                    data = TeleSocket.receive_data()
                except Exception as e:
                    err_msg = "{0} : Telecommand, error while trying to receive data : {1}...".format(self.Name, e)
                    self.logger.error(err_msg)
                    raise Exception(err_msg)
                
                if not data:
                    self.logger.error("{0} : Telecommand just lost connection with TeleRemote !".format(self.Name))
                    raise Exception("[Errno 61] Connection refused")
                try:
                    if data != '0' and data != POWER_OFF.starQs_message and data != CLOSE_ALL_POSITION_CONFIRMATION.starQs_message: 
                        if isinstance(data, Qmsg):
                            self.TeleBufQ.append(data)
                            while len(self.TeleBufQ) > 0:
                                data = self.TeleBufQ[-1]
                                #self._send_priority_msg(data)
                                self.TeleBufQ.popleft()
                        elif isinstance(data, SubsQ): 
                            # subscribe object... to send scripts directly from telecommand
                            pass
                        else:
                            # tele_funcs (telecommande functionnalities)
                            TeleSocket.send_data(tele_funcs.Tele_Dispatcher(data, self.main_queue_beat))
                    else:
                        if data == POWER_OFF.starQs_message:
                            self.state = data
                            self.killTele(TeleSocket=TeleSocket, poweroff_msg=POWER_OFF.starQs_response(self.Name), logger_msg="{0} : Telecommand, received 'power off' command, program killed at : {1} !!!".format(self.Name, datetime.utcnow()))
                        elif data == CLOSE_ALL_POSITION_CONFIRMATION.starQs_message:
                            self.state = data   
                            self.stopTele(TeleSocket=TeleSocket)
                            break
                        else:
                            TeleSocket.send_data(UNDER_CONSTRUCTION.starQs_response())
                except Exception as e:
                    self.logger.critical("{0} : Telecommand, critical error while trying to get message from TeleRemote : {1}".format(self.Name, e))
                    pass

    def killTele(self, TeleSocket, poweroff_msg, logger_msg):
        parentPid = osGetppid() if osGetppid() > 1 else osGetpid()
        procChilds = psutilProcess(parentPid).children(recursive=True)
        if osName != 'nt':
            pidList = str(parentPid)
            for procChild in procChilds:
                pidList+=" "+str(procChild.pid)
        else:
            pidList = [int(parentPid)]
            if not procChilds is None:
                for procChild in procChilds:
                    pidList.append(int(procChild.pid))
        ThreadQKill(pidList=pidList, logger=self.logger, logger_msg=logger_msg, TeleSocket=TeleSocket, poweroff_msg=poweroff_msg)
        
    def stopTele(self, TeleSocket):
        if self.run:
            self.run = False
            self.StarQlocked = True
            for key, subs in self.Subscribers.items():
                (subs).unSubs()
                while not (subs).ends:
                    sleep(self.main_queue_beat)
                    #(subs).unSubs()
            subs_to_remove = self.Subscribers.copy()
            for key, subs in subs_to_remove.items():
                self.remove_linked((subs).name)
            self.SafeQ.clear()
            TeleSocket.send_data(CLOSE_ALL_POSITION_CONFIRMATION.starQs_response(self.Name))
            return False
        else:
            self.logger.error("{0} : Telecommand, received 'stop' message but it's already stopped !".format(self.Name))
            return True


##############################################################################################################################################################################################

asyncLock = None

class ATelecommand:
    @aStickyTelecommand(delay=10, backoff=1, tries=-1) 
    @aStickyTelecommand(delay=DEFAULT_RETRY_PERIOD, backoff=1, tries=10, jitter=1)
    async def TeleCommand(self):
        global asyncLock
        asyncLock = self.get_asyncLock()
        self.state = 'started'
        async with await MyAsyncSocketObj(name=self.Name).make_connection(server=self.config.TB_IP, port=int(self.config.TB_PORT)) as TeleSocket:
            await self.logger.asyncInfo("{0} : Telecommand, sending TCP address to TeleRemote.. .  . ".format(self.Name))
            AStarQsPort = int(TeleSocket.sock_info[1])
            await TeleSocket.send_data("{0}:{1}:{2}".format(self.Name, self.config.TB_IP, AStarQsPort))
            while True:
                if self.state == POWER_OFF.starQs_message or self.state == CLOSE_ALL_POSITION_CONFIRMATION.starQs_message:
                    break

                try:
                    data = await TeleSocket.receive_data()
                except Exception as e:
                    err_msg = "{0} : Telecommand, error while trying to receive data : {1}...".format(self.Name, e)
                    await self.logger.asyncError(err_msg)
                    raise Exception(err_msg)
                
                if not data:
                    await self.logger.asyncError("{0} : Telecommand, just lost connection with TeleRemote !".format(self.Name))
                    raise Exception("[Errno 61] Connection refused")
                try:
                    if data != '0' and data != POWER_OFF.starQs_message and data != CLOSE_ALL_POSITION_CONFIRMATION.starQs_message: 
                        if isinstance(data, Qmsg):
                            #self.TeleBufQ.append(data)
                            #while len(self.TeleBufQ) > 0:
                            #    data = self.TeleBufQ[-1]
                            #    #self._send_priority_msg(data)
                            #    self.TeleBufQ.popleft()
                            pass
                        elif isinstance(data, SubsQ): 
                            # subscribe object... to send scripts directly from telecommand
                            pass
                        else:
                            # tele_funcs (telecommande functionnalities)
                            await TeleSocket.send_data(tele_funcs.Tele_Dispatcher(data, self.main_queue_beat))
                    else:
                        if data == POWER_OFF.starQs_message:
                            self.state = data
                            self.asyncLoop.run_until_complete(await self.killTele(TeleSocket=TeleSocket, poweroff_msg=POWER_OFF.starQs_response(self.Name), logger_msg="{0} : Telecommand, received 'power off' command, program killed at : {1} !!!".format(self.Name, datetime.utcnow())))
                        elif data == CLOSE_ALL_POSITION_CONFIRMATION.starQs_message:
                            self.state = data   
                            await self.stopTele(TeleSocket=TeleSocket)
                        else:
                            await TeleSocket.send_data(UNDER_CONSTRUCTION.starQs_response())
                except Exception as e:
                    await self.logger.asyncCritical("{0} : Telecommand, critical error while trying to get message from TeleRemote : '{1}'".format(self.Name, e))
                    pass

    async def killTele(self, TeleSocket, poweroff_msg, logger_msg):
        parentPid = osGetppid() if osGetppid() > 1 else osGetpid()
        procChilds = psutilProcess(parentPid).children(recursive=True)
        if osName != 'nt':
            pidList = str(parentPid)
            for procChild in procChilds:
                pidList+=" "+str(procChild.pid)
        else:
            pidList = [int(parentPid)]
            if not procChilds is None:
                for procChild in procChilds:
                    pidList.append(int(procChild.pid))
        await self.logger.asyncInfo(str(pidList))
        await asyncThreadQKill(pidList=pidList, logger=self.logger, logger_msg=logger_msg, TeleSocket=TeleSocket, poweroff_msg=poweroff_msg)

    async def _stop_tasks(self):
        global asyncLock
        async with asyncLock:
            for task in asyncioAll_tasks():
                if task.get_name() in self.clients:
                    task.cancel()
    async def stopTele(self, TeleSocket):
        await self.asyncLoop.create_task(self._stop_tasks())
        await TeleSocket.send_data(CLOSE_ALL_POSITION_CONFIRMATION.starQs_response(self.Name))
        await self.logger.asyncInfo("{0} : Telecommand, received 'stop' command, program stopped at : {1} !!!".format(self.Name, datetime.utcnow()))
        self.asyncLoop.stop()
        while True:
            if not self.asyncLoop.is_running():
                break
            await asyncioSleep(0.1)
        self.asyncLoop.close()