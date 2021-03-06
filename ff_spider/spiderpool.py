# #*** <License> ************************************************************#
# This module is part of the repository CNDB.
#
# This module is licensed under the terms of the BSD 3-Clause License
# <http://www.c-tanzer.at/license/bsd_3c.html>.
# #*** </License> ***********************************************************#

from   __future__      import print_function

from   _TFL.pyk        import pyk

import os
import pickle
import sys

from argparse          import ArgumentParser
from multiprocessing   import Pool, Manager
from rsclib.autosuper  import autosuper
from rsclib.execute    import Log
from rsclib.timeout    import Timeout, Timeout_Error
from rsclib.IP_Address import IP4_Address
from ff_olsr.parser    import get_olsr_container
from ff_spider.parser  import Guess, site_template
from itertools         import islice
from logging           import INFO
from gzip              import GzipFile

def get_node_info \
    (result_dict, ip, timeout = 180, ip_port = {}, debug = False) :
    w = Worker \
        (result_dict, ip, timeout = timeout, ip_port = ip_port, debug = debug)
    try :
        return w.get_node_info ()
    except Exception as err :
        self.log.error ("Error in IP %s:" % ip)
        w.log.log_exception ()
# end def get_node_info

class Worker (Log, Timeout) :

    def __init__ \
        ( self
        , result_dict
        , ip
        , timeout = 180
        , ip_port = {}
        , debug = False
        , **kw
        ) :
        self.__super.__init__ (** kw)
        self.ip          = ip
        self.result_dict = result_dict
        self.timeout     = timeout
        self.ip_port     = ip_port
        if not debug :
            self.log.setLevel (INFO)
        self.log.debug ("Started for IP: %s" % self.ip)
    # end def __init__

    def get_node_info (self) :
        try :
            if self.ip in self.result_dict :
                return
            self.arm_alarm (timeout = self.timeout)
            try :
                url  = ''
                site = site_template % self.__dict__
                self.log.debug ("%s: before guess" % self.ip)
                port = None
                if self.ip in self.ip_port :
                    port = self.ip_port [self.ip]
                g    = Guess (site = site, ip = self.ip, url = '', port = port)
                self.log.debug ("%s: after  guess" % self.ip)
            except ValueError as err :
                self.disable_alarm ()
                self.log.error ("Error in IP %s:" % self.ip)
                self.log_exception ()
                self.result_dict [self.ip] = ('ValueError', err)
                return
            except Timeout_Error as err :
                self.disable_alarm ()
                self.log.debug ("Timeout")
                self.result_dict [self.ip] = ('Timeout_Error', err)
                return
            except Exception as err :
                self.disable_alarm ()
                self.log.error ("Error in IP %s:" % self.ip)
                self.log_exception ()
                self.result_dict [self.ip] = ('Exception', err)
                return
            self.disable_alarm ()
            result = []
#            for iface_ip in pyk.iterkeys (g.ips) :
#                iface = iface_ip.iface
#                r = [iface.name]
#                if iface.is_wlan :
#                    r.extend \
#                        (( True
#                        ,  iface.wlan_info.ssid
#                        ,  iface.wlan_info.mode
#                        ,  iface.wlan_info.channel
#                        ,  iface.wlan_info.bssid
#                        ))
#                else :
#                    r.append (False)
#                result.append (r)
            self.result_dict [self.ip] = g
        except Exception as err :
            self.log.error ("Error in IP %s:" % self.ip)
            self.log_exception ()
            self.result_dict [self.ip] = ("ERROR", err)
    # end def get_node_info

# end class Worker

class Spider (Log) :

    def __init__ \
        ( self
        , olsr_file
        , processes =    20
        , N         =     0
        , timeout   =   180
        , ip_port   =    {}
        , debug     = False
        , ** kw
        ) :
        self.__super.__init__ (**kw)
        olsr = get_olsr_container (olsr_file)
        self.olsr_nodes = {}
        assert len (olsr.topo.forward)
        for t in pyk.iterkeys (olsr.topo.forward) :
            self.olsr_nodes [t] = True
        for t in pyk.iterkeys (olsr.topo.reverse) :
            self.olsr_nodes [t] = True
        # limit to N elements
        if N :
            self.olsr_nodes = dict \
                ((k, v) for k, v in islice (pyk.iteritems (self.olsr_nodes), N))
        self.pool        = Pool (processes = processes)
        self.mgr         = Manager ()
        self.result_dict = self.mgr.dict ()
        self.timeout     = timeout
        self.ip_port     = ip_port
        self.debug       = debug
        olsr_nodes       = None
        if not debug :
            self.log.setLevel (INFO)
        self.log.debug ("Starting ...")
    # end def __init__

    def process (self) :
        for node in self.olsr_nodes :
            self.pool.apply_async \
                ( get_node_info
                , ( self.result_dict
                  , str (node)
                  , self.timeout
                  , self.ip_port
                  , self.debug
                  )
                )
        self.pool.close ()
        self.pool.join  ()
        # broken dict proxy interface, make local dict with full interface
        self.result_dict = dict (self.result_dict)
    # end def process

# end def Spider


def main () :
    cmd = ArgumentParser ()
    cmd.add_argument \
        ( "-D", "--debug"
        , dest    = "debug"
        , help    = "Turn on debug logging"
        , action  = "store_true"
        , default = False
        )
    cmd.add_argument \
        ( "-d", "--dump"
        , dest    = "dump"
        , help    = "Destination file of pickle dump, default: %(default)s"
        , default = "Funkfeuer-spider-pickle.dump"
        )
    cmd.add_argument \
        ( "-i", "--ip-port"
        , dest    = "ip_port"
        , action  = "append"
        , help    = "IP-Addres:Port combination with non-standard port"
        , default = []
        )
    cmd.add_argument \
        ( "-n", "--limit-devices"
        , dest    = "limit_devices"
        , help    = "Limit spidering to given number of devices"
        , type    = int
        , default = 0
        )
    cmd.add_argument \
        ( "-p", "--processes"
        , dest    = "processes"
        , help    = "Use given number of processes, default: %(default)s"
        , type    = int
        , default = 20
        )
    cmd.add_argument \
        ( "-o", "--olsr-file"
        , dest    = "olsr_file"
        , help    = "File or Backfire-URL containing OLSR information, "
                    "default: %(default)s"
        , default = "olsr/txtinfo.txt"
        )
    cmd.add_argument \
        ( "-t", "--timeout"
        , dest    = "timeout"
        , help    = "Timout in seconds for subprocesses, default: %(default)s"
        , type    = int
        , default = 180
        )
    cmd.add_argument \
        ( "-v", "--verbose"
        , dest    = "verbose"
        , help    = "Show verbose results"
        , action  = "count"
        )
    opt = cmd.parse_args ()
    sp = Spider \
        ( opt.olsr_file
        , opt.processes
        , opt.limit_devices
        , opt.timeout
        , dict (x.split (':', 1) for x in opt.ip_port)
        , opt.debug
        )
    try :
        sp.process ()
        if opt.dump.endswith ('.gz') :
            f = GzipFile (opt.dump, "wb", 9)
        else :
            f = open (opt.dump, "wb")
        pickle.dump (sp.result_dict, f)
        f.close ()
        if opt.verbose :
            for k, v in sorted \
                ( pyk.iteritems (sp.result_dict)
                , key = lambda z : IP4_Address (z [0])
                ) :
                print (k, v)
    except Exception as err :
        sp.log_exception ()
# end def main

if __name__ == '__main__' :
    main ()
