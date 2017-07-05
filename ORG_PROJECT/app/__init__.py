from flask import Flask

import os
appFlask=Flask(__name__)
appFlask.config.from_object('config')

from app import views
#from app import build_org
from app import db_params

org_db_name='org_provisioning_db'
archive_db_name='archive_db_name'

org_table_name='org_requisition_data'
archive_org_table_name='archive_org_requisition_data'

features_dict={'Enhanced Account Encryption': {'account_encryption': {'on': True, 'off': False}}, 'Elastic Runtime': {'elastic_runtime': {'on': 'elastic-runtime', 'off': None}}, 'Ultra Tasks': {'always_on_tasks': {'on': True, 'off': False}}, 'Spark': {'spark': {'on': 'spark', 'off': None}}, 'Lifecycle Management': {'dev_test_prod': {'on': True, 'off': False}}}
reverse_features_dict={}
for i in features_dict:
    reverse_features_dict[features_dict[i].keys()[0]]=i


jcc_table_name='jcc_creation_data'
migration_jcc_table_name='jcc_migration_table_data'
controls_table_name='system_activation_table'
premium_snap_table_name='premium_snap_table'
sales_org_table_name='sales_org_table'
jcc_lock_table_name='jcc_lock_record'
login_users_table_name='authorized_users_table'
mysql_account='root'

this_user=os.environ['USER']
if os.uname()[0] == 'Darwin':
   APP_HOME='/Users/cseymour/claude_scripts/ORG_PROJECT'
   SNAPLOGIC_HOME='/Users/cseymour/snaplogic'
   USER_HOME='/Users/cseymour'
else:
   APP_HOME="/home/%s/ORG_PROJECT"%(this_user)
   SNAPLOGIC_HOME="/home/%s/snaplogic"%(this_user)
   USER_HOME="/home/%s"%(this_user)

from sqlalchemy import create_engine
from sqlalchemy.orm import session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, BLOB, Boolean, Enum

devops_admin_users={}
devops_admin_users['cseymour@snaplogic.com']='admin'
#devops_admin_users['rkawai@snaplogic.com']='admin'
#devops_admin_users['rsherla@snaplogic.com']='admin'
#devops_admin_users['jreyes@snaplogic.com']='admin'

def create_login_users_table(engine_id, db_name, login_users_table):
    #-------------------------------------------------------------------------------------------------------
    #-
    #-------------------------------------------------------------------------------------------------------
    mysql_db_list=[]
    mysql_table_list=[]
    Base=declarative_base(engine_id)    #to create a new table, this must be done first
    class AuthorizedUsers(Base):
        __tablename__= login_users_table
        user_login_name=Column(String(200), primary_key=True,nullable=False)
        user_firstname=Column(String(200), nullable=False)
        user_lastname=Column(String(200), nullable=False)
        user_password=Column(String(512), nullable=False)
        create_date_time=Column(DateTime)
        update_date_time=Column(DateTime)
    command="""use %s"""%(db_name)
    for i in engine_id.execute('show databases').fetchall():
        mysql_db_list.append(i[0])
    if db_name not in mysql_db_list:        #create db if it does not exist
       engine_id.execute('create database '+db_name)
    engine_id.execute(command)
    for i in engine_id.execute('show tables').fetchall():
        mysql_table_list.append(i[0])
    if login_users_table not in mysql_table_list:    #only create the table if it is not there
       Base.metadata.create_all(engine_id)   #allows Create Table before any table is created
    return AuthorizedUsers 


