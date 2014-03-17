import socket
from hematite.compat.socket_io import bio_from_socket


def test_bio_from_socket_read():
    expected = 'ABCDEF\x00\nEFG\x01\0x1\n'
    a, b = socket.socketpair()
    bio = bio_from_socket(b, mode='rb')
    a.sendall(expected)
    a.close()
    # keepends=True
    assert bio.readlines() == expected.splitlines(True)


def test_bio_from_socket_write():
    expected = 'ABCD\x00\n', 'EFG\x00\x01'
    a, b = socket.socketpair()
    bio = bio_from_socket(b, mode='wb')
    bio.writelines(expected)
    bio.flush()
    b.close()
    assert a.recv(1024) == ''.join(expected)
