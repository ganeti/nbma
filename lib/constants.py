#
#

# Copyright (C) 2009 Google Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

"""Module for holding Ganeti NBMA related constants."""


from ganeti_nbma import _autoconf

RELEASE_VERSION = _autoconf.PACKAGE_VERSION
CONF_DIR = _autoconf.PKGSYSCONFDIR
DEFAULT_CONF_FILE = CONF_DIR + "/common.conf"

DEFAULT_ROUTING_TABLE = "100"
DEFAULT_NEIGHBOUR_INTERFACE = "gtun0"
