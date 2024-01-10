#!/usr/bin/env python
# coding:utf-8

from time import sleep 
from datetime import datetime, timedelta
from uuid import uuid1
from traceback import format_exc as tracebackFormat_exc
from asyncio import iscoroutinefunction
from asyncio import run as asyncioRun, create_task as asyncioCreate_task, get_running_loop as asyncioGet_running_loop, \
                    get_event_loop as asyncioGet_event_loop ,sleep as asyncSleep, new_event_loop as asyncioNew_event_loop, \
                    gather as asyncioGather
from apscheduler.schedulers.background import BackgroundScheduler

# relative import
from sys import path;path.extend("..")
from common.Scheduler.job_loops import *


DEBUG = True
runLoop = None


class Job:
    asyncLoop = None
    config = None
    logger = None
    Name = None
    ##########################################################################
    # init, call, do and exec_job
    def __init__(self, jobName, interval):
        self.jobName = jobName
        self.interval = interval ; self.waitEnd = False
        self.func = None ; self.args = None ; self.kwargs = None
        self.last_run = None ; self.next_run = None
        self.error = 0 ; self.last_error = None
        self.is_running = False
        self.task = None
        self.do = self.__call__
        
    def __call__(self, func, wait_end=False, on_time=False, rerun_on_error=False, *args, **kwargs):
        global runLoop
        self.jobName = "{0} {1} {2}".format(func.__name__, self.jobName, uuid1())
        self.func = func
        self.args = args or []
        self.kwargs = kwargs or {}
        self.waitEnd = wait_end

        asyncJob = iscoroutinefunction(func)

        if rerun_on_error and on_time and asyncJob and wait_end: self.asyncExec_job = self.rerun_async_func ; runLoop = runTaskAsyncOnTimeWaitEnd
        elif rerun_on_error and on_time and asyncJob and (not wait_end): self.asyncExec_job = self.rerun_async_func ; runLoop = runTaskAsyncOnTime
        elif rerun_on_error and on_time and (not asyncJob) and wait_end: self.exec_job = self.rerun_sync_func ; runLoop = runTaskSyncOnTimeWaitEnd
        elif rerun_on_error and on_time and (not asyncJob) and (not wait_end): self.exec_job = self.rerun_sync_func ; runLoop = runTaskSyncOnTime
        elif rerun_on_error and (not on_time) and asyncJob and wait_end: self.asyncExec_job = self.rerun_async_func ; runLoop = runTaskAsyncWaitEnd
        elif rerun_on_error and (not on_time) and asyncJob and (not wait_end): self.asyncExec_job = self.rerun_async_func ; runLoop = runTaskAsync
        elif rerun_on_error and (not on_time) and (not asyncJob) and wait_end: self.exec_job = self.rerun_sync_func ; runLoop = runTaskSyncWaitEnd
        elif rerun_on_error and (not on_time) and (not asyncJob) and (not wait_end): self.exec_job = self.rerun_sync_func ; runLoop = runTaskSync

        elif (not rerun_on_error) and on_time and asyncJob and wait_end: self.asyncExec_job = self.async_func ; runLoop = runTaskAsyncOnTimeWaitEnd
        elif (not rerun_on_error) and on_time and asyncJob and (not wait_end): self.asyncExec_job = self.async_func ; runLoop = runTaskAsyncOnTime
        elif (not rerun_on_error) and on_time and (not asyncJob) and wait_end: self.exec_job = self.sync_func ; runLoop = runTaskSyncOnTimeWaitEnd
        elif (not rerun_on_error) and on_time and (not asyncJob) and (not wait_end): self.exec_job = self.sync_func ; runLoop = runTaskSyncOnTime
        elif (not rerun_on_error) and (not on_time) and asyncJob and wait_end: self.asyncExec_job = self.async_func ; runLoop = runTaskAsyncWaitEnd
        elif (not rerun_on_error) and (not on_time) and asyncJob and (not wait_end): self.asyncExec_job = self.async_func ; runLoop = runTaskAsync
        elif (not rerun_on_error) and (not on_time) and (not asyncJob) and wait_end: self.exec_job = self.sync_func ; runLoop = runTaskSyncWaitEnd
        elif (not rerun_on_error) and (not on_time) and (not asyncJob) and (not wait_end): self.exec_job = self.sync_func ; runLoop = runTaskSync

        ScheduledJobs.jobs[self.jobName] = self

        if not self.is_running:
            self.start(asyncJob)             
    
    def do(func, wait_end=False, on_time=False, rerun_on_error=False, *args, **kwargs):
        pass

    def exec_job(self):
        pass

    async def asyncExec_job(self):
        pass

    ##########################################################################
    # main funcs
    def sync_func(self):
        try:
            self.func(*self.args, **self.kwargs)
            self.last_run = datetime.utcnow()
            self.next_run = self.last_run + self.interval
        except Exception as e:
            if DEBUG: Job.logger.error("{0} : error while running scheduled job '{1}' : {2}".format(ScheduledJobs.Name, self.jobName, tracebackFormat_exc()))
            Job.logger.error("{0} : error while running scheduled job '{1}' : {2}".format(ScheduledJobs.Name, self.jobName, e))
            self.error+=1 ; self.last_error = datetime.utcnow()
            pass

    def rerun_sync_func(self):
        try:
            self.func(*self.args, **self.kwargs)
            self.last_run = datetime.utcnow()
            self.next_run = self.last_run + self.interval
        except Exception as e:
            if DEBUG: Job.logger.error("{0} : error while running scheduled job '{1}' : {2}".format(self.Name, self.jobName, tracebackFormat_exc()))
            Job.logger.error("{0} : error while running scheduled job '{1}' : {2}".format(self.Name, self.jobName, e))
            self.error+=1 ; self.last_error = datetime.utcnow()
            try:
                Job.logger.info("{0} : scheduled job '{1}' rerun immediately...".format(self.Name, self.jobName))
                self.func(self.args, self.kwargs)
            except Exception as e:
                if DEBUG: Job.logger.error("{0} : error while running scheduled job '{1}' : {2}".format(self.Name, self.jobName, tracebackFormat_exc()))
                Job.logger.error("{0} : error while running scheduled job '{1}' : {2}".format(self.Name, self.jobName, e))
                self.error+=1 ; self.last_error = datetime.utcnow()
                pass

    async def async_func(self):
        try:
            await self.func(*self.args, **self.kwargs)
            self.last_run = datetime.utcnow()
            self.next_run = self.last_run + self.interval
        except Exception as e:
            if DEBUG: await Job.logger.asyncError("{0} : error while running scheduled job '{1}' : {2}".format(ScheduledJobs.Name, self.jobName, tracebackFormat_exc()))
            await Job.logger.asyncError("{0} : error while running scheduled job '{1}' : {2}".format(ScheduledJobs.Name, self.jobName, e))
            self.error+=1 ; self.last_error = datetime.utcnow()
            return

    async def rerun_async_func(self):
        try:
            await self.func(*self.args, **self.kwargs)
            self.last_run = datetime.utcnow()
            self.next_run = self.last_run + self.interval
        except Exception as e:
            if DEBUG: await Job.logger.asyncError("{0} : error while running scheduled job '{1}' : {2}".format(self.Name, self.jobName, tracebackFormat_exc()))
            await Job.logger.asyncError("{0} : error while running scheduled job '{1}' : {2}".format(self.Name, self.jobName, e))
            self.error+=1 ; self.last_error = datetime.utcnow()
            try:
                await Job.logger.asyncInfo("{0} : scheduled job '{1}' rerun immediately...".format(self.Name, self.jobName))
                self.func(self.args, self.kwargs)
            except Exception as e:
                if DEBUG: await Job.logger.asyncError("{0} : error while running scheduled job '{1}' : {2}".format(self.Name, self.jobName, tracebackFormat_exc()))
                await Job.logger.asyncError("{0} : error while running scheduled job '{1}' : {2}".format(self.Name, self.jobName, e))
                self.error+=1 ; self.last_error = datetime.utcnow()
                return

    ##########################################################################
    # start stop
    def start(self, asyncJob):
        global runLoop
        if not self.is_running:
            self.is_running = True
            if not asyncJob:
                if self.waitEnd:
                    self.task = Job.asyncLoop.create_task(runLoop(obj=self, interval=self.interval, loop=Job.asyncLoop))
                else:
                    self.task = Job.asyncLoop.create_task(runLoop(obj=self, interval=self.interval)) 
            else:  
                if self.waitEnd:
                    self.task = Job.asyncLoop.create_task(runLoop(obj=self, interval=self.interval))
                else:
                    self.task = Job.asyncLoop.create_task(runLoop(obj=self, interval=self.interval, loop=Job.asyncLoop))                             
            Job.logger.info("{0} : scheduled job '{1}' is starting.. .  . with interval : {2}".format(ScheduledJobs.Name, self.jobName, self.interval))
        else:
            Job.logger.warning("{0} : scheduled job '{1}' is already running !".format(ScheduledJobs.Name, self.jobName, self.interval))

    def stop(self):
        if self.is_running:
            self.task.cancel()
            self.is_running = False
            Job.logger.info("{0} : scheduled job '{1}' has been stopped at {2} !".format(ScheduledJobs.Name, self.jobName, datetime.utcnow()))
        else:
            Job.logger.error("{0} : scheduled job '{1}' received stop command, but task is not running !".format(ScheduledJobs.Name, self.jobName))

    def restart(self):
        self.stop()
        self.start()

