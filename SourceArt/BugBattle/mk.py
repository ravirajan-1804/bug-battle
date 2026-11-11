# usage: python mk.py body.py -> prints JSON {"script": ...} file for MCP call
import sys, json
body = open(sys.argv[1]).read()
src = open('hdr.py').read() + "\n" + body
open(sys.argv[1] + '.json', 'w').write(json.dumps({"script": src}))
print(len(src))
