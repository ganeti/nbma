AC_PREREQ(2.59)
AC_INIT(ganeti-nbma, 0.2.0, ganeti@googlegroups.com)

AC_CONFIG_AUX_DIR(autotools)
AC_CONFIG_SRCDIR(configure)

AM_INIT_AUTOMAKE([1.9 foreign tar-ustar -Wall -Wno-portability])

# Check common programs
AC_PROG_INSTALL
AC_PROG_LN_S

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

AC_OUTPUT
