#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# Copyright (C) 2013-18 Dr. Ralf Schlatterbeck Open Source Consulting.
# Reichergasse 131, A-3411 Weidling.
# Web: http://www.runtux.com Email: office@runtux.com
# All rights reserved
# #*** <License> ************************************************************#
# This module is licensed under the terms of the BSD 3-Clause License
# <http://www.c-tanzer.at/license/bsd_3c.html>.
# #*** </License> ***********************************************************#
# ****************************************************************************

try :
    from ff_spider.Version import VERSION
except :
    VERSION = None
from distutils.core import setup

description = []
f = open ('README.rst')
for line in f :
    description.append (line)

license     = 'BSD License'
rq          = '>=2.7, <3'
setup \
    ( name             = "ff-spider"
    , version          = VERSION
    , description      = "Spider for wireless community network"
    , long_description = ''.join (description)
    , license          = license
    , author           = "Ralf Schlatterbeck"
    , author_email     = "rsc@runtux.com"
    , packages         = ['ff_spider']
    , platforms        = 'Any'
    , scripts          = ['bin/ff_spider_parser', 'bin/ff_spiderpool']
    , python_requires  = rq
    , classifiers      = \
        [ 'Development Status :: 5 - Production/Stable'
        , 'License :: OSI Approved :: ' + license
        , 'Operating System :: OS Independent'
        , 'Programming Language :: Python'
        , 'Intended Audience :: Developers'
        , 'Programming Language :: Python :: 2'
        , 'Programming Language :: Python :: 2.7'
        ]
    )
