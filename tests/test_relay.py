"""Minimal TURN relay for local testing only (RFC 5389/5766 subset, UDP).

Lets you test the app's relay features without an account at a relay provider:

    python3 test_relay.py 192.168.1.20            # your computer's local IP address
    python3 test_relay.py 192.168.1.20 --slow-first 10   # first answers take 10 s (like a slow first login)

Then in the app use relay address 192.168.1.20:3478, username "tester", password "secret".
For temporary logins (TURN REST API) use the secret key "restsecret" instead of a password.
Not for real use: it has no rate limits or security hardening.

Copyright (C) 2026 SlickAlex. Licensed under the GNU GPL v3 or later (see LICENSE).
"""
import asyncio, hashlib, hmac, os, socket, struct, sys, zlib

IP = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else '127.0.0.1'   # address to listen on and relay from
SLOW_FIRST = float(sys.argv[sys.argv.index('--slow-first') + 1]) if '--slow-first' in sys.argv else 0
FIRST_ALLOC = []   # when the first allocation was asked for (for --slow-first)
PORT = 3478
USER, PASS, REALM = 'tester', 'secret', 'test.local'
REST_SECRET = b'restsecret'   # temporary logins: username "expiry:name", password base64(HMAC-SHA1(secret, username))
KEY = hashlib.md5(f'{USER}:{REALM}:{PASS}'.encode()).digest()
import base64, time
def key_for(username):
    if username == USER: return KEY
    m = username.split(':', 1)
    if len(m) == 2 and m[0].isdigit():
        if int(m[0]) < time.time(): return None          # expired temporary login: refused by the relay itself
        pwd = base64.b64encode(hmac.new(REST_SECRET, username.encode(), hashlib.sha1).digest()).decode()
        return hashlib.md5(f'{username}:{REALM}:{pwd}'.encode()).digest()
    return None
COOKIE = 0x2112A442
NONCE = os.urandom(8).hex().encode()
LOG = []

A_MAPPED_XOR, A_USERNAME, A_MI, A_ERR, A_CHAN, A_LIFE = 0x20, 0x06, 0x08, 0x09, 0x0C, 0x0D
A_PEER, A_DATA, A_REALM, A_NONCE, A_RELAYED, A_FP = 0x12, 0x13, 0x14, 0x15, 0x16, 0x8028

def parse(msg):
    t, ln, ck = struct.unpack('!HHI', msg[:8])
    tid = msg[8:20]; attrs = []; i = 20
    while i + 4 <= 20 + ln:
        at, al = struct.unpack('!HH', msg[i:i+4])
        attrs.append((at, msg[i+4:i+4+al], i)); i += 4 + al + ((4 - al % 4) % 4)
    return t, tid, attrs

def xaddr(ip, port):
    return struct.pack('!BBH', 0, 1, port ^ (COOKIE >> 16)) + struct.pack('!I', struct.unpack('!I', socket.inet_aton(ip))[0] ^ COOKIE)

def unxaddr(v):
    port = struct.unpack('!H', v[2:4])[0] ^ (COOKIE >> 16)
    ip = socket.inet_ntoa(struct.pack('!I', struct.unpack('!I', v[4:8])[0] ^ COOKIE))
    return ip, port

def build(t, tid, attrs, integrity=False, key=None):
    body = b''
    for at, val in attrs:
        body += struct.pack('!HH', at, len(val)) + val + b'\0' * ((4 - len(val) % 4) % 4)
    if integrity:
        hdr = struct.pack('!HHI', t, len(body) + 24, COOKIE) + tid
        mac = hmac.new(key or KEY, hdr + body, hashlib.sha1).digest()
        body += struct.pack('!HH', A_MI, 20) + mac
    hdr = struct.pack('!HHI', t, len(body) + 8, COOKIE) + tid
    fp = (zlib.crc32(hdr + body) ^ 0x5354554e) & 0xffffffff
    body += struct.pack('!HHI', A_FP, 4, fp)
    return struct.pack('!HHI', t, len(body), COOKIE) + tid + body

def check_mi(msg, attrs, key):
    for at, val, off in attrs:
        if at == A_MI:
            hdr = bytearray(msg[:off]); struct.pack_into('!H', hdr, 2, off + 24 - 20)
            return hmac.compare_digest(hmac.new(key, bytes(hdr), hashlib.sha1).digest(), val)
    return None

