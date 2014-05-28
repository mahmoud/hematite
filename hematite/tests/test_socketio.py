from hematite import socket_io as sio
import io
import pytest
import socket


def test_iopair_from_socket_read():
    expected = 'ABCDEF\x00\nEFG\x01\0x1\n'
    a, b = socket.socketpair()
    reader, _ = sio.iopair_from_socket(b)
    a.sendall(expected)
    a.close()
    # keepends=True
    assert reader.readlines() == expected.splitlines(True)


def test_iopair_from_socket_write():
    expected = 'ABCD\x00\n', 'EFG\x00\x01'
    a, b = socket.socketpair()
    _, writer = sio.iopair_from_socket(a)
    writer.writelines(expected)
    writer.close()
    assert b.recv(1024) == ''.join(expected)


def test_iopair_from_socket_nonblocking_read():
    a, b = socket.socketpair()
    b.setblocking(0)
    reader, _ = sio.iopair_from_socket(b)

    assert isinstance(reader, sio.NonblockingBufferedReader)

    first, second = 'abcd', 'efg\n'

    a.send(first)

    assert not reader.linebuffer

    with pytest.raises(io.BlockingIOError):
        reader.readline()

    assert reader.linebuffer == [first]

    # this seems awkward, but the standard BufferedReader behavior is
    # to return an empty string when read() returns None.  that means
    # a call to .readline() should only be triggered by select(2)
    # returning a socket as readable.
    assert not reader.readline()

    a.send(second)

    assert reader.readline() == first + second


def test_iopair_from_socket_nonblocking_write():
    a, b = socket.socketpair()
    a.setblocking(False)
    a.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 0)
    bufsize = a.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)

    expected = 'a' * (bufsize + 1)

    _, writer = sio.iopair_from_socket(a)

    with pytest.raises(io.BlockingIOError) as exc_info:
        writer.write(expected)

    assert exc_info.value.characters_written < len(expected)
    assert not writer.empty

    first = b.recv(bufsize)
    assert len(first) == exc_info.value.characters_written

    assert not writer.empty

    with pytest.raises(ValueError):
        writer.write("thrown away because backlog isn't empty")

    writer.write(None)
    assert writer.empty

    second = b.recv(bufsize)

    assert len(first) + len(second) == len(expected)
