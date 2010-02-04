Developer notes
===============

Git submodule
-------------

In order to be able to share some of the build infrastructure nbma uses
ganeti as a git submodule. Please remember to run::

  git submodule init
  git submodule update

After a checkout.

Configuring for development
---------------------------

.. highlight:: sh

Run the following command (only use ``PYTHON=...`` if you need to use a
different python version)::

  ./autogen.sh && \
  ./configure PYTHON=python2.4 \
    --prefix=/usr/local --sysconfdir=/etc --localstatedir=/var


.. vim: set textwidth=72 :
