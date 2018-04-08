# To use this Makefile, get a copy of my SF Release Tools
# git clone git://git.code.sf.net/p/sfreleasetools/code sfreleasetools
# And point the environment variable RELEASETOOLS to the checkout
ifeq (,${RELEASETOOLS})
    RELEASETOOLS=../releasetools
endif
SPIDER=ff_spider
LASTRELEASE:=$(shell $(RELEASETOOLS)/lastrelease -n)
VERSIONPY=$(SPIDER)/Version.py
VERSION=$(VERSIONPY)
README=README.rst
SRC=Makefile setup.py MANIFEST.in $(README) $(FILES:%.py=$(SPIDER)/%.py)
FILES= backfire.py common.py freifunk.py __init__.py luci.py \
    olsr_httpinfo.py openwrt.py parser.py routeros.py spiderpool.py

all: $(VERSION)

$(VERSION): $(SRC)

dist: all
	python setup.py sdist --formats=gztar,zip

clean:
	rm -f MANIFEST $(SPIDER)/Version.py README.html README.aux \
	    README.dvi README.log README.out README.tex
	rm -rf dist build upload ReleaseNotes.txt

include $(RELEASETOOLS)/Makefile-sf
