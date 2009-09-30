#!/usr/bin/python
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


"""Script for unittesting the config module"""


import unittest

from nbma import config

class TestBashFragmentConfigParser(unittest.TestCase):

  def setUp(self):
    self.my_str = """
# A bash script containing only variable declarations
MYINT=2
# comment
MYSTRING1="foobar"
MYSTRING2='foobar'

MY_STRING2=ciao

MYQUOTSTRING1="ci'ao"
MYQUOTSTRING2='ci"ao'
MYQUOTSTRING3=c'ia'o

    """
    self.my_fname = "test/data/bash_var_fragment.sh"

  def _testParser(self, parser, section):
    self.assert_(parser.has_section(section))
    self.assert_(parser.has_option(section, "MYINT"))
    self.assert_(parser.has_option(section, "MYSTRING1"))
    self.assert_(parser.has_option(section, "MY_STRING2"))
    self.assertEquals(parser.get(section, "MYINT"), "2")
    self.assertEquals(parser.get(section, "MYSTRING1"), "foobar")
    self.assertEquals(parser.get(section, "MYSTRING2"), "foobar")
    self.assertEquals(parser.get(section, "MY_STRING2"), "ciao")
    self.assertEquals(parser.get(section, "MYQUOTSTRING1"), "ci'ao")
    self.assertEquals(parser.get(section, "MYQUOTSTRING2"), "ci\"ao")
    self.assertEquals(parser.get(section, "MYQUOTSTRING3"), "c'ia'o")

  def testStringLoad(self):
    cfg = config.BashFragmentConfigParser.LoadFragmentFromString(self.my_str)
    self._testParser(cfg, config.DEFAULT_SECTION)

  def testNonDefaultSection(self):
    cfg = config.BashFragmentConfigParser.LoadFragmentFromString(self.my_str,
                                                                 section="tst")
    self._testParser(cfg, "tst")

  def testFileLoad(self):
    cfg = config.BashFragmentConfigParser.LoadFragmentFromFile(self.my_fname)
    self._testParser(cfg, config.DEFAULT_SECTION)

  def testFileLoadSection(self):
    cfg = config.BashFragmentConfigParser.LoadFragmentFromFile(self.my_fname,
                                                               section="tst")
    self._testParser(cfg, "tst")


if __name__ == '__main__':
  unittest.main()
