#!/bin/bash

# DO NOT RUN THIS SCRIPT UNLESS YOU KNOW WHAT YOU'RE DOING

THE_DIR=$(python3 -c "import aiohttp;print(aiohttp.__path__[0])"|head -n1)
mv -v "$THE_DIR/web_fileresponse.py" "$THE_DIR/web_fileresponse.py.original"
cp -v web_fileresponse.py.patch "$THE_DIR/web_fileresponse.py"
