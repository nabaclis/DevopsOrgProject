#!/usr/local/bin/python

import os, sys
import app

JCC_DELETE_FILE_LIST='/tmp/jcc_delete_entries.txt'   #file with entries like "prodxl-jcc99999 prodxl"

if __name__=='__main__':
   if os.path.exists(JCC_DELETE_FILE_LIST) and os.path.isfile(JCC_DELETE_FILE_LIST):
      for i in open(JCC_DELETE_FILE_LIST):
          i=i.strip()
          j=i.split()
          if len(j) == 2:
             jcc_name=j[0]
             pod=j[1]
             cmd="""%s/Tectonic/cloudops/tools/manage_inst.py --prefix prod.sladmin update delete 'name=%s;role=jcc;pod=%s'"""%(app.SNAPLOGIC_HOME,jcc_name,pod)
             print 'Executing:',cmd
             results=os.popen(cmd).read()
             print '>>>Results:',results
          if pod.find('prod') >= 0:
             jcc_name=jcc_name+'.fullsail.snaplogic.com'
          cmd1="""curl -X DELETE http://mon1.fullsail.snaplogic.com:4567/client/%s"""%(jcc_name)
          print 'Deleting Sensu Entry:',cmd1
          results=results=os.popen(cmd1).read()
          print '>>>Results:',results
      os.unlink(JCC_DELETE_FILE_LIST)


#The  delete
#     sensu
#     aws
#     zabbix, 

