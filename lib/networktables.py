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


"""Neighbour IPs interface

Module used to update both the Neighbour and Routing table.

Besides adding and removing individual entries, it can also be used to
add (or replace, if necessary) the entries in a given dictionary with
src_ip:dest_addr mapping.

"""


from ganeti import errors as ganeti_errors
from ganeti import utils


NEIGHBOUR_CONTEXT = "neigh"
ROUTING_CONTEXT = "route"
CONTEXTS = frozenset([NEIGHBOUR_CONTEXT, ROUTING_CONTEXT])


def _CheckValidContext(context):
  """Verify if the context is valid.

  @type context: str
  @param context: one of CONTEXTS

  @raise L{ganeti.errors.ParameterError}: invalid context

  """
  if context not in CONTEXTS:
    raise ganeti_errors.ParameterError("Invalid context '%s'" % context)


def RemoveNetworkEntry(ip_address, context, iface):
  """Remove an entry in the local Neighbour or Routing table.

  @type ip_address: str
  @param ip_address: IP address to be updated
  @type context: str
  @param context: one of CONTEXTS
  @type iface: str
  @param iface: network interface to use

  @raise L{ganeti.errors.Commanderror}: if an error occurs during removal

  """
  _CheckValidContext(context)
  result = utils.RunCmd(["ip", context, "del", ip_address, "dev", iface])

  # Check the command return code.
  #   0: success
  #   2: non-existent entry, we're fine with that
  #   something else: unknown, raise error
  if result.exit_code not in (0, 2):
    raise ganeti_errors.CommandError("Can't remove network entry")


def UpdateNetworkEntry(ip_address, dest_address, context, iface):
  """Update (add if inexistant) an entry in the Neigh or Routing table.

  @type ip_address: str
  @param ip_address: IP address to be updated
  @type dest_address: str
  @param dest_address: new destination address
  @type context: str
  @param context: one of CONTEXTS
  @type iface: str
  @param iface: network interface to use

  @raise L{ganeti.errors.CommandError}: if error occurs when updating an entry

  """
  _CheckValidContext(context)

  # Context-specific args
  if context == NEIGHBOUR_CONTEXT:
    dest_token = "lladdr"
    extra_args = ["nud", "permanent"]
  else:
    dest_token = "via"
    extra_args = []

  cmd = ["ip", context, "replace", ip_address, dest_token, dest_address,
         "dev", iface]

  if extra_args:
    cmd.extend(extra_args)
  result = utils.RunCmd(cmd)
  if result.failed:
    raise ganeti_errors.CommandError("Could not update table, error %s" %
                                     result.output)


def UpdateNetworkTable(instances, context, iface):
  """Add or replace the entries in instances in the Neigh|Routing table.

  If the instance's IP is not there, add it.

  @type instances: dict
  @param instances: dict with instance:dest_address mapping
  @type context: str
  @param context: one of CONTEXTS
  @type iface: str
  @param iface: network interface to use

  @raise L{ganeti.errors.CommandError}: if an error occurs when listing a table

  """
  _CheckValidContext(context)
  # Check the local table
  result = utils.RunCmd(["ip", context, "show", "dev", iface])
  if result.failed:
    raise ganeti_errors.CommandError("Could not list table, error %s" %
                                     result.output)
  table = result.output.splitlines()

  # Check if the local entries are up to date.
  for entry in table:
    # Skip empty lines
    if not entry.strip():
      continue
    parts = entry.split()
    # Get the address (first field)
    src_ip = parts[0]
    if src_ip in instances:
      dest_addr = instances[src_ip]
      UpdateNetworkEntry(src_ip, dest_addr, context, iface)

  # Check the instance list, to make sure we're not missing anything
  for instance_ip in instances:
    if instance_ip not in table:
      UpdateNetworkEntry(instance_ip, instances[instance_ip],
                         context, iface)
