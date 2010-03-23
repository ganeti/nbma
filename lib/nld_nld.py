#
#

# Copyright (C) 2010 Google Inc.
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


"""Ganeti NLD->NLD communication related functions

"""

# pylint: disable-msg=E0203

# E0203: Access to member %r before its definition, since we use
# objects.py which doesn't explicitely initialise its members


import logging
import time

from ganeti_nbma import constants
from ganeti_nbma import errors
from ganeti_nbma import objects

from ganeti import errors as gnt_errors
from ganeti import objects as gnt_objects
from ganeti import serializer
from ganeti import daemon
from ganeti import utils


_FOURCC_LEN = 4


def PackMagic(payload):
  """Prepend the NLD magic fourcc to a payload.

  """
  return ''.join([constants.NLD_MAGIC_FOURCC, payload])


def UnpackMagic(payload):
  """Unpack and check the NLD magic fourcc from a payload.

  """
  if len(payload) < _FOURCC_LEN:
    raise errors.NLDMagicError("UDP payload too short to contain the"
                                 " fourcc code")

  magic_number = payload[:_FOURCC_LEN]
  if magic_number != constants.NLD_MAGIC_FOURCC:
    raise errors.NLDMagicError("UDP payload contains an unkown fourcc")

  return payload[_FOURCC_LEN:]


class NLDRequestProcessor(object):
  """A processor for NLD requests.

  """
  def __init__(self, cluster_keys, updaters):
    """Constructor for NLDRequestProcessor

    """
    self.cluster_keys = cluster_keys
    self.updaters = updaters

    self.dispatch_table = {
      constants.NLD_REQ_PING: self._Ping,
      constants.NLD_REQ_ROUTE_INVALIDATE: self._RouteInvalidate,
      }

    assert \
      not constants.NLD_REQS.symmetric_difference(self.dispatch_table), \
      "dispatch_table is unaligned with NLD_REQS"

  # pylint: disable-msg=R0201
  def _Ping(self, query):
    if query is None:
      status = constants.NLD_REPL_STATUS_OK
      answer = 'ok'
    else:
      status = constants.NLD_REPL_STATUS_ERROR
      answer = 'non-empty ping query'

    return status, answer

  def _RouteInvalidate(self, query):
    if not query:
      logging.debug("missing body from route invalidation query")
      return constants.NLD_REPL_STATUS_ERROR, constants.NLD_ERROR_ARGUMENT

    logging.debug("executing route invalidation query: [%s]", query)
    # TODO: can we make it cluster-aware to avoid a mass-update like this?
    for _, updater in self.updaters.iteritems():
      updater.UpdateInstances()
    answer = 'done'
    return constants.NLD_REPL_STATUS_OK, answer

  def ExecQuery(self, payload, ip, port):
    """Process a single NLD request.

    @type payload: string
    @param payload: request raw data
    @type ip: string
    @param ip: source ip address
    @param port: integer
    @type port: source port

    """
    try:
      cluster_name, request = self.ExtractRequest(payload)
      reply, rsalt = self.ProcessRequest(request)
      payload_out = self.PackReply(reply, rsalt, cluster_name)
      return payload_out
    except errors.NLDRequestError, err:
      logging.info('Ignoring broken query from %s:%d: %s', ip, port, err)
      return None

  def ExtractRequest(self, payload):
    """Extracts an NLDRequest object from a serialized hmac signed string.

    This function also performs signature/timestamp validation.

    """
    current_time = time.time()
    logging.debug("Extracting request with size: %d", len(payload))
    try:
      (message, salt) = serializer.LoadSigned(payload,
                                              key=self.cluster_keys.get)
    except gnt_errors.SignatureError, err:
      msg = "invalid signature: %s" % err
      raise errors.NLDRequestError(msg)
    try:
      message_timestamp = int(salt)
    except (ValueError, TypeError):
      msg = "non-integer timestamp: %s" % salt
      raise errors.NLDRequestError(msg)

    skew = abs(current_time - message_timestamp)
    if skew > constants.NLD_MAX_CLOCK_SKEW:
      msg = "outside time range (skew: %d)" % skew
      raise errors.NLDRequestError(msg)

    try:
      cluster_name = message["cluster"]
    except KeyError:
      raise errors.NLDRequestError("Cluster name is missing from NLD request")

    try:
      request = objects.NLDRequest.FromDict(message)
    except AttributeError, err:
      raise errors.NLDRequestError('%s' % err)

    return cluster_name, request

  def ProcessRequest(self, request):
    """Process one NLDRequest, and produce an answer

    @type request: L{objects.NLDRequest}
    @rtype: (L{objects.NLDReply}, string)
    @return: tuple of reply and salt to add to the signature

    """
    logging.debug("Processing request: %s", request)
    if request.protocol != constants.NLD_PROTOCOL_VERSION:
      msg = "wrong protocol version %d" % request.protocol
      raise errors.NLDRequestError(msg)

    if request.type not in constants.NLD_REQS:
      msg = "wrong request type %d" % request.type
      raise errors.NLDRequestError(msg)

    rsalt = request.rsalt
    if not rsalt:
      msg = "missing requested salt"
      raise errors.NLDRequestError(msg)

    status, answer = self.dispatch_table[request.type](request.query)
    reply = objects.NLDReply(
      protocol=constants.NLD_PROTOCOL_VERSION,
      is_request=False,
      status=status,
      answer=answer,
      )

    logging.debug("Sending reply: %s", reply)

    return (reply, rsalt)

  def PackReply(self, reply, rsalt, cluster_name):
    """Serialize and sign the given reply, with salt rsalt

    @type reply: L{objects.NLDReply}
    @type rsalt: string
    @param cluster_name: name of the cluster

    """
    message = reply.ToDict()
    message['cluster'] = cluster_name
    return serializer.DumpSigned(
      message,
      self.cluster_keys[cluster_name],
      salt=rsalt,
      key_selector=cluster_name
      )


