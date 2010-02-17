#
#

# Copyright (C) 2009, 2010 Google Inc.
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
from ganeti import constants as gnt_constants

NLD = "ganeti-nld"

RELEASE_VERSION = _autoconf.PACKAGE_VERSION
CONF_DIR = _autoconf.PKGSYSCONFDIR
DEFAULT_CONF_FILE = CONF_DIR + "/common.conf"

DEFAULT_ROUTING_TABLE = "100"
DEFAULT_NEIGHBOUR_INTERFACE = "gtun0"
DEFAULT_NFLOG_QUEUE = 0

# NLD communication protocol related constants below

# A few common errors for NLD
NLD_ERROR_UNKNOWN_ENTRY = 1
NLD_ERROR_INTERNAL = 2
NLD_ERROR_ARGUMENT = 3

# Each nld request is "salted" by the current timestamp.
# This constants decides how many seconds of skew to accept.
# TODO: make this a default and allow the value to be more configurable
NLD_MAX_CLOCK_SKEW = 2 * gnt_constants.NODE_MAX_CLOCK_SKEW

NLD_PROTOCOL_VERSION = 1

NLD_REQ_PING = 0
NLD_REQ_ROUTE_INVALIDATE = 1

# NLD request query fields. These are used to pass parameters.
# These must be strings rather than integers, because json-encoding
# converts them to strings anyway, as they're used as dict-keys.
NLD_REQQ_LINK = "0" # FIXME: rename or remove

NLD_REQFIELD_NAME = "0" # FIXME: rename or remove

NLD_REQS = frozenset([
  NLD_REQ_PING,
  NLD_REQ_ROUTE_INVALIDATE,
  ])

NLD_REPL_STATUS_OK = 0
NLD_REPL_STATUS_ERROR = 1
NLD_REPL_STATUS_NOTIMPLEMENTED = 2

NLD_REPL_STATUSES = frozenset([
  NLD_REPL_STATUS_OK,
  NLD_REPL_STATUS_ERROR,
  NLD_REPL_STATUS_NOTIMPLEMENTED,
  ])

# Magic number prepended to all nld queries.
# This allows us to distinguish different types of nld protocols and handle
# them. For example by changing this we can move the whole payload to be
# compressed, or move away from json.
NLD_MAGIC_FOURCC = 'plj0'

# Timeout in seconds to expire pending query request in the nld client
# library. We don't actually expect any answer more than 10 seconds after we
# sent a request.
NLD_CLIENT_EXPIRE_TIMEOUT = 10
