"""RFB (VNC) client for KaihongOS guest: shot / click / dbl / key.

Usage:
  python rfb.py shot  <out.png>
  python rfb.py click <x> <y>
  python rfb.py dbl   <x> <y>
  python rfb.py key   <keysym> [hold_ms]
"""
import socket
import struct
import sys
import time
import zlib

HOST = "127.0.0.1"
PORT = 5901


def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise RuntimeError("connection closed")
        buf += chunk
    return buf


class Session:
    def __init__(self):
        self.s = socket.create_connection((HOST, PORT), timeout=15)
        self.s.settimeout(25)
        s = self.s
        recv_exact(s, 12)
        s.sendall(b"RFB 003.008\n")
        n_types = struct.unpack(">B", recv_exact(s, 1))[0]
        types = recv_exact(s, n_types)
        if 1 not in types:
            raise RuntimeError("no None security")
        s.sendall(struct.pack(">B", 1))
        recv_exact(s, 4)
        s.sendall(struct.pack(">B", 1))
        self.w, self.h = struct.unpack(">HH", recv_exact(s, 4))
        recv_exact(s, 16)
        name_len = struct.unpack(">I", recv_exact(s, 4))[0]
        recv_exact(s, name_len)
        s.sendall(struct.pack(">Bxxx", 0) + struct.pack(">BBBBHHHBBBxxx", 32, 24, 0, 1, 255, 255, 255, 16, 8, 0))
        s.sendall(struct.pack(">BxH", 2, 2) + struct.pack(">i", 0) + struct.pack(">i", -223))

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass

    def shot(self, out_path, small_path=None):
        s = self.s
        s.sendall(struct.pack(">BBHHHH", 3, 0, 0, 0, self.w, self.h))
        pixels = bytearray(self.w * self.h * 4)
        got = False
        deadline = time.time() + 12
        while not got and time.time() < deadline:
            msg = struct.unpack(">B", recv_exact(s, 1))[0]
            if msg == 0:
                recv_exact(s, 1)
                n = struct.unpack(">H", recv_exact(s, 2))[0]
                for _ in range(n):
                    x, y, rw, rh, enc = struct.unpack(">HHHHi", recv_exact(s, 12))
                    if enc == 0:
                        raw = recv_exact(s, rw * rh * 4)
                        for row in range(rh):
                            src = row * rw * 4
                            dst = ((y + row) * self.w + x) * 4
                            pixels[dst:dst + rw * 4] = raw[src:src + rw * 4]
                        got = True
                    elif enc == -223:
                        self.w, self.h = rw, rh
                        pixels = bytearray(self.w * self.h * 4)
                    else:
                        raise RuntimeError(f"encoding {enc}")
            elif msg == 1:
                recv_exact(s, 5)
                n = struct.unpack(">H", recv_exact(s, 2))[0]
                recv_exact(s, n * 6)
            elif msg == 3:
                recv_exact(s, 1)
                ln = struct.unpack(">I", recv_exact(s, 1) + b"\x00\x00\x00")[0]
                recv_exact(s, ln)
            else:
                time.sleep(0.05)

        def write_png(path, w, h, step):
            rows = h // step
            cols = w // step
            raw = bytearray()
            for y in range(rows):
                raw.append(0)
                sy = y * step
                for x in range(cols):
                    i = (sy * w + x * step) * 4
                    raw.append(pixels[i + 2])
                    raw.append(pixels[i + 1])
                    raw.append(pixels[i])

            def chunk(t, d):
                c = t + d
                return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)

            png = b"\x89PNG\r\n\x1a\n"
            png += chunk(b"IHDR", struct.pack(">IIBBBBB", cols, rows, 8, 2, 0, 0, 0))
            png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            png += chunk(b"IEND", b"")
            with open(path, "wb") as f:
                f.write(png)
            return cols, rows

        w1, h1 = write_png(out_path, self.w, self.h, 1)
        info = f"shot {w1}x{h1} -> {out_path}"
        if small_path:
            w2, h2 = write_png(small_path, self.w, self.h, 2)
            info += f" | small {w2}x{h2}"
        return info

    def pointer(self, x, y, mask):
        self.s.sendall(struct.pack(">BBHH", 5, mask, int(x), int(y)))

    def click(self, x, y):
        self.pointer(x, y, 0)
        time.sleep(0.05)
        self.pointer(x, y, 1)
        time.sleep(0.08)
        self.pointer(x, y, 0)
        time.sleep(0.12)

    def dbl(self, x, y):
        self.pointer(x, y, 0)
        time.sleep(0.05)
        for _ in range(2):
            self.pointer(x, y, 1)
            time.sleep(0.06)
            self.pointer(x, y, 0)
            time.sleep(0.06)
        time.sleep(0.15)

    def key_event(self, keysym, down):
        self.s.sendall(struct.pack(">BBxxI", 4, 1 if down else 0, keysym))


def main():
    cmd = sys.argv[1]
    sess = Session()
    if cmd == "shot":
        print(sess.shot(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    elif cmd == "click":
        sess.click(int(sys.argv[2]), int(sys.argv[3]))
        print(f"clicked ({sys.argv[2]},{sys.argv[3]})")
    elif cmd == "dbl":
        sess.dbl(int(sys.argv[2]), int(sys.argv[3]))
        print(f"dbl ({sys.argv[2]},{sys.argv[3]})")
    elif cmd == "key":
        ks = int(sys.argv[2])
        sess.key_event(ks, True)
        time.sleep(float(sys.argv[3]) / 1000 if len(sys.argv) > 3 else 0.08)
        sess.key_event(ks, False)
        print(f"key {ks}")
    sess.close()


if __name__ == "__main__":
    main()