def create_org_table(engine_id, db_name, org_table):
    #-------------------------------------------------------------------------------------------------------
    #-
    #-------------------------------------------------------------------------------------------------------
    mysql_db_list=[]
    mysql_table_list=[]
    Base=declarative_base(engine_id)    #to create a new table, this must be done first
    class SnaplogicOrg(Base):
        __tablename__= org_table
        record_id=Column(String(200))
        sales_record_id=Column(String(200))
        create_date_time=Column(DateTime)
        update_date_time=Column(DateTime)
        user_email=Column(String(200),nullable=False)
        requestor_email=Column(String(200),nullable=False)
        user_firstname=Column(String(200), nullable=False)
        user_lastname=Column(String(200), nullable=False)
        org_name=Column(String(120),primary_key=True,nullable=False)
        pod_name=Column(Enum('prodxl','prodxl2','uatxl','canaryxl','canaryxl2','snap','ux3', 'ux2','ux','portal','budgy','spark','salespod','perf','prov-sldb','dev-sldb','stage'), primary_key=True,nullable=False)
        jcc_project_id=Column(Enum('default','prodv2','SL_PROD_23_001','SL_PCIC_81_001','SL_MISC_77_001','SL_TOUI_66_001','SL_UAT_02_001'))
        requestor_type=Column(Enum('admin', 'regular'), default='regular')
        groundplex_environment=Column(String(120))
        cloudplex_environment=Column(String(120))
        hadooplex_environment=Column(String(120))
        cloud_plex_name=Column(String(120))
        ground_plex_name=Column(String(120))
        hadoop_plex_name=Column(String(120))
        premium_snap_list=Column(BLOB,nullable=False)
        features_list_dict=Column(BLOB,nullable=False)
        number_of_cloud=Column(Integer,default=0)
        cloudplex_created=Column(Integer,default=0)
        admin_users_list=Column(String(2000))
        list_of_jcc_names=Column(String(1024))
        sidekick_keys=Column(BLOB)
        create_sidekick=Column(Boolean,default=False)
        create_org_flag=Column(Boolean,default=False)
        create_jcc_flag=Column(Boolean,default=False)
        create_cloud=Column(Boolean,default=False)
        create_hadooplex=Column(Boolean,default=False)
        salesforce_link=Column(String(120))
        org_create_status=Column(Enum('success','failed','processing','go'))
        org_create_error_log=Column(BLOB)
        jcc_create_status=Column(Enum('success','failed','processing','go'))
        jcc_create_error_log=Column(BLOB)
    command="""use %s"""%(db_name)
    for i in engine_id.execute('show databases').fetchall():
        mysql_db_list.append(i[0])
    if db_name not in mysql_db_list:        #create db if it does not exist
       engine_id.execute('create database '+db_name)
    engine_id.execute(command)
    for i in engine_id.execute('show tables').fetchall():
        mysql_table_list.append(i[0])
    if org_table not in mysql_table_list:    #only create the table if it is not there
       Base.metadata.create_all(engine_id)   #allows Create Table before any table is created
    return SnaplogicOrg

def create_sales_org_table(engine_id, db_name, sales_org_table):
    #-------------------------------------------------------------------------------------------------------
    #-
    #-------------------------------------------------------------------------------------------------------
    mysql_db_list=[]
    mysql_table_list=[]
    Base=declarative_base(engine_id)    #to create a new table, this must be done first
    class SalesSnaplogicOrg(Base):
        __tablename__= sales_org_table
        record_id=Column(String(200))
        create_date_time=Column(DateTime)
        update_date_time=Column(DateTime)
        user_email=Column(String(200),nullable=False)
        requestor_email=Column(String(200),nullable=False)
        user_firstname=Column(String(200), nullable=False)
        user_lastname=Column(String(200), nullable=False)
        org_name=Column(String(120),primary_key=True,nullable=False)
        pod_name=Column(Enum('prodxl','prodxl2','uatxl','canaryxl','canaryxl2','snap','ux3', 'ux2','ux','portal','budgy','spark','salespod','perf','prov-sldb','dev-sldb','stage'), primary_key=True,nullable=False)
        project_id=Column(Enum('default','prodv2','SL_PROD_23_001','SL_PCIC_81_001','SL_MISC_77_001','SL_TOUI_66_001','SL_UAT_02_001'))
        requestor_type=Column(Enum('admin', 'regular'), default='regular')

        create_sidekick=Column(Boolean,default=False)
        create_cloud=Column(Boolean,default=False)
        create_hadooplex=Column(Boolean,default=False)
        number_of_cloud=Column(Integer,default=0)

        premium_snap_list=Column(BLOB,nullable=False)
        salesforce_link=Column(String(120))
        org_create_status=Column(Enum('success','failed','processing','go'))
    command="""use %s"""%(db_name)
    for i in engine_id.execute('show databases').fetchall():
        mysql_db_list.append(i[0])
    if db_name not in mysql_db_list:        #create db if it does not exist
       engine_id.execute('create database '+db_name)
    engine_id.execute(command)
    for i in engine_id.execute('show tables').fetchall():
        mysql_table_list.append(i[0])
    if sales_org_table not in mysql_table_list:    #only create the table if it is not there
       Base.metadata.create_all(engine_id)   #allows Create Table before any table is created
    return SalesSnaplogicOrg


