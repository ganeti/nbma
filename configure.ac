AC_PREREQ(2.59)
AC_INIT(ganeti-nbma, 0.2.0, ganeti@googlegroups.com)

AC_CONFIG_AUX_DIR(autotools)
AC_CONFIG_SRCDIR(configure)

AM_INIT_AUTOMAKE([1.9 foreign tar-ustar -Wall -Wno-portability])

# Check common programs
AC_PROG_INSTALL
AC_PROG_LN_S

# Check required Ganeti version
AC_MSG_CHECKING([Ganeti submodule version])
required_ganeti_version=2.1.1
current_ganeti_version=$(sed -n 's/^Version \(.*\)/\1/p; 10q' \
                         < ganeti.git/NEWS)
if ! test "${current_ganeti_version}" == "${required_ganeti_version}"
then
  AC_MSG_ERROR([Ganeti version $required_ganeti_version is required, but \
$current_ganeti_version is present in ganeti.git])
fi

AC_CONFIG_FILES([ Makefile ])

# Check for pylint
AC_ARG_VAR(PYLINT, [pylint path])
AC_PATH_PROG(PYLINT, [pylint], [])
if test -z "$PYLINT"
then
  AC_MSG_WARN([pylint not found, checking code will not be possible])
fi

# Check for Python
AM_PATH_PYTHON(2.4)

AC_PYTHON_MODULE(ganeti, t)
AC_PYTHON_MODULE(netfilter, t)
AC_PYTHON_MODULE(nflog, t)

AC_OUTPUT
