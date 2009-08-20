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

Ganeti nld will be a daemon responsible for neighbour lookups inside a Ganeti
cluster over an NBMA network. Here is a detailed breakdown of how it will work:

Lookup triggering
~~~~~~~~~~~~~~~~~

This is how instance traffic triggers a ganeti-nld lookup:
- When a packet is routed on a node to an unknown instance, it will be routed
  by default on a non-terminated GRE interface.
- iptables will intercept GRE packets without a peer defined exiting through
  the main node interface (they can be recognized because they have an
  instance's address on the outside of the GRE encapsulation) and queue them to userspace.
- the ganeti-nld daemon will intercept them from there.

(another option for lookup triggering would be to use the userspace arpd kernel
implementation. Currently though, we don't want to rely on it, as we think
iptables+nfqueue is far more widespread)

Ganeti neighbour lookup
~~~~~~~~~~~~~~~~~~~~~~~

Upon receiving a packet from iptables/netlink ganeti-nld will:
- If it hasn't just sent a request, trigger a ganeti-confd request to a subset
  of the master candidates
- Note it has just sent a request and it is waiting for an answer for the
  target instance
- Forward the GRE packet to a peer that knows its final destination, if known.
  (this step is just an optimization to avoid stalling the communication until
  the optimized route is in place)

Upon receiving a response ganeti-nld will:
- Check the hmac signature on the response, and if valid:
- Check if the configuration version in the response is greater than the latest
  response (or if it was waiting for any response), and if so:
- Note the configuration version of the response it got
- Check that the answers matches a known ganeti node in the cluster
- Update the node arp table, associating the instance with the remote node, eg:
  ip neigh add $INSTANCE_IP lladdr $NODE_IP dev $GRE_DEVICE nud {permanent/reachable}

This will make any future packet be encapsulated directly to the remote node.

Ganeti neighbour invalidation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On instance migration/failover instances can change their destination. We want
to make sure remote instances talking to them continue to be able to do so,
without relying just on the arp table expiration of the lookup entries. In
order to do so we plan to trigger a ganeti-nld request when a node receives
traffic for an instance which is not local (anymore). This will trigger an
invalidation package to be sent to the remote node, so that the arp table entry
will be deleted, and a new lookup will be triggered. In the meantime the
packets can be forwarded to the usual "knowledgeable peer" to make sure the
communication goes on, even if it's slowed down by the extra hops.

Endpoints
---------