class Alloc:
    def __init__(self, server, client):
        self.server, self.client, self.perms, self.ch2peer, self.peer2ch = server, client, set(), {}, {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); self.sock.bind((IP, 0)); self.sock.setblocking(False)
        self.port = self.sock.getsockname()[1]
        asyncio.get_event_loop().add_reader(self.sock.fileno(), self.on_peer)
    def on_peer(self):
        try: data, peer = self.sock.recvfrom(65535)
        except BlockingIOError: return
        if peer[0] not in self.perms: return
        ch = self.peer2ch.get(peer)
        if ch: out = struct.pack('!HH', ch, len(data)) + data
        else: out = build(0x0017, os.urandom(12), [(A_PEER, xaddr(*peer)), (A_DATA, data)])
        self.server.transport.sendto(out, self.client)

class Server(asyncio.DatagramProtocol):
    def __init__(self): self.allocs = {}
    def connection_made(self, tr): self.transport = tr
    def datagram_received(self, msg, addr):
        if len(msg) >= 4 and 0x40 <= msg[0] <= 0x7F:
            ch, ln = struct.unpack('!HH', msg[:4]); a = self.allocs.get(addr)
            if a and ch in a.ch2peer: a.sock.sendto(msg[4:4+ln], a.ch2peer[ch])
            return
        if len(msg) < 20: return
        t, tid, attrs = parse(msg); d = {at: val for at, val, _ in attrs}
        method = t & 0x3EEF; cls = t & 0x0110
        if method == 0x001 and cls == 0:  # binding
            self.transport.sendto(build(0x0101, tid, [(A_MAPPED_XOR, xaddr(*addr))]), addr); return
        if method == 0x006 and cls == 0x010:  # send indication
            a = self.allocs.get(addr)
            if a and A_PEER in d and A_DATA in d:
                peer = unxaddr(d[A_PEER])
                if peer[0] in a.perms: a.sock.sendto(d[A_DATA], peer)
            return
        if cls != 0: return
        uname = d.get(A_USERNAME, b'').decode(errors='replace')
        key = key_for(uname)
        ok = check_mi(msg, attrs, key) if key else None
        if ok is None:
            LOG.append(('401', method, addr)); err = struct.pack('!HBB', 0, 4, 1) + b'Unauthorized'
            self.transport.sendto(build(method | 0x0110, tid, [(A_ERR, err), (A_REALM, REALM.encode()), (A_NONCE, NONCE)]), addr); return
        if not ok:
            LOG.append(('badmi', method, addr)); err = struct.pack('!HBB', 0, 4, 1) + b'Unauthorized'
            self.transport.sendto(build(method | 0x0110, tid, [(A_ERR, err), (A_REALM, REALM.encode()), (A_NONCE, NONCE)]), addr); return
        a = self.allocs.get(addr)
        if method == 0x003:  # allocate
            if not a: a = self.allocs[addr] = Alloc(self, addr); LOG.append(('alloc', addr, a.port))
            reply = build(0x0103, tid, [(A_RELAYED, xaddr(IP, a.port)), (A_MAPPED_XOR, xaddr(*addr)), (A_LIFE, struct.pack('!I', 600))], True, key)
            if not FIRST_ALLOC: FIRST_ALLOC.append(time.time())
            wait = FIRST_ALLOC[0] + SLOW_FIRST - time.time()
            if wait > 0: asyncio.get_event_loop().call_later(wait, self.transport.sendto, reply, addr)
            else: self.transport.sendto(reply, addr)
        elif method == 0x004:  # refresh
            self.transport.sendto(build(0x0104, tid, [(A_LIFE, struct.pack('!I', 600))], True, key), addr)
        elif method == 0x008 and a:  # create permission
            for at, val, _ in attrs:
                if at == A_PEER: a.perms.add(unxaddr(val)[0])
            self.transport.sendto(build(0x0108, tid, [], True, key), addr)
        elif method == 0x009 and a:  # channel bind
            ch = struct.unpack('!H', d[A_CHAN][:2])[0]; peer = unxaddr(d[A_PEER])
            a.ch2peer[ch] = peer; a.peer2ch[peer] = ch; a.perms.add(peer[0])
            self.transport.sendto(build(0x0109, tid, [], True, key), addr)

async def main():
    loop = asyncio.get_event_loop()
    await loop.create_datagram_endpoint(Server, local_addr=(IP, PORT))
    print(f'TURN on {IP}:{PORT}', flush=True)
    while True:
        await asyncio.sleep(3600)

asyncio.run(main())
