#!/usr/bin/env python
# coding:utf-8

from retry.compat import decorator
from functools import partial

# relative import
from sys import path;path.extend("..")
from common.Helpers.retrye import Tele_retry, aTele_retry, Feeder_retry, SslTunnel_retry
from common.TeleRemote.tele_funcs import POWER_OFF, CLOSE_ALL_POSITION_CONFIRMATION

###################################################################
######################## Get My Public IP  ########################
# FIXME create func my get DNS server and ask for my publique IP
# https://unix.stackexchange.com/questions/22615/how-can-i-get-my-external-ip-address-in-a-shell-script/81699#81699
# OpenDNS (since 2009)
#$ dig @resolver3.opendns.com myip.opendns.com +short
#$ dig @resolver4.opendns.com myip.opendns.com +short
## Akamai (since 2009)
#$ dig @ns1-1.akamaitech.net ANY whoami.akamai.net +short
## Akamai approximate
## NOTE: This returns only an approximate IP from your block,
## but has the benefit of working with private DNS proxies.
#$ dig +short TXT whoami.ds.akahelp.net
## Google (since 2010)
## Supports IPv6 + IPv4, use -4 or -6 to force one.
#$ dig @ns1.google.com TXT o-o.myaddr.l.google.com +short
from os import name as osName, popen as osPopen
from re import match as reMatch
from itertools import cycle
from requests import get as requestsGet
def get_my_public_ip(logger=None):
    myPublicIP = ""
    # FIXME => get my dns server, to get my IP
    if osName != 'nt':
        # dig command  =>  +time=1 +tries=1  =>  timeout 1 seconde, 1 tries....
        DNS_servers = [
            #"dig +time=1 +tries=1 @resolver1.opendns.com myip.opendns.com +short", IPV6
            #"dig +time=1 +tries=1 @resolver2.opendns.com myip.opendns.com +short", IPV6
            "dig +time=1 +tries=1 @resolver3.opendns.com myip.opendns.com +short", 
            "dig +time=1 +tries=1 @resolver4.opendns.com myip.opendns.com +short",
            "dig +time=1 +tries=1 @ns1-1.akamaitech.net ANY whoami.akamai.net +short",
            "dig +time=1 +tries=1 @ns1.google.com TXT o-o.myaddr.l.google.com +short",
        ]
        DNS_Iter = cycle(DNS_servers)
        cpt = 0
        while True:
            if cpt > 12:
                break
            try:
                myPublicIP = str.strip(osPopen(next(DNS_Iter)).read()).replace('"', '')
                if reMatch(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', myPublicIP):
                    # unix
                    return myPublicIP
            except:
                pass
            cpt += 1
        if not logger is None:
            logger.error("Get public IP : unable to get public IP from DNS servers list {0}".format(DNS_servers))
            return 
        else:
            raise "Unable to get public IP from DNS servers list {0}".format(DNS_servers)
    else:
        try:
            # "nslookup -timeout=1 myip.opendns.com resolver3.opendns.com" osPopen().read() doesn't works...
            return (str.strip((requestsGet('https://ipinfo.io/json').text).split(':')[1]).split(',')[0]).replace('"','')
        except Exception as e:
            if not logger is None:
                logger.error("Get public IP : 'Unable to get public IP from https://ipinfo.io/json'")
                return
            else:
                raise "Unable to get public IP from 'https://ipinfo.io/json'"
######################## Get My Public IP  ########################
####################################################################
################## Secure socket Layer local  ######################
import ssl
def SSL_client_context():
    context = ssl.SSLContext()
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    context.load_default_certs()
    return context
################## Secure socket Layer local  ######################
####################################################################
################## Secure socket Layer local  ######################
from os import getcwd as osGetcwd
from os.path import join as osPathJoin
def SSL_server_context(keyPath=None, certPath=None):
    # https://support.microfocus.com/kb/doc.php?id=7013103
    # How to create a self-signed PEM file: 
    # openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -keyout key.pem -out cert.pem  
    if keyPath == None or certPath == None:
        if keyPath == None:
            keyPath = osPathJoin(osGetcwd(), "common", "SslTunnel", "key.pem") 
        if certPath == None:
            certPath = osPathJoin(osGetcwd(), "common", "SslTunnel", "cert.pem") 
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=certPath, keyfile=keyPath)
    return context
