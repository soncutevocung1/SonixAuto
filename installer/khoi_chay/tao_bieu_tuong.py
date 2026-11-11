"""Tạo rsrc_windows_amd64.syso (COFF .rsrc) chứa biểu tượng từ file .ico, cho Go linker."""
import struct, sys
ico = open(sys.argv[1], 'rb').read()
_, typ, n = struct.unpack_from('<HHH', ico, 0)
assert typ == 1
imgs, grp = [], struct.pack('<HHH', 0, 1, n)
for i in range(n):
    w, h, c, r, planes, bits, size, off = struct.unpack_from('<BBBBHHII', ico, 6 + 16 * i)
    imgs.append(ico[off:off + size])
    grp += struct.pack('<BBBBHHIH', w, h, c, r, planes, bits, size, i + 1)
# bố cục: root(3,14) -> type dirs -> name dirs -> lang data entries -> blobs
blobs = imgs + [grp]
def d(nent): return 16 + 8 * nent
root = 0
t3 = d(2); t14 = t3 + d(n)
names = t14 + d(1)                 # n+1 name dirs, mỗi cái 1 entry lang
data_entries = names + (n + 1) * d(1)
blob_off = data_entries + 16 * (n + 1)
offs = []
p = blob_off
for b in blobs:
    p = (p + 7) & ~7; offs.append(p); p += len(b)
total = (p + 7) & ~7
sec = bytearray(total)
def dirhdr(at, nid): struct.pack_into('<IIHHHH', sec, at, 0, 0, 0, 0, 0, nid)
def ent(at, ident, off, sub): struct.pack_into('<II', sec, at, ident, off | (0x80000000 if sub else 0))
dirhdr(root, 2); ent(16, 3, t3, True); ent(24, 14, t14, True)
dirhdr(t3, n)
for i in range(n): ent(t3 + 16 + 8 * i, i + 1, names + i * d(1), True)
dirhdr(t14, 1); ent(t14 + 16, 1, names + n * d(1), True)
relocs = []
for k in range(n + 1):
    nd = names + k * d(1); de = data_entries + 16 * k
    dirhdr(nd, 1); ent(nd + 16, 0x409, de, False)
    struct.pack_into('<IIII', sec, de, offs[k], len(blobs[k]), 0, 0); relocs.append(de)
    sec[offs[k]:offs[k] + len(blobs[k])] = blobs[k]
hdr = struct.pack('<HHIIIHH', 0x8664, 1, 0, 60 + total + 10 * len(relocs), 1, 0, 0)
sh = struct.pack('<8sIIIIIIHHI', b'.rsrc', 0, 0, total, 60, 60 + total, 0, len(relocs), 0, 0x40000040)
rel = b''.join(struct.pack('<IIH', r, 0, 3) for r in relocs)
sym = struct.pack('<8sIhHBB', b'.rsrc', 0, 1, 0, 3, 0)
open(sys.argv[2], 'wb').write(hdr + sh + bytes(sec) + rel + sym + struct.pack('<I', 4))
print('syso', n, 'icons', total, 'bytes')
