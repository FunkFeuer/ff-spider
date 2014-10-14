#!/usr/bin/python
# -*- coding: utf-8 -*-
# #*** <License> ************************************************************#
# This module is part of the repository CNDB.
# 
# This module is licensed under the terms of the BSD 3-Clause License
# <http://www.c-tanzer.at/license/bsd_3c.html>.
# #*** </License> ***********************************************************#

import re
from   rsclib.HTML_Parse  import tag, Page_Tree
from   rsclib.autosuper   import autosuper
from   spider.common      import Interface, Inet4, Inet6, unroutable
from   spider.common      import WLAN_Config
from   spider.luci        import Version_Mixin
from   olsr.common        import Topo_Entry, HNA_Entry

class Interfaces (Page_Tree, Version_Mixin) :
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
        root = self.tree.getroot ()
        self.if_by_name = {}
        self.ips        = {}
        for div in root.findall (".//%s" % tag ("div")) :
            self.try_get_version (div)
            if div.get ('id') == 'maincontent' and not self.if_by_name :
                tbl = div.find (".//%s" % tag ("table"))
                for n, tr in enumerate (tbl) :
                    if tr [0].tag == tag ('th') :
                        assert tr [0].text in ('Interface', 'Schnittstelle') \
                            , tr [0].text
                        continue
                    name, status, mtu, wlan, ip, mask, bcast = \
                        (x.text for x in tr)
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
        self.set_version (root)
        if not self.if_by_name :
            raise ValueError, "No interface config found"
        bfw = Backfire_WLAN_Config (site = self.site)
        for d in bfw.wlans :
            if d.name in self.if_by_name :
                iface = self.if_by_name [d.name]
                iface.wlan_info = d
    # end def parse

# end class Interfaces

class Backfire_WLAN_Config (Page_Tree) :
    url          = 'cgi-bin/luci/freifunk/status'
    retries      = 2
    timeout      = 10
    html_charset = 'utf-8' # force utf-8 encoding

    title_re     = re.compile \
        (r'.*ignal.*(?:(-[0-9]+)|(?:N/A))\s+d.*oise.*(-[0-9]+)\s+d')

    def parse (self) :
        wlo = \
            ( 'Wireless Overview'
            , 'Drahtlosübersicht'.decode ('utf-8')
            , 'WLAN Übersicht'.decode ('utf-8')
            )
        root = self.tree.getroot ()
        self.wlans = []
        for div in root.findall (".//%s" % tag ("div")) :
            if div.get ('class') != 'cbi-map' :
                continue
            if not len (div) or div [0].tag != tag ('h2') :
                continue
            if div [0].text not in wlo :
                continue
            for tr in div.findall (".//%s" % tag ("tr")) :
                cls = tr.get ('class') or ''
                cls = cls.split ()
                if 'cbi-section-table-row' not in cls :
                    continue
                d = WLAN_Config ()
                self.wlans.append (d)
                for td in tr :
                    k = td.get ('id')
                    if k :
                        k = k.split ('-') [-1]
                        # special handling of signal picture which has
                        # the necessary info in a title attribute :-(
                        if k == 'signal' and not td.text :
                            if td [0].tag == tag ('img') :
                                title = td [0].get ('title') 
                                m = self.title_re.search (title)
                                if m :
                                    d.set \
                                        ( signal = m.group (1)
                                        , noise  = m.group (2)
                                        )
                                    continue
                    else :
                        k = 'name'
                    v = td.text
                    d.set (** {k : v})
            break
    # end def parse
# end class Backfire_WLAN_Config

class MID_Parser (Page_Tree) :

    url = 'cgi-bin/luci/freifunk/olsr/mid/'

    def __init__ (self, site, content) :
        self.content = content
        self.__super.__init__ (site = site)
    # end def __init__

    def parse (self) :
        root = self.tree.getroot ()
        for fs in root.findall (".//%s" % tag ("fieldset")) :
            if fs.get ('class') == 'cbi-section' :
                tbl = fs.find (".//%s" % tag ("table"))
                assert tbl.get ('class') == 'cbi-section-table'
                for tr in tbl :
                    if tr [0].tag == tag ('th') :
                        assert tr [0].text == 'OLSR node'
                        continue
                    assert tr [0][0].tag == tag ('a')
                    self.content.add (tr [0][0].text, * tr [1].text.split (';'))
    # end def parse

# end class MID_Parser

class HNA_Parser (Page_Tree) :

    url = 'cgi-bin/luci/freifunk/olsr/hna/'

    def __init__ (self, site, content) :
        self.content = content
        self.__super.__init__ (site = site)
    # end def __init__

    def parse (self) :
        root = self.tree.getroot ()
        for fs in root.findall (".//%s" % tag ("fieldset")) :
            if fs.get ('class') == 'cbi-section' :
                tbl = fs.find (".//%s" % tag ("table"))
                assert tbl.get ('class') == 'cbi-section-table'
                for tr in tbl :
                    if tr [0].tag == tag ('th') :
                        assert tr [0].text == 'Announced network'
                        continue
                    assert tr [1][0].tag == tag ('a')
                    self.content.add (HNA_Entry (tr [0].text, tr [1][0].text))
    # end def parse

# end class HNA_Parser

class Topo_Parser (Page_Tree) :

    url = 'cgi-bin/luci/freifunk/olsr/topology/'

    def __init__ (self, site, content) :
        self.content = content
        self.__super.__init__ (site = site)
    # end def __init__

    def parse (self) :
        root = self.tree.getroot ()
        for fs in root.findall (".//%s" % tag ("fieldset")) :
            if fs.get ('class') == 'cbi-section' :
                tbl = fs.find (".//%s" % tag ("table"))
                assert tbl.get ('class') == 'cbi-section-table'
                for tr in tbl :
                    if tr [0].tag == tag ('th') :
                        assert tr [0].text == 'OLSR node'
                        continue
                    assert tr [0][0].tag == tag ('a')
                    assert tr [1][0].tag == tag ('a')
                    p = [tr [0][0].text, tr [1][0].text]
                    for v in tr [2:] :
                        v = v.text
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
        for k, v in self.parsers.iteritems () :
            if k in self.request :
                v (site = self.site, content = self.request [k])
    # end def __init__

# end class Backfire
