import os
import logging
from threading import Thread
from subprocess import call, check_call
import atexit
from commands import getoutput

from myvpn.consts import DEFAULT_PORT

logger = logging.getLogger(__name__)

def get_platform():
    return os.uname()[0].lower()

def populate_common_argument_parser(parser):
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                        help="TCP port [default: %(default)s]")
    platform = get_platform()
    default_device = '/dev/tun5' if platform == 'darwin' else '/dev/net/tun'
    parser.add_argument('--device', default=default_device,
                        help="TUN device [default: %(default)s]")


def encrypt(data):
    return data[::-1]

def decrypt(data):
    return data[::-1]

def proxy(tun_fd, sock):
    t1 = Thread(target=copy_fd_to_socket, args=(tun_fd, sock))
    t1.setDaemon(True)
    t1.start()

    copy_socket_to_fd(sock, tun_fd)

    t1.join()

def copy_fd_to_socket(fd, sock):
    while 1:
        data = os.read(fd, 1500)
        data = encrypt(data)
        logger.debug("> %dB", len(data))
        sock.sendall('%04x' % len(data) + data)

def copy_socket_to_fd(sock, fd):
    while 1:
        data_len = int(sock.recv(4), 16)
        data = ''
        while len(data) < data_len:
            data += sock.recv(data_len - len(data))
        logger.debug("< %dB", data_len)
        data = decrypt(data)
        os.write(fd, data)


def add_route(ip, gateway):
    call(['route', 'delete', ip+'/32'])
    check_call(['route', 'add', ip+'/32', gateway])
    atexit.register(call, ['route', 'delete', ip+'/32'])


def get_default_gateway():
    output = getoutput("netstat -nr | grep default | head -n1 | awk '{ print $2 }'")
    gateway = output.strip()
    return gateway


