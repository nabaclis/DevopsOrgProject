#used by many scripts to get the admin user for a pod

import sys, os, datetime
import slutils.sladmin

import app

#PODS=('prodxl','prodxl2','uatxl','canaryxl','canaryxl2','snap','ux3', 'ux2','ux','portal','budgy','spark','stage','prov-sldb','dev-sldb','perf','salespod')

def get_file_names():
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    keys_file_name=os.environ['HOME']+'/snaplogic/Tectonic/etc/keys.properties'
    if not(os.path.exists(keys_file_name) and os.path.isfile(keys_file_name)):
       message_buffer.append('Error: Missing keys.properties file:'+input_file)
       syslog.syslog('Error: Missing keys.properties file:%s'%(input_file))
       return 'Error: Could not get the keys_file_name...'
    return keys_file_name

def get_pod_admin_user(a_pod):
   #-----------------------------------------------------------------------------------------------------
   #-
   #-----------------------------------------------------------------------------------------------------
   uri=''
   admin_user=None
   if a_pod in ['uat','uatxl']:
      admin_user='uatxl-operator'
   elif a_pod in ['prod','prodxl', 'prodxl2']:
       admin_user='prod-operator'
   elif a_pod=='portal':
       admin_user='portal-operator'
   elif a_pod=='ux':
       admin_user='ux-operator'
   elif a_pod=='ux2':
       admin_user='ux2-operator'
   elif a_pod=='ux3':
       admin_user='ux3-operator'
   elif a_pod=='prov-sldb':
       admin_user='prod.sladmin'
   elif a_pod=='dev-sldb':
       admin_user='dev.sladmin'
   elif a_pod in ['canary','canaryxl','canaryxl2']:
       admin_user='canary-operator'
   elif a_pod=='stage':
       admin_user='stage-operator'
   elif a_pod=='qa':
       admin_user='qa-operator'
   elif a_pod in ['snap','snapxl']:
       admin_user='snapxl-operator'
   elif a_pod=='perf':
       admin_user='perf-operator'
   elif a_pod=='budgy':
       admin_user='budgy-operator'
   elif a_pod=='spark':
       admin_user='sparkpod-operator'
   elif a_pod=='auditpod':
       admin_user='auditpod-operator'
   elif a_pod=='salespod':
       admin_user='salespod-operator'
   admin_name, api_key, uri = slutils.sladmin.init_sladmin(admin_user, None)
   return admin_user, uri

def check_and_update_premium_snap_record(pod, snap_list):
    #---------------------------------------------------------------------------------------------------
    #-   Update the Premium snap list for a given POD
    #---------------------------------------------------------------------------------------------------
    record_count=app.session_id.query(app.SnaplogicPremiumSnapRec).filter_by(pod_name=pod).count()
    if record_count == 0:
       print '>>>>Inserting new premium record for POD:',pod
       R1=app.SnaplogicPremiumSnapRec(create_date_time=datetime.datetime.now(),pod_name=pod,premium_snap_list=snap_list)
       app.session_id.add(R1)
       app.session_id.commit()
    else:
       rec=app.session_id.query(app.SnaplogicPremiumSnapRec).filter_by(pod_name=pod)
       if rec[0].premium_snap_list != snap_list:
          print '>>>Premium Snap list changed for update it'
          rec[0].premium_snap_list = snap_list
          rec[0].create_date_time=datetime.datetime.now()
          app.session_id.commit()

