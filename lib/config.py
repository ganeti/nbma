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

import re

from ganeti import objects
from ganeti import utils
from ganeti import errors

from cStringIO import StringIO


DEFAULT_SECTION="default"
ENDPOINT_EXTIP_KEY="endpoint_external_ip"


class BashFragmentConfigParser(objects.SerializableConfigParser):
  """A configparser loader for bash fragments.

  If a bash fragment contains only variable definitions mapped to simple values
  (no further variable expansion supported), it can be loaded as an ini file,
  with a section added on top.

  """
  _QUOTE_RE = re.compile("^(('.*')|(\".*\"))$")

  @classmethod
  def LoadFragmentFromString(cls, str, section=DEFAULT_SECTION):
    """Load a bash variable fragment as an ini config file

    @type str: string
    @param str: bash variable declaration fragment in string format
    @type section: string
    @keyword section: section name to prepend to the fragment

    """
    buf = StringIO()
    buf.write("[%s]\n" % section)
    buf.write(str)
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
  __slots__ = objects.ConfigObject.__slots__ + [
    "endpoints",
    "out_mc_file",
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

    for config_file in files:
      parser = BashFragmentConfigParser.LoadFragmentFromFile(config_file)
      if parser.has_option(DEFAULT_SECTION, ENDPOINT_EXTIP_KEY):
        ip = parser.get(DEFAULT_SECTION, ENDPOINT_EXTIP_KEY)
        if ip in endpoints:
          raise errors.ConfigurationError('Endpoint %s already declared' % ip)
        endpoints.append(ip)

    if not endpoints:
      raise errors.ConfigurationError('No endpoints found')

    return NLDConfig(endpoints=endpoints)

