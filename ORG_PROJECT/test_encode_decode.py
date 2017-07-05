#!/usr/local/bin/python

import os, sys, boto3, syslog, uuid
import time, argparse, datetime, socket

default_size='mxlarge'
default_mrc='mrc226'
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

data=open('/Users/cseymour/JCC-LOG.txt','rb').read()
data=data.encode('utf-8')

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
           if column_name=='jcc_deploy_message_log':
              jcc_record_obj.jcc_deploy_message_log=value
           elif column_name=='jcc_create_message_log':
              jcc_record_obj.jcc_create_message_log=value
           app.session_id.commit()
           print '>>>Updated Instance:',db_column_value
        except:
           print sys.exc_info()[1]
           syslog.syslog(str(sys.exc_info()[1]))
           app.session_id.rollback()

update_jcc_record('jcc_deploy_message_log', data,'i-1456cd84','instance_id')
update_jcc_record('jcc_deploy_message_log', data,'i-cb08474d','instance_id')
update_jcc_record('jcc_deploy_message_log', data,'i-6bc132f4','instance_id')
update_jcc_record('jcc_deploy_message_log', data,'i-8dc73412','instance_id')

