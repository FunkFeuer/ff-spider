#!/usr/bin/python
# -*- coding: utf-8 -*-
# #*** <License> ************************************************************#
# This module is part of the repository CNDB.
# 
# This module is licensed under the terms of the BSD 3-Clause License
# <http://www.c-tanzer.at/license/bsd_3c.html>.
# #*** </License> ***********************************************************#

from   rsclib.autosuper   import autosuper
from   ff_spider.common   import Interface, Inet4, Inet6, Soup_Client

class Config (Soup_Client) :
    url     = None
    retries = 2
    timeout = 10

    def append_iface (self, n, name, ** kw) :
        iface = Interface (n, name, kw ['mtu'])
        i4 = Inet4 (iface = name, ** kw)
        iface.append_inet4 (i4)
        iface.is_wlan = kw ['wlan'].lower () == 'yes'
        self.if_by_name [name] = iface
        self.ips [iface.inet4 [0]] = True
    # end def append_iface

    def parse (self) :
        self.if_by_name = {}
        self.ips        = {}
        for div in self.soup.find_all ('div') :
            if div.get ('id') == 'maintable' :
                break
        else :
            raise Parse_Error ("Unable to find main table")
        # get version
        c  = div.contents [0]
        assert c.name is None
        vt = c.strip ()
        assert vt.startswith ('Version:')
        self.version = vt.split (' - ') [1].strip ()
        # we search for the first table after the h2 Interfaces element
        found = False
        h2  = div.find ('h2', string = 'Interfaces')
        tbl = h2
        while tbl.name != 'table' :
            tbl = tbl.next_sibling
        name = None
        d    = {}
        n    = 0
        # Broken html: some tr's don't have a /tr
        for tr in tbl.find_all ('tr') :
            child = tr.find ()
            if child.name == 'th' :
                if name and d.get ('status') == 'UP' :
                    self.append_iface (n, name, ** d)
                    n += 1
                name = child.string
                d    = {}
            else :
                for td in tr.find_all (recursive = False) :
                    k, v = (x.strip ()
                            for x in ' '.join (td.strings).split (':', 1)
                           )
                    d [k.lower ()] = v
            if name and d.get ('status') == 'UP' :
                self.append_iface (n, name, ** d)
                n += 1
    # end def parse

# end class Config

class OLSR (autosuper) :

    def __init__ (self, site, request, url = None) :
        self.site    = site
        self.url     = url
        self.request = request
        if 'interfaces' in self.request or 'ips' in self.request :
            cfg = Config (site = self.site, url = url)
            self.request ['ips']        = cfg.ips
            self.request ['interfaces'] = cfg.if_by_name
            self.request ['version']    = cfg.version
    # end def __init__

# end class OLSR