##########################################################################

def EveryWrapper(unit, timelaps):
    # Asyncio sleep
    if timelaps.lower().startswith("millisecond"): return Job(jobName= "({0} {1})".format(unit, timelaps), interval=(timedelta(milliseconds=unit)))
    if timelaps.lower().startswith("second"): return Job(jobName= "({0} {1})".format(unit, timelaps), interval=(timedelta(seconds=unit)))
    if timelaps.lower().startswith("minute"): return  Job(jobName= "({0} {1})".format(unit, timelaps), interval=(timedelta(minutes=unit)))
    if timelaps.lower().startswith("hour"): return  Job(jobName= "({0} {1})".format(unit, timelaps), interval=(timedelta(hours=unit)))

    if timelaps.lower().startswith("day"): return Job(jobName= "({0} {1})".format(unit, timelaps), interval=timedelta(days=unit))
    if timelaps.lower().startswith("week"): return Job(jobName= "({0} {1})".format(unit, timelaps), interval=(timedelta(weeks=unit)))
    if timelaps.lower().startswith("month"): return Job(jobName= "({0} {1})".format(unit, timelaps), interval=(timedelta(months=unit)))

    #def on(self, weekday):          self.job.weekday = weekday                                                                                                                          ; return self
    #def at(self, time_str):         time_parts = [int(x) for x in time_str.split(':')] ; self.job.at_time = time(hour=time_parts[0], minute=time_parts[1], second=time_parts[2])        ; return self

