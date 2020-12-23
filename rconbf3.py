import codecs
import time
import shlex
import hashlib
import socket
import _thread

import bf3protocol


def connect(ip, port, sock_timeout=0.5, callback=None):
    """
    Creates a non-blocking socket with a timeout of sock_timeout and attempts
    to connect to the server at (ip, port).


    Arguments:
        ip
            The IP address or hostname to connect to [string]

        port
            The port to connect to [int]

        sock_timeout
            The amount of time in seconds to block on a call to socket.recv()
            before raising a socket.timeout exception. [float]

        callback
            The function to call when an event has been received from the
            server [function pointer or None]


    Return value:
        False
            If an exception is raised while attempting to connect.

        State dictionary
            {"sock": <socket object>, -- A socket object or None. When None,
                                        used as a flag to check if the socket
                                        is connected.
            "lock": <lock object>, -- A lock to prevent multiple threads
                                    accessing resources at the same time.
            "recvstr": <string>, -- A string to hold overflow data from the
                                    server.
            "recvbuffer": <dict>, -- A dictionary holding response packets
                                    where key is the sequence number and value
                                    is the packet data.
            "events": <list>, -- A list holding any events received from the
                                    server (Unused if callback is defined).
            "callback": <function pointer>, -- A function which will be called
                                                when an event has been
                                                received.
            "error": <string>} -- A string which contains any errors which may
                                occur during operations on the state or any of
                                its contents.

    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((ip, port))

    except socket.error or socket.herror or socket.gaierror:
        return False

    sock.setblocking(0)
    sock.settimeout(sock_timeout)

    return {"sock": sock,
            "lock": _thread.allocate_lock(),
            "recvstr": "",
            "recvbuffer": {},
            "events": [],
            "callback": callback,
            "error": ""}

def close(conn):
    """
    Closes socket and flags it as disconnected.


    Arguments:
        conn
            A dictionary containing the state of a connection as described in
            the connect function docs.


    Return value:
        True

    """

    if conn["sock"] is None:
        return True

    conn["sock"].close()
    conn["sock"].shutdown()
    conn["sock"] = None

    return True

def authenticate(conn, password, timeout=False):
    """
    Attempts to authenticate with the server conn is connected to.


    Arguments:
        conn
            A dictionary containing the state of a connection as described in
            the connect function docs.

        password
            The rcon password [string]

        timeout
            The time in seconds to wait for a response [float]


    Return value:
        False
            Socket error

        None
            Socket timeout

        A list containing the response from the server (Will be either ["OK"]
        or ["InvalidPasswordHash"])

    """

    salt = invoke(conn, "login.hashed", timeout)

    if salt is None:
        return None

    elif salt is False:
        return False
    decode_hex = codecs.getdecoder("hex_codec")
    m = hashlib.md5()
    m.update(decode_hex(salt[1])[0])
    m.update(password.encode("utf-8"))
    pwhash = m.hexdigest().upper()

    return invoke(conn, "login.hashed {0}".format(pwhash), timeout)


def invoke(conn, msg, timeout=False, wait=0.01):
    """
    Attempts to send msg to the server and receive a response.


    Arguments:
        conn
            A dictionary containing the state of a connection as described in
            the connect function docs.

        msg
            A string to send to the server.

        timeout
            The time in seconds to wait for a response [float]
        wait
            The time in seconds to pause between polling the recvbuffer for
            responses. [float]


    Return value:
        False
            Socket error

        None
            Timeout

        A list containing the response from the server.

    """

    if conn["sock"] is None:
        return False

    conn["lock"].acquire()
    seq = _send(conn["sock"], msg)
    conn["lock"].release()

    if seq is False:
        conn["sock"] = None
        return False

    start = time.time()
    while not seq in conn["recvbuffer"]:
        if timeout and time.time() - start > timeout:
            return None

        time.sleep(wait)

    ret = conn["recvbuffer"][seq]
    del conn["recvbuffer"][seq]

    return ret

def start_update(conn, wait=0.01):
    """
    Starts a thread which updates the connection state conn with any new data
    from the server and/or calls the callback.

    Arguments:
    conn -- -- A dictionary containing the state of a connection as described in
            the connect function docs.
    wait -- The time in seconds to pause between polling the server for
            responses and events. [float]

    Return value:
    True

    """

    def _update_loop():
        while conn["sock"] is not None:
            time.sleep(wait)

            conn["lock"].acquire()
            res = _recv(conn)
            conn["lock"].release()

            if res is None:
                continue

            elif res is False:
                break

            from_server, is_response, sequence_nr, words = res

            if is_response:
                conn["recvbuffer"][sequence_nr] = words

            elif from_server:
                if conn["callback"]:
                    _thread.start_new_thread(conn["callback"], (words,))

                else:
                    conn["events"].append(words)

                conn["lock"].acquire()
                res = _reply(conn["sock"], sequence_nr, "OK")
                conn["lock"].release()

                if res is False:
                    conn["sock"] = None
                    break

    _thread.start_new_thread(_update_loop, ())
    return True


def _send(sock, command):
    msg, seq = bf3protocol.EncodeClientRequest(shlex.split(command))

    return seq if _raw_send(sock, msg) else False

def _reply(sock, seq, command):
    return _raw_send(sock, bf3protocol.EncodeClientResponse(seq, shlex.split(command)))

def _raw_send(sock, msg):
    try:
        sock.sendall(bytes(msg, "utf-8"))

    except socket.error:
        return False

    return True

def _recv(conn):
    while not bf3protocol.containsCompletePacket(conn["recvstr"]):
        try:
            temp = conn["sock"].recv(4096)

        except socket.timeout:
            return None

        except socket.error:
            conn["sock"] = None
            return False

        if not temp:
            return False
            
        conn["recvstr"] += temp.decode('windows-1252')

    size = bf3protocol.DecodeInt32(conn["recvstr"][4:8])

    packet = conn["recvstr"][0:size]
    conn["recvstr"] = conn["recvstr"][size:len(conn["recvstr"])]

    return bf3protocol.DecodePacket(packet)
