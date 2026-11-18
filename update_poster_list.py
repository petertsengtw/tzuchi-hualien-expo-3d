#!/usr/bin/env python3
"""更新海報清單：掃描 posters 資料夾，把檔名寫進 content.js 的 POSTER_FILES。
每次增加或更換海報圖檔後，在終端機執行一次，再把 content.js 和 posters 資料夾一起上傳。
用法：python3 update_poster_list.py            （預設處理 expo-deploy）
      python3 update_poster_list.py 其他資料夾
"""
import os, re, sys
root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'expo-deploy')
pdir, cjs = os.path.join(root, 'posters'), os.path.join(root, 'content.js')
files = sorted(f for f in os.listdir(pdir) if re.match(r'^A[\d-]+\.(jpe?g|png|webp)$', f, re.I))
line = 'window.POSTER_FILES = ' + ('[' + ', '.join('"%s"' % f for f in files) + ']') + ';   // 由 update_poster_list.py 自動產生，請勿手改\n'
src = open(cjs, encoding='utf-8').read()
if 'window.POSTER_FILES' in src: src = re.sub(r'window\.POSTER_FILES = .*\n', line, src)
else: src = src.rstrip('\n') + '\n' + line
open(cjs, 'w', encoding='utf-8').write(src)
print('已寫入 %d 個海報檔名：%s' % (len(files), ', '.join(files) or '（無）'))
