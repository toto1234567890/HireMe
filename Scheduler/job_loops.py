#!/usr/bin/env python
# coding:utf-8

from datetime import datetime
from asyncio import sleep as asyncSleep, get_running_loop as asyncioGet_running_loop


##########################################################################
# sync loops
# run sync task, do not check time, do not wait for end
async def runTaskSync(interval, obj=None, func=None, *args, **kwargs):
    Interval = interval.total_seconds()
    if not func is None:
        while True:
            func(*args, **kwargs)
            await asyncSleep(Interval)    
    else:
        while True:
            if not obj.is_running:
                break
            obj.exec_job()
            await asyncSleep(Interval)

# run sync task, do not check time, wait for end
async def runTaskSyncWaitEnd(interval, obj=None, loop=None, func=None, *args, **kwargs):
    if loop is None : loop = asyncioGet_running_loop()
    Interval = interval.total_seconds()
    if not func is None:
        while True:
            try:_ = await loop.run_in_executor(None, func(*args, **kwargs))
            except:break
            await asyncSleep(Interval)
    else:
        while True:
            if not obj.is_running:
                break
            try:_ = await loop.run_in_executor(None, obj.exec_job())
            except:break
            await asyncSleep(Interval)

# run sync task, check time, do not wait for end
async def runTaskSyncOnTime(interval, obj=None, func=None, logger=None, *args, **kwargs):
    next_next_run = None
    if not func is None:
        while True:
            next_run = datetime.utcnow() + interval
            next_next_run = next_run + interval
            func(*args, **kwargs)
            if datetime.utcnow() > next_next_run:
                if not logger is None:
                    logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format("job_loops", func.__name__, next_run))
                break
            if datetime.utcnow() > next_run:
                if not logger is None:
                    logger.warning("{0} : scheduled job '{1}' starts with delay, starting now but should runs at : {2}".format("job_loops", func.__name__, next_run))
                func(*args, **kwargs)
                if datetime.utcnow() > next_next_run:
                    if not logger is None:
                        logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format("job_loops", func.__name__, next_run))
                    return
                next_run = next_next_run
            wait = next_run - datetime.utcnow()
            await asyncSleep(wait.total_seconds())
    else:
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
async def runTaskSyncOnTimeWaitEnd(interval, obj=None, loop=None, func=None, logger=None, *args, **kwargs):
    if loop is None : loop = asyncioGet_running_loop()
    next_next_run = None
    if not func is None:
           while True:
            next_run = datetime.utcnow() + interval
            next_next_run = next_run + interval
            try:_ = await loop.run_in_executor(None, func(*args, **kwargs))
            except:break
            if datetime.utcnow() > next_next_run:
                if not logger is None:
                    logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format("job_loops", func.__name__, next_run))
                break
            if datetime.utcnow() > next_run:
                if not logger is None:
                    logger.warning("{0} : scheduled job '{1}' starts with delay, starting now but should runs at : {2}".format("job_loops", func.__name__, next_run))
                try:_ = await loop.run_in_executor(None, func(*args, **kwargs))
                except:break
                if datetime.utcnow() > next_next_run:
                    if not logger is None:
                        logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format("job_loops", func.__name__, next_run))
                    return
                next_run = next_next_run
            wait = next_run - datetime.utcnow()
            await asyncSleep(wait.total_seconds()) 
    else:
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
async def runTaskAsync(interval, obj=None, loop=None, func=None, *args, **kwargs):
    if loop is None: loop = asyncioGet_running_loop()
    Interval = interval.total_seconds()
    if not func is None:
        while True:
            loop.create_task(func(*args, **kwargs))
            await asyncSleep(Interval)
    else:
        while True:
            if not obj.is_running:
                break
            loop.create_task(obj.asyncExec_job())
            await asyncSleep(Interval)

# run Async task, do not check time, wait for end
async def runTaskAsyncWaitEnd(interval, obj=None, func=None, *args, **kwargs):
    Interval = interval.total_seconds()
    if not func is None:
        while True:
            _ = await func(*args, **kwargs)
            await asyncSleep(Interval)    
    else:
        while True:
            if not obj.is_running:
                break
            _ = await obj.asyncExec_job()
            await asyncSleep(Interval)

# run Async task, check time, do not wait for end
async def runTaskAsyncOnTime(interval, obj=None, loop=None, func=None, logger=None, *args, **kwargs):
    if loop is None: loop = asyncioGet_running_loop()
    next_next_run = None
    if not func is None:
        while True:
            next_run = datetime.utcnow() + interval
            next_next_run = next_run + interval
            loop.create_task(func(*args, **kwargs))
            if datetime.utcnow() > next_next_run:
                if not logger is None:
                    logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format("job_loops", func.__name__, next_run))
                break
            if datetime.utcnow() > next_run:
                if not logger is None:
                    logger.warning("{0} : scheduled job '{1}' starts with delay, starting now but should runs at : {2}".format("job_loops", func.__name__, next_run))
                _ = await func(*args, **kwargs)
                if datetime.utcnow() > next_next_run:
                    if not logger is None:
                        logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format("job_loops", func.__name__, next_run))
                    return
                next_run = next_next_run
            wait = next_run - datetime.utcnow()
            await asyncSleep(wait.total_seconds())
    else:
        while True:
            if not obj.is_running:
                break
            obj.next_run = datetime.utcnow() + interval
            next_next_run = obj.next_run + interval
            loop.create_task(obj.asyncExec_job())
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
async def runTaskAsyncOnTimeWaitEnd(interval, obj=None, func=None, logger=None, *args, **kwargs):
    next_next_run = None
    if not func is None:
        while True:
            next_run = datetime.utcnow() + interval
            next_next_run = next_run + interval
            _ = await func(*args, **kwargs)
            if datetime.utcnow() > next_next_run:
                if not logger is None:
                    logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format("job_loops", func.__name__, next_run))
                break
            if datetime.utcnow() > next_run:
                if not logger is None:
                    logger.warning("{0} : scheduled job '{1}' starts with delay, starting now but should runs at : {2}".format("job_loops", func.__name__, next_run))
                _ = await func(*args, **kwargs)
                if datetime.utcnow() > next_next_run:
                    if not logger is None:
                        logger.warning("{0} : scheduled job '{1}' starts with too much delay it will stops, starting now but should runs at : {2}, please reschedule job with longer time interval...".format("job_loops", func.__name__, next_run))
                    return
                next_run = next_next_run
            wait = next_run - datetime.utcnow()
            await asyncSleep(wait.total_seconds())
    else:
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


#================================================================
if __name__ == "__main__":
    from datetime import timedelta
    from asyncio import run as asyncioRun
    from common.Helpers.helpers import init_logger

    config, logger = init_logger(name="testSchedule", config="current")

    def exec_job(teh=None, msg="coucou", msg2="toi"):
            teh.error(msg + " " + msg2)

    asyncioRun(runTaskSync(interval=timedelta(seconds=5), func=exec_job, teh=logger, msg="essai", msg2="qui fonctionne ?"))
