============================
Ganeti NBMA tools 1.0 design
============================

This document contains the initial design for the Ganeti NBMA tools.


Objective
=========

Create a set of tools that integrates with Ganeti in order to build a fully
virtualized instance network over a foreign network, which doesn't allow
broadcast communication between the nodes.


Background
==========

Ganeti Clusters
---------------

For an overview of Ganeti please see http://code.google.com/p/ganeti/.
Normally ganeti nodes, which are the physical machines making up a cluster,
share a single broadcast network, and connect instances (the virtual machines)
to it through bridging.

In Ganeti branch-2.1 a feature to allow non-bridged instances, whose traffic
would be routed out of the nodes, has been added. This project complements that
feature by allowing those instances to transparently communicate with each
other as if they were on the same network.

NBMA Networks
-------------

A Non-Broadcast-Multiple-Access network is a network in which multiple hosts
are connected and can communicate with each other, but there is no common
broadcast channel between them. For this project we assume that nodes cannot
use broadcast or multicast between each other (suppose, for example, that they
live in different small subnets, with no network-level multicast support).

Over such a network we want to build GRE tunnels to transport instance traffic
from node to node and to designed gateways to the outside world (nbma endpoints).

With the Linux GRE implementation, it's possible to create open-ended tunnels,
and then use a hosts' ARP table to map "virtual" addresses to physical ones. We
intend to exploit this feature to build the instance's virtual network.

Overview
========

nbma implementation will consist mainly of two components:

- nld (neighbour lookup daemon) is a new daemon residing on Ganeti nodes, which
  will allow instance-to-instance traffic
- endpoints, to gateway instance traffic to the outside world

Detailed design
===============

Ganeti NLd
------------

Endpoints
---------

