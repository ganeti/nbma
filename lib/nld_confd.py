#!/usr/bin/python
#

# Copyright (C) 2010, Google Inc.
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

"""Ganeti nld->confd communication related classes

"""

import logging

from ganeti_nbma import networktables

from ganeti import confd
from ganeti import constants as gnt_constants
from ganeti import utils

# pylint: disable-msg=W0611
import ganeti.confd.client


# Node list update period (seconds)
NODE_LIST_UPDATE_TIMEOUT = 30

# Master candidate update period (seconds)
MC_LIST_UPDATE_TIMEOUT = 120

# Master node IP update period (seconds)
MASTER_UPDATE_TIMEOUT = 30

# Instance map update period (seconds)
#
# For now we need a low number here, but in the future we'll rely on
# invalidation. Until we have invalidation the instance will not be
# accessible, when it changes node, for up to this number of seconds, plus the
# time to get a confd response.
INSTANCE_MAP_UPDATE_TIMEOUT = 5


class NLDConfdCallback(object):
  """NLD callback for confd queries.

  """
  def __init__(self, cluster_name, nld_config, peer_manager,
               instance_node_map):
    self.dispatch_table = {
      gnt_constants.CONFD_REQ_NODE_PIP_LIST:
        self.UpdateNodeIPList,
      gnt_constants.CONFD_REQ_MC_PIP_LIST:
        self.UpdateMCIPList,
      gnt_constants.CONFD_REQ_INSTANCES_IPS_LIST:
        self.UpdateInstanceIPList,
      gnt_constants.CONFD_REQ_NODE_PIP_BY_INSTANCE_IP:
        self.UpdateInstanceNodeMapping,
      gnt_constants.CONFD_REQ_CLUSTER_MASTER:
        self.UpdateMasterNodeIP,
    }
    self.cluster_name = cluster_name
    self.nld_config = nld_config
    self.cluster_config = nld_config.clusters[cluster_name]
    self.peer_manager = peer_manager
    self.peer_manager.RegisterPeerSet(cluster_name)
    self.cached_mc_list = None
    self.cached_instance_node_map = instance_node_map
    self.cached_master_ip = None
    self.cached_master_node_ip = None

  def UpdateNodeIPList(self, up):
    """Update dynamic iptables rules from the node list

    """
    logging.debug("Received node IP list reply [cluster: %s]",
                  self.cluster_name)
    self.peer_manager.UpdatePeerSetNodes(self.cluster_name,
                                         up.server_reply.answer)

  def UpdateMCIPList(self, up):
    """Update dynamic iptables rules from the node list

    """
    logging.debug("Received master candidate IP list reply [cluster: %s]",
                  self.cluster_name)
    if up.server_reply.answer == self.cached_mc_list:
      return
    self.cached_mc_list = up.server_reply.answer
    mc_list = up.server_reply.answer
    logging.debug("Updating confd peers [cluster: %s]: %s",
                  self.cluster_name, mc_list)
    up.client.UpdatePeerList(mc_list)
    if self.cluster_config["mc_list_update"]:
      utils.WriteFile(self.cluster_config["mc_list_file"],
                      data="%s\n" % "\n".join(mc_list))

  def UpdateInstanceIPList(self, up):
    """Update the instances list

    """
    logging.debug("Received instance IP list reply [cluster: %s]."
                  " Sending mapping query.", self.cluster_name)
    link = up.orig_request.query
    iplist = up.server_reply.answer

    mapping_query = {
      gnt_constants.CONFD_REQQ_IPLIST: iplist,
      gnt_constants.CONFD_REQQ_LINK: link,
      }

    req = confd.client.ConfdClientRequest(
      type=gnt_constants.CONFD_REQ_NODE_PIP_BY_INSTANCE_IP,
      query=mapping_query,
      )
    up.client.SendRequest(req, args=link)

  def UpdateInstanceNodeMapping(self, up):
    """Update the instances mapping

    """
    logging.debug("Received instance node mapping reply [cluster: %s]",
                  self.cluster_name)
    instances = up.orig_request.query[gnt_constants.CONFD_REQQ_IPLIST]
    link = up.orig_request.query[gnt_constants.CONFD_REQQ_LINK]
    replies = up.server_reply.answer

    for instance, reply in zip(instances, replies):
      status, node = reply
      if status != gnt_constants.CONFD_REPL_STATUS_OK:
        logging.warning("Error %s retrieving node for instance %s: %s"
                        " [cluster: %s]",
                        status, instance, node, self.cluster_name)
        continue
      if not node:
        logging.warning("Empty answer retrieving node for instance %s"
                        " [cluster: %s]",
                        instance, self.cluster_name)
        continue
      if link not in self.cached_instance_node_map:
        self.cached_instance_node_map[link] = {}
      if self.cached_instance_node_map[link].get(instance, None) == node:
        continue
      self.cached_instance_node_map[link][instance] = node
      tunnel = self.nld_config.tables_tunnels[link]
      networktables.UpdateNetworkEntry(instance, node,
                                       networktables.NEIGHBOUR_CONTEXT,
                                       tunnel)

  def UpdateMasterNodeIP(self, up):
    """Update the IP address of the master node

    """
    master_ip, master_node_ip = up.server_reply.answer
    logging.debug("Received master node IP reply. Master IP: %s,"
                  " master node IP: %s [cluster: %s]",
                  master_ip, master_node_ip, self.cluster_name)

    master_route_changed = False

    if master_ip != self.cached_master_ip:
      master_route_changed = True
      if self.cached_master_ip is None:
        self.cached_master_ip = master_ip
      else:
        logging.warning("Master IP address changed (old: %s, new: %s)."
                        " This is unexpected. [cluster: %s]",
                        master_ip, self.cached_master_ip,
                        self.cluster_name)

    if master_node_ip != self.cached_master_node_ip:
      master_route_changed = True
      self.cached_master_node_ip = master_node_ip

    if master_route_changed:
      networktables.UpdateNetworkEntry(
        master_ip, master_node_ip,
        networktables.NEIGHBOUR_CONTEXT,
        self.cluster_config['master_neighbour_interface'])

  def __call__(self, up):
    """NLD confd callback.

    @type up: L{ConfdUpcallPayload}
    @param up: upper callback

    """
    if up.type == confd.client.UPCALL_REPLY:
      if up.server_reply.status != gnt_constants.CONFD_REPL_STATUS_OK:
        logging.warning("Received error '%s' to confd request %s"
                        " [cluster: %s]",
                        up.server_reply.answer, up.orig_request,
                        self.cluster_name)
        return

      rtype = up.orig_request.type
      try:
        dispatcher = self.dispatch_table[rtype]
      except KeyError, err: # pylint: disable-msg=W0612
        logging.warning("Unhandled confd response type: %s [cluster: %s]",
                        rtype, self.cluster_name)
      dispatcher(up)


