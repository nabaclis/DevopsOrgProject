#!/usr/local/bin/python

import os, sys, uuid
import time, datetime, syslog

org_db_name='org_provisioning_db'
org_table_name='org_requisition_data'
mysql_account='root'

data_file_name='/Users/cseymour/Desktop/KEN_merge_20160726.csv'

import app
from sqlalchemy import exc

def sanitize_required_fields(field_dict):
    #--------------------------------------------------------------------------------------
    #-Get ret of blanks and line feed in the field
    #--------------------------------------------------------------------------------------
    error_message=[]
    null_fields=True
    for i in field_dict:
        if field_dict[i] is None:
           error_message.append('Error: '+i+' cannot be empty')
        else:
           field_dict[i]=field_dict[i].strip().replace(' ','')
           if len(field_dict[i]) == 0:
              error_message.append('Error: '+i+' cannot be empty')
    for key in field_dict:
        if type(field_dict[key]) is not None and (type(field_dict[key]) is str or type(field_dict[key]) is unicode) and len(field_dict[key]) > 0:
           null_fields=False
           break
    return field_dict, error_message,null_fields

def insert_org_record(org_name,pod_name,create_sidekick,create_cloud,create_hadooplex,number_of_cloud,org_create_status):
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    error_message=[]
    date_time=datetime.datetime.now()
    create_org_menu=[False,True]
    create_jcc_menu=[False,True]
    pod_name_menu=['prodxl','prodxl2','canaryxl','canaryxl2','uatxl','qa']
    requestor_type='admin'

    user_email_val='cseymour@snaplogic.com'
    user_email_val=user_email_val.lower()

    requestor_email_val='cseymour@snaplogic.com'
    requestor_email_val=requestor_email_val.lower()
         
    user_firstname='claude'; user_lastname='cseymour'

    key_fields_dict={'user_email':user_email_val, 'requestor_email':requestor_email_val, 'org_name':org_name, 'user_firstname':user_firstname,'user_lastname':user_lastname}
    key_fields_dict['pod_name']=pod_name

    key_fields_dict,error_message,all_null_fields=sanitize_required_fields(key_fields_dict)
    if len(error_message) > 0: 
       for k in error_message:
           print  (k)
 
    try:
       rec_id=uuid.uuid4()
       create_jcc_flag_val=True
       create_org_flag_val=False


       groundplex_name=None
       groundplex_environment=None
       cloudplex_name=None
       cloudplex_environment=None
       hadooplex_name=None
       hadooplex_environment=None

       if create_sidekick is True:
          groundplex_name='Sidekick - '+org_name
          groundplex_environment='Sidekick-dev'
       if create_cloud is True:
          cloudplex_name='Cloud - '+org_name
          cloudplex_environment='dev'
       if create_hadooplex is True:
          hadooplex_name='Hadooplex - '+org_name
          hadooplex_environment='hadooplex-dev'
       R1=app.SnaplogicOrgRec(create_date_time=date_time, 
                              org_name=org_name, 
                              pod_name=pod_name, 
                              user_email=user_email_val, 
                              requestor_email=requestor_email_val, 
                              requestor_type=requestor_type, 
                              record_id=rec_id,
                              groundplex_environment=groundplex_environment,
                              cloudplex_environment=cloudplex_environment,
                              hadooplex_environment=hadooplex_environment,
                              user_firstname=user_firstname,
                              user_lastname=user_lastname,
                              cloud_plex_name=cloudplex_name,
                              ground_plex_name=groundplex_name,
                              hadoop_plex_name=hadooplex_name,
                              create_sidekick=create_sidekick,
                              create_cloud=create_cloud,
                              create_hadooplex=create_hadooplex,
                              create_jcc_flag=create_jcc_flag_val,
                              create_org_flag=create_org_flag_val,
                              org_create_status=org_create_status,
                              sidekick_keys='',
                              number_of_cloud=number_of_cloud)
       app.session_id.add(R1)
       app.session_id.commit()
       print('Success: Org Record successfully inserted')
    except exc.SQLAlchemyError:
       print sys.exc_info()[0]
       syslog.syslog(str(sys.exc_info()[1]))
       app.session_id.rollback()

def insert_db_record(jcc_name, an_org_name, a_pod_name, mrc_id,jcc_ver,an_elastic_ip):
    #---------------------------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------------------------
    a_record_id=uuid.uuid4()
    try:
       R1=app.MigrationJCCRec(create_date_time=datetime.datetime.now(),
                              record_id=a_record_id,
                              org_name=an_org_name,
                              pod_name=a_pod_name,
                              old_mrc=mrc_id,
                              old_jcc_ver=jcc_ver,
                              elastic_ip=an_elastic_ip,
                              old_jcc_name=jcc_name)
       app.session_id.add(R1)
       app.session_id.commit()
       print 'Success: JCC Migration Record successfully inserted for '+jcc_name
       return a_record_id
    except:
       print '>>>Sys-Message:',sys.exc_info()[1]
       app.session_id.rollback()
       print 'Could not add jcc record...'
       print '================================================='
       print '===== Inputs that caused the Insert to fail     ='
       print '\trecord_id=',a_record_id
       print '\torg_name=',an_org_name
       print '\tpod_name=',a_pod_name
       print '\told_mrc=',mrc_id
       print '\tJcc_ver=',jcc_ver
       print '\told_jcc_name=',old_jcc_name
       print '\telastic_ip=',an_elastic_ip

       return None

if __name__ == '__main__':
   org_dict={}

   if os.path.exists(data_file_name) and os.path.isfile(data_file_name):
      for i in open (data_file_name):
          j=i.split(',')
          if len(j) == 31 and j[-4].find('1.7')==0:   #only process records with Java 1.7 and reord has 31 fields
             try:
                if not org_dict.has_key(j[-7]):
                   org_dict[j[-7]]={}
                if not org_dict[j[-7]].has_key(j[-21]):
                   org_dict[j[-7]][j[-21]]=[]
                org_dict[j[-7]][j[-21]].append(j[-8]+','+j[9]+':'+j[22]+','+j[-4])
                #print 'RECORD>>'+j[-7]+'|'+ j[-21]+'|'+j[9],'|'+j[-4]
             except:
                print '>>>>',sys.exc_info()[1]
                #pass
   
   for org_name in org_dict:
       for pod in org_dict[org_name]:
           #(Add master ORG Rec)
           number_of_jcc=len(org_dict[org_name][pod])
           #print org_name+'|'+pod+'|',number_of_jcc
           hadooplex_required=False
           cloud_required=True
           groundplex_required=False
           create_status='success'
           insert_org_record(org_name,pod,groundplex_required,cloud_required,hadooplex_required,number_of_jcc,create_status)
           for k in org_dict[org_name][pod]:
               mrc_id,jcc_name,jcc_version=k.split(',')
               old_jcc_name,elastic_ip=jcc_name.split(':')
               insert_db_record(old_jcc_name, org_name, pod, mrc_id,jcc_version,elastic_ip)
               #(insert JCC instance record)
               #print '\t',k
            
