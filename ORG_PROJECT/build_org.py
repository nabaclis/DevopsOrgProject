#!/usr/local/bin/python

import os, sys, syslog, datetime
import simplejson
import slutils.sladmin
import snapi.snapi_request
import snapi.snapi_asset
import snapi.snapi_admin
import snapi.snapi_audit
import snapi.snapi_catalog
import snapi.snapi_context
import snapi_base.exceptions
import snapi.snapi_plex
import snapi_base.keys as keys
import argparse
org_db_name='org_provisioning_db'
org_table_name='org_requisition_data'
mysql_account='root'
import app

debug=False

from app.custom_org_utility_functions import does_org_exist, generate_property_keys #add_subscription , get_asset_api_ptr
from app import appFlask
from app import db_params
from app.forms import orgInputForm, dbOutputForm
from flask import render_template, flash, redirect, request

from sqlalchemy import exc

message_buffer=[]

PODS=('prodxl','prodxl2','uatxl','canaryxl','canaryxl2','snap','ux3', 'ux2','ux','portal','budgy','spark','salespod','perf','prov-sldb','dev-sldb','stage')

def help_instructions():
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    return """
This program requires the file ORG_INPUT_FILE.txt in your home directory with the Org details.
The file expects the Org name, the Environment, and a list of email addresses and their type.

   org_name='<org name>' should be the first entry in the file

   environment='canary|prodxl|uatxl' should be the second entry in the file

A list of email addresses may follow, one per line in the format below:

   user='jdoe@snaplogic.com   admin"
   user='jdoe1@snaplogic.com'  

To specify an email address without admin priviliges, exclude the "admin" string above.

All blank lines or ones starting with the '#' character will be ignored
    """

def update_org_features(org_name,pod_prefix,config_file,features_dict):
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    if len(features_dict) > 0:
       print '>>>>Adding Features: '+str(features_dict)
       admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_prefix, config_file)
       session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
       asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)
       x=asset_api.update_subscription(org_name, data=features_dict)
       selected_items=features_dict.keys()
       selected_items=','.join(selected_items)
       print """>>>>>Added Features: %s"""%(selected_items)

def create_hadooplex_snaplex(pod_prefix,container_path, subscriber, hplex):
    #---------------------------------------------------------------------------------------------------
    #- Added on 6/29/2017 to create hadooplex simply
    #---------------------------------------------------------------------------------------------------
    configfile=None
    DEFAULT_HADOOPLEX_ENVIRONMENT = 'Hadooplex-dev'
    DEFAULT_MIN_JCC = 1
    admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_prefix,configfile)
    session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
    asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)
    plex_api = snapi.snapi_plex.SnapiPlex(session, admin_uri)
    if hplex is not None:
        plex_api.create_plex(container_path, hplex, '/' + subscriber, 'sidekick', DEFAULT_HADOOPLEX_ENVIRONMENT, min_jcc=DEFAULT_MIN_JCC,container_type='yarn')   #yarn needed for Hadooplex
        print('Snaplex ' + hplex + ' created.')

def get_premium_snaps(asset_api,sysadmin_snapi_snap_pack, org_name):
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    config_file=None
    snap_list_dict={}

    org_snid=asset_api.lookup_org(org_name)['snode_id']
    subs = sysadmin_snapi_snap_pack.check_subscriptions(org_snid)[keys.SNAP_PACK_SUBSCRIPTIONS]
    for i in subs:
        snap_list_dict[i['snap_pack_label']]=i
    return snap_list_dict

def add_subscription(org_name, sysadmin_snapi_snap_pack, snaps_dict, required_snap_list):
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    subs=[]
    for key in required_snap_list:
        syslog.syslog('>>>Adding subscription:'+key)
        message_buffer.append('>>>Adding subscription:'+key)
        snaps_dict[key]['is_sub']=True
        subs.append(snaps_dict[key])
    org_snid=asset_api.lookup_org(org_name)['snode_id']
    sysadmin_snapi_snap_pack.modify_subscriptions(org_snid, {keys.SNAP_PACK_SUBSCRIPTIONS: subs})
    
