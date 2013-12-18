from gevent.timeout import Timeout
import pytest
import zmq.green as zmq
from zmq.utils import z85
from zope.interface.verify import verifyClass


def test_noop_auth_backend_client():
    from pybidirpc.auth import NoOpAuthenticationBackendForClient
    from pybidirpc.interfaces import IAuthenticationBackend

    assert verifyClass(IAuthenticationBackend,
                       NoOpAuthenticationBackendForClient)


def test_noop_auth_backend_server():
    from pybidirpc.auth import NoOpAuthenticationBackendForServer
    from pybidirpc.interfaces import IAuthenticationBackend

    assert verifyClass(IAuthenticationBackend,
                       NoOpAuthenticationBackendForServer)


def test_trusted_curve_client():
    from pybidirpc.auth import CurveWithTrustedKeyForClient
    from pybidirpc.interfaces import IAuthenticationBackend

    assert verifyClass(IAuthenticationBackend, CurveWithTrustedKeyForClient)


def test_trusted_curve_server():
    from pybidirpc.auth import CurveWithTrustedKeyForServer
    from pybidirpc.interfaces import IAuthenticationBackend

    assert verifyClass(IAuthenticationBackend, CurveWithTrustedKeyForServer)


def test_untrusted_curve_client():
    from pybidirpc.auth import CurveWithUntrustedKeyForClient
    from pybidirpc.interfaces import IAuthenticationBackend

    assert verifyClass(IAuthenticationBackend, CurveWithUntrustedKeyForClient)


def test_untrusted_curve_server():
    from pybidirpc.auth import CurveWithUntrustedKeyForServer
    from pybidirpc.interfaces import IAuthenticationBackend

    assert verifyClass(IAuthenticationBackend, CurveWithUntrustedKeyForServer)


def test_trusted_curve():
    from pybidirpc._gevent import Client, Server
    from pybidirpc import auth, heartbeat  # NOQA
    client_id = 'client'
    server_id = 'server'
    endpoint = 'tcp://127.0.0.1:8998'
    server_public, server_secret = zmq.curve_keypair()
    client_public, client_secret = zmq.curve_keypair()
    security_plugin = 'trusted_curve'
    client = Client(client_id, server_id,
                    security_plugin=security_plugin,
                    public_key=client_public,
                    secret_key=client_secret,
                    peer_public_key=server_public)

    server = Server(server_id, security_plugin=security_plugin,
                    public_key=server_public,
                    secret_key=server_secret)

    server.bind(endpoint)
    client.connect(endpoint)
    assert server.socket.mechanism == zmq.CURVE
    assert client.socket.mechanism == zmq.CURVE

    server.start()
    client.start()
    future = client.string.lower('FOO')
    assert future.get() == 'foo'
    server.stop()
    client.stop()


def test_trusted_curve_with_wrong_peer_public_key():
    from pybidirpc._gevent import Client, Server
    from pybidirpc import auth, heartbeat  # NOQA
    client_id = 'client'
    server_id = 'server'
    endpoint = 'inproc://{}'.format(__name__)
    endpoint = 'tcp://127.0.0.1:8998'
    server_public, server_secret = zmq.curve_keypair()
    client_public, client_secret = zmq.curve_keypair()
    client = Client(client_id, server_id,
                    security_plugin='trusted_curve',
                    public_key=client_public,
                    secret_key=client_secret,
                    peer_public_key=z85.encode('R' * 32))

    server = Server(server_id, security_plugin='trusted_curve',
                    public_key=server_public,
                    secret_key=server_secret)

    server.bind(endpoint)
    client.connect(endpoint)
    assert server.socket.mechanism == zmq.CURVE
    assert client.socket.mechanism == zmq.CURVE

    server.start()
    client.start()
    future = client.string.lower('BAR')
    with pytest.raises(Timeout):
        future.get(timeout=0.1)
    server.stop()
    client.stop()


def test_untrusted_curve_with_allowed_password():
    from pybidirpc._gevent import Client, Server
    from pybidirpc import auth, heartbeat  # NOQA
    client_id = 'john'
    server_id = 'server'
    endpoint = 'tcp://127.0.0.1:8998'
    server_public, server_secret = zmq.curve_keypair()
    client_public, client_secret = zmq.curve_keypair()
    security_plugin = 'untrusted_curve'
    password = 's3cret!'

    client = Client(client_id, server_id,
                    security_plugin=security_plugin,
                    public_key=client_public,
                    secret_key=client_secret,
                    peer_public_key=server_public,
                    password=password)

    server = Server(server_id,
                    security_plugin=security_plugin,
                    public_key=server_public,
                    secret_key=server_secret)

    server.bind(endpoint)
    client.connect(endpoint)
    assert server.socket.mechanism == zmq.CURVE
    assert client.socket.mechanism == zmq.CURVE

    # configure manually authentication backend
    server.auth_backend.user_map[client_id] = password

    server.start()
    client.start()
    future = client.string.lower('FOO')
    future2 = client.string.lower('FOO_JJ')
    assert future.get() == 'foo'
    assert future2.get() == 'foo_jj'
    server.stop()
    client.stop()


def test_untrusted_curve_with_wrong_password():
    from pybidirpc._gevent import Client, Server
    from pybidirpc.interfaces import UnauthorizedError
    from pybidirpc import auth, heartbeat  # NOQA

    client_id = 'john'
    server_id = 'server'
    endpoint = 'tcp://127.0.0.1:8998'
    server_public, server_secret = zmq.curve_keypair()
    client_public, client_secret = zmq.curve_keypair()
    security_plugin = 'untrusted_curve'
    password = 's3cret!'

    client = Client(client_id, server_id,
                    security_plugin=security_plugin,
                    public_key=client_public,
                    secret_key=client_secret,
                    peer_public_key=server_public,
                    password=password)

    server = Server(server_id,
                    security_plugin=security_plugin,
                    public_key=server_public,
                    secret_key=server_secret)

    server.bind(endpoint)
    client.connect(endpoint)
    assert server.socket.mechanism == zmq.CURVE
    assert client.socket.mechanism == zmq.CURVE

    # configure manually authentication backend
    server.auth_backend.user_map[client_id] = password + 'Looser'

    server.start()
    client.start()
    future = client.string.lower('IMSCREAMING')
    with pytest.raises(UnauthorizedError):
        future.get()
    server.stop()
    client.stop()