def create_jcc_table(engine_id, db_name, jcc_table):
    #-------------------------------------------------------------------------------------------------------
    #-
    #-------------------------------------------------------------------------------------------------------
    mysql_db_list=[]
    mysql_table_list=[]
    Base=declarative_base(engine_id)    #to create a new table, this must be done first
    class SnaplogicJcc(Base):
        __tablename__= jcc_table
        record_id=Column(String(200),primary_key=True,nullable=False)
        create_date_time=Column(DateTime)
        update_date_time=Column(DateTime)
        jcc_name=Column(String(200),primary_key=True,nullable=False)
        instance_id=Column(String(200),primary_key=True,nullable=False)
        org_name=Column(String(200),nullable=False)
        pod_name=Column(String(200), nullable=False)
        mrc=Column(String(64), nullable=False)
        deploy_jcc=Column(Boolean,default=True)
        build_prefix=Column(String(64), nullable=False)
        org_record_id=Column(String(200))
        jcc_create_status=Column(Enum('success','failed','processing'))
        jcc_create_message_log=Column(BLOB)
        jcc_deploy_status=Column(Enum('success','failed','processing'))
        jcc_deploy_message_log=Column(BLOB)
        jcc_complete_date_time=Column(DateTime)
        deploy_start_date_time=Column(DateTime)
        deploy_end_date_time=Column(DateTime)
    command="""use %s"""%(db_name)
    for i in engine_id.execute('show databases').fetchall():
        mysql_db_list.append(i[0])
    if db_name not in mysql_db_list:        #create db if it does not exist
       engine_id.execute('create database '+db_name)
    engine_id.execute(command)
    for i in engine_id.execute('show tables').fetchall():
        mysql_table_list.append(i[0])
    if jcc_table not in mysql_table_list:    #only create the table if it is not there
       Base.metadata.create_all(engine_id)   #allows Create Table before any table is created
    return SnaplogicJcc

def create_migration_jcc_table(engine_id, db_name, jcc_table):
    #-------------------------------------------------------------------------------------------------------
    #-
    #-------------------------------------------------------------------------------------------------------
    mysql_db_list=[]
    mysql_table_list=[]
    Base=declarative_base(engine_id)    #to create a new table, this must be done first
    class MigrationSnaplogicJcc(Base):
        __tablename__= jcc_table
        record_id=Column(String(200),primary_key=True,nullable=False)
        create_date_time=Column(DateTime)
        update_date_time=Column(DateTime)
        old_jcc_name=Column(String(200),primary_key=True,nullable=False)
        new_jcc_name=Column(String(200))
        elastic_ip=Column(String(32))
        org_name=Column(String(200),nullable=False)
        pod_name=Column(String(200), nullable=False)
        old_mrc=Column(String(64), nullable=False)
        old_jcc_ver=Column(String(64), nullable=False)
        org_record_id=Column(String(200))
    command="""use %s"""%(db_name)
    for i in engine_id.execute('show databases').fetchall():
        mysql_db_list.append(i[0])
    if db_name not in mysql_db_list:        #create db if it does not exist
       engine_id.execute('create database '+db_name)
    engine_id.execute(command)
    for i in engine_id.execute('show tables').fetchall():
        mysql_table_list.append(i[0])
    if jcc_table not in mysql_table_list:    #only create the table if it is not there
       Base.metadata.create_all(engine_id)   #allows Create Table before any table is created
    return MigrationSnaplogicJcc

def create_controls_table(engine_id, db_name,system_controls_table):
    #-------------------------------------------------------------------------------------------------------
    #-
    #-------------------------------------------------------------------------------------------------------
    mysql_db_list=[]
    mysql_table_list=[]
    Base=declarative_base(engine_id)    #to create a new table, this must be done first
    class SnaplogicControls(Base):
        __tablename__= system_controls_table
        create_date_time=Column(DateTime,primary_key=True,nullable=False)
        update_date_time=Column(DateTime)
        activate_org_creation=Column(Boolean,default=False)
        activate_jcc_creation=Column(Boolean,default=False)
    command="""use %s"""%(db_name)
    for i in engine_id.execute('show databases').fetchall():
        mysql_db_list.append(i[0])
    if db_name not in mysql_db_list:        #create db if it does not exist
       engine_id.execute('create database '+db_name)
    engine_id.execute(command)
    for i in engine_id.execute('show tables').fetchall():
        mysql_table_list.append(i[0])
    if system_controls_table not in mysql_table_list:    #only create the table if it is not there
       Base.metadata.create_all(engine_id)   #allows Create Table before any table is created
    return SnaplogicControls