##########################################################################

class ScheduledJobs:
    """ 
        An asyncio copy (chatGPT) of : https://schedule.readthedocs.io/en/stable/
        schedule.every(5).seconds.do(SafeScheduler.job, logger=logger, arg2="test")
        schedule.every(10).minutes.do(SafeScheduler.job, logger=logger, arg2="10 minutes")
        schedule.every(1).hour.do(job)
        schedule.every().day.at("10:30").do(job)
        schedule.every().monday.do(job)
        schedule.every().wednesday.at("13:15").do(job)
        schedule.every().minute.at(":17").do(job)
    """
    Name = "ScheduledJob"
    jobs = {}
    def __init__(self, config, logger, name:str=None, asyncioLoop=None, mainProcess=False):
        if not name is None:
            self.Name = name
        self.is_running = False

        Job.Name = self.Name
        Job.config = self.config = config 
        Job.logger = self.logger = logger

        if not asyncioLoop is None: Job.asyncLoop = self.loop = asyncioLoop 
        elif mainProcess:           self.mainProcess() 
        else:                       Job.asyncLoop = self.loop = asyncioNew_event_loop()

    def mainProcess(self):
        Job.asyncLoop = self.loop = asyncioGet_event_loop()

    @staticmethod
    def every(unit, timelaps):
        return EveryWrapper(unit=unit, timelaps=timelaps)

    def cancel(self, jobsName:list):
        jobList = [job.stop() for jobName, job in self.jobs.items() if jobName in jobsName]
        self.logger("{0} : the following jobs have been stopped : {1}".format(self.Name, jobList))

    def run_forever(self):
        self.loop.run_forever()

    def stop(self):
        jobList, _ = [(jobName, job.stop()) for jobName, job in self.jobs.items() if job.is_running], []
        self.logger.info("{0} : at '{1}' the following jobs have been stopped : {2}".format(self.Name, datetime.utcnow(), jobList))
        self.loop.stop()
        while True:
            if not self.loop.is_running():
                break
            sleep(0.1)
        self.loop.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()
        return



