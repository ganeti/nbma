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

"""Module for handling NLD configuration settings

"""

import re

from ganeti_nbma import constants

from ganeti import objects
from ganeti import utils
from ganeti import errors

from cStringIO import StringIO


DEFAULT_SECTION = "default"
ENDPOINT_EXTIP_KEY = "endpoint_external_ip"
INTERFACE_KEY = "gre_interface"
TABLE_KEY = "routing_table"


class BashFragmentConfigParser(objects.SerializableConfigParser):
  """A configparser loader for bash fragments.

  If a bash fragment contains only variable definitions mapped to simple values
  (no further variable expansion supported), it can be loaded as an ini file,
  with a section added on top.

  """
  _QUOTE_RE = re.compile("^(('.*')|(\".*\"))$")

  @classmethod
  def LoadFragmentFromString(cls, string, section=DEFAULT_SECTION):
    """Load a bash variable fragment as an ini config file

    @type string: string
    @param string: bash variable declaration fragment in string format
    @type section: string
    @keyword section: section name to prepend to the fragment

    """
    buf = StringIO()
    buf.write("[%s]\n" % section)
    buf.write(string)
    ini_string = buf.getvalue()
    parser = BashFragmentConfigParser.Loads(ini_string)
    for option in parser.options(section):
      value = parser.get(section, option)
      if cls._QUOTE_RE.match(value):
        parser.set(section, option, value[1:-1])
    return parser

  @staticmethod
  def LoadFragmentFromFile(file_name, section=DEFAULT_SECTION):
    """Load a bash variable fragment as an ini config file

    @type file_name: string
    @param file_name: file containing a bash variable declaration fragment
    @type section: string
    @keyword section: section name to prepend to the fragment

    """
    file_content = utils.ReadFile(file_name)

    return BashFragmentConfigParser.LoadFragmentFromString(file_content,
                                                           section=section)


class NLDConfig(objects.ConfigObject):
  __slots__ = [
    "endpoints",
    "out_mc_file",
    "tables_tunnels",
    ]

  @staticmethod
  def FromConfigFiles(files):
    """Parse the config files

    @type files: list
    @param files: list of config files
    @rtype: NLDConfig
    @return: Initialized NLD config

    """
    endpoints = []
    tables_map = {}

    for config_file in files:
      parser = BashFragmentConfigParser.LoadFragmentFromFile(config_file)
      if parser.has_option(DEFAULT_SECTION, ENDPOINT_EXTIP_KEY):
        ip = parser.get(DEFAULT_SECTION, ENDPOINT_EXTIP_KEY)
        if ip in endpoints:
          raise errors.ConfigurationError('Endpoint %s already declared' % ip)
        endpoints.append(ip)

      if parser.has_option(DEFAULT_SECTION, TABLE_KEY):
        table = parser.get(DEFAULT_SECTION, TABLE_KEY)
        has_table = True
      else:
        table = constants.DEFAULT_ROUTING_TABLE
        has_table = False

      if parser.has_option(DEFAULT_SECTION, INTERFACE_KEY):
        interface = parser.get(DEFAULT_SECTION, INTERFACE_KEY)
        has_interface = True
      else:
        interface = constants.DEFAULT_NEIGHBOUR_INTERFACE
        has_interface = False

      if (has_table or has_interface) and table not in tables_map:
        tables_map[table] = interface
      elif (has_table or has_interface) and tables_map[table] != interface:
        raise errors.ConfigurationError('Mapping for table %s already declared'
          ' (was: %s, new one: %s)' % (table, tables_map[table], interface))

    if not endpoints:
      raise errors.ConfigurationError('No endpoints found')

    if not tables_map:
      tables_map[constants.DEFAULT_ROUTING_TABLE] = \
        constants.DEFAULT_NEIGHBOUR_INTERFACE

    return NLDConfig(endpoints=endpoints, tables_tunnels=tables_map)
