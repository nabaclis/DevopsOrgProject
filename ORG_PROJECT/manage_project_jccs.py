#!/usr/local/bin/python

import os, sys
import argparse
import snapi.snapi_request
import snapi.snapi_asset
import snapi.snapi_meter
import snapi.snapi_plex
import slutils.sladmin

import syslog
import app

from  datetime import datetime
from glob import *
import psycopg2, psycopg2.extensions

from app.common_org_utility_functions import get_pod_admin_user 

pod_name_menu=['prodxl','prodxl2','canaryxl','canaryxl2','uatxl','qa','snap','ux','ux2','ux3','portal','budgy','spark','salespod','perf','prov-sldb','dev-sldb','stage']
PROJECTS=['SL_DRKSIDE_99_001','SL_PCIC_81_001','SL_MISC_77_001','SL_TOUI_66_001','SL_UAT_02_001','SL_PROD_23_001','prodv2']
PEM_FILE='~/.ssh/sl_root_access_prodv2.pem'
copy_command_file='FILE_WITH_COPY_COMMANDS.txt'
#LATEST_IMAGE_ID='04bb2026-c521-4855-8dca-434645fb5a7d'      #id of the latest image
snaplogic_etc_files='snaplogic_etc'

prov_properties="""
jcc.http_chunked_streaming = False
jcc.location = cloud
jcc.heap.max_size = 12g
jcc.subscriber_id = Quorum-Trial
jcc.sldb_uri = https://elastic.snaplogic.com:443
jcc.ccreg.key_prefix = cc
jcc.environment = dev
"""

def process_migration_properties_file(a_dir):
    #--------------------------------------------------------------------------------------------------------------
    # Build a dictionary where key is orgname and values are hostnames
    #--------------------------------------------------------------------------------------------------------------
    count=0
    org_dict={}
    if os.path.exists(a_dir) and os.path.isdir(a_dir):
       for i in glob(a_dir+'/*'):
           if os.path.isdir(i):
              if os.path.exists(i+'/provisioned.properties') and os.path.isfile(i+'/provisioned.properties'):
                 for j in open(i+'/provisioned.properties'):
                     j=j.strip()
                     if len(j) > 0 and j[0] != '#' and j.find('jcc.subscriber_id') == 0:
                        k=j.split('=')
                        if len(k)== 2:
                           count+=1
                           the_org_name=k[1].strip()
                           if not org_dict.has_key(the_org_name):
                              org_dict[the_org_name]=[i]
                           else:
                              org_dict[the_org_name].append(i)
                           break
                        else:
                           print '>>ERROR:',i+'/provisioned.properties'
    return org_dict, count 

def update_org_names(cursor,update_records):
    #---------------------------------------------------------------------------------------------------------------
    #- Find a matching JCC record based on the Ip address and set its Org namd and provision date 
    #---------------------------------------------------------------------------------------------------------------
    for i in update_records:
        try:
          print 'Update DB:%s'%(i)
          syslog.syslog('Update DB:%s'%(i))
          cursor.execute(i)
        except:
          print 'Failed to execute the following record:\n\t',i

def set_org_name_and_prov_date(conn,cursor,jcc_name,org_name,location_name,date_time):
    #---------------------------------------------------------------------------------------------------------------
    #- Set the org name and prov date
    #---------------------------------------------------------------------------------------------------------------
    print 'Adjusting Org names'
    is_cplex,is_gplex,is_hplex=False,False,False #initialize to False
    if location_name=='cloud':
       is_cplex=True
    elif location_name=='sidekick':
       is_gplex=True
    elif location_name=='hadooplex':
       is_hplex=True
    command="""update vegas_jcc_instances set prov_date='%s', org_name='%s',is_cplex='%s', is_gplex='%s',is_hplex='%s' where jcc_name='%s'"""%(date_time,org_name,is_cplex,is_gplex,is_hplex,jcc_name) 
    print command
    try:
      cursor.execute(command)
      print 'Successfully updated Provisioned date and Org name for Org:'+org_name
      syslog.syslog('Successfully updated Provisioned date and Org name for Org:'+org_name)
    except:
      syslog.syslog('Failed Org-nme Update:'+command)
      print 'Failed Org-nme Update:'+command

