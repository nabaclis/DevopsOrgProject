#!/usr/local/bin/python

##./snaplogic/Tectonic/sldb/build/lib/sldb/services/public/group_handler.py
##./sldb/build/lib/sldb/services/admin/snap_pack_handler.py
## for features, see ./Tectonic/sldb/build/lib/sldb/services/admin/org_manager.py
# UX Build Command /Users/cseymour/snaplogic/Tectonic/cloudops/tools/create_inst.py -r jcc --pe=uxpod --pm=puppet-dev.clouddev.snaplogic.com --prefix=dev.sladmin --facts_uri=http://dev.sldb.clouddev.snaplogic.com:8086 --pkg-host=puppet-dev.clouddev.snaplogic.com -p uxpod -f mxlarge -n ux-jcc7 -d "Production jcc instance for snaplogic" --rp "snaplogic/rt/cloud/dev"
#UX deploy command: /Users/cseymour/snaplogic/Tectonic/cloudops/provision/deploy.py -P http://puppetm1.fullsail.snaplogic.com/fullsail -p uxpod -t ux183 -s repo -v --prefix dev.sladmin -H ux-jcc7.clouddev.snaplogic.com

import os, sys, boto3, syslog, uuid,json
import time, argparse, datetime, socket

default_size='mxlarge'
#default_mrc='mrc291'
instances_created_dict={}

#org_db_name='org_provisioning_db'
#org_table_name='org_requisition_data'
#mysql_account='root'

import app
from app import appFlask
from app import db_params
from app.forms import orgInputForm, dbOutputForm
from flask import render_template, flash, redirect, request

from sqlalchemy import exc, and_

def get_elastic_mrc():
    #-----------------------------------------------------------------------------------------------------------------------
    #
    #-----------------------------------------------------------------------------------------------------------------------
    build_results=os.popen('curl https://elastic.snaplogic.com/status 2> /dev/null').read()
    a_json=json.loads(build_results)
    if 'build_tag' in a_json:
       return str(a_json['build_tag'])
    else:
       print 'Terminating program because the MRC could not be determined...'
       sys.exit()

def update_org_record(org_record_obj,column_name, value):
    #-----------------------------------------------------------------------------------------------------------------------
    #
    #-----------------------------------------------------------------------------------------------------------------------
    try:
       if column_name=='jcc_create_status':
          org_record_obj.jcc_create_status=value
       elif column_name=='cloudplex_created':
          org_record_obj.cloudplex_created=int(value)
       app.session_id.commit()
    except:
       print sys.exc_info()[1]
       syslog.syslog(str(sys.exc_info()[1]))
       app.session_id.rollback()

def check_puppet_disk_size(puppet_host,instance_user):
    #-----------------------------------------------------------------------------------------------------------------------
    #
    #-----------------------------------------------------------------------------------------------------------------------
    cmd="""ssh -i ~/.ssh/tectonic4-24-12_rsa %s@%s 'df -h'"""%(instance_user,puppet_host)
    print '>>>Chech Disk Size:',cmd
    try:
       results=os.popen(cmd).read()
    except:
       syslog.syslog("Unable to reach the Puppet master")
       return False
    results=results.split('\n')[1].split()[3]
    if results.find('G') >= 0:
       results=results.strip('G')
    else:
       print 'No Gigs allocated'
       syslog.syslog("No Gigs allocated in root partition of puppet server:"+puppet_host)
       return False
    if int(results) > 1:
       return True
    else:
       syslog.syslog("Less than 1 Gig remain in root partition of puppet server:"+puppet_host)
       print "Less than 1 Gig remain in root partition of puppet server:"+puppet_host
       return False

