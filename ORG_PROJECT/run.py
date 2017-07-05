#!/usr/local/bin/python

from app import appFlask
from app import *
import os

#screen -d -m -S OrgCreationSystem ./run.py 

appFlask.secret_key = os.urandom(16)

if os.uname()[0]=='Darwin':
   appFlask.run(host='127.0.0.1', port=5555, debug=True)
else:
   appFlask.run(host='127.0.0.1', port=8088, debug=True)
