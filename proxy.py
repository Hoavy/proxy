#!/usr/bin/env python
# coding: utf-8
import socket, re, sys, threading
from optparse import OptionParser

class Log():
    def __init__(self,msg):
        if verbose:
            with threading.Lock():
                print msg

class ParserClass():
    def __init__(self):
        self.re_ip_port = r'^(?P<addr>.+:)?(?P<port>[0-9]{1,5})$'
    
    def pares(self):
        
        parser = OptionParser(usage='%prog -l [host:]port -r host:port [-v]', version='%prog 0.1')
        parser.add_option('-l', dest='local', help='local addr(optional) & port: 0.0.0.0:8208 or 8208')
        parser.add_option('-r', dest='remote', help='remote addr & & port: 0.0.0.0:3306 or 3306')
        parser.add_option('-v', dest='verbose', default=False, action='store_true', help='print stat to screen')
        
        (options, args) = parser.parse_args()
        if not options.local or not options.remote:
            parser.print_usage()
            sys.exit(-1)
            
        x = re.match(self.re_ip_port, options.local)
        if not x:
            parser.error('local addr port parser error!')
        local_addr = x.group('addr') or '0.0.0.0'
        local_addr = local_addr.rstrip(':')
        
        local_port = x.group('port')
        if not local_port:
            parser.error('local port error!')
        local_port = int(local_port)
        
        
        x = re.match(self.re_ip_port, options.remote)
        if not x:
            parser.error('remote addr port parser error')
        remote_addr = x.group('addr') or '0.0.0.0'
        remote_addr = remote_addr.rstrip(':')
        
        remote_port = x.group('port')
        if not remote_port:
            parser.error('remote port error')
        remote_port = int(remote_port)
        
        verbose = options.verbose
        
        return local_addr,local_port,remote_addr,remote_port,verbose
    
class Dispatch(threading.Thread):
    def __init__(self, sock_in, sock_out, name):
        threading.Thread.__init__(self)
        self.sock_in = sock_in
        self.sock_out = sock_out
        self.name = name
        self.maxpack = 1024*4
        
    def run(self):
        addr_in = '%s:%d' % self.sock_in.getpeername()
        addr_out = '%s:%d' % self.sock_out.getpeername()
        
        while True:
            try:
                data = self.sock_in.recv(self.maxpack)
            except Exception, e:
                Log('Dispatch Socket read error of %s: %s' % (addr_in, str(e)))
                break
    
            if not data:
                Log('Dispatch Socket closed by %s: %s ' % (addr_in,self.name))
                break
            
            try:
                self.sock_out.sendall(data)
            except Exception, e:
                Log('Dispatch Socket write error of %s: %s' % (addr_out, str(e)))
                break
    
            Log('%s => %s (%d bytes) %s ' % (addr_in, addr_out, len(data), self.name))
            
        try:
            self.sock_out.shutdown(2)
        except Exception, e:
            self.sock_out.close()
        try:
            self.sock_in.shutdown(2)
        except Exception, e:
            self.sock_in.close()

class Proxy(threading.Thread):
    def __init__(self,socket,remote_addr,remote_port):
        threading.Thread.__init__(self)
        self.sock_in = socket
        self.remote_addr = remote_addr
        self.remote_port = remote_port
        
    def run(self):
        sock_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock_out.connect((remote_addr, remote_port))
        except socket.error, e:
            self.sock_in.close()
            Log('Remote error: %s' % str(e))
            return

        t = Dispatch(self.sock_in, sock_out, 'local -> remote')
        t.start()
        
        t = Dispatch(sock_out, self.sock_in, 'remote -> local')
        t.start()



if __name__ == '__main__':
    local_addr, local_port, remote_addr, remote_port, verbose = ParserClass().pares()
    
    try:
        sock_master = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_master.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    except socket.error,e:
        print 'Strange error creating socket: %s' % str(e)
        sys.exit(1)
    try:
        sock_master.bind((local_addr, local_port))
        sock_master.listen(5)
    except socket.error,e:
        print 'socket bind error : %s' % str(e)
        sock_master.close()
        sys.exit(1)
        
    Log('Listening at %s:%d ...' % (local_addr, local_port))
    
    while True:
        try:
            sock, addr = sock_master.accept()
        except (KeyboardInterrupt, SystemExit):
            Log('Closing master')
            sock_master.close()
            sys.exit(1)
            
        t = Proxy(sock,remote_addr, remote_port)
        t.start()
        #t.join(10)
        Log('New clients from %s:%d' % addr)
    