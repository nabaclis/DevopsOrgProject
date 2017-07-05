#!/usr/local/bin/python

import os, sys, boto3, syslog, uuid
import time, argparse, datetime, socket

instances_created_dict={}

org_db_name='org_provisioning_db'
org_table_name='org_requisition_data'
mysql_account='root'

import app
from app import appFlask
from app import db_params
from app.forms import orgInputForm, dbOutputForm
from flask import render_template, flash, redirect, request

from sqlalchemy import exc, and_

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
              results=os.popen(deploy_command_list[i]).read()
              time.sleep(10)      #sleep for 10 seconds
           except:
              results=str(sys.exc_info()[1])
              syslog.syslog(results)
           fd=os.fdopen(y[i],'w',0)
           fd.write(results)
           os._exit(0)
        else:
           update_jcc_record(db_column_name, datetime.datetime.now(), deploy_command_list[i].split('-H')[-1].strip(),'jcc_name')   #set deploy start time
           deploy_pid_list.append(pid[i])
           pipes_to_read.append(x[i])
           os.close(y[i])
    return deploy_pid_list, pipes_to_read

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
           app.session_id.commit()                               #save changes made 
        except:
           print sys.exc_info()[1]
           syslog.syslog(str(sys.exc_info()[1]))
           app.session_id.rollback()


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


if __name__=='__main__':
  #-----------------------------------------------------------------
  Verbose=True
  jcc_fullname_list=[]
  instances_ids_to_monitor=[]
  # get JCC records where jcc_create_status is 'success', deploy_jcc is True, jcc_deploy_status is 'processing' and deploy_start_date_time is None
  jcc_list=app.session_id.query(app.SnaplogicJCCRec).filter(and_(app.SnaplogicJCCRec.jcc_create_status=='success',app.SnaplogicJCCRec.deploy_jcc==True,app.SnaplogicJCCRec.jcc_deploy_status=='processing', app.SnaplogicJCCRec.deploy_start_date_time==None)) # >,>= work with filter and not filter_by
  for jcc_record in jcc_list:
      instances_created_dict[jcc_record.instance_id]=(jcc_record.pod_name,jcc_record.mrc,jcc_record.build_prefix,jcc_record.jcc_name)
      jcc_fullname_list.append(jcc_record.jcc_name)
      jcc_record.deploy_jcc=False
      try:
         app.session_id.commit()       #set the deploy_jcc flag to False to prevent rerun
      except:
         print sys.exc_info()[1]
         syslog.syslog(str(sys.exc_info()[1]))
         app.session_id.rollback()

  instances_ids_to_monitor=instances_created_dict.keys()

  if len(instances_ids_to_monitor) == 0:
     print '>>>Nothing to deploy, terminating processing...'
     sys.exit()

  #--------------------JCC Deployment Section-----------------------------------------------------------------------#
  print '>>Get the region and instance ID and test to see if its running and the 2/2 checks are good'
  config_region=set_config_array()
  region=get_region_of_the_instance(instances_ids_to_monitor,config_region) #pass a list of instance ids created


  print '***REGION:', region
  s=boto3.Session(profile_name=region)
  y=s.resource('ec2')
    
  deploy_commands_list=[]
  while instances_ids_to_monitor:                                                      #go through look looking for each instance to pass the 2/2 checks
        for status in y.meta.client.describe_instance_status(InstanceIds=instances_ids_to_monitor)['InstanceStatuses']:
            if status['InstanceState']['Name'] == 'running' and status['SystemStatus']['Status']=='ok' and status['InstanceStatus']['Status'] == 'ok':
               instances_ids_to_monitor.remove(status['InstanceId'])                    #remove instance from the loop list if it passes the tests
               #get and set status to procesing
               column_name='jcc_deploy_status'
               column_value='processing'
               try:
                  update_jcc_record(column_name, column_value,status['InstanceId'],'instance_id')
               except:
                  print 'Could not update the JCC record with deploy_status=processing'
                  pass
               print 'Deploy instance...', status['InstanceId']
               POD,default_mrc,PREFIX,the_jcc=instances_created_dict[status['InstanceId']]
               deploy_commands_list.append(deploy_jcc(POD,default_mrc,PREFIX,the_jcc,Verbose))  #build the deploy command and add it to list for later use
  #sleep until all JCCs come alive
  print '>>Waiting on all JCC nodes to resolve before running deploy...'
  while True:
        if len(jcc_fullname_list)==0:
           break
        for k in jcc_fullname_list:
            try:
               y=socket.gethostbyname(k)
               jcc_fullname_list.remove(k)
               update_jcc_record('jcc_complete_date_time', datetime.datetime.now(),k,'jcc_name')  #set completion time of the JCC from AWS 2/2 and DNS checks
            except:
               print '>>>',k, 'is not alive!'
               pass
        time.sleep(30)

  #Create a number of pipes and forks to deploy the command(s)
  pids_to_check, pipes_to_read=fork_deploy_jcc_with_pipes(deploy_commands_list)
    
  for ret_pipe in pipes_to_read:            #Read results from the Instance deploy script
      fd=os.fdopen(ret_pipe,'r',0)
      z=fd.read()
      if z.find('Host') >= 0 and z.find('is up,') >= 0:
         hostname=z.split('Host')[1].split()[0]
         #get and set status to procesing
         column_name='jcc_deploy_status'
         if len(hostname) > 0:
            column_value='success'
         else:
            column_value='failed'
         try:
            update_jcc_record(column_name, column_value,hostname,'jcc_name')          #set run status
         except:
            print '***Warning: Could not update JCC Deploy Status...'
            pass

         try:
            update_jcc_record('deploy_end_date_time', datetime.datetime.now(),hostname,'jcc_name')  #set completion time
         except:
            print '***Warning: Could not update Deploy end time...'
            pass

         try:
            update_jcc_record('jcc_deploy_message_log', z.encode('utf-8'),hostname,'jcc_name')  #load deploy transcript
         except:
            print 'Could not update the Deploy Message Log'
            pass

  print '>>Wait for Deploy subprocesses with PIDs',pids_to_check,'to complete'
  for i in pids_to_check:
      the_pid, results=os.waitpid(i,0)
      print '>>Instance deploy pid with:',the_pid,'RESULTS:',results
  #Deployment is good when this curl returns 'OK', /usr/bin/curl http://prodxl-jcc351.fullsail.snaplogic.com:8090/healthz