def get_pod_prefix(pod_name, elastic,clouddev, keys_file):
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    error_messages=[]
    if pod_name in ['prodxl','prodxl2']:
       uri='https://'+elastic
    elif pod_name in ['canaryxl', 'canaryxl2']:
       uri='https://canary.'+elastic
    elif pod_name == 'uatxl':
       uri='https://uat.'+elastic
    elif pod_name == 'ux':
       uri='https://ux.'+clouddev
    elif pod_name == 'ux2':
       uri='https://ux2.'+clouddev
    elif pod_name == 'ux3':
       uri='https://ux3.'+clouddev
    elif pod_name == 'portal':
       uri='https://portal.'+elastic
    elif pod_name == 'qa':
       uri='https://qa.'+clouddev
    elif pod_name == 'budgy':
       uri='https://budgy.'+elastic
    elif pod_name == 'spark':
       uri='https://spark.'+elastic
    elif pod_name == 'salespod':
       uri='https://SnapLogicSales.'+elastic
    elif pod_name == 'snap':
       uri='https://snapxl.'+elastic
    elif pod_name == 'perf':
       uri='https://perfxl.'+elastic
    elif pod_name == 'prov-sldb':
       uri='https://prov-sldb.'+clouddev
    elif pod_name == 'dev-sldb':
       uri='https://dev-sldb.'+clouddev
    elif pod_name == 'stage':
       uri='https://stage.'+elastic
    else:
       uri='https://'+pod_name+'.'+elastic
    with open(keys_file) as fp:
       for i in fp:
          if i.find(uri) > 0:
             j=i.split('=')
             if len(j) > 0:
                k=j[0].split('.')
             if len(k) > 0:
                return k[0].strip(), error_messages
    message_buffer.append("""No keys exist in the keys.properties file for pod name:%s"""%(pod_name))
    syslog.syslog("""No keys exist in the keys.properties file for pod name: %s"""%(pod_name))
    error_messages.append("""No keys exist in the keys.properties file for pod name:%s"""%(pod_name))

    return None, error_messages 

#def create_property_keys(org_name,prefix):
#    #--------------------------------------------------------------------------------------
#    #-
#    #--------------------------------------------------------------------------------------
#    if prefix.find('prod')==0:
#       prefix='prod-operator'
#    elif prefix.find('canary')==0:
#       prefix='canary-operator'
#    elif prefix.find('uat')==0:
#       prefix='uat-operator'
#    elif prefix.find('snap')==0:
#       prefix='snap-operator'
#    elif prefix.find('qa')==0:
#       prefix='qa-operator'
#    else:
#       return 'Error: Could not generate Keys because of unknown prefix'
#    cmd="""%s/Tectonic/cloudops/tools/getkey.py --prefix=%s --subscriber_id=%s --target_prefix=cc"""%(app.SNAPLOGIC_HOME,prefix,org_name)
#    try:
#      results=os.popen(cmd).read()
#      return results
#    except:
#      syslog.syslog('Failed command:'+cmd)
#      return None

def get_asset_api_ptr(pod_prefix, config_file=None):
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_prefix, config_file)
    session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
    asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)
    sysadmin_context = snapi.snapi_context.SnapiContext(admin_name,
                                                        api_key,
                                                        admin_uri,
                                                        sldb_uri=admin_uri)
    sysadmin_snapi_snap_pack = sysadmin_context.schema_manager
    return asset_api,sysadmin_snapi_snap_pack

