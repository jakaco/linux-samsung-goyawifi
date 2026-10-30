#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise V4L2 MMAP restart on one open fd, without issuing S_FMT.

Run as the logged-in user with camera access. No images are saved.
"""
import argparse
import ctypes as C
import fcntl
import hashlib
import json
import mmap
import os
import select
import struct
import time

class Timeval(C.Structure):
    _fields_ = [('sec', C.c_long), ('usec', C.c_long)]
class Timecode(C.Structure):
    _fields_ = [('type', C.c_uint32), ('flags', C.c_uint32), ('data', C.c_uint8 * 8)]
class Memory(C.Union):
    _fields_ = [('offset', C.c_uint32), ('userptr', C.c_ulong), ('fd', C.c_int32)]
class Buffer(C.Structure):
    _fields_ = [('index', C.c_uint32), ('type', C.c_uint32), ('bytesused', C.c_uint32),
                ('flags', C.c_uint32), ('field', C.c_uint32), ('timestamp', Timeval),
                ('timecode', Timecode), ('sequence', C.c_uint32), ('memory', C.c_uint32),
                ('m', Memory), ('length', C.c_uint32), ('reserved2', C.c_uint32),
                ('request_fd', C.c_int32)]
class FormatUnion(C.Union):
    _fields_ = [('raw', C.c_uint8 * 200), ('align', C.c_void_p)]
class Format(C.Structure):
    _fields_ = [('type', C.c_uint32), ('fmt', FormatUnion)]
class Request(C.Structure):
    _fields_ = [('count', C.c_uint32), ('type', C.c_uint32), ('memory', C.c_uint32),
                ('capabilities', C.c_uint32), ('flags', C.c_uint8), ('reserved', C.c_uint8 * 3)]

def ioctl(fd, nr, value, direction=3):
    code = (direction << 30) | (C.sizeof(value) << 16) | (ord('V') << 8) | nr
    fcntl.ioctl(fd, code, value)

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--device', default='/dev/video0')
p.add_argument('--cycles', type=int, default=3)
p.add_argument('--frames', type=int, default=6)
a = p.parse_args()
assert 1 <= a.cycles <= 20 and 1 <= a.frames <= 100
fd = os.open(a.device, os.O_RDWR | os.O_NONBLOCK)
maps = []
streaming = False
report = {'same_open_fd': True, 'set_format_calls': 0, 'cycles': []}
try:
    fmt = Format(type=1)
    ioctl(fd, 4, fmt)
    width, height, fourcc, field, stride, size = struct.unpack_from('6I', bytes(fmt.fmt.raw))
    report['format'] = {'width': width, 'height': height, 'fourcc': struct.pack('I', fourcc).decode(), 'sizeimage': size}
    req = Request(count=4, type=1, memory=1)
    ioctl(fd, 8, req)
    assert req.count >= 3
    for index in range(req.count):
        buf = Buffer(index=index, type=1, memory=1)
        ioctl(fd, 9, buf)
        maps.append(mmap.mmap(fd, buf.length, flags=mmap.MAP_SHARED, prot=mmap.PROT_READ | mmap.PROT_WRITE, offset=buf.m.offset))
    for cycle in range(a.cycles):
        for index in range(req.count):
            ioctl(fd, 15, Buffer(index=index, type=1, memory=1))
        start = time.monotonic()
        ioctl(fd, 18, C.c_int(1), direction=1)
        streaming = True
        hashes = set()
        for _ in range(a.frames):
            assert select.select([fd], [], [], 5)[0], 'Frame timeout'
            buf = Buffer(type=1, memory=1)
            ioctl(fd, 17, buf)
            assert buf.bytesused == size and not (buf.flags & 0x40), (buf.bytesused, size, buf.flags)
            hashes.add(hashlib.sha256(maps[buf.index][:buf.bytesused]).digest())
            ioctl(fd, 15, buf)
        ioctl(fd, 19, C.c_int(1), direction=1)
        streaming = False
        row = {'cycle': cycle + 1, 'complete_frames': a.frames, 'distinct_frames': len(hashes), 'seconds': round(time.monotonic() - start, 3)}
        report['cycles'].append(row)
        print(json.dumps(row), flush=True)
    report['pass'] = True
finally:
    if streaming:
        ioctl(fd, 19, C.c_int(1), direction=1)
    for mapping in maps:
        mapping.close()
    os.close(fd)
print(json.dumps(report, indent=2))
