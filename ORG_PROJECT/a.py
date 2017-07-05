#!/usr/bin/python 

import os, sys


test_jcc_command="""ping -c1 -t20 %s.fullsail.snaplogic.com"""%('prodxl-jcc367')
y=os.popen(test_jcc_command).read() #check if JCC exists anyway
y=y.strip()


print 'Should be > 0:', y.find('Unknown host')

print 'BOOLEAN VALUE:',y.find('Unknown') >= 0

z='Hello world---Unknown host'

print 'z-BOOLEAN VALUE:',z.find('Unknown') >= 0