def check_and_update_premium_snap_record(pod, snap_list):
    #---------------------------------------------------------------------------------------------------
    #-   Update the Premium snap list for a given POD
    #---------------------------------------------------------------------------------------------------
    record_count=app.session_id.query(app.SnaplogicPremiumSnapRec).filter_by(pod_name=pod).count()
    if record_count == 0:
       message_buffer.append('>>>>Inserting new premium record for POD:'+pod_name)
       syslog.syslog('>>>>Inserting new premium record for POD:'+pod_name)
       R1=app.SnaplogicPremiumSnapRec(create_date_time=datetime.datetime.now(),pod_name=pod,premium_snap_list=snap_list)
       app.session_id.add(R1)
       app.session_id.commit()
    else:
       rec=app.session_id.query(app.SnaplogicPremiumSnapRec).filter_by(pod_name=pod)
       if rec[0].premium_snap_list != snap_list:
          syslog.syslog('>>>Premium Snap list changed for update it')
          message_buffer.append('>>>Premium Snap list changed for update it')
          rec[0].premium_snap_list = snap_list 
          rec[0].create_date_time=datetime.datetime.now()
          app.session_id.commit()

def check_if_org_was_already_created(org, pod, status_code):
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    db_record=app.session_id.query(app.SnaplogicOrgRec).filter_by(org_name=org, pod_name=pod, org_create_status=status_code)
    for i in db_record:
        return True
    return False 

def add_users_to_org(asset_api, org_name, email_list):
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    user_type=''
    config_file=None
    admin_user_list=[]
    error_messages=[]

    for i in email_list:     #for each username
        user_type=None
        try:
           asset_api.add_user_to_phorg(None, i, org_name)
           if email_list[i]=='admin':
              admin_user_list.append(i)
        except:
           message_buffer.append('Warning: '+i+':'+str(sys.exc_info()[1]).split(':')[-2])
           syslog.syslog('Warning: '+i+':'+str(sys.exc_info()[1]).split(':')[-2])
           error_messages.append('Warning: '+i+':'+str(sys.exc_info()[1]).split(':')[-2])
    #add the list of Admin users to the admins group of the Org
    asset_api.update_group(None,'/'+org_name, 'admins',admin_user_list)
    return error_messages

def build_command(program,pod, org, prefix, first,last,email,cloud_plex,ground_plex,hadoop_plex,container_path,jcc_name,description):
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    command="""%s -p %s -s %s --pod-prefix %s --first "%s" --last "%s" --email "%s" --plex "%s" --gplex "%s" --hplex "%s" --container-path "%s" -n %s -d "%s"
           """%(program,pod,org,prefix,first,last,email,cloud_plex,ground_plex,hadoop_plex,container_path,jcc_name,description)
    message_buffer.append('>>>CMD:'+command)
    syslog.syslog(command)
    #sys.exit()
    return command

#def build_command(program,pod, org, prefix, first,last,email,cloud_plex,ground_plex,hadoop_plex,container_path,jcc_name,description):
#    #---------------------------------------------------------------------------------------------------
#    #-
#    #---------------------------------------------------------------------------------------------------
#    command="""%s -p %s -s %s --pod-prefix %s --first "%s" --last "%s" --email "%s" --plex "%s" --gplex "%s" --container-path "%s" -n %s -d "%s"
#           """%(program,pod,org,prefix,first,last,email,cloud_plex,ground_plex,container_path,jcc_name,description)
#    message_buffer.append('>>>CMD:'+command)
#    syslog.syslog(command)
#    #sys.exit()
#    return command


def get_file_data(input_file):
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    the_org=''
    data_array={}
    for i in open(input_file):
        i=i.strip()
        if len(i) > 0 and i[0] != '#':
           fields= i.split('=')
           if len(fields) > 0:
              if fields[0]=='org_name':
                 the_org=eval(fields[1].strip())
                 data_array[the_org]={}
                 data_array[the_org]['user']=[]
              elif fields[0]=='user':
                 if data_array.has_key(the_org):
                    data_array[the_org]['user'].append(eval(fields[1].strip()))
              elif fields[0]=='environment':
                 if data_array.has_key(the_org):
                    data_array[the_org]['environment']=eval(fields[1].strip())
    return data_array 
    
def get_file_names():
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    keys_file_name=os.environ['HOME']+'/snaplogic/Tectonic/etc/keys.properties'
    if not(os.path.exists(keys_file_name) and os.path.isfile(keys_file_name)):
       message_buffer.append('Error: Missing keys.properties file:'+input_file)
       syslog.syslog('Error: Missing keys.properties file:%s'%(input_file))
       sys.exit()
    
    return keys_file_name

