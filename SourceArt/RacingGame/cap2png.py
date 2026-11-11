"""Extract the PNG from a saved CaptureViewport tool result: cap2png.py <result.txt> <out.png>"""
import base64, json, re, sys
raw = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r'"data"\s*:\s*"([A-Za-z0-9+/=]+)"', raw)
open(sys.argv[2], "wb").write(base64.b64decode(m.group(1)))
print("ok", len(m.group(1)))
