nbmautilsdir = $(libdir)/ganeti/nbma-utils
pkgsysconfdir = $(sysconfdir)/ganeti

ACLOCAL_AMFLAGS = -I autotools
REPLACE_VARS_SED = autotools/replace_vars.sed

dist_doc_DATA = \
	COPYING \
	README

CLEANFILES = \
	autotools/replace_vars.sed \
	stamp-directories

DIRS = \
       doc \
       autotools \
       lib

stamp-directories: Makefile
	@mkdir_p@ $(DIRS)
	touch $@

$(REPLACE_VARS_SED): Makefile stamp-directories
	set -e; \
	{	echo 's#@PREFIX@#$(prefix)#g'; \
		echo 's#@PKGSYSCONFDIR@#$(pkgsysconfdir)#g'; \
		echo 's#@LOCALSTATEDIR@#$(localstatedir)#g'; \
		echo 's#@NBMA_VERSION@#$(PACKAGE_VERSION)#g'; \
	} > $@
