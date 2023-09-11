#!/usr/bin/env python
# coding:utf-8

import os
from genericpath import exists

# relative import
from sys import path;path.extend("..")
from common.Helpers.helpers import getOrDefault, threadIt

LOST_QMSG_DIR = os.path.join(os.getcwd(), "logs", "lost")

@threadIt
def LostQmsg(Qmsg):
    global LOST_QMSG_DIR
    if not exists(LOST_QMSG_DIR):
        os.mkdir(LOST_QMSG_DIR)
    with open(os.path.join(LOST_QMSG_DIR, "{0}.Qmsg".format(Qmsg.id)), 'w') as file:
        file.write(str(Qmsg.__dict__))


def starQ_route_msg(self, cur_msg, QueuesOut):#, logger:MyLogger):
    try :
        QueuesOut[cur_msg.too].append(cur_msg)
        self.logger.info("StarQs : sent message id '{0}' from '{1}' to '{2}'".format(cur_msg.id, cur_msg.frome, cur_msg.too))
    except Exception as e:
        self.logger.critical("StarQs : error while trying to route message id '{0}' in Threads Queues '{1}' : {2}".format(getOrDefault(cur_msg.id, "#None"), cur_msg.too, e))
        if not (cur_msg.too in QueuesOut):
            self.logger.critical("StarQs : threads Queue '{0}' doesn't exist in subscribers StarQs...".format(cur_msg.too))

        self.logger.critical("StarQs : message id '{0}' has been lost !!!".format(getOrDefault(cur_msg.id, "#None")))
        LostQmsg(cur_msg)


#================================================================
if __name__ == "__main__":
    pass