################## Secure socket Layer local  ######################
####################################################################
################## Secure socket Layer local  ######################
def SSL_test_context():
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context
################## Secure socket Layer local  ######################
####################################################################
################# Ignore socket Timeout  ###########################
import socket
def continueOnTimeOut(sock, logger):
    try:
        msg = sock.recv()
        return msg
    except socket.timeout:
        return None
    except Exception as e:
        logger.critical("Socket : error while trying to received message : {0}".format(e))
################# Ignore socket Timeout  ###########################
####################################################################
################# check if service is started ######################
def is_service_listen(server, port, timeout=1):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.SOL_TCP)
        sock.settimeout(timeout)
        sock.connect((server, int(port)))
        sock.close()
        return True
    except Exception as e:
        print(e)
        if not sock is None:
            sock.close()
        return False
################# check if service is started ######################
####################################################################
########### Insure correct exchange between sockets  ###############
import pickle, struct
class SafeSocket:
    """ Default split message = '>L' ?? """
    Name = "safeSocket"
    def __init__(self, conn, name=None):
        if not name is None: 
            self.Name = name
        self.pickle = pickle
        self.struct = struct
        self.conn = conn
    def send_data(self, data):
        serialized_data = self.pickle.dumps(data)
        self.conn.sendall(self.struct.pack('>L', len(serialized_data)))
        self.conn.sendall(serialized_data)
    def receive_data(self):
        #while True:           
        chunk = self.conn.recv(4)
        if len(chunk) < 4:
            #break
            return False
        slen = self.struct.unpack('>L', chunk)[0]
        chunk = self.conn.recv(slen)
        while len(chunk) < slen:
            chunk = chunk + self.conn.recv(slen - len(chunk))
        return self.pickle.loads(chunk)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        if not self.conn._closed:
            self.conn.close()
########### Insure correct exchange between sockets  ###############
####################################################################
######### Insure correct exchange between async sockets  ###########
class SafeAsyncSocket:
    """ Default split message = '>L' ?? """
    Name = "safeSocket"
    def __init__(self, reader, writer, name=None):
        if not name is None: 
            self.Name = name
        self.pickle = pickle
        self.struct = struct
        self.reader = reader
        self.writer = writer
    def send_data_sync(self, data):
        serialized_data = self.pickle.dumps(data)
        slen = self.struct.pack('>L', len(serialized_data))
        self.writer._transport.write(slen)
        self.writer._transport.write(serialized_data)
    async def send_data(self, data):
        serialized_data = self.pickle.dumps(data)
        slen = self.struct.pack('>L', len(serialized_data))
        self.writer.write(slen)
        await self.writer.drain()
        self.writer.write(serialized_data)
        await self.writer.drain()
    async def receive_data(self):           
        chunk = await self.reader.read(4)
        if len(chunk) < 4:
            return False
        slen = self.struct.unpack('>L', chunk)[0]
        chunk = await self.reader.read(slen)
        while len(chunk) < slen:
            chunk = chunk + await self.reader.read(slen - len(chunk))
        return self.pickle.loads(chunk)
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        self.writer.close()
        await self.writer.wait_closed()
######### Insure correct exchange between async sockets  ###########
####################################################################
###### Insure correct exchange between Pipe MultiProcess  ##########
class SafePipe:
    def __init__(self, conn):
        self.pickle = pickle
        self.struct = struct
        self.conn = conn
    def send_data(self, data):
        serialized_data = self.pickle.dumps(data)
        self.conn.send_bytes(self.struct.pack('>L', len(serialized_data)), size=4)
        self.conn.send_bytes(serialized_data, size=len(serialized_data))
    def receive_data(self):
        while True:           
            chunk = self.conn.recv_bytes(maxlength=4)
            if len(chunk) < 4:
                break
            slen = self.struct.unpack('>L', chunk)[0]
            chunk = self.conn.recv_bytes(maxlength=slen)
            while len(chunk) < slen:
                chunk = chunk + self.conn.recv_bytes(maxlength=(slen - len(chunk)))
            return self.pickle.loads(chunk)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        if not self.conn._closed:
            self.conn.close()
