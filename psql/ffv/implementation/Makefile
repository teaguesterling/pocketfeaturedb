# contrib/cube/Makefile

MODULE_big = ffv
OBJS= ffv.o ffvparse.o $(WIN32RES)

EXTENSION = ffv
DATA = ffv--1.0.sql ffv--unpackaged--1.0.sql
PGFILEDESC = "ffv - multidimensional ffv data type"

REGRESS = ffv

EXTRA_CLEAN = y.tab.c y.tab.h

SHLIB_LINK += $(filter -lm, $(LIBS))

ifdef USE_PGXS
PG_CONFIG = pg_config
PGXS := $(shell $(PG_CONFIG) --pgxs)
include $(PGXS)
else
subdir = contrib/ffv
top_builddir = ../..
include $(top_builddir)/src/Makefile.global
include $(top_srcdir)/contrib/contrib-global.mk
endif


# ffvscan is compiled as part of cubeparse
ffvparse.o: ffvscan.c

distprep: ffvparse.c ffvscan.c

maintainer-clean:
	rm -f ffvparse.c ffvscan.c