def update_jcc_record(column_name, value,db_column_value,key_field):
    #-----------------------------------------------------------------------------------------------------------------------
    #  DB column is either instance_id or jcc_name
    #-----------------------------------------------------------------------------------------------------------------------
    if key_field=='instance_id':
       cmd="""app.SnaplogicJCCRec.%s %s "%s" """%('instance_id','==',db_column_value)
    else:
       cmd="""app.SnaplogicJCCRec.%s %s "%s" """%('jcc_name','==',db_column_value)
    db_list=app.session_id.query(app.SnaplogicJCCRec).filter(eval(cmd)) # >,>= work with filter and not filter_by
    for jcc_record_obj in db_list:
        try:
           jcc_record_obj.update_date_time=datetime.datetime.now()
           if column_name=='jcc_deploy_status':
              jcc_record_obj.jcc_deploy_status=value
           elif column_name=='jcc_create_status':
              jcc_record_obj.jcc_create_status=value
           elif column_name=='jcc_deploy_message_log':
              jcc_record_obj.jcc_deploy_message_log=value
           elif column_name=='jcc_create_message_log':
              jcc_record_obj.jcc_create_message_log=value
           elif column_name=='jcc_complete_date_time':
              jcc_record_obj.jcc_complete_date_time=value
           elif column_name=='deploy_start_date_time':
              jcc_record_obj.deploy_start_date_time=value
           elif column_name=='deploy_end_date_time':
              jcc_record_obj.deploy_end_date_time=value
           app.session_id.commit()
        except:
           print sys.exc_info()[1]
           syslog.syslog(str(sys.exc_info()[1]))
           app.session_id.rollback()

def get_response_jcc_and_instance_id(data):
    #-----------------------------------------------------------------------------------------------------------------------
    #
    #-----------------------------------------------------------------------------------------------------------------------
    try:
       instance,fqdn=data.split('FQDN:')
       jcc=fqdn.split('.')[0].strip()
       instance=instance.split('id:')[1].strip()
       return jcc,instance
    except:
       print sys.exc_info()[1], 'expect string like:Created Instance id:i-12345  FQDN:<pod>-jcc000009.fullsail.snaplogic.com'
       syslog.syslog(str(sys.exc_info()[1]))
       return None,None

def set_config_array():
    #-----------------------------------------------------------------------------------------------------------------------
    #
    #-----------------------------------------------------------------------------------------------------------------------
    config_file="""%s/.aws/config"""%(app.USER_HOME)
    config_region=[]

    if os.path.exists(config_file) and os.path.isfile(config_file):
       for i in open(config_file):
           i=i.strip()
           if len(i) > 0 and i[0]=='[' and i.find('profile') >= 0:
              i=i.replace('[','')
              i=i.replace('profile','')
              i=i.replace(' ','')
              if i.find(']') >= 0:
                 i=i.replace(']','')
              config_region.append(i)
    else:
       print config_file,'does not exist!'
       sys.exit()

    return config_region

def get_region_of_the_instance(instance_id_list,config_region):
    #-----------------------------------------------------------------------------------------------------------------------
    #
    #-----------------------------------------------------------------------------------------------------------------------
    for region in config_region:
       print '***Processing Region:',region
       boto3.setup_default_session(profile_name=region)
       ec2_conn=boto3.client('ec2')
       instances=ec2_conn.describe_instances()

       for i in instances['Reservations']:
           for j in i['Instances']:
               if j['InstanceId'] in instance_id_list:
                  return region
    return None

def fork_deploy_jcc_with_pipes(deploy_command_list):
    #-----------------------------------------------------------------------------------------------------------------------
    #
    #-----------------------------------------------------------------------------------------------------------------------
    x={}
    y={}
    pid={}
    deploy_pid_list=[]
    pipes_to_read=[]
    db_column_name='deploy_start_date_time'
    for i in range(len(deploy_command_list)):
        x[i],y[i]=os.pipe()
        pid[i]=os.fork()
        if pid[i]==0:
           os.close(x[i])
           try:
              print '**Deploying:\n\t',deploy_command_list[i]
              if len(deploy_command_list[i]) > 0:
                 jcc_name=deploy_command_list[i].split('-H')[-1].strip()   #used for jcc DB record update
                 if len(jcc_name) > 0:
                    update_jcc_record(db_column_name, datetime.datetime.now(),jcc_name,'jcc_name')
              results=os.popen(deploy_command_list[i]).read()
              time.sleep(10)      #sleep for 10 seconds
           except:
              results=str(sys.exc_info()[1])
              syslog.syslog(results)
           fd=os.fdopen(y[i],'w',0)
           fd.write(results)
           os._exit(0)
        else:
           deploy_pid_list.append(pid[i])
           pipes_to_read.append(x[i])
           os.close(y[i])
    return deploy_pid_list, pipes_to_read

    