def update_the_jcc_db_record(conn,cursor,new_jcc_list, org_name):
    #---------------------------------------------------------------------------------------------------------------
    #-  Set the DB record to reflect that it is now taken`
    #---------------------------------------------------------------------------------------------------------------
    sql_command_list=[]
    date_time=str(datetime.now()).split('.')[0]
    for jcc_host in new_jcc_list:
        sql_command_list.append("""update vegas_jcc_instances set prov_date='%s', org_name='%s',is_cplex='%s' where jcc_name='%s'"""%(date_time,org_name,True,jcc_host))
    update_org_names(cursor,sql_command_list)


def get_prov_properties_params(org_name, pod_name, location, jcc_env, pod_prefix, uri):
    #---------------------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------------------
    keys_properties=''
    prov_properties=''
    try:
       keys_properties=generate_property_keys(org_name,pod_name)
       prov_properties="""
jcc.http_chunked_streaming = False
jcc.location = %s
jcc.heap.max_size = 12g
jcc.subscriber_id = %s
jcc.sldb_uri = %s
jcc.ccreg.key_prefix = cc
jcc.environment = %s 
"""%(location,org_name,uri,jcc_env)
    except:
       error_msg=str(sys.exc_info()[1])
       syslog.syslog(error_msg)

    print keys_properties
    print prov_properties

def does_org_exist(pod_prefix,org_name,org_location):
    #----------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------
    pod_login_user, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_prefix, None)
    session = snapi.snapi_request.SnapiRequest(pod_login_user, api_key)

    asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)
    plex_api = snapi.snapi_plex.SnapiPlex(session, admin_uri)
    meter_api = snapi.snapi_meter.SnapiMeter(session, admin_uri)

    for i in plex_api.list_all_plexes():
        if i['path'].find(org_name+'/shared') >= 0 and i['path'].split('shared/')[-1].lower().find(org_location.lower()) >= 0:
           if i['runtime_path_id'].find(org_name) >= 0 and i['runtime_path_id'].find('/'+org_location+'/') > 0:
              return True, i['runtime_path_id'].split('/')[-1]          #return True and the Cloud/Groundplex environment
    return False, None

def generate_property_keys(org_name,pod_name):
    #--------------------------------------------------------------------------------------
    #- Get the keys for the new cloudplex
    #--------------------------------------------------------------------------------------
    get_key_home='/Users/cseymour/snaplogic/Tectonic/cloudops/tools/getkey.py'
    prefix,uri=get_pod_admin_user(pod_name)
    cmd="""%s --prefix=%s --subscriber_id=%s --target_prefix=cc"""%(get_key_home,prefix,org_name)
    try:
      syslog.syslog('Command:'+cmd)
      results=os.popen(cmd).read()
      return results
    except:
      syslog.syslog('Failed command:'+cmd)
      return None

def is_jcc_on_the_host(host_name,jcc_project):
    #--------------------------------------------------------------------------------------------------------------
    #- Check to make sure JCC is not running on the host and that /opt/snaplogic is missing
    #--------------------------------------------------------------------------------------------------------------
    print '===>>>Is JCC on host',host_name
    if jcc_project=='prodv2':
       print '=>>>Build Command'
       command="""ssh -t -i ~/.ssh/aws-ec2-west2-user.pem centos@%s 'if [ -e /opt/snaplogic ]; then echo True; else echo False; fi'"""%(host_name)
       print 'Command:',command
       results=os.popen(command).read()
       print '>>>>RESULTS:',results
       

def migrate_jccs(jcc_count, org_name, jcc_stack, pod_name, selected_jccs, conn, cursor, copy_cmd):
    #---------------------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------------------
    new_jcc_list=[]
    for i in selected_jccs:
        a_free_jcc=jcc_stack.pop()
        new_jcc_list.append(a_free_jcc)     #pick a JCC from the free list
        copy_cmd.append("""scp -rp %s cloud@%s:/tmp/%s"""%(i,a_free_jcc,snaplogic_etc_files))
    update_the_jcc_db_record(conn,cursor,new_jcc_list, org_name)
    #copy the files to the host
    #      Start the JCC
    return jcc_stack


