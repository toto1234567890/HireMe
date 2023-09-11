#!/usr/bin/env python
# coding:utf-8

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from flask import Flask, render_template

class TaskScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

    def add_task(self, task, interval_seconds):
        self.scheduler.add_job(task, "interval", seconds=interval_seconds)

    def add_cron_task(self, task, cron_expression):
        self.scheduler.add_job(task, "cron", year='*', month='*', day='*', week='*', day_of_week='*', hour='*', minute='*', second='*', start_date=datetime.now(), end_date=None, timezone=None, jitter=None, id=None, coalesce=False, max_instances=1, misfire_grace_time=None, next_run_time=None, jobstore='default', executor='default', args=None, kwargs=None)

    def remove_all_tasks(self):
        self.scheduler.remove_all_jobs()

    def shutdown(self):
        self.scheduler.shutdown()

app = Flask(__name__)
scheduler = TaskScheduler()

@app.route('/')
def index():
    return render_template('index.html', jobs=scheduler.scheduler.get_jobs())

if __name__ == '__main__':
    from threading import Thread

    # Start the web server on a separate thread
    server_thread = Thread(target=app.run)
    server_thread.start()

    # Add some tasks to the scheduler
    def my_task():
        print("Running task...")

    scheduler.add_task(my_task, 10)
    scheduler.add_cron_task(my_task, "0 0 * * *")