def fork_jcc_with_pipes(jcc_command_list):
    #-----------------------------------------------------------------------------------------------------------------------
    #
    #-----------------------------------------------------------------------------------------------------------------------
    x={}
    y={}
    pid={}
    jcc_pid_list=[]
    pipes_to_read=[]
    
    for i in range(len(jcc_command_list)):
        x[i],y[i]=os.pipe()
        pid[i]=os.fork()
        if pid[i]==0:
           os.close(x[i])
           try:
              print '***Executing:\n\t',jcc_command_list[i]
              results=os.popen(jcc_command_list[i]).read()
           except:
              results=sys.exc_info()[1]
              syslog.syslog(str(sys.exc_info()[1]))
           fd=os.fdopen(y[i],'w',0)
           fd.write(results)
           os._exit(0)
        else:
           jcc_pid_list.append(pid[i])
           pipes_to_read.append(x[i])
           os.close(y[i])
    return jcc_pid_list, pipes_to_read


def get_jcc_numbers(root_dir,prefix,pod_name,jcc_name_head,echo_command):
    #-----------------------------------------------------------------------------------------------------------------------
    #
    #-----------------------------------------------------------------------------------------------------------------------
    jcc_numbers=set()
    try:
       y=os.popen("""%s/cloudops/tools/manage_inst.py --prefix=%s list pod=%s\;role=jcc"""%(root_dir,prefix,pod_name))
       if echo_command:
          print """Get JCC List using:\n\t%s/cloudops/tools/manage_inst.py --prefix=%s list pod=%s\;role=jcc"""%(root_dir,prefix,pod_name)
    except:
       print sys.exc_info()[1]
       syslog.syslog(str(sys.exc_info()[1]))
       sys.exit()
    for i in y:
        i=i.strip()
        if len(i) > 0 and i.find(':') > 0:
           j=i.split(':')
           if len(j) > 1:
              jcc_name = j[0]
              if jcc_name.find(jcc_name_head+'-jcc')==0:
                 k=jcc_name.split('jcc')
                 if len(k) == 2:
                    try:
                       jcc_numbers.add(int(k[1]))
                    except:
                       pass
    #print '***NUMBERS:',jcc_numbers
    #sys.exit()
    return jcc_numbers

def insert_db_record(a_jcc_name, an_instance_id, an_org_name, a_pod_name,an_org_rec_id,the_create_status, the_create_message,the_deploy_status,mrc_id,build_prefix):
    #---------------------------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------------------------
    a_record_id=uuid.uuid4()
    try:
       R1=app.SnaplogicJCCRec(create_date_time=datetime.datetime.now(), 
                              record_id=a_record_id,
                              org_name=an_org_name,
                              pod_name=a_pod_name, 
                              mrc=mrc_id,
                              deploy_jcc=True,
                              build_prefix=build_prefix,
                              instance_id=an_instance_id,
                              jcc_name=a_jcc_name,
                              org_record_id=an_org_rec_id,
                              jcc_create_status=the_create_status,
                              jcc_deploy_status=the_deploy_status,
                              jcc_create_message_log=the_create_message)
       app.session_id.add(R1)
       app.session_id.commit()
       print 'Success: JCC Record successfully inserted:'+a_jcc_name
       return a_record_id
    except:
       app.session_id.rollback()
       print 'Could not add jcc record...'
       print '================================================='
       print '===== Inputs that caused the Insert to fail     ='
       print 'record_id=',a_record_id
       print 'org_name=',an_org_name
       print 'pod_name=',a_pod_name
       print 'mrc=',mrc_id
       print 'build_prefix',build_prefix
       print 'instance_id=',an_instance_id
       print 'jcc_name=',a_jcc_name
       print 'org_record_id=',an_org_rec_id
       print 'jcc_create_status=',the_create_status
       print 'jcc_deploy_status=',the_deploy_status
       print 'jcc_create_message_log=',the_create_message

       return None 

