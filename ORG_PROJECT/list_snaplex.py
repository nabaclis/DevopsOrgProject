#!/usr/local/bin/python

import simplejson
import os, sys, syslog, datetime
import slutils.sladmin
import snapi.snapi_request
import snapi.snapi_asset
import snapi.snapi_meter
import snapi.snapi_plex
import argparse

import app.common_org_utility_functions

program_path=os.environ['HOME']+'/snaplogic/Tectonic/cloudops/tools/init_org.py'

def get_api_ptrs(pod_prefix):
    #--------------------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------------------
    admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_prefix, None)
    print 'admin_name:',admin_name
    print 'api_key:', api_key
    print 'admin_uri:',admin_uri
    session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
    
    asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)
    plex_api = snapi.snapi_plex.SnapiPlex(session, admin_uri)
    meter_api = snapi.snapi_meter.SnapiMeter(session, admin_uri)   
    return asset_api,plex_api,meter_api

#for i in plex_api.list_all_plexes():
#    print i

#for i in plex_api.list_plex_org('BUCloudplex'):
#    print i

#print asset_api.get_subscription('BSU-Trial', None)

if __name__ == '__main__':
   parser=argparse.ArgumentParser(description='This program is used to list all the Snaplexes in a POD or to list a specific one')
  
   parser.add_argument('-p',required=True,choices=['salespod','spark','auditpod','budgy','qa','snapxl','perf','prod','canary','qapod','uat','portal','ux','ux2','ux3','prov-sldb','dev-sldb','stage'],help='The POD where the Org belongs')
   args=parser.parse_args()

   pod_prefix, the_uri=app.common_org_utility_functions.get_pod_admin_user(args.p)
   print '>>>Prefix:', pod_prefix
   asset,plex,meter=get_api_ptrs(pod_prefix)

   for i in plex.list_all_plexes():
       print i 

   for i in plex.list_plex_org('BUUAT'):
       for j in i:
           print j,'==>',i[j]


