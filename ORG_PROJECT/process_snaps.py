#!/usr/local/bin/python

import simplejson
import os, sys, syslog, datetime
import slutils.sladmin
import snapi.snapi_request
import snapi.snapi_asset
import snapi.snapi_schema_manager
from snapi_base import keys
import argparse

pod_admin_user='prod-operator'
config_file = None
admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_admin_user, config_file)
session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
schema_manager = snapi.snapi_schema_manager.SnapiSchemaManager(admin_uri)