class NLDPeriodicUpdater(object):
  """Update network lookup tables periodically

  """
  def __init__(self, cluster_name, mainloop, nld_config,
               hmac_key, mc_list, peer_manager, instance_node_map):
    """Constructor for NLDPeriodicUpdater

    @type cluster_name: string
    @param cluster_name: name identifying the cluster
    @type mainloop: L{daemon.Mainloop}
    @param mainloop: ganeti-nld mainloop
    @type nld_config: L{lib.config.NLDConfig}
    @param nld_config: ganeti-nld configuration
    @type hmac_key: string
    @param hmac_key: hmac key to talk to the cluster
    @type mc_list: list of strings
    @param mc_list: list of master candidates (confd peers)
    @type peer_manager: L{server.PeerSetManager}
    @param peer_manager: ganeti-nld peer manager
    @type instance_node_map: dictionary
    @param instance_node_map: an instance->node map

    """
    self.cluster_name = cluster_name
    self.mainloop = mainloop
    self.nld_config = nld_config
    my_callback = NLDConfdCallback(cluster_name,
                                   nld_config,
                                   peer_manager,
                                   instance_node_map)
    callback = confd.client.ConfdFilterCallback(my_callback, logger=logging)
    self.confd_client = confd.client.ConfdClient(hmac_key, mc_list,
                                                 callback, logger=logging)

    self.node_timer_handle = None
    self.mc_timer_handle = None
    self.instance_timer_handle = None
    self.master_timer_handle = None
    self._EnableTimers(immediate_schedule=True)

  def _EnableTimers(self, immediate_schedule=False):
    """Schedule the update events on the main loop.

    @type immediate_schedule: boolean
    @param immediate_schedule: If set to True, all unscheduled events get
        scheduled with no delay.

    """
    timeout_update_nodes = NODE_LIST_UPDATE_TIMEOUT
    timeout_update_mcs = MC_LIST_UPDATE_TIMEOUT
    timeout_update_instances = INSTANCE_MAP_UPDATE_TIMEOUT
    timeout_update_master = MASTER_UPDATE_TIMEOUT

    if immediate_schedule:
      timeout_update_nodes = 0
      timeout_update_mcs = 0
      timeout_update_instances = 0
      timeout_update_master = 0

    if self.node_timer_handle is None:
      self.node_timer_handle = \
        self.mainloop.scheduler.enter(timeout_update_nodes,
                                      1, self.UpdateNodes, [])

    if self.mc_timer_handle is None:
      self.mc_timer_handle = \
        self.mainloop.scheduler.enter(timeout_update_mcs,
                                      1, self.UpdateMCs, [])

    if self.instance_timer_handle is None:
      self.instance_timer_handle = \
        self.mainloop.scheduler.enter(timeout_update_instances,
                                      1, self.UpdateInstances, [])

    if self.master_timer_handle is None:
      self.master_timer_handle = \
        self.mainloop.scheduler.enter(timeout_update_master,
                                      1, self.UpdateMaster, [])

  def UpdateNodes(self):
    """Periodically update the node list.

    The updated node list will be handled by the iptables module.

    """
    self.node_timer_handle = None
    self._EnableTimers()
    logging.debug("Sending node IP list request [cluster: %s]",
                  self.cluster_name)
    req = confd.client.ConfdClientRequest(
      type=gnt_constants.CONFD_REQ_NODE_PIP_LIST)
    self.confd_client.SendRequest(req)

  def UpdateMCs(self):
    """Periodically update the MC list.

    """
    self.mc_timer_handle = None
    self._EnableTimers()
    logging.debug("Sending master candidate IP list request [cluster: %s]",
                  self.cluster_name)
    req = confd.client.ConfdClientRequest(
      type=gnt_constants.CONFD_REQ_MC_PIP_LIST)
    self.confd_client.SendRequest(req)

  def UpdateInstances(self):
    """Periodically update the instance list.

    The updated instance ip list will be used to build an instance map.

    """
    self.instance_timer_handle = None
    self._EnableTimers()
    logging.debug("Sending instance IP list request [cluster: %s]",
                  self.cluster_name)
    for link in self.nld_config.tables_tunnels:
      req = confd.client.ConfdClientRequest(
              type=gnt_constants.CONFD_REQ_INSTANCES_IPS_LIST,
              query=link)
    self.confd_client.SendRequest(req)

  def UpdateMaster(self):
    """Periodically update the master node IP.

    """
    self.master_timer_handle = None
    self._EnableTimers()
    logging.debug("Sending master node IP request [cluster: %s]",
                  self.cluster_name)
    query = {
      gnt_constants.CONFD_REQQ_FIELDS: (
        gnt_constants.CONFD_REQFIELD_IP,
        gnt_constants.CONFD_REQFIELD_MNODE_PIP,
        )
      }
    req = confd.client.ConfdClientRequest(
      type=gnt_constants.CONFD_REQ_CLUSTER_MASTER,
      query=query
      )
    self.confd_client.SendRequest(req)
