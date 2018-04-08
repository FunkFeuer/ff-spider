#!/usr/bin/python
# -*- coding: utf-8 -*-
# #*** <License> ************************************************************#
# This module is part of the repository CNDB.
# 
# This module is licensed under the terms of the BSD 3-Clause License
# <http://www.c-tanzer.at/license/bsd_3c.html>.
# #*** </License> ***********************************************************#

from rsclib.autosuper import autosuper

class Version_Mixin (autosuper) :
    version      = "Unknown"
    luci_version = bf_version = None

    def try_get_version (self, div) :
        if 'footer' in (div.get ('class') or []) :
            for p in div.find_all ("p") :
                child = p.find ()
                if  (   'luci' in p.get ('class')
                    and child
                    and child.name == "a"
                    ) :
                    a = child
                    if a.string.startswith ("Powered by LuCI") :
                        self.luci_version = a.string
        if 'header_right' in (div.get ('class') or []) :
            s = div.contents [0]
            if not s.name :
                self.bf_version = s.strip ()
        if 'hostinfo' in (div.get ('class') or []) :
            assert self.bf_version is None
            s = div.contents [0].split ('|')
            if len (s) > 1 and 'Backfire' in s [1] :
                self.bf_version = s [1].strip ()
            else :
                self.bf_version = s [0].strip ()
        if div.get ('id') == 'header' and not self.bf_version :
            p = div.find ("p")
            if p is not None :
                if p.string is None :
                    s = p.contents [0].strip ()
                else :
                    s = p.string.strip ()
                v = s.split (':', 1) [-1].split ('|', 1) [0]
                self.bf_version = v
    # end def try_get_version

    def set_version (self, root) :
        lv = self.luci_version
        if lv is None :
            p  = None
            ps = root.find_all ("p")
            if ps :
                p = ps [-1]
            if p and 'luci' in p.get ('class') :
                lv = self.luci_version = ' '.join (p.stripped_strings)
        # New 2014-Beta (sic) backfire has changed the version info :-(
        if lv is None :
            footer = None
            a = None
            a = root.find ("a", href = 'http://luci.subsignal.org/')
            if a is None :
                footer = root.find ('footer')
                if footer :
                    a = footer.find ('a')
            if a is None :
                a = root.find ("a", string = 'Powered by LuCI')
            if a is not None :
                if a.string.startswith ("Powered by LuCI") :
                    self.luci_version = lv = a.string
                    # The thing after a is not a tag
                    if a.next_sibling and not a.next_sibling.name :
                        self.bf_version = a.next_sibling.strip ()
        if (lv and lv.startswith ('Powered by LuCI')) :
            lv = lv.split ('(', 1) [-1].split (')', 1) [0]
            self.luci_version = lv
        if self.bf_version and self.luci_version :
            self.version = "%s / Luci %s" % (self.bf_version, self.luci_version)
    # end def set_version

# end class Version_Mixin