def deploy_jccs(jcc_count, org_name, pod_name, selected_jccs, project_id, conn, cursor):
    #---------------------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------------------
    #update_the_jcc_db_record(conn,cursor,selected_jccs, org_name)
    print '>>SELECTED-JCCs:',selected_jccs
    print 'Deploying Jccs...'
    print jcc_count, org_name, pod_name
    for i in selected_jccs:
        is_jcc_on_the_host(i,project_id)
    
    print 'First: Set the Org name, provision date, and so on for the JCC record in the db'
    print 'Second: Test to make sure jcc is not running on the host'
    print 'Third: Copy the newly made directory data into /opt/snaplogic/etc/*'
    print 'Fourth: Start the JCC on the host'

def get_postgres_connection():
    #---------------------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------------------
    db='vegas_inventory'; user='vegas_admin'; host='52.73.179.64'; port='5432'; password='vegas123!'
    connect_str="""dbname=%s user=%s host=%s password=%s port=%s"""%(db,user,host,password, port)
    try:
      conn = psycopg2.connect(connect_str)
      conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    except:
      print "I am unable to connect to the database"
      sys.exit()
    return conn, conn.cursor()

if __name__=='__main__':
   print 'Projects:', PROJECTS,'\n'
   parser=argparse.ArgumentParser(description="This program is used to manage Las Vegas Datacenter JCC hosts deployment")
   subparsers=parser.add_subparsers(help='User sub-parser')
   parser.add_argument('-p',required=True,choices=PROJECTS,help='A Project ID is expected to follow')

   process_jccs=subparsers.add_parser('LIST_JCCS')
   process_jccs.add_argument('-f','--feature',choices=['available','used','all'],required=True, help='Lists JCCS from the input ProjectID')
   process_jccs.set_defaults(which='LIST_JCCS')

   process_jccs=subparsers.add_parser('SET_PROVISIONED_ORG_NAMES')
   process_jccs.set_defaults(which='SET_PROVISIONED_ORG_NAMES')

   process_jccs=subparsers.add_parser('BUILD_JCCS')
   process_jccs.add_argument('-o','--org_name',required=True, help='Org name of ther JCC')
   process_jccs.add_argument('-d','--pod_name',choices=pod_name_menu, required=True, help='Pod name of ther JCC')
   process_jccs.add_argument('-e','--env_name',required=True, help='Environment of the JCC')
   process_jccs.add_argument('-n','--number',required=True, type=int, help='The number of the JCC')
   process_jccs.add_argument('-l','--location',choices=['cloud','sidekick'], required=True, help='The location of the JCC')

   process_jccs.set_defaults(which='BUILD_JCCS')

   process_jccs=subparsers.add_parser('MIGRATE_JCCS')
   process_jccs.add_argument('-f','--file',required=True, help='File name with the backup config files')

   process_jccs.set_defaults(which='MIGRATE_JCCS')

   args=parser.parse_args()

   if args.p == 'prodv2':
      LATEST_IMAGE_ID='ami-f5cd7795'          # the AWS image ID
   else:
      LATEST_IMAGE_ID='04bb2026-c521-4855-8dca-434645fb5a7d'  # the VEGAS JCC image ID
 
   available_command="""select * from vegas_jcc_instances where org_name is NULL and decomm_date is NULL and prov_date is NULL and project_id='%s' and jcc_name like '%%-jccs-%%'  and image_id='%s'"""%(args.p,LATEST_IMAGE_ID)
   #print available_command

   all_command="""select * from vegas_jcc_instances where project_id='%s' and jcc_name like '%%-jccs-%%'"""%(args.p)
   used_command="""select * from vegas_jcc_instances where org_name is not NULL and decomm_date is NULL and prov_date is not NULL and project_id='%s' and jcc_name like '%%-jccs-%%' order by org_name"""%(args.p)
   all_jcc_and_org_names_command="""select jcc_name, org_name from vegas_jcc_instances where project_id='%s' and jcc_name like '%%-jccs-%%'"""%(args.p)
   all_config_jcc_and_org_names_command="""select jcc_name, org_name,jcc_location_name from config_backup_table where insert_date=(select max(insert_date) from config_backup_table)"""

   if args.which == 'SET_PROVISIONED_ORG_NAMES':
      a_date_time=str(datetime.now()).split('.')[0]
      print 'Processing Orgs assignment...'
      conn,cursor=get_postgres_connection()
      cursor.execute(all_jcc_and_org_names_command)
      all_jcc_list=cursor.fetchall()
      cursor.execute(all_config_jcc_and_org_names_command)
      all_config_jcc_list=cursor.fetchall()
      config_jcc_dict={}
      for i in all_config_jcc_list: 
          config_jcc_dict[i[0]]=i[1],i[2]
      for i in all_jcc_list:
          if i[0] in config_jcc_dict:
             if i[1] != config_jcc_dict[i[0]][0]:
                #print message to show Org name changed
                #print i[0],config_jcc_dict[i[0]][0],config_jcc_dict[i[0]][1],a_date_time
                set_org_name_and_prov_date(conn,cursor,i[0],config_jcc_dict[i[0]][0],config_jcc_dict[i[0]][1],a_date_time) #jcc_name,new org_name, location
   elif args.which=='LIST_JCCS':
      if args.p not in PROJECTS:
         print 'Project must be one of the following:'
         print PROJECTS 
         sys.exit()
   
      conn,cursor=get_postgres_connection()
      if args.feature == 'available':
         cursor.execute(available_command)
      elif args.feature == 'all':
         cursor.execute(all_command)
      elif args.feature == 'used':
         cursor.execute(used_command)
      try:
         for i in cursor.fetchall():
             print i
      except:
         print 'Unable to get Postgres data'
   elif args.which=='BUILD_JCCS':
      assigned_jccs=[]
      conn,cursor=get_postgres_connection()
      cursor.execute(available_command)
      available_records=cursor.fetchall()
      if args.number <= len(available_records):
         for j,i in enumerate(available_records):
             if j < args.number:
                assigned_jccs.append(i[2])
      pod_prefix,uri=get_pod_admin_user(args.pod_name)
      return_code, cloud_env=does_org_exist(pod_prefix,args.org_name,args.location)   #get the cloud env from SLDB
      if return_code:
         get_prov_properties_params(args.org_name, args.pod_name, 'cloud', cloud_env,pod_prefix, uri)
         deploy_jccs(args.number,args.org_name, args.pod_name,assigned_jccs,args.p,conn,cursor)
      else:
         syslog.syslog("The Org has no cloudplex created so exiting, Org name is:%s"%(args.org_name))
         print "The Org has no cloudplex created so exiting, Org name is:%s"%(args.org_name)
   #elif args.which=='MIGRATE_JCCS':
   #   copy_command=[]
   #   stack_of_available_jccs=[]
   #   conn,cursor=get_postgres_connection()
   #   cursor.execute(available_command)
   #   print 'Fetching DB data...'
   #   available_records=cursor.fetchall()
   #   org_dict, jcc_count=process_migration_properties_file(args.file)
   #   print "Require:%s JCCs"%(jcc_count) 
   #   sorted_keys=org_dict.keys()
   #   sorted_keys.sort()
   #   assigned_jccs=[]
   #   print 'JCC-COUNT:',jcc_count, 'AVAIL-RECS:',len(available_records)
   #   for k in available_records:
   #       stack_of_available_jccs.append(k[2]) 
   #   if jcc_count <= len(stack_of_available_jccs):
   #      x=0
   #      for org_name in org_dict:
   #          stack_of_available_jccs=migrate_jccs(len(org_dict[org_name]),org_name, stack_of_available_jccs, args.p,org_dict[org_name],conn,cursor, copy_command)
   #          x+=1
   #      fp=open(copy_command_file,"w")
   #      for i in copy_command:
   #          fp.write(i+'\n')
   #      fp.close()
   #      print '\n>>>SCP commands written to:',copy_command_file
   #   else:
   #      syslog.syslog("Error: Not enough JCCs available. Available: %s, Required: %s"%(len(available_records),jcc_count))
   #      print ("Error: Not enough JCCs available. Available: %s, Required: %s"%(len(available_records),jcc_count))




