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


"""NLD server classes.

"""

import logging

from ganeti import errors

from ganeti_nbma import iptables

class PeerSetManager(object):
  """Merge the peer list from multiple sets

  """

  def __init__(self):
    self._peer_sets = {}

  def RegisterPeerSet(self, name):
    """Register a peer set.

    Each updater must be registered under a unique name.

    @type name: string
    @param name: set name

    """
    if name in self._peer_sets:
      raise errors.ProgrammerError("Double registration for set %s" % name)
    self._peer_sets[name] = None

  def _UpdateIptablesRules(self):
    """Update iptables rules, merging all remote sets.

    """
    global_peer_list = []
    for peer_list in self._peer_sets.values():
      global_peer_list.extend(peer_list)
    logging.debug("Updating trusted NBMA nodes: %s" % global_peer_list)
    iptables.UpdateIptablesRules(peer_list)

  def UpdatePeerSetNodes(self, name, nodes):
    """Update a single set peer list, and keep a cache

    @type name: string
    @param name: set name
    @type nodes: list
    @param nodes: nodes associated with the peer set

    """
    assert isinstance(nodes, (tuple, list))
    nodes = sorted(nodes)
    if name not in self._peer_sets:
      raise errors.ProgrammerError("Unknown peer set %s" % name)
    if nodes == self._peer_sets[name]:
      return
    self._peer_sets[name] = nodes
    self._UpdateIptablesRules()