#================================================================
if __name__ == "__main__":
    from common.Helpers.helpers import init_logger, threadIt
    name="SafeScheduler"
    configStr="common"
    #config="trading"
    config, logger = init_logger(name=name, config=configStr)

    xy = 0 
    def syncFunc():
        global xy
        xy+=1

    async def asyncFunc():
        global xy
        xy+=1
        await asyncSleep(0.001)
    
    @threadIt
    def stopIt(schedule):
        sleep(5)
        schedule.stop()

# with main Process 
    schedule = ScheduledJobs(config=config, logger=logger, mainProcess=True)
    ## 1-sync function, no wait : 41483.2 executions in 1 second !!
    schedule.every(unit=0.01, timelaps='milliseconds').do(func=syncFunc)
    schedule.every(unit=0.01, timelaps='milliseconds').do(func=syncFunc, rerun_on_error=True)
    schedule.every(unit=5, timelaps='milliseconds').do(func=syncFunc, rerun_on_error=True, on_time=True, wait_end=True)
    schedule.every(unit=4, timelaps='milliseconds').do(func=syncFunc, rerun_on_error=True, on_time=True)
    schedule.every(unit=0.01, timelaps='milliseconds').do(func=syncFunc, rerun_on_error=True, wait_end=True)
    schedule.every(unit=4, timelaps='milliseconds').do(func=syncFunc, on_time=True, wait_end=True)
    schedule.every(unit=5, timelaps='milliseconds').do(func=syncFunc, on_time=True)
    schedule.every(unit=0.01, timelaps='milliseconds').do(func=syncFunc, wait_end=True)

    ## 2- async function only
    schedule.every(unit=0.01, timelaps='milliseconds').do(func=asyncFunc, rerun_on_error=True)
    schedule.every(unit=0.01, timelaps='second').do(func=asyncFunc)
    schedule.every(unit=0.1, timelaps='second').do(func=asyncFunc, rerun_on_error=True, on_time=True, wait_end=True)
    schedule.every(unit=0.001, timelaps='second').do(func=asyncFunc, rerun_on_error=True, on_time=True)
    schedule.every(unit=0.001, timelaps='seconds').do(func=asyncFunc, rerun_on_error=True, wait_end=True)
    schedule.every(unit=4, timelaps='millisecond').do(func=asyncFunc, on_time=True, wait_end=True)
    schedule.every(unit=0.5, timelaps='second').do(func=asyncFunc, on_time=True)
    schedule.every(unit=10, timelaps='milliseconds').do(func=asyncFunc, wait_end=True)

    stopIt(schedule)
    schedule.run_forever()
    
    print(float(xy/5))
    