class NLDAsyncUDPServer(daemon.AsyncUDPSocket):
  """The NLD UDP server, suitable for use with asyncore.

  """
  def __init__(self, bind_address, port, processor, callback, cluster_keys):
    """Constructor for NLDAsyncUDPServer

    @type bind_address: string
    @param bind_address: socket bind address ('' for all)
    @type port: int
    @param port: udp port
    @type processor: L{NLDRequestProcessor}
    @param processor: NLDRequestProcessor to use to handle queries
    @param callback: NLDResponseCallback to use to handle responses
    @param cluster_keys: dictinary with the cluster hmac keys

    """
    daemon.AsyncUDPSocket.__init__(self)
    self.bind_address = bind_address
    self.port = port
    self.processor = processor
    self.bind((bind_address, port))
    self._callback = callback
    self._cluster_keys = cluster_keys
    self._requests = {}
    self._expire_requests = []

    logging.debug("listening on ('%s':%d)", bind_address, port)

  # this method is overriding the daemon.AsyncUDPSocket method
  def handle_datagram(self, payload_in, ip, port):
    try:
      payload = UnpackMagic(payload_in)
    except errors.NLDMagicError, err:
      logging.debug(err)
      return

    signed_message = serializer.LoadJson(payload)
    message = serializer.LoadJson(signed_message['msg'])

    message_is_request = message.get('is_request', None)
    if message_is_request is None:
      logging.error("Message request/response discriminator field is missing."
                    " Message: [%s]", message)
      return

    if message_is_request:
      self.HandleRequest(payload, ip, port)
    else:
      self.HandleResponse(payload, ip, port)

  def HandleRequest(self, payload, ip, port):
    answer =  self.processor.ExecQuery(payload, ip, port)
    if answer is not None:
      try:
        self.enqueue_send(ip, port, PackMagic(answer))
      except gnt_errors.UdpDataSizeError:
        logging.error("Reply too big to fit in an udp packet.")

  def _PackRequest(self, request, cluster_name, timestamp=None):
    """Prepare a request to be sent on the wire.

    This function puts a proper salt in an NLD request and adds the correct
    magic number.

    """
    if timestamp is None:
      timestamp = time.time()
    tstamp = '%d' % timestamp
    req = serializer.DumpSignedJson(request.ToDict(),
                                    self._cluster_keys[cluster_name],
                                    tstamp,
                                    key_selector=cluster_name)
    return PackMagic(req)

  def _UnpackReply(self, payload):
    (dict_answer, salt) = serializer.LoadSignedJson(payload,
                                                    key=self._cluster_keys.get)
    answer = objects.NLDReply.FromDict(dict_answer)
    return answer, salt

  def ExpireRequests(self):
    """Delete all the expired requests.

    """
    now = time.time()
    while self._expire_requests:
      expire_time, rsalt = self._expire_requests[0]
      if now >= expire_time:
        self._expire_requests.pop(0)
        (request, args) = self._requests[rsalt]
        del self._requests[rsalt]
        client_reply = NLDUpcallPayload(salt=rsalt,
                                        type=UPCALL_EXPIRE,
                                        orig_request=request,
                                        extra_args=args,
                                        client=self,
                                        )
        self._callback(client_reply)
      else:
        break

  def SendRequest(self, request, cluster_name, destination, args=None):
    """Send an NLD request to another NLD instance

    @type request: L{objects.NLDRequest}
    @param request: the request to send
    @param cluster_name: name of the cluster
    @param destination: the address of the target NLD instance
    @type args: tuple
    @keyword args: additional callback arguments

    """
    request.cluster = cluster_name

    if not request.rsalt:
      raise errors.NLDClientError("Missing request rsalt")

    self.ExpireRequests()
    if request.rsalt in self._requests:
      raise errors.NLDClientError("Duplicate request rsalt")

    if request.type not in constants.NLD_REQS:
      raise errors.NLDClientError("Invalid request type")

    now = time.time()
    payload = self._PackRequest(request, cluster_name, timestamp=now)

    try:
      self.enqueue_send(destination, self.port, payload)
    except gnt_errors.UdpDataSizeError:
      raise errors.NLDClientError("Request too big")

    self._requests[request.rsalt] = (request, args)
    expire_time = now + constants.NLD_CLIENT_EXPIRE_TIMEOUT
    self._expire_requests.append((expire_time, request.rsalt))

  def HandleResponse(self, payload, ip, port):
    """Asynchronous handler for an NLD reply

    Call the relevant callback associated with the original request.

    """
    try:
      try:
        answer, salt = self._UnpackReply(payload)
      except (gnt_errors.SignatureError, errors.NLDMagicError), err:
        if self._logger:
          self._logger.debug("Discarding broken package: %s" % err)
        return

      try:
        (request, args) = self._requests[salt]
      except KeyError:
        if self._logger:
          self._logger.debug("Discarding unknown (expired?) reply: %s" % err)
        return

      client_reply = NLDUpcallPayload(salt=salt,
                                      type=UPCALL_REPLY,
                                      server_reply=answer,
                                      orig_request=request,
                                      server_ip=ip,
                                      server_port=port,
                                      extra_args=args,
                                      client=self,
                                      )
      self._callback(client_reply)

    finally:
      self.ExpireRequests()


