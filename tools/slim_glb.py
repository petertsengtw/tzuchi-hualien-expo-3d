#!/usr/bin/env python3
"""把已經縮減過的人偶 .glb 再瘦一點（座標不變）：
  1. 拿掉法線（網頁用不受光材質，用不到）
  2. 索引改用 16 位元（頂點數 < 65536 時）
  3. 顏色貼圖重新壓縮
用法：uv run --python 3.12 --with numpy --with pillow python -I tools/slim_glb.py 輸入.glb 輸出.glb [JPEG品質=80] [貼圖邊長=1024]
"""
import io, json, struct, sys
import numpy as np
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]; q = int(sys.argv[3]) if len(sys.argv) > 3 else 80; side = int(sys.argv[4]) if len(sys.argv) > 4 else 1024
f = open(src, 'rb').read(); jl = struct.unpack('<I', f[12:16])[0]; j = json.loads(f[20:20+jl]); B = f[20+jl+8:]
prim = j['meshes'][0]['primitives'][0]; CT = {5126: '<f4', 5125: '<u4', 5123: '<u2'}; NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}
def acc(i):
    a = j['accessors'][i]; v = j['bufferViews'][a['bufferView']]; o = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    return np.frombuffer(B, CT[a['componentType']], count=a['count']*NC[a['type']], offset=o).reshape(-1, NC[a['type']])
P = acc(prim['attributes']['POSITION']).astype('<f4'); U = acc(prim['attributes']['TEXCOORD_0']).astype('<f4'); I = acc(prim['indices']).reshape(-1)
tv = j['images'][j['textures'][j['materials'][0]['pbrMetallicRoughness']['baseColorTexture']['index']]['source']]['bufferView']
v = j['bufferViews'][tv]; im = Image.open(io.BytesIO(B[v.get('byteOffset', 0):v.get('byteOffset', 0)+v['byteLength']])).convert('RGB')
if im.size[0] > side: im = im.resize((side, side), Image.LANCZOS)
b = io.BytesIO(); im.save(b, 'JPEG', quality=q, optimize=True, progressive=True); jpg = b.getvalue()
use16 = len(P) < 65536; idx = I.astype('<u2' if use16 else '<u4')
pad = lambda x, c=b'\0': x + c*((4-len(x) % 4) % 4)
chunks = [idx.tobytes(), P.tobytes(), U.tobytes(), jpg]; offs, body = [], b''
for c in chunks: offs.append(len(body)); body += pad(c)
J = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
     "meshes": [{"primitives": [{"attributes": {"POSITION": 1, "TEXCOORD_0": 2}, "indices": 0, "material": 0}]}],
     "materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}, "metallicFactor": 0, "roughnessFactor": 1}, "doubleSided": True}],
     "textures": [{"source": 0}], "images": [{"bufferView": 3, "mimeType": "image/jpeg"}],
     "accessors": [{"bufferView": 0, "componentType": 5123 if use16 else 5125, "count": len(idx), "type": "SCALAR"},
                   {"bufferView": 1, "componentType": 5126, "count": len(P), "type": "VEC3", "min": P.min(0).tolist(), "max": P.max(0).tolist()},
                   {"bufferView": 2, "componentType": 5126, "count": len(P), "type": "VEC2"}],
     "bufferViews": [{"buffer": 0, "byteOffset": offs[i], "byteLength": len(chunks[i])} for i in range(4)], "buffers": [{"byteLength": len(body)}]}
js = pad(json.dumps(J).encode(), b' ')
open(dst, 'wb').write(struct.pack('<III', 0x46546C67, 2, 12+8+len(js)+8+len(body)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(body), 0x004E4942) + body)
print('%s: %.2f MB -> %.2f MB（頂點 %d，貼圖 %d KB）' % (src.split('/')[-1], len(f)/1e6, (len(js)+len(body))/1e6, len(P), len(jpg)//1024))