def get_org_records_to_process():
    #---------------------------------------------------------------------------------------------------------------------
    #- get records where cloud to create > 0, and create_jcc_flag on the Org record is True
    #---------------------------------------------------------------------------------------------------------------------
    record_list=[]
    print '>>>Checking for Org records with number_of_cloud > 0 and create_jcc_flag=True'
    db_list=app.session_id.query(app.SnaplogicOrgRec).filter(and_(app.SnaplogicOrgRec.number_of_cloud > 0,app.SnaplogicOrgRec.create_jcc_flag==True))
    for i in db_list:
        if i.org_create_status == 'success' and i.create_jcc_flag is True and (i.number_of_cloud - i.cloudplex_created) > 0:
           record_list.append((i,i.org_name,i.record_id,i.pod_name,i.number_of_cloud-i.cloudplex_created,i.record_id,i.org_create_status,i.jcc_create_status,i.cloudplex_created))
        else:
           print '>>>No DB records found...'
    return record_list
         


def deploy_jcc(pod,mrc,prefix,jcc_name,echo_command):
    #-----------------------------------------------------------------------------------------------------------------------
    #
    #-----------------------------------------------------------------------------------------------------------------------
    user=os.environ['USER']
    command="""%s/Tectonic/cloudops/provision/deploy.py -P http://puppetm1.fullsail.snaplogic.com/fullsail/master -p %s -t %s -s repo -v --prefix %s -H %s"""%(app.SNAPLOGIC_HOME,pod,mrc,prefix,jcc_name)
    if echo_command:
       print """The JCC Deploy command is:\n\t"""+command
       syslog.syslog("""The JCC Deploy command is:\n\t"""+command)
    return command

def build_jcc_command(org_name,pod,prefix,jcc_name, size,echo_command,puppet_master,snaplex_name='cloud',location='dev'):
    #-----------------------------------------------------------------------------------------------------------------------
    #
    #-----------------------------------------------------------------------------------------------------------------------
    user=os.environ['USER']
    if pod=='prodxl' or pod == 'prodxl2':
       command="""%s/Tectonic/cloudops/tools/create_inst.py -r jcc --pe=prod --pm=%s --prefix=%s --facts_uri=http://prov-sldb.clouddev.snaplogic.com:8086 -l prod-internal --pkg-host=puppet-test.fullsail.snaplogic.com -p %s -f %s --aws-ami ami-7303dc65 -n %s -d "Production jcc instance for %s" --rp "%s/rt/%s/%s" """%(app.SNAPLOGIC_HOME,puppet_master,prefix,pod,size,jcc_name,org_name,org_name,snaplex_name,location)
    elif pod=='canaryxl':
       command="""%s/Tectonic/cloudops/tools/create_inst.py -r jcc --pe=release --pm=%s --prefix %s -l prod-internal --pkg-host=puppetm1.fullsail.snaplogic.com -p %s --aws-availability-zone us-east-1a -f %s --aws-ami ami-7303dc65 -n %s -d "Canary jcc instance for %s" --rp "%s/rt/%s/%s" """%(app.SNAPLOGIC_HOME,puppet_master,prefix,pod,size,jcc_name,org_name,org_name,snaplex_name,location)
    elif pod=='uatxl':  
       #because the init_org puts the org in stage-internal, set the -l to stage-internal
       command="""%s/Tectonic/cloudops/tools/create_inst.py -r jcc --pe=release --pm=%s --prefix %s -l stage-internal --pkg-host=puppetm1.fullsail.snaplogic.com -p %s --aws-availability-zone us-east-1a -f %s --aws-ami ami-7303dc65 -n %s -d "UAT jcc instance for %s" --rp "%s/rt/%s/%s" """%(app.SNAPLOGIC_HOME,puppet_master,prefix,pod,size,jcc_name,org_name,org_name,snaplex_name,location)
    elif pod=='snap':
       #because the init_org puts the org in stage-internal, set the -l to stage-internal
       command="""%s/Tectonic/cloudops/tools/create_inst.py -r jcc --pe=release --pm=%s --prefix %s -l stage-internal --pkg-host=puppetm1.fullsail.snaplogic.com -p %s --aws-availability-zone us-east-1a -f %s --aws-ami ami-7303dc65 -n %s -d "SNAP jcc instance for %s" --rp "%s/rt/%s/%s" """%(app.SNAPLOGIC_HOME,puppet_master,prefix,pod,size,jcc_name,org_name,org_name,snaplex_name,location)

    if echo_command:
       print """Command Used to build the JCC:\n\t"""+command
    return command

