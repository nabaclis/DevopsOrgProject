#!/usr/local/bin/python

import simplejson
import os, sys, syslog, datetime
import slutils.sladmin
import snapi.snapi_request
import snapi.snapi_asset
import snapi.snapi_meter
import snapi.snapi_plex
import snapi.snapi_request
import snapi.snapi_admin
import snapi.snapi_audit
import snapi.snapi_catalog
import snapi.snapi_context
import argparse

import snapi_base.exceptions
import snapi_base.keys as keys

org_db_name='org_provisioning_db'
org_table_name='org_requisition_data'
mysql_account='root'
import app.common_org_utility_functions
import app

elastic='elastic.snaplogic.com'
clouddev='clouddev.snaplogic.com'
PODS=('prodxl','prodxl2','uatxl','canaryxl','canaryxl2','snap','ux3', 'ux2','ux','portal','budgy','spark','stage','prov-sldb','dev-sldb','perf','salespod')
keys_file='/Users/cseymour/snaplogic/Tectonic/etc/keys.properties'

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


def get_premium_snaps(asset_api,sysadmin_snapi_snap_pack, org_name):
    #---------------------------------------------------------------------------------------------------
    #- I picked a random org in the Pod and listed all available subscriptions
    #---------------------------------------------------------------------------------------------------
    config_file=None
    snap_list_dict={}
    org_snid=asset_api.lookup_org(org_name)['snode_id']
    subs = sysadmin_snapi_snap_pack.check_subscriptions(org_snid)[keys.SNAP_PACK_SUBSCRIPTIONS]
    for i in subs:
        snap_list_dict[i['snap_pack_label']]=i
    return snap_list_dict


if __name__=='__main__':
   config_file=None

   for pod_name in PODS:
       print 'POD-NAME:',pod_name
       pod_prefix, the_uri=app.common_org_utility_functions.get_pod_admin_user(pod_name)
       try:
          admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_prefix, None)
      
          session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
   
          asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)
          plex_api = snapi.snapi_plex.SnapiPlex(session, admin_uri)
          meter_api = snapi.snapi_meter.SnapiMeter(session, admin_uri)   
   
          try:
             for i in plex_api.list_all_plexes():
                 org_name=i['runtime_path_id'].split('/')[0].strip()
                 #print '>>>>>Org:',org_name
                 premium_asset_api,sysadmin_snapi_snap_pack=get_asset_api_ptr(pod_prefix, config_file)
                 premium_list=get_premium_snaps(premium_asset_api,sysadmin_snapi_snap_pack, org_name)
                 premium_snaps_keys_sorted=premium_list.keys()
                 premium_snaps_keys_sorted.sort()
                 print 'ORG:'+org_name+'\n\t',premium_snaps_keys_sorted
                 app.common_org_utility_functions.check_and_update_premium_snap_record(pod_name, str(premium_snaps_keys_sorted))
                 break
          except:
             print sys.exc_info()
             print '>>>Could not get Premium snap list for POD:'+pod_name 
       except:
           print sys.exc_info()
           pass

