#!/usr/bin/env python
# coding:utf-8

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from asyncio import sleep as asyncSleep, wrap_future as asyncioWrap_future


##########################################################################
# sync loops
# run sync task, do not check time, do not wait for end
async def runTaskSync(obj, interval):
    Interval = interval.total_seconds()
    while True:
        if not obj.is_running:
            break
        obj.exec_job()
        await asyncSleep(Interval)

# run sync task, do not check time, wait for end
async def runTaskSyncWaitEnd(obj, interval, loop):
    Interval = interval.total_seconds()
    while True:
        if not obj.is_running:
            break
        try:_ = await loop.run_in_executor(None, obj.exec_job())
        except:break
        await asyncSleep(Interval)

# run sync task, check time, do not wait for end
async def runTaskSyncOnTime(obj, interval):
    next_next_run = None
    while True:
        if not obj.is_running:
            break
        obj.next_run = datetime.utcnow() + interval
        next_next_run = obj.next_run + interval
        obj.exec_job()
        if datetime.utcnow() > next_next_run:
            obj.logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format(obj.Name, obj.jobName, obj.next_run))
            break
        if datetime.utcnow() > obj.next_run:
            obj.logger.warning("{0} : scheduled job '{1}' starts with delay, starting now but should runs at : {2}".format(obj.Name, obj.jobName, obj.next_run))
            obj.exec_job()
            if datetime.utcnow() > next_next_run:
                obj.logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format(obj.Name, obj.jobName, obj.next_run))
                return
            obj.next_run = next_next_run
        wait = obj.next_run - datetime.utcnow()
        await asyncSleep(wait.total_seconds())

# run sync task, check time, wait for end
async def runTaskSyncOnTimeWaitEnd(obj, interval, loop):
    next_next_run = None
    while True:
        if not obj.is_running:
            break
        obj.next_run = datetime.utcnow() + interval
        next_next_run = obj.next_run + interval
        try:_ = await loop.run_in_executor(None, obj.exec_job())
        except:break
        if datetime.utcnow() > next_next_run:
            obj.logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format(obj.Name, obj.jobName, obj.next_run))
            break
        if datetime.utcnow() > obj.next_run:
            obj.logger.warning("{0} : scheduled job '{1}' starts with delay, starting now but should runs at : {2}".format(obj.Name, obj.jobName, obj.next_run))
            try:_ = await loop.run_in_executor(None, obj.exec_job())
            except:break
            if datetime.utcnow() > next_next_run:
                obj.logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format(obj.Name, obj.jobName, obj.next_run))
                return
            obj.next_run = next_next_run
        wait = obj.next_run - datetime.utcnow()
        await asyncSleep(wait.total_seconds())

##########################################################################
# Async loops
# run Async task, do not check time, do not wait for end
async def runTaskAsync(obj, interval, loop):
    executor = ThreadPoolExecutor()
    Interval = interval.total_seconds()
    while True:
        if not obj.is_running:
            break
        #try: _ = await obj.asyncExec_job()
        #except:break
        doNotWaitEnds = loop.run_in_executor(executor, obj.asyncExec_job())
        _ = asyncioWrap_future(doNotWaitEnds)
        await asyncSleep(Interval)

# run Async task, do not check time, wait for end
async def runTaskAsyncWaitEnd(obj, interval):
    Interval = interval.total_seconds()
    while True:
        if not obj.is_running:
            break
        _ = await obj.asyncExec_job()
        await asyncSleep(Interval)

# run Async task, check time, do not wait for end
async def runTaskAsyncOnTime(obj, interval, loop):
    next_next_run = None
    while True:
        if not obj.is_running:
            break
        obj.next_run = datetime.utcnow() + interval
        next_next_run = obj.next_run + interval
        doNotWaitEnds = loop.run_in_executor(None, obj.asyncExec_job())
        _ = asyncioWrap_future(doNotWaitEnds)
        if datetime.utcnow() > next_next_run:
            obj.logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format(obj.Name, obj.jobName, obj.next_run))
            break
        if datetime.utcnow() > obj.next_run:
            obj.logger.warning("{0} : scheduled job '{1}' starts with delay, starting now but should runs at : {2}".format(obj.Name, obj.jobName, obj.next_run))
            _ = await obj.asyncExec_job()
            if datetime.utcnow() > next_next_run:
                obj.logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format(obj.Name, obj.jobName, obj.next_run))
                return
            obj.next_run = next_next_run
        wait = obj.next_run - datetime.utcnow()
        await asyncSleep(wait.total_seconds())

# run Async task, check time, wait for end
async def runTaskAsyncOnTimeWaitEnd(obj, interval):
    next_next_run = None
    while True:
        if not obj.is_running:
            break
        obj.next_run = datetime.utcnow() + interval
        next_next_run = obj.next_run + interval
        _ = await obj.asyncExec_job()
        if datetime.utcnow() > next_next_run:
            obj.logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format(obj.Name, obj.jobName, obj.next_run))
            break
        if datetime.utcnow() > obj.next_run:
            obj.logger.warning("{0} : scheduled job '{1}' starts with delay, starting now but should runs at : {2}".format(obj.Name, obj.jobName, obj.next_run))
            _ = await obj.asyncExec_job()
            if datetime.utcnow() > next_next_run:
                obj.logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format(obj.Name, obj.jobName, obj.next_run))
                return
            obj.next_run = next_next_run
        wait = obj.next_run - datetime.utcnow()
        await asyncSleep(wait.total_seconds())



