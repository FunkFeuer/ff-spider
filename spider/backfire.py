#!/usr/bin/python
# -*- coding: utf-8 -*-
# #*** <License> ************************************************************#
# This module is part of the repository CNDB.
#
# This module is licensed under the terms of the BSD 3-Clause License
# <http://www.c-tanzer.at/license/bsd_3c.html>.
# #*** </License> ***********************************************************#

from   __future__         import print_function, unicode_literals
from   _TFL.pyk           import pyk

import re
from   bs4                import BeautifulSoup
from   rsclib.autosuper   import autosuper
from   spider.common      import Interface, Inet4, Inet6, unroutable
from   spider.common      import WLAN_Config, Soup_Client
from   spider.luci        import Version_Mixin
from   olsr.common        import Topo_Entry, HNA_Entry

class Interfaces (Soup_Client, Version_Mixin) :
    url          = 'cgi-bin/luci/freifunk/olsr/interfaces'
    retries      = 2
    wlan_info    = None
    timeout      = 10
    html_charset = 'utf-8' # force utf-8 encoding

    yesno = dict \
        ( yes  = True
        , no   = False
        , ja   = True
        , nein = False
        )

    def parse (self) :
        self.if_by_name = {}
        self.ips        = {}
        for div in self.soup.find_all ("div") :
            self.try_get_version (div)
            if div.get ('id') == 'maincontent' and not self.if_by_name :
                tbl = div.find ("table")
                for n, tr in enumerate (tbl.find_all (recursive = False)) :
                    child = tr.find ()
                    if child.name == 'th' :
                        assert child.string in ('Interface', 'Schnittstelle') \
                            , child.string
                        continue
                    name, status, mtu, wlan, ip, mask, bcast = \
                        (x.string for x in tr.find_all (recursive = False))
                    if name in self.if_by_name :
                        iface = self.if_by_name [name]
                    else :
                        iface = Interface (n, name, mtu)
                        iface.is_wlan = self.yesno.get (wlan, False)
                    if status == 'DOWN' :
                        continue
                    # append IP address to interface if there is one
                    if ip is not None :
                        if ':' in ip :
                            i6 = Inet6 (ip, mask, bcast, iface = name)
                            iface.append_inet6 (i6)
                        else :
                            i4 = Inet4 (ip, mask, bcast, iface = name)
                            iface.append_inet4 (i4)
                            if not unroutable (i4.ip) :
                                self.if_by_name [name] = iface
                                self.ips [i4] = True
        self.set_version (self.soup)
        if not self.if_by_name :
            return
        bfw = Backfire_WLAN_Config (site = self.site)
        for d in bfw.wlans :
            if d.name in self.if_by_name :
                iface = self.if_by_name [d.name]
                iface.wlan_info = d
    # end def parse

# end class Interfaces

class Backfire_WLAN_Config (Soup_Client) :
    url          = 'cgi-bin/luci/freifunk/status'
    retries      = 2
    timeout      = 10
    html_charset = 'utf-8' # force utf-8 encoding

    title_re     = re.compile \
        (r'.*ignal.*(?:(-[0-9]+)|(?:N/A))\s+d.*oise.*(-[0-9]+)\s+d')

    def parse (self) :
        wlo = \
            ( 'Wireless Overview'
            , pyk.decoded ('Drahtlosübersicht', 'utf-8')
            , pyk.decoded ('WLAN Übersicht',    'utf-8')
            )
        self.wlans = []
        for div in self.soup.find_all ("div") :
            if 'cbi-map' not in (div.get ('class') or []) :
                continue
            if not len (div) or div.find ().name != 'h2' :
                continue
            if div.find ().string not in wlo :
                continue
            for tr in div.find_all ("tr") :
                cls = tr.get ('class') or []
                if 'cbi-section-table-row' not in cls :
                    continue
                d = WLAN_Config ()
                self.wlans.append (d)
                for td in tr.find_all (recursive = False) :
                    k = td.get ('id')
                    if k :
                        k = k.split ('-') [-1]
                        # special handling of signal picture which has
                        # the necessary info in a title attribute :-(
                        if k == 'signal' and not td.string :
                            if td.find ().name == 'img' :
                                title = td.find ().get ('title')
                                m = self.title_re.search (title)
                                if m :
                                    d.set \
                                        ( signal = m.group (1)
                                        , noise  = m.group (2)
                                        )
                                    continue
                    else :
                        k = 'name'
                    v = td.string
                    d.set (** {k : v})
            break
    # end def parse