###### Insure correct exchange between Pipe MultiProcess  ##########
####################################################################
#### Reconnect starQs with telecommand in case of problems  ########
def stickySslTunnel(exceptions=Exception, tries=-1, delay=1, max_delay=None, backoff=1, jitter=0):
    @decorator
    def retry_decorator(f, *fargs, **fkwargs):
        args = fargs if fargs else list()
        kwargs = fkwargs if fkwargs else dict()
        # (args[0]) = self = current starQs
        if (args[0]).state != CLOSE_ALL_POSITION_CONFIRMATION.starQs_message and (args[0]).state != POWER_OFF.starQs_message:
            return SslTunnel_retry(partial(f, *args, **kwargs), exceptions, tries, delay, max_delay, backoff, jitter, clsPtr=(args[0]))
        else:
            return
    return retry_decorator
#### Reconnect starQs with telecommand in case of problems  ########
####################################################################
#### Reconnect starQs with telecommand in case of problems  ########
def stickyTelecommand(exceptions=Exception, tries=-1, delay=1, max_delay=None, backoff=1, jitter=0):
    @decorator
    def retry_decorator(f, *fargs, **fkwargs):
        args = fargs if fargs else list()
        kwargs = fkwargs if fkwargs else dict()
        # (args[0]) = self = current starQs
        if (args[0]).state != CLOSE_ALL_POSITION_CONFIRMATION.starQs_message and (args[0]).state != POWER_OFF.starQs_message:
            return Tele_retry(partial(f, *args, **kwargs), exceptions, tries, delay, max_delay, backoff, jitter, clsPtr=(args[0]))
        else:
            return
    return retry_decorator
#### Reconnect starQs with telecommand in case of problems  ########
####################################################################
#### Reconnect starQs with telecommand in case of problems  ########
def aStickyTelecommand(exceptions=Exception, tries=-1, delay=1, max_delay=None, backoff=1, jitter=0, clsPtr=None):
    @decorator
    async def retry_decorator(f, *fargs, **fkwargs):
        args = fargs if fargs else list()
        kwargs = fkwargs if fkwargs else dict()
        # (args[0]) = self = current starQs
        if (args[0]).state != CLOSE_ALL_POSITION_CONFIRMATION.starQs_message and (args[0]).state != POWER_OFF.starQs_message:
            return await aTele_retry(partial(f, *args, **kwargs), exceptions, tries, delay, max_delay, backoff, jitter, clsPtr=(args[0]))
    return retry_decorator
#### Reconnect starQs with telecommand in case of problems  ########
####################################################################
######## stickySocket reconnect socket in case of problem  #########
def MyStickySocket(exceptions=Exception, tries=-1, delay=1, max_delay=None, backoff=1, jitter=0, dequeSockets=None, retryFunc=Feeder_retry):
    @decorator
    def retry_decorator(f, *fargs, **fkwargs):
        args = fargs if fargs else list()
        kwargs = fkwargs if fkwargs else dict()
        # (args[0]) = self = current InstanceObj | (args[1]) = first argument of the function
        sockName = args[1]
        server = args[2]
        port = args[3]
        if not dequeSockets is None:
            pass
        else:
            return retryFunc(partial(f, *args, **kwargs), exceptions, tries, delay, max_delay, backoff, jitter, clsPtr=(args[0]), sockName=sockName, server=server, port=port)   
    return retry_decorator
