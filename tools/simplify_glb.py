#!/usr/bin/env python3
"""把 Meshy 匯出的高解析人偶 .glb 縮減成網頁用的小檔（約 4 萬面、1024 貼圖、只留顏色貼圖）。

用法（需要 uv）：
  uv run --python 3.12 --with numpy --with pillow --with meshoptimizer \
    python -I tools/simplify_glb.py 輸入.glb site/assets/輸出.glb [目標面數=40000] [貼圖邊長=1024]

模型假設：高度約 1.9、朝 +z、腳底約在 y=-0.95（Meshy 預設）。輸出同樣座標，makeRig() 直接可用。
最後會印出各高度的左右寬度分佈，用來判斷手臂是否離開身體（A 字姿勢）。
"""
import ctypes, io, json, struct, sys
import numpy as np
from PIL import Image
from meshoptimizer import simplifier as S

src, dst = sys.argv[1], sys.argv[2]
tris = int(sys.argv[3]) if len(sys.argv) > 3 else 40000
tex = int(sys.argv[4]) if len(sys.argv) > 4 else 1024

f = open(src, 'rb').read()
jl = struct.unpack('<I', f[12:16])[0]; j = json.loads(f[20:20+jl]); B = f[20+jl+8:]
def bv(i):
    v = j['bufferViews'][i]; o = v.get('byteOffset', 0); return B[o:o+v['byteLength']]
prim = j['meshes'][0]['primitives'][0]
CT = {5126: '<f4', 5125: '<u4', 5123: '<u2'}; NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}
def acc(i):   # 依 accessor 讀取（不同匯出的 bufferView 順序不一定相同）
    a = j['accessors'][i]; v = j['bufferViews'][a['bufferView']]; o = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    return np.frombuffer(B, CT[a['componentType']], count=a['count']*NC[a['type']], offset=o).reshape(-1, NC[a['type']])
pos = acc(prim['attributes']['POSITION']).astype(np.float32)
uv = acc(prim['attributes']['TEXCOORD_0']).astype(np.float32)
nor = acc(prim['attributes']['NORMAL']).astype(np.float32)
idx = acc(prim['indices']).reshape(-1).astype(np.uint32)
tex_view = j['images'][j['textures'][j['materials'][0]['pbrMetallicRoughness']['baseColorTexture']['index']]['source']]['bufferView']
# 正規化：高度縮放成 1.9、腳底放在 y=-0.952、左右與前後置中（不同模型原點不同，makeRig 假設這個座標）
h0 = pos[:, 1].max() - pos[:, 1].min(); k = 1.9 / h0
pos = (pos - np.array([(pos[:, 0].max()+pos[:, 0].min())/2, pos[:, 1].min(), (pos[:, 2].max()+pos[:, 2].min())/2], dtype=np.float32)) * k
pos[:, 1] -= 0.952
pos = pos.astype(np.float32)
attrs = np.hstack([uv, nor]).astype(np.float32); w = np.array([1.5, 1.5, .3, .3, .3], dtype=np.float32)
out_idx = np.zeros(len(idx), dtype=np.uint32)
fn = S.lib.meshopt_simplifyWithAttributes; fn.argtypes = None; fn.restype = ctypes.c_size_t
n = fn(out_idx.ctypes.data_as(ctypes.c_void_p), idx.ctypes.data_as(ctypes.c_void_p), ctypes.c_size_t(len(idx)),
       pos.ctypes.data_as(ctypes.c_void_p), ctypes.c_size_t(len(pos)), ctypes.c_size_t(12),
       attrs.ctypes.data_as(ctypes.c_void_p), ctypes.c_size_t(20), w.ctypes.data_as(ctypes.c_void_p), ctypes.c_size_t(5),
       None, ctypes.c_size_t(tris*3), ctypes.c_float(0.05), ctypes.c_uint(0), None)
out_idx = out_idx[:n]
used = np.unique(out_idx); remap = np.zeros(len(pos), dtype=np.uint32); remap[used] = np.arange(len(used))
P, U, N, I = pos[used], uv[used], nor[used], remap[out_idx].astype(np.uint32)
im = Image.open(io.BytesIO(bv(tex_view))).convert('RGB').resize((tex, tex), Image.LANCZOS)
b = io.BytesIO(); im.save(b, 'JPEG', quality=86); jpg = b.getvalue()
pad = lambda x, c=b'\0': x + c*((4-len(x) % 4) % 4)
chunks = [I.astype('<u4').tobytes(), P.astype('<f4').tobytes(), U.astype('<f4').tobytes(), N.astype('<f4').tobytes(), jpg]
offs, body = [], b''
for c in chunks: offs.append(len(body)); body += pad(c)
J = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
     "meshes": [{"primitives": [{"attributes": {"POSITION": 1, "TEXCOORD_0": 2, "NORMAL": 3}, "indices": 0, "material": 0}]}],
     "materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}, "metallicFactor": 0, "roughnessFactor": 1}, "doubleSided": True}],
     "textures": [{"source": 0}], "images": [{"bufferView": 4, "mimeType": "image/jpeg"}],
     "accessors": [{"bufferView": 0, "componentType": 5125, "count": len(I), "type": "SCALAR"},
                   {"bufferView": 1, "componentType": 5126, "count": len(P), "type": "VEC3", "min": P.min(0).tolist(), "max": P.max(0).tolist()},
                   {"bufferView": 2, "componentType": 5126, "count": len(P), "type": "VEC2"}, {"bufferView": 3, "componentType": 5126, "count": len(P), "type": "VEC3"}],
     "bufferViews": [{"buffer": 0, "byteOffset": offs[i], "byteLength": len(chunks[i])} for i in range(5)], "buffers": [{"byteLength": len(body)}]}
js = pad(json.dumps(J).encode(), b' ')
open(dst, 'wb').write(struct.pack('<III', 0x46546C67, 2, 12+8+len(js)+8+len(body)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(body), 0x004E4942) + body)
print('面數 %d、頂點 %d、檔案 %.2f MB；高度 %.2f（y %.2f ~ %.2f）' % (n//3, len(P), (len(js)+len(body))/1e6, P[:,1].max()-P[:,1].min(), P[:,1].min(), P[:,1].max()))
for y in np.arange(.95, -.96, -.1):
    s = P[(P[:, 1] < y) & (P[:, 1] >= y-.1)]
    h, _ = np.histogram(s[:, 0], bins=np.arange(-.6, .61, .05))
    print('%5.2f' % y, ''.join('#' if c > 200 else ('+' if c > 20 else ('.' if c > 0 else ' ')) for c in h))
