#!/usr/bin/env python3
"""把開發版 site/ 整理成可上傳的 expo-deploy/（不會動你已放進 expo-deploy 的 posters 與 content.js）。"""
import os, re, shutil, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(HERE, 'site'); D = os.path.join(HERE, 'expo-deploy')
os.makedirs(D + '/assets', exist_ok=True); os.makedirs(D + '/posters', exist_ok=True)
html = open(SRC + '/index.html', encoding='utf-8').read()
html = html.replace('https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js', 'js/three.min.js').replace('https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js', 'js/OrbitControls.js').replace('https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js', 'js/GLTFLoader.js')
if 'rel="icon"' not in html: html = html.replace('<title>', '<link rel="icon" href="data:,">\n<title>', 1)
assert 'cdn.jsdelivr' not in html
open(D + '/index.html', 'w', encoding='utf-8').write(html)
for root, _, fs in os.walk(SRC + '/assets'):
    for f in fs:
        rel = os.path.relpath(os.path.join(root, f), SRC + '/assets'); stem = os.path.splitext(f)[0]
        used = (re.search(r'(?<![\w-])' + re.escape(stem) + r'(?![\w-])', html) and stem != 'director')
        if used: os.makedirs(os.path.dirname(f'{D}/assets/{rel}'), exist_ok=True); shutil.copy(f'{SRC}/assets/{rel}', f'{D}/assets/{rel}')
for f in ('content.js',):
    if not os.path.exists(f'{D}/{f}'): shutil.copy(f'{SRC}/{f}', f'{D}/{f}')
if not os.path.exists(D + '/posters/說明.txt'): shutil.copy(SRC + '/posters/說明.txt', D + '/posters/說明.txt')
for root, ds, fs in os.walk(D):      # 讓 Apache 一定讀得到（來源檔若是 600 權限，上傳後會變 403）
    for d in ds: os.chmod(os.path.join(root, d), 0o755)
    for f in fs: os.chmod(os.path.join(root, f), 0o644)
zp = os.path.join(HERE, 'expo-deploy.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, fs in os.walk(D):
        for f in fs:
            if f != '.DS_Store': z.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), D))
print('完成：', D, '與', zp)
