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


"""iptables interface

With this module is possible to generate a chain containing a list of trusted
IPs to communicate with.

E.g.: if the list of all nodes of a Ganeti cluster is passed to
UpdateIptablesRules() function, then the chain can be used allow a certain kind
of network traffic only if it is accepted by the chain.

The functions in this module expect to find a pre-configured GNT_TRUST chain in
the filter table containing this kind of rules: "-j CHAINNAME"

"""


import random
# pylint: disable-msg=W0402
# Uses of a deprecated module 'string'
import string
import netfilter.table
import netfilter.rule

from ganeti import errors


_TABLE_FILTER = "filter"
_TARGET_ACCEPT = "ACCEPT"
_CHAIN_TRUST = "GNT_TRUST"
_CHAIN_NAME_LEN = 30


def _GenRandomString(length):
  """Generate a random string of the given length.

  @type length: int
  @param length: length of random string

  @rtype: str
  @return: the random suffix

  """
  return "".join(random.Random().sample(string.lowercase, length))


def CheckIptablesChain(table_name, chain_name):
  """Check chain_name exists in table_name and contains only our rules.

  @type table_name: str
  @param table_name: the name of the table
  @type chain_name: str
  @param chain_name: the name of the chain

  @raise errors.ConfigurationError: if a check fails
  @raise errors.CommandError: if an error occurs during check

  """
  # Check chain exists
  table = netfilter.table.Table(table_name)
  try:
    rules = table.list_rules(chain_name)
  except KeyError:
    raise errors.ConfigurationError("Chain %s not present" % chain_name)
  except netfilter.table.IptablesError, err:
    raise errors.CommandError("Cannot lookup %s: %s" %
                              (chain_name, err))

  # Check rules in the chain
  for rule in rules:
    rule_args = rule.specbits()
    if len(rule_args) != 2:
      raise errors.ConfigurationError("In %s non-well formed rule: %r" %
                                      (chain_name, rule_args))
    # pylint: disable-msg=W0612
    # Unused variable 'dest'
    (jump, dest) = rule_args
    if jump != "-j":
      raise errors.ConfigurationError("In %s non-well formed rule: %r" %
                                      (chain_name, rule_args))


def UpdateIptablesRules(ip_addresses, table_name=_TABLE_FILTER,
                        trust_chain=_CHAIN_TRUST, jump_chain=_TARGET_ACCEPT,
                        chain_name_len=_CHAIN_NAME_LEN):
  """Update rules allowing the given list of ip_addresses.

  @type ip_addresses: list
  @param ip_addresses: the IPs to allow
  @type table_name: str
  @param table_name: the name of the table to work in
  @type trust_chain: str
  @param trust_chain: the name of the chain to modify
  @type jump_chain: str
  @param jump_chain: the name of the chain to jump in generated rules
  @type chain_name_len: int
  @param chain_name_len: maximum length of a chain name

  @raise errors.CommandError: if an error occurs while using iptables

  """
  CheckIptablesChain(table_name, trust_chain)
  table = netfilter.table.Table(table_name)
  try:
    old_rules = table.list_rules(trust_chain)
  except netfilter.table.IptablesError, err:
    raise errors.CommandError("Cannot lookup %s: %s" %
                              (trust_chain, err))

  # Create new IPs chain
  ips_prefix = "%s_IPS_" % trust_chain
  ips_suffix = _GenRandomString(chain_name_len - len(ips_prefix))
  new_ips = "%s%s" % (ips_prefix, ips_suffix)
  try:
    table.create_chain(new_ips)
    try:
      # Populate new chain
      for addr in ip_addresses:
        rule = netfilter.rule.Rule(source=addr, jump=jump_chain)
        table.append_rule(new_ips, rule)
      # Add new chain to trust chain
      new_ips_rule = netfilter.rule.Rule(jump=new_ips)
      table.prepend_rule(trust_chain, new_ips_rule)
    except netfilter.table.IptablesError, err:
      table.flush_chain(new_ips)
      table.delete_chain(new_ips)
      raise
  except netfilter.table.IptablesError, err:
    raise errors.CommandError("Cannot create new IPs table: %s" % err)

  # Deactivate old chains
  for rule in old_rules:
    try:
      old_chain = rule.specbits()[1]
      table.delete_rule(trust_chain, rule)
      table.flush_chain(old_chain)
      table.delete_chain(old_chain)
    except netfilter.table.IptablesError, err:
      raise errors.CommandError("Cannot remove old IPs tables: %s" % err)