######## stickySocket reconnect socket in case of problem  #########
####################################################################
############# create custom generic socket connection ##############
def MySocket(name:str=None, server:str="127.0.0.1", port:int=54321, timeout:int=None):
    MySock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.SOL_TCP) 
    MySock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if not timeout is None:
        MySock.settimeout(timeout)
    if server != "127.0.0.1" and server.lower() != "localhost":
        context = SSL_test_context() if server.startswith('192.168.1.') or server.startswith('192.168.0.') else SSL_client_context()
        MySslSock = context.wrap_socket(MySock, server_hostname=server)
        MySslSock.connect((server, int(port)))
        if name is None:name = "sock_{0}".format(MySock.getsockname()[1])
        return SafeSocket(conn=MySslSock, name=name)
    else:   
        MySock.connect((server, int(port)))
        if name is None:name = "sock_{0}".format(MySock.getsockname()[1])
        return SafeSocket(conn=MySock, name=name)
############# create custom generic socket connection ##############
####################################################################
############### create custom generic socket object ################
class MySocketObj(socket.socket):
    Name = "MySocketObj"
    def __init__(self, name:str=None, timeout:int=None):
        super().__init__(socket.AF_INET, socket.SOCK_STREAM, socket.SOL_TCP)
        if not name is None:
            self.Name = name
        self.context = None
        self.pickle = pickle
        self.struct = struct
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if not timeout is None: 
            self.settimeout(timeout)
    def make_connection(self, server:str="127.0.0.1", port:int=54321):
        if server != "127.0.0.1" and server.lower() != "localhost":
            self.context = SSL_test_context() if server.startswith('192.168.1.') or server.startswith('192.168.0.') else SSL_client_context()
            self.context.wrap_socket(self, server_hostname=server)
            self.connect((server, int(port)))
        else:   
            self.connect((server, int(port)))
        if self.Name is None:
            self.Name = "sock_{0}".format(self.getsockname()[1])
        return self
    def send_data(self, data):
        serialized_data = self.pickle.dumps(data)
        self.sendall(self.struct.pack('>L', len(serialized_data)))
        self.sendall(serialized_data)
    def receive_data(self):       
        chunk = self.recv(4)
        if len(chunk) < 4:
            return False
        slen = self.struct.unpack('>L', chunk)[0]
        chunk = self.recv(slen)
        while len(chunk) < slen:
            chunk = chunk + self.recv(slen - len(chunk))
        return self.pickle.loads(chunk)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        if not self._closed:
            self.close()
############### create custom generic socket object ################
####################################################################
############ create custom generic async socket object #############
from asyncio import open_connection as asyncioOpen_connection
class MyAsyncSocketObj:
    Name = "MyAsyncSocketObj"
    def __init__(self, name=None, ):
        if not name is None:
            self.Name = name
        self.host = None ; self.port = None
        self.reader = None
        self.writer = None
        self.sock_info = None
        self.pickle = pickle
        self.struct = struct
    async def make_connection(self, server:str="127.0.0.1", port:int=54321):
        self.host = server
        self.port = port
        self.reader, self.writer = await asyncioOpen_connection(server, port)
        self.sock_info = (self.writer.get_extra_info('socket')).getsockname()
        return self
    async def send_data(self, data):
        serialized_data = self.pickle.dumps(data)
        self.writer.write(self.struct.pack('>L', len(serialized_data)))
        self.writer.write(serialized_data)
        await self.writer.drain()
    async def receive_data(self):
        chunk = await self.reader.read(4)
        if len(chunk) < 4:
            return False
        slen = self.struct.unpack('>L', chunk)[0]
        chunk = await self.reader.read(slen)
        while len(chunk) < slen:
            chunk = chunk + await self.reader.read(slen - len(chunk))
        return self.pickle.loads(chunk)
    async def close_connection(self):
        if not self.writer is None:
            self.writer.close()
            await self.writer.wait_closed()
        self.reader = None
        self.writer = None
    async def __aenter__(self):
        return await self.make_connection(self.host, self.port)
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_connection()
############ create custom generic async socket object #############
####################################################################