#!/usr/bin/env python
# coding:utf-8

from sys import path;path.extend("..")
from common.Helpers.network_helpers import MySocket
from uuid import uuid4

class Qmsg:
    def __init__(self, msg, frome, too, ackw=None, priority=False):
        self.id = uuid4()
        self.msg = msg
        self.frome = frome
        self.too = too
        self.ackw = ackw
        self.priority = priority

#with MySocket(name="MT5 testeur", port=10000, server='192.168.1.102') as sockTest:
#    sockTest.send_data(data="MT5Tester:127.0.0.1:{0}".format(sockTest.conn.getsockname()[1]))
#    data = Qmsg(msg="QUOTE|EURCHF", frome="MT5Tester", too="MT5Server")
#    sockTest.send_data(data=data)
#    while True:
#        val = sockTest.receive_data()
#        print("{0}".format(val))    
 

with MySocket(name="MT5 testeur 7", port=10000, server='192.168.1.102') as sockTest:
    sockTest.send_data(data="MT5Tester 7:127.0.0.1:{0}".format(sockTest.conn.getsockname()[1]))
    data = Qmsg(msg="QUOTE|EURCHF", frome="MT5Tester", too="MT5Server")
    sockTest.send_data(data=data)
    while True:
        val = sockTest.receive_data()
        print("{0}".format(val))    

#with MySocket(name="MT5 testeur", port=10000, server='192.168.1.102') as sockTest:
#    sockTest.send_data(data="MT5Tester:127.0.0.1:{0}".format(sockTest.conn.getsockname()[1]))
#    data = Qmsg(msg="SELL|EURCHF|0.1", frome="MT5Tester", too="MT5Server")
#    sockTest.send_data(data=data)
#    val = sockTest.receive_data()
#    print("{0} - {1} - {2}".format(val.id, val.frome, val.msg))    
