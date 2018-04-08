#!/usr/bin/python
# -*- coding: utf-8 -*-
# #*** <License> ************************************************************#
# This module is part of the repository CNDB.
#
# This module is licensed under the terms of the BSD 3-Clause License
# <http://www.c-tanzer.at/license/bsd_3c.html>.
# #*** </License> ***********************************************************#

from   __future__         import print_function

from   _TFL.pyk           import pyk

from   rsclib.autosuper   import autosuper
from   spider.common      import Interface, Inet4, unroutable, Soup_Client
from   spider.common      import Parse_Error

class Routes (Soup_Client) :
    retries      = 2
    timeout      = 10
    url          = '/cgi-bin/index.cgi?post_routes=1'

    def parse (self) :
        self.ip_dev = {}
        for pre in self.soup.find_all ("pre") :
            state = 0
            devname = None
            for a in pre.find_all ('a', recursive = False) :
                if state == 0 :
                    ns = a.next_sibling
                    if ns.name or 'scope link' not in ns :
                        continue
                    state = 1
                    found = False
                    for w in ns.strip ().split () :
                        if found :
                            devname = w
                            break
                        if w == 'dev' :
                            found = True
                    continue
                if state == 1 :
                    if devname :
                        self.ip_dev [a.string.strip ()] = devname
                    devname = None
                    state = 0
        for sm in self.soup.find_all ("small") :
            if sm.string :
                s = sm.string.strip ()
                if s.startswith ('0xffolsr') :
                    self.version = s
                    break
    # end def parse

# end class Routes

class Details (Soup_Client) :
    retries      = 2
    timeout      = 10
    url          = '/cgi-bin/index.cgi?post_olsr=1'

    def parse (self) :
        self.ip_dev = {}
        self.gw_ip  = {}
        self.metric = {}
        for pre in self.soup.find_all ("pre") :
            state = 0
            assert 'Table: Links' in pre.contents [0]
            for a in pre.find_all ('a', recursive = False) :
                if state == 0 :
                    state = 1
                    ip = a.string
                elif state == 1 :
                    state = 0
                    ns = a.next_sibling
                    if not ns.name and 'Table:' in ns :
                        state = 2
                    assert ip
                    self.gw_ip [a.string] = ip
                    # LQ, NLQ, Cost, 0th parameter varies with version
                    pars = ns.strip ().split () [1:4]
                    pars = ((x, 'nan')[x == 'INFINITE'] for x in pars)
                    self.metric [ip] = [float (x) for x in pars]
                elif state == 2 :
                    ns = a.next_sibling
                    if not ns.name and 'Table: Routes' in ns :
                        state = 3
                elif state == 3 :
                    state = 4
                    dst = a.string
                    if dst in self.gw_ip :
                        ip = self.gw_ip [dst]
                    else :
                        ip = None
                elif state == 4 :
                    ns = a.next_sibling
                    state = 3
                    if ip :
                        assert dst
                        self.ip_dev [ip] = ns.strip ().split () [-1]
    # end def parse

# end class Details

class Router_OS (autosuper) :

    url = '/cgi-bin/index.cgi?post_routes=1'

    def __init__ (self, site, request, url = url) :
        self.site    = site
        self.request = request
        rtparm = 1
        if url.endswith ('cgi') :
            rtparm = 2
        if 'interfaces' in self.request or 'ips' in self.request :
            rt = Routes  (site = site, url = url + '?post_routes=%s' % rtparm)
            dt = Details (site = site, url = url + '?post_olsr=1')
            if not getattr (rt, 'version', None) :
                raise Parse_Error ('No version, probably login of router-os')
            self.version = rt.version
            interfaces   = {}
            ips          = {}
            base         = 0
            for count, (ip, ifname) in enumerate (pyk.iteritems (rt.ip_dev)) :
                i4 = Inet4 (ip, None, None, iface = ifname)
                # ignore interfaces with unroutable IPs
                if unroutable (i4.ip) :
                    #print ("Unroutable: %s" % i4)
                    continue
                ips [i4] = 1
                iface = Interface (count, ifname, None)
                iface.is_wlan = False
                interfaces [ifname] = iface
                iface.append_inet4 (i4)
                base = count
            base += 1
            for count, (ip, ifname) in enumerate (pyk.iteritems (dt.ip_dev)) :
                i4 = Inet4 (ip, None, None, iface = ifname)
                is_wlan = sum (x == 1.0 for x in dt.metric [ip]) != 3
                #print ("ip", ip, dt.metric [ip])
                if unroutable (i4.ip) :
                    continue
                if i4 in ips :
                    if ifname not in interfaces :
                        iface = Interface (base + count, ifname, None)
                        interfaces [ifname] = iface
                        iface.append_inet4 (i4)
                    else :
                        iface = interfaces [ifname]
                        if i4 not in iface.inet4 :
                            #print ("Oops:", ifname, i4, iface.inet4 [0])
                            del iface.inet4 [0]
                            iface.append_inet4 (i4)
                    iface.is_wlan = is_wlan
                    continue
                ips [i4] = 1
                iface = Interface (base + count, ifname, None)
                iface.is_wlan = is_wlan
                interfaces [ifname] = iface
                iface.append_inet4 (i4)

            # check own ip
            n  = 'unknown'
            i4 = Inet4 (self.request ['ip'], None, None, iface = n)
            if i4 not in ips :
                ips [i4] = 1

            self.request ['ips']        = ips
            self.request ['interfaces'] = interfaces
            self.request ['version']    = rt.version
    # end def __init__

# end class Router_OS
