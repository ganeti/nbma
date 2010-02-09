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


"""Async NFLOG interface

"""

import asyncore
import logging
import nflog

from socket import AF_INET

def NFLogLoggingCallback(i, payload):
  logging.debug("NFLogLoggingCallback() called. i: %s payload length: %s",
                i, payload.get_length())
  return 1


class AsyncNFLog(asyncore.file_dispatcher):
  """An asyncore dispatcher of NFLOG events.

  """

  def __init__(self, callback, log_group=0, family=AF_INET,
               asyncore_channel_map=None):
    self._q = nflog.log()
    self._q.set_callback(callback)
    self._q.fast_open(log_group, family)
    self.fd = self._q.get_fd()
    asyncore.file_dispatcher.__init__(self, self.fd, asyncore_channel_map)
    self._q.set_mode(nflog.NFULNL_COPY_PACKET)

  def handle_read(self):
    self._q.process_pending(5)

  # We don't need to check for the socket to be ready for writing
  def writable(self):
    return False