# end class Backfire_WLAN_Config

class MID_Parser (Soup_Client) :

    url = 'cgi-bin/luci/freifunk/olsr/mid/'

    def __init__ (self, site, content) :
        self.content = content
        self.__super.__init__ (site = site)
    # end def __init__

    def parse (self) :
        for fs in self.soup.find_all ("fieldset") :
            if fs.get ('class') == 'cbi-section' :
                tbl = fs.find ("table")
                assert tbl.get ('class') == 'cbi-section-table'
                for tr in tbl :
                    child = tr.find ()
                    chch  = child.find ()
                    next  = child.next_sibling
                    nch   = next.find ()
                    if child.name == 'th' :
                        assert child.string == 'OLSR node'
                        continue
                    assert chch.name == 'a'
                    self.content.add (chch.string, * next.string.split (';'))
    # end def parse

# end class MID_Parser

class HNA_Parser (Soup_Client) :

    url = 'cgi-bin/luci/freifunk/olsr/hna/'

    def __init__ (self, site, content) :
        self.content = content
        self.__super.__init__ (site = site)
    # end def __init__

    def parse (self) :
        for fs in self.soup.find_all ("fieldset") :
            if fs.get ('class') == 'cbi-section' :
                tbl = fs.find ("table")
                assert tbl.get ('class') == 'cbi-section-table'
                for tr in tbl :
                    child = tr.find ()
                    next  = child.next_sibling
                    schld = next.find ()
                    if not child :
                        continue
                    if child.name == 'th' :
                        assert child.string == 'Announced network'
                        continue
                    assert schld.name == 'a'
                    self.content.add (HNA_Entry (child.string, schld.string))
    # end def parse

# end class HNA_Parser

class Topo_Parser (Soup_Client) :

    url = 'cgi-bin/luci/freifunk/olsr/topology/'

    def __init__ (self, site, content) :
        self.content = content
        self.__super.__init__ (site = site)
    # end def __init__

    def parse (self) :
        for fs in self.soup.find_all ("fieldset") :
            if fs.get ('class') == 'cbi-section' :
                tbl = fs.find ("table")
                assert tbl.get ('class') == 'cbi-section-table'
                for tr in tbl :
                    child = tr.find ()
                    chch  = child.find ()
                    next  = child.next_sibling
                    nch   = next.find ()
                    if child.name == 'th' :
                        assert child.string == 'OLSR node'
                        continue
                    assert chch.name == 'a'
                    assert nch.name  == 'a'
                    p = [chch.string, nch.string]
                    for v in tr.find_all (True) [2:] :
                        v = v.string
                        if v == 'INFINITE' : v = 'inf'
                        v = float (v)
                        p.append (v)
                    self.content.add (Topo_Entry (* p))
    # end def parse

# end class Topo_Parser

class Backfire (autosuper) :

    parsers = dict (hna = HNA_Parser, mid = MID_Parser, topo = Topo_Parser)

    def __init__ (self, site, request) :
        self.site    = site
        self.request = request
        if 'interfaces' in self.request or 'ips' in self.request :
            bfi = Interfaces (site = self.site)
            self.request ['ips']        = bfi.ips
            self.request ['interfaces'] = bfi.if_by_name
            self.request ['version']    = bfi.version
        for k, v in pyk.iteritems (self.parsers) :
            if k in self.request :
                v (site = self.site, content = self.request [k])
    # end def __init__

# end class Backfire
