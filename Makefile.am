nbmautilsdir = $(libdir)/ganeti/nbma-utils
pkgsysconfdir = $(sysconfdir)/ganeti

ACLOCAL_AMFLAGS = -I autotools
REPLACE_VARS_SED = autotools/replace_vars.sed

dist_doc_DATA = \
	COPYING \
	README \
	doc/examples/nbma-utils.conf

nodist_nbmautils_SCRIPTS = \
	scripts/gre_setup \
	scripts/iptables_setup \
	scripts/routing_setup \
	scripts/common.sh

EXTRA_DIST = \
	scripts/gre_setup.in \
	scripts/iptables_setup.in \
	scripts/routing_setup.in \
	scripts/common.sh.in

CLEANFILES = \
	autotools/replace_vars.sed \
	stamp-directories \
	$(nodist_nbmautils_SCRIPTS)

DIRS = \
       scripts \
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
		echo 's#@NBMAUTILSDIR@#$(nbmautilsdir)#g'; \
		echo 's#@NBMA_VERSION@#$(PACKAGE_VERSION)#g'; \
	} > $@

scripts/%: scripts/%.in stamp-directories $(REPLACE_VARS_SED)
	sed -f $(REPLACE_VARS_SED) < $< > $@
	chmod u+x $@