if __name__ == '__main__':
  print '******************************WARNING**********************************************************'
  print '******This sript cannot be used for building JCCs. A new oone with different procedures *******'
  print '******is being completed.       ***************************************************************'
  sys.exit()
  org_records=[]
  ec2_user='ec2-user'
  default_mrc=get_elastic_mrc()
  default_mrc='mrc291'
  PUPPET_TEST_SERVER_FOR_JCC='puppet-test.fullsail.snaplogic.com'
  if check_puppet_disk_size(PUPPET_TEST_SERVER_FOR_JCC,ec2_user) == False:
     print 'Terminating process because Puppet host:'+PUPPET_TEST_SERVER_FOR_JCC+' is low on space'
     sys.exit()

  PROCESSING='processing'
  if len(sys.argv) > 1:
     parser=argparse.ArgumentParser(description='Arguments entered here control the the creation and deployment of a number of JCCs')
     parser.add_argument('-o',required=True, help='TheOrg name used to create the Org is the value here')
     parser.add_argument('-p',required=True,choices=['prodxl','prodxl2','canaryxl','canaryxl2','qapod','uatxl'],help='The pod name is expected to fillow. It can be one of "prodxl|canaryxl|qapod"')
     parser.add_argument('-n',required=True,type=int, help='This is an integer that specifies the number of JCCs to be build')
     parser.add_argument('-v',required=False,action='store_true',help='Echo the built commands back to the terminal')
     args=parser.parse_args()
     org_records.append((args.o,args.p,args.n,None))
  else:
     jcc_activate_signal=app.session_id.query(app.SnaplogicControlsRec)
     for i in jcc_activate_signal:
         jcc_activate_signal=i.activate_jcc_creation
     if jcc_activate_signal is True:
        print '>>>jcc_active_signal is True so getting Org records to process where Org Create Status is \'success\''
        org_records=get_org_records_to_process()     #get records to publish
     else:
        print '>>Nothing to do...'
        sys.exit()

  Verbose=True

  lock_rec=app.session_id.query(app.SnaplogicLockRec).all()
  for a_lock_rec in lock_rec:
      if a_lock_rec.block_jcc_creation is True:
         print 'Cannot run ',sys.argv[0],'at this time because it is in use'
         a_lock_rec.attempts_to_get_lock=a_lock_rec.attempts_to_get_lock + 1
         try:
           print 'Updating DB Lock record...'
           app.session_id.commit()
         except:
           print sys.exc_info()[1]
         sys.exit() 
      else:
         print 'Updating Lock record and proceeding with JCC processing...'
         a_lock_rec.lock_begin_time=datetime.datetime.now()
         a_lock_rec.lock_end_time=None
         a_lock_rec.lock_process_name=sys.argv[0]
         a_lock_rec.attempts_to_get_lock=0               #reset counter
         a_lock_rec.block_jcc_creation=True              #block other runs of this program
         app.session_id.commit()

  for org_record in org_records:
      org_record_obj,org_name,an_org_rec_id,POD,number_of_jcc,record_id,org_create_status,jcc_create_status,cloudplex_created=org_record
      print '>>>',org_name, POD, number_of_jcc, record_id,org_create_status,jcc_create_status,cloudplex_created,an_org_rec_id
      JCC_CREATED=cloudplex_created
      update_org_record(org_record_obj,'jcc_create_status',PROCESSING)
      #sys.exit()
      jcc_numbers=set()
      #number_of_jcc=1
      PREFIX=''
      jcc_instance_name_head=''
      jcc_commands=[]
      #org_name=args.o
      #POD=args.p
      SL_ROOT=os.environ['SL_ROOT']
      if POD=='prodxl' or POD=='prodxl2':
         PREFIX='prod.sladmin'
         #default_mrc='mrc291'
         jcc_instance_name_head='prodxl'
         domainname='fullsail.snaplogic.com'
         jcc_numbers=get_jcc_numbers(SL_ROOT,PREFIX,POD,jcc_instance_name_head,Verbose)
      elif POD=='canaryxl' or POD=='canaryxl2':
         PREFIX='prod.sladmin'
         #default_mrc='mrc291'
         jcc_instance_name_head='canxl'
         domainname='fullsail.snaplogic.com'
         jcc_numbers=get_jcc_numbers(SL_ROOT,PREFIX,POD,jcc_instance_name_head,Verbose)
      elif POD=='qapod':
         PREFIX='dev.sladmin'
         jcc_instance_name_head='qa'
         domainname='clouddev.snaplogic.com'
         jcc_numbers=get_jcc_numbers(SL_ROOT,PREFIX,POD,jcc_instance_name_head,Verbose)
      elif POD=='uatxl':
         PREFIX='prod.sladmin'
         #default_mrc='mrc291'
         jcc_instance_name_head='uatxl'
         domainname='fullsail.snaplogic.com'
         jcc_numbers=get_jcc_numbers(SL_ROOT,PREFIX,POD,jcc_instance_name_head,Verbose)
      elif POD=='snap':
         PREFIX='prod.sladmin'
         #default_mrc='mrc291'
         jcc_instance_name_head='snapxl'
         domainname='fullsail.snaplogic.com'
         jcc_numbers=get_jcc_numbers(SL_ROOT,PREFIX,POD,jcc_instance_name_head,Verbose)
      else:
        print 'Unsupported pod...'
        sys.exit()

      jcc_list=list(jcc_numbers)
      jcc_list.sort()              #sort used JCC numbers ascending
    
      #print 'JCCs',jcc_list
      if len(jcc_list)==0:
         jcc_list.append(0)

      jcc_availability_pool=range(jcc_list[-1]+1, jcc_list[-1]+1000)
      jcc_availability_pool.sort()

      #print '**==================================================================================='
      #print '****Availability_pool:',jcc_availability_pool
      #print '**==================================================================================='
      #sys.exit()

      #----------------------------Prevent system from creating more than 5 JCCs for an aor at the same time--------------#
      if number_of_jcc > 5:
         number_of_jcc=5
      #----------------------------End prevention block-------------------------------------------------------------------#
    
      print "The next available Jcc's are:"
      jccs_found=0
      while True:                                                        #loop until the correct number of JCCs is gotten
         jcc_number_selected=jcc_availability_pool.pop(0)                #get the lowest one on the list
         the_jcc=jcc_instance_name_head+'-jcc'+str(jcc_number_selected)  #build JCC name
         test_jcc_name="%s.fullsail.snaplogic.com"%(the_jcc)
         y=None
         try:
            y=socket.gethostbyname(test_jcc_name)                        #check if JCC exists in DNS. if NOT, the name is good to use 
         except:
            pass
         if y is None:                                                   #host is not in DNS 
            jccs_found += 1                                              #get a number of Jccs not in DNS
            #--------------------------------Generate the JCC Command------------------------------------------------------------#
            jcc_commands.append(build_jcc_command(org_name,POD,PREFIX,the_jcc,default_size,Verbose,PUPPET_TEST_SERVER_FOR_JCC,'cloud','dev'))
            #--------------------------------End Command Generation--------------------------------------------------------------#
            if jccs_found == number_of_jcc:
               break

      jcc_fullname_list=[]  #lists all JCCs created    
      if len(jcc_commands) > 0:
         pids_to_check, pipes_to_read=fork_jcc_with_pipes(jcc_commands)
         for ret_pipe in pipes_to_read:
             fd=os.fdopen(ret_pipe,'r',0)
             z=fd.read()
             print '>>>RESULTS:\n\t', z                                            #echo results back to the screen
             a_jcc_created,an_instance_id=get_response_jcc_and_instance_id(z)      #get the jcc name and instance Id from the return string
             if not (a_jcc_created is None and an_instance_id is None):
                JCC_CREATED=JCC_CREATED+1
                instances_created_dict[an_instance_id]=a_jcc_created               #Create a dict of name value pairs for reuse
                the_create_status='success'
                the_deploy_status='processing'
                the_create_message_log=''
                try:
                   update_org_record(org_record_obj,'cloudplex_created',JCC_CREATED)  #update the ORG master record 
                   update_org_record(org_record_obj,'jcc_create_status','success')
                   app.session_id.commit()
                except:
                   print 'Org-Rec: cloudplex_created could not be updated with value:'+str(JCC_CREATED)
                   syslog.syslog('Org-Rec: cloudplex_created could not be updated with value:'+str(JCC_CREATED))
                   print sys.exc_info()[0]
                   app.session_id.rollback()
                try:   
                   jcc_fullname_list.append(a_jcc_created+'.'+domainname)
                   the_jcc_record_id=insert_db_record(a_jcc_created+'.'+domainname, an_instance_id, org_name, POD, an_org_rec_id,the_create_status, the_create_message_log,the_deploy_status,default_mrc,PREFIX)
                   update_jcc_record('jcc_complete_date_time', datetime.datetime.now(),an_instance_id,'instance_id')  #set completion date 
                   update_jcc_record('jcc_create_message_log', z.encode('utf-8'),an_instance_id,'instance_id')  #save createn log
                except:
                   print "Jcc-Rec: Could not insert JCC record for created jcc:"+a_jcc_created
                   syslog.syslog("Jcc-Rec: Could not insert JCC record for created jcc:"+a_jcc_created)
                   print sys.exc_info()[0]
                   app.session_id.rollback() 

         #print '*****PID-LIST:',pids_to_check
         print '>>Waiting for Jcc creation to complete in sub-processes'
         for i in pids_to_check:
             the_pid, results=os.waitpid(i,0)
             print '\tPID:',the_pid,'RESULTS:',results

      instances_ids_to_monitor=instances_created_dict.keys()   #save the instance Ids for the monitoring test loop
      for k in instances_created_dict:                         #print the instances created
          print '>>Created instance:'+k
          syslog.syslog('>>Created instance:'+k)
  try:
     print 'Resetting Lock record and proceeding with JCC processing...'
     a_lock_rec.lock_process_name=None
     a_lock_rec.attempts_to_get_lock=0               #reset counter
     a_lock_rec.block_jcc_creation=False             #Release lock record
     app.session_id.commit()
  except:
     print sys.exc_info()[0]
     app.session_id.rollback()
  print '****Completed building JCC without Deploy...'







