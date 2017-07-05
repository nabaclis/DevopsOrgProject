#!/usr/local/bin/python

import simplejson
import os, sys, syslog, datetime
import slutils.sladmin
import snapi.snapi_request
import snapi.snapi_asset
import argparse

def find_user(pod_admin_user, a_username):
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    config_file = None
    admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_admin_user, config_file)
    session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
    asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)

    try:
      print asset_api.get_user(None, a_username)['username']
    except:
      print 'Username:',a_username,'is not in pod'

def display_assets(pod_admin_user,org):
    config_file = None
    admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_admin_user, config_file)
    session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
    asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)

    print asset_api.list_assets(org, None)



pod_admin_user='prod-operator'
a_username='cseymour@snaplogic.com'
org='AMAG-iPaaSModernization-MandA-Trial'

display_assets(pod_admin_user,org)

#find_user(pod_admin_user, a_username)
#list_assets(self, path, caller, asset_type=None)