if __name__ == '__main__':
  config_file=None
  FAILED='failed'
  SUCCESS='success'
  PROCESSING='processing'
  if debug is True:
     print 'Running script'
  message_buffer.append('Running script')
  GO='go'
  NONE=None
  if len(sys.argv) > 1:
     parser=argparse.ArgumentParser(description='This program is used to create in Org in a specified environment (prod| canary|qapod|uatxl)')
     parser.add_argument('-o',required=True, help='TheOrg name used to create the Org is the value here')
     parser.add_argument('-p',required=True,choices=PODS,help='The pod name is expected to follow')
     parser.add_argument('-e',required=True,help='This is the creator email address')
     parser.add_argument('-f',required=True,help='This is the firstname of the creator')
     parser.add_argument('-s',required=True,help='This is the surname of the creator')
     parser.add_argument('-n',required=True,help='This is the cloud_plex_name')
     parser.add_argument('-g',required=True,help='This is the ground_plex_name')
     parser.add_argument('-a',required=True,help='This is the hadoop_plex_name')
     args=parser.parse_args()
  else:
     org_activate_signal=app.session_id.query(app.SnaplogicControlsRec)
     for i in org_activate_signal:
         org_activate_signal=i.activate_org_creation
     if org_activate_signal is True:
        if debug is True:
           print '>>Master: org_activate_signal is True and checking if org_create_status is None and create_org_flag is True on the record...'
        message_buffer.append('>>Master: org_activate_signal is True and checking if org_create_status is None and create_org_flag is True on the record...')
        db_list=app.session_id.query(app.SnaplogicOrgRec).filter_by(org_create_status=None,create_org_flag=True)
     else:
        if debug is True:
           print '>>>Bypassing this record because org_create_status is not \"None\" and create_org_flag is not True'
        syslog.syslog('>>>Bypassing this record because org_create_status is not \"None\" and create_org_flag is not True')
        message_buffer.append('>>>Bypassing this record because org_create_status is not \"None\" and create_org_flag is not True')
        message_buffer.append('>>>Nothing to do...')
        if debug is True:
           print '>>>Nothing to do...'
        sys.exit()
     for a_db_record in db_list:
         if debug is True:
            print a_db_record.record_id
         if a_db_record.create_org_flag is False:
            if debug is True:
               print '>>>Bypassing this Org because \"create_org_flag\" is False'
            message_buffer.append('>>>Bypassing this Org because \"create_org_flag\" is False')
            next
         if debug is True:
            print '>>>Creating Org:',a_db_record.org_name
         message_buffer.append('>>>Creating Org:'+a_db_record.org_name)
         org_users_to_add={}
         elastic='elastic.snaplogic.com'
         clouddev='clouddev.snaplogic.com'
         keys_file=get_file_names() 
       
         pod_prefix=''
         pod_name=a_db_record.pod_name
         org_name=a_db_record.org_name
         premium_snaps_required=eval(a_db_record.premium_snap_list)
         org_features=eval(a_db_record.features_list_dict)   #convert the features dict stored as text
         if 'Email' not in premium_snaps_required:         #every Org gets the Email 
            premium_snaps_required.append('Email')

         cloud_plex_name=a_db_record.cloud_plex_name
         ground_plex_name=a_db_record.ground_plex_name
         hadoop_plex_name=a_db_record.hadoop_plex_name
         create_hadooplex=a_db_record.create_hadooplex

         #cloud_plex_name='Sidekick '+'-'+org_name
         user_email=a_db_record.user_email
         requestor_email=a_db_record.requestor_email
         requestor_type=a_db_record.requestor_type
       
         first_name=a_db_record.user_firstname
         last_name=a_db_record.user_lastname
       
         container_path=org_name+'/shared'
         jcc_name=org_name+'jcc'
         description='This is a JCC for '+org_name
         program_path=os.environ['HOME']+'/snaplogic/Tectonic/cloudops/tools/init_org.py'
       
         pod_prefix, error_messages = get_pod_prefix(pod_name,elastic,clouddev,keys_file)
         if pod_prefix is not None:
            if does_org_exist(pod_prefix,org_name) != True:
               asset_api,sysadmin_snapi_snap_pack=get_asset_api_ptr(pod_prefix, config_file)
               no_hadooplex="None"        #set this not the create the Hadoopkex at Org create time
               cmd=build_command(program_path,pod_name, org_name, pod_prefix, first_name,last_name,user_email,cloud_plex_name,ground_plex_name, no_hadooplex,container_path,jcc_name,description)
               #check if Org was successfully created
               #if check_if_org_was_already_created(org_name,pod_name,SUCCESS) is True:
               #   a_message="""Org:%s in Pod:%s Is Already Successfully Created..."""%(org_name,pod_name)
               #   syslog.syslog(a_message)
               #   print a_message
               #   continue            #do the next record
   
               if debug is True:
                  print '>>',cmd
               syslog.syslog(str(cmd))
               message_buffer.append(str(cmd))
 
               try:
                  results=os.popen(cmd).read()
                  message_buffer.append('Org successfully created!')
                  if debug is True:
                     print '>>>>', results
                  message_buffer.append(results)
                  a_db_record.org_create_status=SUCCESS  #the org is already created
                  a_db_record.cloud_plex_name=cloud_plex_name
                  a_db_record.sidekick_keys=generate_property_keys(org_name,pod_name)
                  app.session_id.commit()
   
                  #store db message in db
                  a_db_record.org_create_error_log=results
                  a_db_record.update_date_time=datetime.datetime.now()
                  app.session_id.commit() 

                  premium_snaps_dict=get_premium_snaps(asset_api,sysadmin_snapi_snap_pack, org_name)
                  premium_snaps_dict_sorted=premium_snaps_dict.keys()
                  premium_snaps_dict_sorted.sort()
                  check_and_update_premium_snap_record(pod_name, str(premium_snaps_dict_sorted))

                  if debug is True:
                     print '\n\n===>PREMIUM-SNAPS-DICT:', premium_snaps_dict
                     print '<<==================>>REQUIRED-SNAPS:', premium_snaps_required

                  add_subscription(org_name, sysadmin_snapi_snap_pack, premium_snaps_dict, premium_snaps_required)    #add subscriptions to the Org
                  update_org_features(org_name,pod_prefix,config_file,org_features)     #added 6/28/2017
                  if create_hadooplex is True:       #create Snaplex of type Hadooplex
                     print '>>>>>>>>Calling to create hadooplex....'
                     create_hadooplex_snaplex(pod_prefix,container_path, org_name, hadoop_plex_name)
                  else:
                     print '>>>>>>>No Hadooplex required...'

                  syslog.syslog(results)
               except:
                  app.session_id.rollback()
                  if debug is True:
                     print sys.exc_info()[1]
                  message_buffer.append(str(sys.exc_info()[1]))
                  syslog.syslog(str(sys.exc_info()[1]))
                  a_db_record.org_create_status=FAILED
                  a_db_record.org_create_error_log=str(sys.exc_info()[1])
                  a_db_record.update_date_time=datetime.datetime.now()
                  app.session_id.commit()
          
               #add_users_to_org(pod_prefix, org_name, data_dict[org_name]['user'])
               for usr in app.devops_admin_users:
                   org_users_to_add[usr]=app.devops_admin_users[usr]
               org_users_to_add[requestor_email]=requestor_type            
               error_messages=add_users_to_org(asset_api, org_name, org_users_to_add)
            else:
               if debug is True:
                  print 'Org:',org_name,'already exists in',pod_name,'so skipping...' 
               syslog.syslog('Org: '+org_name+' already exists in '+pod_name+' so skipping...')
               message_buffer.append('Org: '+org_name+' already exists in '+pod_name+' so skipping...')
   
  print message_buffer


