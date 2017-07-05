#!/usr/local/bin/python
#see insert_snap-pack( from 
#    src/main/python/sldb/services/admin/snap_pack_handler.py
#
#    uses _snap_pack_manager.insert_snap_pack
#
#src/main/python/sldb/sldb_manager_factory.py is used to create the _snap_pack_manager

#----------------------------------------------------------
#  see file  ./psnapi/src/main/python/snapi/snapi_asset.py
#----------------------------------------------------------

import simplejson
import os, sys, syslog, datetime
import slutils.sladmin
import snapi.snapi_request
import snapi.snapi_asset
import argparse

user_type=''
config_file=None
admin_user_list=[]
error_messages=[]

features_dict={'Enhanced Account Encryption': {'account_encryption': {'on': 'True', 'off': 'False'}}, 'Elastic Runtime': {'elastic_runtime': {'on': 'elastic-runtime', 'off': 'None'}}, 'Ultra Tasks': {'always_on_tasks': {'on': 'True', 'off': 'False'}}, 'Spark': {'spark': {'on': 'spark', 'off': 'None'}}, 'Lifecycle Management': {'dev_test_prod': {'on': 'True', 'off': 'False'}}}

features_dict={'Ultra Tasks':'always_on_tasks','Enhanced Account Encryption':'account_encryption','Lifecycle Management':'dev_test_prod','Elastic Runtime':'elastic_runtime','Spark':'spark'}

admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin('prod-operator', config_file)

print '>>>Params:',admin_name, api_key, admin_uri

session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)

subs=asset_api.get_all_subscriptions('ClaudeOrg5')  #new function added, Claude-Corp1-Test
#if Ultra Tasks selected, then always_on_tasks ==> True
#if Enhanced Account Encryption, then account_encryption ==> True 
#if Lifecycle Management, then dev_test_prod ==> True
#if Elastic Runtime, then elastic_runtime ==> elastic-runtime
#if Spark, then spark ==> spark

for i in subs:
    print i,'==>',subs[i]

#None true/false variables take None for false and the key name for true
#x=asset_api.update_subscription('ClaudeOrg11', data={'elastic_runtime':None})


#data=['Analytics']
#y=asset_api.update_subscription('claudeApplesTest7',data)
