#
#

# Copyright (C) 20010 Google Inc.
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


"""Ganeti NLD exception handling"""

from ganeti import errors as ganeti_errors


class NLDRequestError(ganeti_errors.GenericError):
  """A request error in Ganeti NLD.

  Events that should make nld abort the current request and proceed serving
  different ones.

  """


class NLDClientError(ganeti_errors.GenericError):
  """A magic fourcc error in Ganeti NLD.

  Errors in the NLD client library.

  """


class NLDMagicError(ganeti_errors.GenericError):
  """A magic fourcc error in Ganeti NLD.

  Errors processing the fourcc in Ganeti NLD datagrams.

  """