# UPCALL_REPLY: server reply upcall
# has all NLDUpcallPayload fields populated
UPCALL_REPLY = 1
# UPCALL_EXPIRE: internal library request expire
# has only salt, type, orig_request and extra_args
UPCALL_EXPIRE = 2
NLD_UPCALL_TYPES = frozenset([
  UPCALL_REPLY,
  UPCALL_EXPIRE,
  ])


class NLDUpcallPayload(gnt_objects.ConfigObject):
  """Callback argument for NLD replies

  @type salt: string
  @ivar salt: salt associated with the query
  @type type: one of client.NLD_UPCALL_TYPES
  @ivar type: upcall type (server reply, expired request, ...)
  @type orig_request: L{objects.NLDRequest}
  @ivar orig_request: original request
  @type server_reply: L{objects.NLDReply}
  @ivar server_reply: server reply
  @type server_ip: string
  @ivar server_ip: answering server ip address
  @type server_port: int
  @ivar server_port: answering server port
  @type extra_args: any
  @ivar extra_args: 'args' argument of the SendRequest function
  @type client: L{NLDClient}
  @ivar client: current NLD client instance

  """
  __slots__ = [
    "salt",
    "type",
    "orig_request",
    "server_reply",
    "server_ip",
    "server_port",
    "extra_args",
    "client",
    ]


class NLDClientRequest(objects.NLDRequest):
  """This is the client-side version of NLDRequest.

  This version of the class helps creating requests, on the client side, by
  filling in some default values.

  """
  def __init__(self, **kwargs):
    objects.NLDRequest.__init__(self, **kwargs)
    self.is_request = True
    if not self.rsalt:
      self.rsalt = utils.NewUUID()
    if not self.protocol:
      self.protocol = constants.NLD_PROTOCOL_VERSION
    if self.type not in constants.NLD_REQS:
      raise errors.NLDClientError("Invalid request type")


class NLDResponseCallback(object):
  """Callback for NLD responses.

  """
  def __init__(self):
    self.dispatch_table = {
      constants.NLD_REQ_PING:
        self.HandlePingResponse,
      constants.NLD_REQ_ROUTE_INVALIDATE:
        self.HandleRouteInvalidateResponse,
    }

  @staticmethod
  def HandlePingResponse(up):
    """Handle response to a ping request

    """
    logging.debug("Received a ping response: [%s]", up.server_reply.answer)

  @staticmethod
  def HandleRouteInvalidateResponse(up):
    logging.debug("Got a reply to a route invalidate request: %s", up)

  def __call__(self, up):
    """NLD response callback.

    @type up: L{NLDUpcallPayload}
    @param up: upper callback

    """
    if up.type == UPCALL_REPLY:
      if up.server_reply.status != constants.NLD_REPL_STATUS_OK:
        logging.warning("Received error '%s' to NLD request %s",
                        up.server_reply.answer, up.orig_request)
        return

      rtype = up.orig_request.type
      try:
        dispatcher = self.dispatch_table[rtype]
      except KeyError, err: # pylint: disable-msg=W0612
        logging.warning("Unhandled NLD response type: %s", rtype)
      dispatcher(up)