def create_jcc_lock_table(engine_id, db_name,jcc_lock_table):
    #-------------------------------------------------------------------------------------------------------
    #-
    #-------------------------------------------------------------------------------------------------------
    mysql_db_list=[]
    mysql_table_list=[]
    Base=declarative_base(engine_id)    #to create a new table, this must be done first
    class SnaplogicLock(Base):
        __tablename__= jcc_lock_table
        create_date_time=Column(DateTime,primary_key=True,nullable=False)
        lock_begin_time=Column(DateTime)
        lock_end_time=Column(DateTime)
        lock_process_name=Column(String(200))
        attempts_to_get_lock=Column(Integer,default=0)
        block_jcc_creation=Column(Boolean,default=False)
        block_deploy_run=Column(Boolean,default=False)
    command="""use %s"""%(db_name)
    for i in engine_id.execute('show databases').fetchall():
        mysql_db_list.append(i[0])
    if db_name not in mysql_db_list:        #create db if it does not exist
       engine_id.execute('create database '+db_name)
    engine_id.execute(command)
    for i in engine_id.execute('show tables').fetchall():
        mysql_table_list.append(i[0])
    if jcc_lock_table not in mysql_table_list:    #only create the table if it is not there
       Base.metadata.create_all(engine_id)   #allows Create Table before any table is created
    return SnaplogicLock

def create_premium_snap_table(engine_id, db_name,premium_snap_table):
    #-------------------------------------------------------------------------------------------------------
    #-
    #-------------------------------------------------------------------------------------------------------
    mysql_db_list=[]
    mysql_table_list=[]
    Base=declarative_base(engine_id)    #to create a new table, this must be done first
    class SnaplogicPremiumSnapList(Base):
        __tablename__= premium_snap_table
        create_date_time=Column(DateTime,nullable=False)
        pod_name=Column(String(200),primary_key=True,nullable=False)
        premium_snap_list=Column(BLOB,nullable=False)
    command="""use %s"""%(db_name)
    for i in engine_id.execute('show databases').fetchall():
        mysql_db_list.append(i[0])
    if db_name not in mysql_db_list:        #create db if it does not exist
       engine_id.execute('create database '+db_name)
    engine_id.execute(command)
    for i in engine_id.execute('show tables').fetchall():
        mysql_table_list.append(i[0])
    if premium_snap_table not in mysql_table_list:    #only create the table if it is not there
       Base.metadata.create_all(engine_id)   #allows Create Table before any table is created
    return SnaplogicPremiumSnapList 



def connect_to_mysql(db_user):
    #-------------------------------------------------------------------------------------------------------
    #-
    #-------------------------------------------------------------------------------------------------------
    engine=create_engine('mysql+mysqldb://%s:@127.0.0.1/%s'%(db_user,org_db_name), pool_timeout=20, pool_recycle=3600)
    session=sessionmaker(bind=engine)
    a_session=session()
    return engine,a_session

def check_and_create_db_and_table():
    #-------------------------------------------------------------------------------------------------------
    #-
    #-------------------------------------------------------------------------------------------------------
    db_handle, a_session_id=connect_to_mysql(mysql_account)
    Base=declarative_base(a_session_id)    #to create a new table, this must be done first
    a_table1=create_org_table(db_handle, org_db_name, org_table_name)
    a_table2=create_jcc_table(db_handle, org_db_name, jcc_table_name)
    a_table3=create_controls_table(db_handle, org_db_name, controls_table_name)
    a_table4=create_migration_jcc_table(db_handle, org_db_name, migration_jcc_table_name)
    a_table5=create_jcc_lock_table(db_handle, org_db_name,jcc_lock_table_name)
    a_table6=create_premium_snap_table(db_handle, org_db_name,premium_snap_table_name)
    a_table7=create_sales_org_table(db_handle, org_db_name, sales_org_table_name)
    a_table8=create_login_users_table(db_handle, org_db_name, login_users_table_name)
    return a_session_id,db_handle,a_table1,a_table2,a_table3,a_table4,a_table5,a_table6,a_table7,a_table8

session_id,db_engine,SnaplogicOrgRec,SnaplogicJCCRec,SnaplogicControlsRec,MigrationJCCRec, SnaplogicLockRec, SnaplogicPremiumSnapRec,SalesSnaplogicOrgRec,UserAuthorizationRec=check_and_create_db_and_table()


