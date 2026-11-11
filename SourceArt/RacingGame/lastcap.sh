#!/bin/sh
# usage: lastcap.sh <name>  -> extracts newest CaptureViewport result to scratchpad/<name>.png
cd "/c/Users/likit/.claude/projects/D--newwgame-BBB/e5b2f890-dac3-4a76-9dcd-42533dfd42cf/tool-results" && \
python /d/newwgame/BBB/SourceArt/RacingGame/cap2png.py "$(ls -t mcp-unreal-mcp-call_tool-*.txt | head -1)" \
  "C:/Users/likit/AppData/Local/Temp/claude/D--newwgame-BBB/e5b2f890-dac3-4a76-9dcd-42533dfd42cf/scratchpad/$1.png"
