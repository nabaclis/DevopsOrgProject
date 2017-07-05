import os, sys, tempfile, shutil, ftplib, tarfile, glob, MySQLdb, json
import threading, Queue, datetime, uuid, syslog

import snapi.snapi_request
import snapi.snapi_asset
import snapi.snapi_meter
import snapi.snapi_plex
import slutils.sladmin
import snapi.snapi_context
import snapi_base.exceptions
import snapi_base.keys as keys


from org_user_manager import *

import app
from custom_org_utility_functions import generate_property_keys
import app.common_org_utility_functions

from app import appFlask
from app import db_params
from forms import orgInputForm, dbOutputForm, jccInputForm, jccOutputForm, dbUpdateOutputForm, orgScriptForm, SystemControlsForm,jccProjectDisplayForm
from forms import dbSpecialUpdateOutputForm, groundplexKeysOutputForm, jccMigrationOutputForm, userVerifyForm, premiumSnapForm,orgPremiumSnapInputForm
from forms import orgFeaturesListForm, orgFeaturesInputForm, loginForm
from flask import render_template, flash, redirect, request, url_for, Response, session
from sqlalchemy import exc
from flask.ext.login import LoginManager, UserMixin, login_required

mysql_account='root'
config_file=None
org_db_name='org_provisioning_db'
org_table_name='org_requisition_data'

login_manager = LoginManager()
login_manager.init_app(app.appFlask)


def get_org_assigned_features(org_name, pod_name):
    #---------------------------------------------------------------------------------------------------
    #- do the DB call and get a list of features already assigned
    #---------------------------------------------------------------------------------------------------
    selected_features_list=[]
    pod_prefix, the_uri=app.common_org_utility_functions.get_pod_admin_user(pod_name)
    asset_api,sysadmin_snapi_snap_pack=get_asset_api_ptr(pod_prefix, config_file)
    subs=asset_api.get_all_subscriptions(org_name)
    for sub in subs:
        print '\t',selected_features_list
        if sub in app.reverse_features_dict:
           selected_features_list.append(app.reverse_features_dict[sub])
    return selected_features_list

def add_subscription(org_name, sysadmin_snapi_snap_pack, snaps_dict, required_snap_list,removal_snap_list,pod_prefix,config_file):
    #---------------------------------------------------------------------------------------------------
    #- After setting is_sub=True on the selected snaps, plus the existing ones, add them all
    #---------------------------------------------------------------------------------------------------
    subs=[]
    for key in required_snap_list:                                        #add all selected snaps
        for an_index, record in enumerate(snaps_dict):
            if record['snap_pack_label']==key:
               snaps_dict[an_index]['is_sub']=True
               subs.append(snaps_dict[an_index])
    for key in removal_snap_list:                                         #remove all the deselected snaps
        for an_index, record in enumerate(snaps_dict):
            if record['snap_pack_label']==key:
               snaps_dict[an_index]['is_sub']=False
               subs.append(snaps_dict[an_index])

    admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_prefix, config_file)
    session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
    asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)

    org_snid=asset_api.lookup_org(org_name)['snode_id']
    sysadmin_snapi_snap_pack.modify_subscriptions(org_snid, {keys.SNAP_PACK_SUBSCRIPTIONS: subs})


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

@appFlask.route('/UpdateOrgPremiumSnaps/',methods=['get','post'])
def update_org_premium_snaps():
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    config_file=None
    snap_list=[]
    available_snap_list=[]
    selected_snaps=[]
    #snap_form=premiumSnapForm()
    input_data=orgPremiumSnapInputForm()

    org_name=str(input_data.org_name.data)
    pod_name=str(input_data.pod_name.data)
    if type(org_name) is str:
       org_name=org_name.strip()
    else:
       org_name=''
    if type(pod_name) is str:
       pod_name=pod_name.strip()
    else:
       pod_name=''
    results=''
    org_name=org_name.strip()
    pod_name=pod_name.strip()
    if len(org_name) > 0 and len(pod_name) > 0 and org_name != 'None' and pod_name != 'None':
       print 'ORG-NAME:',org_name, 'POD-NAME:',pod_name
       return redirect('/UpdateTheOrgPremiumSnaps/%s/%s'%(org_name,pod_name))
    return render_template('update_org_snap_input_menu.html',form=input_data,selected_snap_list=[])

@appFlask.route('/ListOrgFeatures/',methods=['get','post'])
def get_org_features():
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    config_file=None
    snap_list=[]
    input_data=orgFeaturesInputForm()
    org_name=str(input_data.org_name.data)
    pod_name=str(input_data.pod_name.data)
    if type(org_name) is str:
       org_name=org_name.strip()
    else:
       org_name=''
    if type(pod_name) is str:
       pod_name=pod_name.strip()
    else:
       pod_name=''
    results=''
    org_name=org_name.strip()
    pod_name=pod_name.strip()
    if len(org_name) > 0 and len(pod_name) > 0 and org_name != 'None' and pod_name != 'None':
       try:
          return render_template('display_selected_features_template.html',selected_features_list= get_org_assigned_features(org_name, pod_name), org_name=org_name, pod_name=pod_name)
       except:
          message=str(sys.exc_info()[1])
          if message.find('NoneType found') > 0:
             message='Error: Unable to get data. Either the Pod or Org does not exist'
          else:
             for i in str(sys.exc_info()).split(','):
                 if i.find('response_map') >= 0:
                    message=i.split(':')[1:]
                    message=' '.join(message)
                    break
          syslog.syslog(message)
          flash(message)
          return render_template('org_features_input_menu.html',form=input_data,selected_features_list=[])
    return render_template('org_features_input_menu.html',form=input_data,selected_features_list=[])


@appFlask.route('/ListOrgPremiumSnaps/',methods=['get','post'])
def get_premium_snaps():
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    config_file=None
    snap_list=[]

    input_data=orgPremiumSnapInputForm()
    org_name=str(input_data.org_name.data)
    pod_name=str(input_data.pod_name.data)
    if type(org_name) is str:
       org_name=org_name.strip()
    else:
       org_name=''
    if type(pod_name) is str:
       pod_name=pod_name.strip()
    else:
       pod_name=''
    results=''
    org_name=org_name.strip()
    pod_name=pod_name.strip()
    if len(org_name) > 0 and len(pod_name) > 0 and org_name != 'None' and pod_name != 'None':
       try:
          pod_prefix, the_uri=app.common_org_utility_functions.get_pod_admin_user(pod_name)
          asset_api,sysadmin_snapi_snap_pack=get_asset_api_ptr(pod_prefix, config_file)
      
          org_snid=asset_api.lookup_org(org_name)['snode_id']
          subs = sysadmin_snapi_snap_pack.check_subscriptions(org_snid)[keys.SNAP_PACK_SUBSCRIPTIONS]
       
          for i in subs:
              if i['is_sub'] is True:
                 snap_list.append(i['snap_pack_label'])
          snap_list.sort()
          return render_template('display_selected_snaps_template.html',selected_snap_list=snap_list, org_name=org_name, pod_name=pod_name)
       except:
          message=str(sys.exc_info()[1])
          if message.find('NoneType found') > 0:
             message='Error: Unable to get data. Either the Pod or Org does not exist'
          else:
             for i in str(sys.exc_info()).split(','):
                 if i.find('response_map') >= 0:
                    message=i.split(':')[1:]
                    message=' '.join(message)
                    break
          syslog.syslog(message)
          flash(message)
          return render_template('org_snap_input_menu.html',form=input_data,selected_snap_list=[])
    return render_template('org_snap_input_menu.html',form=input_data,selected_snap_list=[])

@appFlask.route('/UpdateTheOrgPremiumSnaps/<org_name>/<pod_name>',methods=['get','post'])
def update_the_org_premium_snaps(org_name, pod_name):
    #--------------------------------------------------------------------------------------
    #-   Used to update the premium snaps on an org
    #--------------------------------------------------------------------------------------
    config_file=None
    results=''
    pod_prefix=''
    snap_list=[]
    selected_snaps=[]
    available_snap_list=[]
    snap_form=premiumSnapForm()

    try:
       pod_prefix, the_uri=app.common_org_utility_functions.get_pod_admin_user(pod_name)
       asset_api,sysadmin_snapi_snap_pack=get_asset_api_ptr(pod_prefix, config_file)

       org_snid=asset_api.lookup_org(org_name)['snode_id']
       subs = sysadmin_snapi_snap_pack.check_subscriptions(org_snid)[keys.SNAP_PACK_SUBSCRIPTIONS]

       for i in subs:
           if i['is_sub'] is True:
              snap_list.append(i['snap_pack_label'])
           available_snap_list.append(i['snap_pack_label'])
    except:
       message='Error getting Org/Pod data. Either the Pod and/or Org is incorrect'
       syslog.syslog(message)
       flash(message)
       return redirect('/UpdateOrgPremiumSnaps/')     #go back to the main menu
    snap_list.sort()
    available_snap_list.sort()     #list of all the snaps

    SELECT_ALL_FLAG=request.values.get('select_all')
    CLEAR_ALL_FLAG=request.values.get('clear_all')

    selected_snaps_index=request.values.getlist('box')
    deselected_snaps_index=request.values.getlist('box1')

    if SELECT_ALL_FLAG=='y':
       print '>>>Adding all Snaps'
       selected_snaps=available_snap_list[:]
    else:
       for k in selected_snaps_index:
           selected_snaps.append(available_snap_list[int(k)])
       selected_snaps=list(set(selected_snaps))
    selected_snaps.sort()

    removal_list=[]
    if CLEAR_ALL_FLAG=='y':
       removal_list=snap_list[:]     #snap_list is the list of snaps already allocated to the Org
    else:
       for k in deselected_snaps_index:
           removal_list.append(snap_list[int(k)])
    if CLEAR_ALL_FLAG=='y':
        new_snaps=[]
        snap_list=[]

    new_snaps=list(set(snap_list) - set(removal_list))
    new_snaps.extend(list(set(selected_snaps)))
    new_snaps=list(set(new_snaps))
    new_snaps.sort()
    add_subscription(org_name, sysadmin_snapi_snap_pack, subs, new_snaps,removal_list,pod_prefix,config_file)    #add subscriptions to the Org
    #commit() write the data to SLDB

    return render_template('premium_snap_list.html', form=snap_form, snap_list=available_snap_list, selected_snap_list=snap_list, org_name=org_name, pod_name=pod_name,new_org_input=False)

@appFlask.route('/ListPremiumSnaps/<pod_name>/<org_name>',methods=['get','post'])
def show_premium_snaps(pod_name, org_name):
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    results=''
    snap_list=[]
    selected_snaps=[]
    snap_form=premiumSnapForm()
    rec=app.session_id.query(app.SnaplogicPremiumSnapRec).filter_by(pod_name=pod_name)
    try:
      snap_list=eval(rec[0].premium_snap_list)
    except:
      print '>>>Found no snaps for Pod:',pod_name
      syslog.syslog('>>>Found no snaps for Pod:'+pod_name)
      flash('Error: Found no snaps for Pod:'+pod_name)
    db_snaps=app.session_id.query(app.SnaplogicOrgRec).filter_by(pod_name=pod_name, org_name=org_name)
    try:
       stored_selected_snaps=eval(db_snaps[0].premium_snap_list)
    except:
       stored_selected_snaps=[] #initialize the stap array

    SELECT_ALL_FLAG=request.values.get('select_all')
    CLEAR_ALL_FLAG=request.values.get('clear_all')

    selected_snaps_index=request.values.getlist('box')
    deselected_snaps_index=request.values.getlist('box1')
    
    if SELECT_ALL_FLAG=='y':
       print '>>>Adding all Snaps'
       selected_snaps=snap_list[:]
    else:
       for k in selected_snaps_index:
           selected_snaps.append(snap_list[int(k)])
       selected_snaps=list(set(selected_snaps)) 
    selected_snaps.sort() 
    removal_list=[]
    for k in deselected_snaps_index:
        removal_list.append(stored_selected_snaps[int(k)])
    if CLEAR_ALL_FLAG=='y':
        removal_list=[]
        new_snaps=[]
        stored_selected_snaps=[]
    new_snaps=list(set(stored_selected_snaps) - set(removal_list))
    new_snaps.extend(list(set(selected_snaps)))
    new_snaps=list(set(new_snaps))
    new_snaps.sort()
    db_snaps[0].premium_snap_list = new_snaps
    app.session_id.commit()
    app.session_id.close()
    if SELECT_ALL_FLAG=='y' or CLEAR_ALL_FLAG=='y':
       return redirect("/ListPremiumSnaps/%s/%s"%(pod_name,org_name))
    else:
       return render_template('premium_snap_list.html', form=snap_form, snap_list=snap_list, selected_snap_list=new_snaps,org_name=org_name,pod_name=pod_name,new_org_input=True)

@appFlask.route('/removeOrgUser/<process_request>',methods=['get','post'])
@appFlask.route('/addOrgUser/<process_request>',methods=['get','post'])
@appFlask.route('/manageOrgUser/<process_request>',methods=['get','post'])
def manage_org_user(process_request):
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    results=''
    org=None
    feature=None
    get_user_valid_flag=True
    group_membership=None
    input_data=userVerifyForm()
    pod_name=str(input_data.pod_name.data).strip()
    user_name=str(input_data.user_name.data).strip()
    pod_name='' if pod_name=='None' else pod_name 

    user_group_menu=[None,'admins', 'members']
    pod_name_menu=[None,'salespod','spark','auditpod','budgy','qa','snapxl','perf','prod','canary','qapod','uat','portal','ux','ux2','ux3','prov-sldb','dev-sldb','stage']

    if len(user_name) == 0:
       flash("A user name is required, so try again...")
       get_user_valid_flag=False
    elif len(pod_name) == 0:
       flash("A POD name must be provided, so please try again...")
       get_user_valid_flag=False

    if process_request=='GET_USER':
       feature=str(input_data.feature_name.data).strip()
       features=[None, 'verify user exists', 'give full user details', 'list user orgs']
       features_dict={'None':'','verify user exists':'verify', 'give full user details':'details','list user orgs':'orgs'}
       feature=features_dict[str(input_data.feature_name.data).strip()]

       if len(feature) == 0:
          flash("The Function type must be provided, please try again...")
          get_user_valid_flag=False

       if get_user_valid_flag == True:
          results=do_user_processing(process_request, user_name, pod_name, feature, org, group_membership)
          flash(results)
       return render_template('manage_user.html',form=input_data,feature_name_menu=features,pod_name_menu=pod_name_menu,results=results)
    elif process_request=='ADD_USER':
       org_name=str(input_data.org_name.data).strip()
       group_name=str(input_data.group_name.data).strip()
       group_name='' if group_name=='None' else group_name
       if len(group_name) == 0:
         flash("A group name is required, so try again...")
         get_user_valid_flag=False
       elif len(org_name) == 0:
         flash("An Org name must be provided, so please try again...")
         get_user_valid_flag=False
 
       if get_user_valid_flag == True:
          results=do_user_processing(process_request, user_name, pod_name, feature, org_name, group_name)
          flash(results)
       return render_template('add_org_user.html',form=input_data,pod_name_menu=pod_name_menu,user_group_menu=user_group_menu,results=results)
    elif process_request=='REMOVE_USER':
       org_name=str(input_data.org_name.data).strip()
       if len(org_name) == 0:
          flash("An Org name must be provided, so please try again...")
          get_user_valid_flag=False

       if get_user_valid_flag == True:
          results=do_user_processing(process_request, user_name, pod_name, feature, org_name) # group_name)
          if results==None:
             results='Nothing was done. Could be the POD is incorrect or the Org and/or User does not exist..'
          flash(results)
       return render_template('remove_org_user.html',form=input_data,pod_name_menu=pod_name_menu, results=results)

@appFlask.route('/collectFeaturesForBatch/<ops_type>/<org_name>/<pod_name>',methods=['get','post'])
def get_features_for_batch_processing(ops_type,org_name,pod_name):
    #------------------------------------------------------------------------------------------------------
    #- if ops_type is 'add' then activate features. if ops_type is 'remove' then deactivate features
    #------------------------------------------------------------------------------------------------------
    print '>>>>ORG-NAME IS: ',org_name
    selected_items=''
    template_message='Add To Org'
    if ops_type == 'LocalDBAdd':
       activate_flag='on'
    elif ops_type == 'Delete':
       activate_flag='off'
    else:
       activate_flag='on'
    ON_dict={}
    config_file=None
    input_data=orgFeaturesListForm()
    features_names=app.features_dict.keys()   #gives all of the available Features names
    selected_records=request.form.getlist('box')
    for i in selected_records:
        ON_dict[app.features_dict[features_names[int(i)]].keys()[0]]=app.features_dict[features_names[int(i)]][app.features_dict[features_names[int(i)]].keys()[0]][activate_flag]
        print ON_dict
        selected_items=selected_items+','+features_names[int(i)]
    if len(selected_items) > 0:
       if selected_items[0]==',':
          selected_items=selected_items[1:]
       flash('Features selected are:'+selected_items)
    db_features=app.session_id.query(app.SnaplogicOrgRec).filter_by(pod_name=pod_name, org_name=org_name)  #get pointer to db
    print '********ON-DICT:',ON_dict
    if db_features[0].create_hadooplex:
       ON_dict['spark']='spark'
    if len(ON_dict) > 0:
       db_features[0].features_list_dict = ON_dict 
       app.session_id.commit()
       app.session_id.close()

    return render_template('org_features_list.html',form=input_data,features_list=features_names,processing_type=template_message, ops_type=ops_type)

@appFlask.route('/showOrgFeaturesForUpdates/<org_name>/<pod_name>/<pod_prefix>/<ops_type>/',methods=['get','post'])
def update_org_features(org_name,pod_name,pod_prefix,ops_type):
    #------------------------------------------------------------------------------------------------------
    #- if ops_type is 'add' then activate features. if ops_type is 'remove' then deactivate features
    #------------------------------------------------------------------------------------------------------
    selected_items=''
    if ops_type == 'Add':
       activate_flag='on'
    elif ops_type == 'Delete':
       activate_flag='off'
    else:
       activate_flag='on'
    ON_dict={}
    config_file=None
    input_data=orgFeaturesListForm()
    features_names=app.features_dict.keys()   #gives all of the available Features names
    if ops_type=='Delete':          #for testing
       features_names=get_org_assigned_features(org_name, pod_name)
    selected_records=request.form.getlist('box')
    for i in selected_records:
        ON_dict[app.features_dict[features_names[int(i)]].keys()[0]]=app.features_dict[features_names[int(i)]][app.features_dict[features_names[int(i)]].keys()[0]][activate_flag]
        print ON_dict
        selected_items=selected_items+','+features_names[int(i)]

    if len(ON_dict) > 0:
       admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_prefix, config_file)
       session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
       asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)
       x=asset_api.update_subscription(org_name, data=ON_dict)
       if selected_items[0]==',':
          selected_items=selected_items[1:]
       if ops_type=='Add':
          flash("""Added Features: %s"""%(selected_items))
       elif ops_type=='Delete':
          flash("""Deleted Features: %s"""%(selected_items))
    return render_template('org_features_list.html',form=input_data,org_name=org_name, pod_name=pod_name, features_list=features_names,processing_type=ops_type)

@appFlask.route('/changeOrgFeatures/<ops_type>/',methods=['get','post'])
def modify_org_features(ops_type):
    #--------------------------------------------------------------------------------------
    #- Function to add/remove Features started 6/19/2016
    #- ops_type could be add|remove
    #--------------------------------------------------------------------------------------
    processing_type=''
    if ops_type=='Add':
       processing_type='For Adding Features'
    elif ops_type=='Delete':
       processing_type='For Deleting Features'
    input_data=orgFeaturesInputForm()
    org_name=str(input_data.org_name.data)
    pod_name=str(input_data.pod_name.data)
    if type(org_name) is str:
       org_name=org_name.strip()
    else:
       org_name=''
    if type(pod_name) is str:
       pod_name=pod_name.strip()
    else:
       pod_name=''
    results=''
    if len(org_name) > 0 and len(pod_name) > 0 and pod_name != 'None':
       keys_file=app.custom_org_utility_functions.get_file_names()
       if keys_file=='ERROR':
          flash('***ERROR:Could not find keys.properties file...')
       pod_prefix, error_messages = app.custom_org_utility_functions.get_pod_prefix(pod_name,app.custom_org_utility_functions.elastic,app.custom_org_utility_functions.clouddev,keys_file)
       if pod_prefix is not None and app.custom_org_utility_functions.does_org_exist(pod_prefix,org_name):
          return redirect ('/showOrgFeaturesForUpdates/%s/%s/%s/%s'%(org_name,pod_name,pod_prefix,ops_type))
       else:
          flash ("Cannot find Org: %s in POD: %s"%(org_name, pod_name))
    return render_template('org_features_input_menu.html',form=input_data,selected_features_list=[],processing_type=processing_type)

@appFlask.route('/getGroundplexKeys',methods=['get','post'])
def show_groundplex_keys():
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    input_data=groundplexKeysOutputForm()
    org_name=str(input_data.org_name.data)
    pod_name=str(input_data.pod_name.data)
    if org_name == 'None':
       org_name=''
    if pod_name == 'None':
       pod_name=''
    if type(org_name) is str:
       org_name=org_name.strip()
    else:
       org_name=''
    if type(pod_name) is str:
       pod_name=pod_name.strip()
    else:
       pod_name=''
    results=''
    if len(org_name) > 0 and len(pod_name) > 0:
       try:
          print '>>>PASSING: Org_name:',org_name, "POD_NAME:",pod_name
          results=generate_property_keys(org_name,pod_name)
          results=results.split('\n')
       except:
          print sys.exc_info()[1]
          flash(sys.exc_info()[1])
    return render_template('groundplex_keys_menu.html',form=input_data,results=results)

@appFlask.route('/createOrgs',methods=['get','post'])
def launch_the_create_org_script():
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    data_str=''
    results_arr=''
    finished_array=[]
    results_fields=orgScriptForm()
    script_path=app.APP_HOME+'/build_org.py'
    results=os.popen(script_path).read()
    if len(results) > 0 and type(results) is str:
       data_str=results[:results.find('[')]
       if len(data_str) > 0:
          finished_array.append(data_str)
       results_arr=results[results.find('['):]
       if len(results) > 0:
          finished_array.extend(eval(results_arr))
    return render_template('launch_org_menu.html',form=results_fields,results=finished_array) 

@appFlask.route('/manageProjectJCCs',methods=['get','post'])
def display_project_jcc_data():
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    results=''
    script_path=app.APP_HOME+'/manage_project_jccs.py'
    input_data=jccProjectDisplayForm()
    jcc_project_id=str(input_data.jcc_project_id.data).strip()
    feature_name=str(input_data.feature_name.data).strip()
    function_type=str(input_data.function_type.data).strip()

    project_id_menu=['default','prodv2','SL_PROD_23_001','SL_PCIC_81_001','SL_MISC_77_001','SL_TOUI_66_001','SL_UAT_02_001']
    feature_name_menu=['used','available','all']
    function_type_menu=['LIST_JCCS']

    if function_type=='LIST_JCCS':
       command="""%s -p %s %s -f %s"""%(script_path,jcc_project_id,function_type, feature_name)
       print 'Command:'+command
       try:
          tmp_results=[]
          message_display_list=[]
          if feature_name == 'used':
             template_title="The List Of JCC Servers in Use For Project-Id "+jcc_project_id
          elif feature_name == 'available':
             template_title="The List Of JCC Servers Than can Be used For Project-Id "+jcc_project_id
          elif feature_name == 'all':
             template_title="The List Of All JCC Servers For Project-Id "+jcc_project_id
          results=os.popen(command).readlines()
          for i in results:
              if i[0]=='(':
                 tmp_results.append(eval(i))
              else:
                 message_display_list.append(i)
          results=tmp_results[:]
          return render_template('jcc_display_menu.html',form=input_data,results=results,template_title=template_title,message_list=message_display_list)
       except:
          flash('Failed to list JCCs...')

    return render_template('manage_project_jccs.html',form=input_data,results=results,project_id_menu=project_id_menu,feature_name_menu=feature_name_menu,function_type_menu=function_type_menu)

def sanitize_existing_fields_change(field_dict,special_keys,db_fields):
    #--------------------------------------------------------------------------------------
    #-Get ret of blanks and line feed in the field
    #--------------------------------------------------------------------------------------
    error_message=[]
    final_dict={}
    for i in field_dict:
        if field_dict[i] is not None and type(field_dict[i]) is str:
           field_dict[i]=field_dict[i].strip()
           if i in special_keys:
              field_dict[i]=field_dict[i].replace(' ','')
    if field_dict.has_key('cloud_plex_name') and type(field_dict['cloud_plex_name']) is not bool:
       field_dict['cloud_plex_name']=db_fields.cloud_plex_name.data.strip()
    if field_dict.has_key('ground_plex_name'):
       field_dict['ground_plex_name']=db_fields.ground_plex_name.data.strip()
    if field_dict.has_key('hadoop_plex_name'):
       field_dict['hadoop_plex_name']=db_fields.hadoop_plex_name.data.strip()

    if field_dict.has_key('number_of_cloud'):
       field_dict['number_of_cloud']=db_fields.number_of_cloud.data
    if field_dict.has_key('cloudplex_created'):
       field_dict['cloudplex_created']=db_fields.cloudplex_created.data
    if field_dict.has_key('reate_sidekick'):
       field_dict['create_sidekick']=db_fields.create_sidekick.data
    if field_dict.has_key('requestor_type'):
       field_dict['requestor_type']=db_fields.requestor_type.data
    if field_dict.has_key('org_create_status'):
       field_dict['org_create_status']=db_fields.org_create_status.data

    for i in field_dict:
        if type(field_dict[i]) is str or type(field_dict[i]) is unicode:
              if len(field_dict[i]) > 0:
                     final_dict[i]=field_dict[i]
        elif type(field_dict[i]) is bool or type(field_dict[i]) is int:
             final_dict[i]=field_dict[i]

    return final_dict, error_message

def sanitize_required_fields(field_dict):
    #--------------------------------------------------------------------------------------
    #-Get rid of blanks and line feed in the field
    #--------------------------------------------------------------------------------------
    error_message=[]
    null_fields_found=[]
    null_fields=True
    for i in field_dict:
        print '***KEY:',i,'  VAL:',field_dict[i]
        if field_dict[i] is None:
           null_fields_found.append(i)
           error_message.append('Error: '+i+' cannot be empty')
        else:
           field_dict[i]=field_dict[i].strip().replace(' ','')
           if len(field_dict[i]) == 0:
              error_message.append('Error: '+i+' cannot be empty')
              null_fields_found.append(i)
    for key in field_dict:
        if type(field_dict[key]) is not None and (type(field_dict[key]) is str or type(field_dict[key]) is unicode) and len(field_dict[key]) > 0:
           null_fields=False
           break
    return field_dict, error_message,null_fields 
    

@appFlask.route('/')
@appFlask.route('/index')
def index():
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    title='Snaplogic Org Deployment Tool'
    return render_template('main_page.html', title=title, user='claude')

@appFlask.route('/showOrgRecordsToBuild/<rec_ids>', methods=['get','post'])
def show_org_records_to_build(rec_ids):
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    db_fields=dbOutputForm()
    db_list=[]
    for i in rec_ids:
        rec=app.session_id.query(app.SnaplogicOrgRec).filter_by(record_id=i)
        cmd="""%s/app/build_org.py -o %s -p %s -e %s -f %s -s %s """%(app.APP_HOME,rec[0].org_name, rec[0].pod_name, rec[0].user_email, rec[0].user_firstname, rec[0].user_lastname)
        flash(cmd)
    app.session_id.close()
    return render_template('build_org_list.html',db_list=db_list,form=db_fields)

@appFlask.route('/listDBRecords',methods=['get','post'])
def list_org_database_items():
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    db_fields=dbOutputForm()
    table_header='ORG DB Records'
    db_list=app.session_id.query(app.SnaplogicOrgRec).all()
    selected_records=request.form.getlist('box')
    if len(selected_records) > 0:
       show_org_records_to_build(selected_records) 
       db_list=[]
       return render_template('build_org_list.html',db_list=db_list,form=db_fields)
    app.session_id.close()
    return render_template('db_entries_list.html',db_list=db_list,form=db_fields,table_header=table_header)

@appFlask.route('/deleteJCCRecords',methods=['get','post'])
def delete_jcc_database_items():
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    db_fields=jccOutputForm()
    db_list=app.session_id.query(app.SnaplogicJCCRec).all()
   
    selected_records=request.form.getlist('box')
    for i in selected_records:
       obj1=app.session_id.query(app.SnaplogicJCCRec).filter_by(record_id=i)
       for k in obj1:
           app.session_id.delete(k)
           app.session_id.commit()
           syslog.syslog("Successfully deleted JCC DB record where Record Id:%s, Jcc name is %s, org_name:%s, pod_name:%s"%(k.record_id,k.jcc_name,k.org_name,k.pod_name))
           flash("Successfully deleted Jcc record where Record Id: %s, Jcc name is %s, org_name:%s, pod_name:%s"%(k.record_id,k.jcc_name,k.org_name,k.pod_name))
    app.session_id.close()
    return render_template('delete_jcc_entries_list.html',db_list=db_list,form=db_fields)


@appFlask.route('/deleteDBRecords',methods=['get','post'])
def delete_org_database_items():
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    db_fields=dbOutputForm()
    db_list=app.session_id.query(app.SnaplogicOrgRec).all()
    
    selected_records=request.form.getlist('box')
    for i in selected_records:
       obj1=app.session_id.query(app.SnaplogicOrgRec).filter_by(record_id=i)
       for k in obj1:
           print k.org_name
           app.session_id.delete(k)
           app.session_id.commit()
           syslog.syslog("Successfully deleted ORG DB record where record_id is %s, org_name:%s, pod_name:%s"%(i,k.org_name,k.pod_name))
           flash("Successfully deleted ORG DB record where record_id is %s, org_name:%s, pod_name:%s"%(i,k.org_name,k.pod_name))
    #app.session_id.close()
    return render_template('delete_entries_list.html',db_list=db_list,form=db_fields)

@appFlask.route('/listJCCRecords',methods=['get','post'])
def list_jcc_database_items():
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    db_fields=jccOutputForm()
    deploy_jcc_menu=[True, False]
    db_list=app.session_id.query(app.SnaplogicJCCRec).all()

    updated_deploy_jcc=request.values.getlist('deploy_jcc')
    for i in updated_deploy_jcc:
        j=i.split()
        if len(j) == 2:
           obj1=app.session_id.query(app.SnaplogicJCCRec).filter_by(record_id=j[0])
           try:
              obj1.update({'deploy_jcc':eval(j[1])})
              app.session_id.commit()
              print 'JCC Rec updated successfully for record_id:'+j[0]+' deploy_jcc:'+str(j[1])
           except:
              print 'Could not update for record_id:'+j[0]+' deploy_jcc:'+str(j[1])
              flash(sys.exc_info()[0])
              app.session_id.rollback()
    app.session_id.close()
    return render_template('jcc_entries_list.html',db_list=db_list,deploy_jcc_menu=deploy_jcc_menu, form=db_fields)

@appFlask.route('/listMigrationJCCRecords',methods=['get'])
def list_migration_jcc_database_items():
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    db_fields=jccMigrationOutputForm()
    db_list=app.session_id.query(app.MigrationJCCRec).all()
    app.session_id.close()
    return render_template('migration_entries_list.html',db_list=db_list, form=db_fields)

@appFlask.route('/getOrgData',methods=['get','post'])
def get_org_data():
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    error_message=[]
    date_time=datetime.datetime.now()
    create_org_menu=[False,True]
    create_jcc_menu=[False,True]
    user_email_val='cseymour@snaplogic.com'
    user_firstname='claude'
    user_lastname='seymour'
    pod_name_menu=['prodxl','prodxl2','canaryxl','canaryxl2','uatxl','qa','snap','ux','ux2','ux3','portal','budgy','spark','salespod','perf','prov-sldb','dev-sldb','stage']
    jcc_project_menu=['default','prodv2','SL_PROD_23_001','SL_PCIC_81_001','SL_MISC_77_001','SL_TOUI_66_001','SL_UAT_02_001']
    requestor_type_menu=['admin','regular']
    f_fields = orgInputForm()

    #user_email_val=f_fields.user_email.data
    if user_email_val is not None:
       user_email_val=user_email_val.lower()

    requestor_email_val=f_fields.requestor_email.data
    if requestor_email_val is not None:
       requestor_email_val=requestor_email_val.lower()

    # Variables below like username first and last name need not be validated because they are preset for right now
    #key_fields_dict={'user_email':user_email_val, 'requestor_email':requestor_email_val, 'org_name':f_fields.org_name.data, 'user_firstname':user_firstname,'user_lastname':user_lastname}
    key_fields_dict={'requestor_email':requestor_email_val, 'org_name':f_fields.org_name.data}

    key_fields_dict['pod_name']=request.values.get('pod_name')
    key_fields_dict['jcc_project_id']=request.values.get('jcc_project_id')

    key_fields_dict,error_message,all_null_fields=sanitize_required_fields(key_fields_dict)
    if all_null_fields is True:
       return render_template('org_input_form.html',form=f_fields,pod_name_menu=pod_name_menu,requestor_type_menu=requestor_type_menu,create_org_menu=create_org_menu,create_jcc_menu=create_jcc_menu,jcc_project_menu=jcc_project_menu)
    elif len(error_message) > 0: 
       flash('ERRORS:')
       for k in error_message:
           flash (k)
       return render_template('org_input_form.html',form=f_fields,pod_name_menu=pod_name_menu,requestor_type_menu=requestor_type_menu,create_org_menu=create_org_menu,create_jcc_menu=create_jcc_menu,jcc_project_menu=jcc_project_menu)
    else:
       for i in key_fields_dict:
           if i == 'pod_name':
              f_fields.pod_name.data=key_fields_dict[i]
           elif i == 'org_name':
              f_fields.org_name.data=key_fields_dict[i]
           elif i== 'user_email':
              f_fields.user_email.data=key_fields_dict[i]
           elif i== 'requestor_email':
              f_fields.requestor_email.data=key_fields_dict[i]
           elif i== 'jcc_project_id':
              f_fields.jcc_project_id.data=key_fields_dict[i]
 
    try:
       rec_id=uuid.uuid4()
       requestor_type_val=request.values.get('requestor_type')
       create_jcc_flag_val=eval(request.values.get('create_jcc_flag'))
       create_org_flag_val=eval(request.values.get('create_org_flag'))


       groundplex_name=None
       groundplex_environment=None
       cloudplex_name=None
       cloudplex_environment=None
       hadooplex_name=None
       hadooplex_environment=None
       essential_features={}

       print '>>>>Bool-Cloud:',f_fields.create_cloud.data
       print '>>>>Bool-sidekick:',f_fields.create_sidekick.data
       print '>>>>Bool-hadooplex:',f_fields.create_hadooplex.data

       if f_fields.create_sidekick.data is True:
          groundplex_name='Sidekick - '+f_fields.org_name.data
          groundplex_environment='Sidekick-dev'
       if f_fields.create_cloud.data is True:
          cloudplex_name='Cloud - '+f_fields.org_name.data
          cloudplex_environment='dev'
       if f_fields.create_hadooplex.data is True:
          hadooplex_name='Hadooplex - '+f_fields.org_name.data
          hadooplex_environment='hadooplex-dev'
          essential_features={'spark':'spark'}
       R1=app.SnaplogicOrgRec(create_date_time=date_time, 
                              org_name=f_fields.org_name.data, 
                              pod_name=key_fields_dict['pod_name'], 
                              jcc_project_id=key_fields_dict['jcc_project_id'],
                              user_email=f_fields.user_email.data, 
                              requestor_email=f_fields.requestor_email.data, 
                              requestor_type=requestor_type_val, 
                              record_id=rec_id,
                              premium_snap_list=[],
                              features_list_dict=essential_features,
                              groundplex_environment=groundplex_environment,
                              cloudplex_environment=cloudplex_environment,
                              hadooplex_environment=hadooplex_environment,
                              user_firstname=user_firstname,
                              user_lastname=user_lastname,
                              cloud_plex_name=cloudplex_name,
                              ground_plex_name=groundplex_name,
                              hadoop_plex_name=hadooplex_name,
                              create_sidekick=f_fields.create_sidekick.data,
                              create_cloud=f_fields.create_cloud.data,
                              create_hadooplex=f_fields.create_hadooplex.data,
                              create_jcc_flag=create_jcc_flag_val,
                              create_org_flag=create_org_flag_val,
                              sidekick_keys='',
                              number_of_cloud=f_fields.number_of_cloud.data)
       app.session_id.add(R1)
       app.session_id.commit()
       flash('Success: Record successfully inserted')
       #generate_property_keys(f_fields.org_name.data,key_fields_dict['pod_name'])    #generate the keys and prepare the form
       #flash('Success: Groundplex keys and form successfully created')
       app.session_id.close()
       return redirect("/ListPremiumSnaps/%s/%s"%(key_fields_dict['pod_name'], f_fields.org_name.data))
    except exc.SQLAlchemyError:
       print sys.exc_info()[0]
       syslog.syslog(str(sys.exc_info()[1]))
       flash(sys.exc_info()[0])
       app.session_id.rollback()
    app.session_id.close()
    return render_template('org_input_form.html',form=f_fields,pod_name_menu=pod_name_menu,requestor_type_menu=requestor_type_menu,create_org_menu=create_org_menu, create_jcc_menu=create_jcc_menu,jcc_project_menu=jcc_project_menu)

@appFlask.route('/showRecordsWithKeys',methods=['get','post'])
def displayGroundplexKeys():
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    display_fields=dbUpdateOutputForm()
    db_list=app.session_id.query(app.SnaplogicOrgRec).all()
    selected_records=request.form.getlist('box')
    if len(selected_records) > 0:
       for i in selected_records:
           obj1=app.session_id.query(app.SnaplogicOrgRec).filter_by(record_id=i)
           for k in obj1:
               flash('Keys for Org:'+k.org_name+' in Pod:'+k.pod_name)
               for j in k.sidekick_keys.split('\n'):
                   flash(j) 
    app.session_id.close()
    return render_template('db_groundplex_keys_menu.html',db_list=db_list,form=display_fields)


@appFlask.route('/getUpdatedOrgData',methods=['get','post'])
def get_and_process_updated_org_data():
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    template_title='Org Records Available For Update'
    submit_button='SubmitRecord'
    update_view=True
    pod_name_menu=[None,'prodxl','prodxl2','canaryxl','canaryxl2','uatxl','qa','snap']
    requestor_type_menu=[None,'admin','regular']
    create_org_flag_menu=[None,False,True]
    create_jcc_flag_menu=[None,False,True]
    db_fields=dbUpdateOutputForm()
    special_keys=('pod_name','org_name','user_firstname','user_lastname')
    db_list=app.session_id.query(app.SnaplogicOrgRec).all()
    key_fields_dict={}
    
    #flash('NOTE:')
    #flash('Org Create Status: success | failed | processing | go. If it is go, then the script will create the Org')
    #flash(' ')

    selected_records=request.form.getlist('box')
    for i in selected_records:
       obj1=app.session_id.query(app.SnaplogicOrgRec).filter_by(record_id=i)
      
       key_fields_dict={'jcc_create_status':db_fields.jcc_create_status.data, 
                        'org_create_status':db_fields.org_create_status.data,
                        'org_name':db_fields.org_name.data, 
                        'number_of_cloud':db_fields.number_of_cloud.data,
                        'user_firstname':db_fields.user_firstname.data,
                        'cloudplex_created':db_fields.cloudplex_created.data,
                        'user_lastname':db_fields.user_lastname.data}

       create_org_flag_val=request.values.get('create_org_flag')
       if create_org_flag_val is not None:
          key_fields_dict['create_org_flag']=eval(create_org_flag_val)

       create_jcc_flag_val=request.values.get('create_jcc_flag')
       if create_jcc_flag_val is not None:
          key_fields_dict['create_jcc_flag']=eval(create_jcc_flag_val)

       pod_name_val=request.values.get('pod_name')
       if pod_name_val != 'None':
          key_fields_dict['pod_name']=pod_name_val

       requestor_type_val=request.values.get('requestor_type')
       if requestor_type_val != 'None':
          key_fields_dict['requestor_type']=requestor_type_val

       key_fields_dict,error_message=sanitize_existing_fields_change(key_fields_dict,special_keys,db_fields)

       if len(key_fields_dict) > 0:
          try:
             print '>>>>>LIST:',key_fields_dict
             key_list=key_fields_dict.keys()
             obj1.update(key_fields_dict)  #update the record
             app.session_id.commit()
             flash("DB Status: Org record successfully updated with modified columns: "+','.join(key_list))
          except exc.SQLAlchemyError:
             flash(sys.exc_info()[0])
             app.session_id.rollback()
          app.session_id.close()
       return render_template('db_update_entries_list.html',db_list=obj1,form=db_fields,pod_name_menu=pod_name_menu,requestor_type_menu=requestor_type_menu,create_jcc_flag_menu=create_jcc_flag_menu,create_org_flag_menu=create_org_flag_menu) #only process 1 record 
    app.session_id.close()
    return render_template('db_entries_list.html',db_list=db_list,form=db_fields,template_title=template_title, submit_button_name=submit_button,org_update_view=update_view)

@appFlask.route('/activateScripts',methods=['get','post'])
def getOrgAndJccControls():
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    key_fields_dict={}
    db_fields=SystemControlsForm()
    controls_menu=[None,'False','True']
    db_list=app.session_id.query(app.SnaplogicControlsRec).all()
    for k in db_list:
        print '>>>>K>>>:',k.create_date_time
    if len(db_list)==0:
       try:
          R1=app.SnaplogicControlsRec(create_date_time=datetime.datetime.now(), activate_jcc_creation=False, activate_org_creation=False)
          app.session_id.add(R1)
          app.session_id.commit()
          flash('Success: Record successfully inserted')
       except exc.SQLAlchemyError:
          print sys.exc_info()[0]
          syslog.syslog(str(sys.exc_info()[1]))
          flash(sys.exc_info()[0])
          app.session_id.rollback()
       try:
          R1=app.SnaplogicLockRec(create_date_time=datetime.datetime.now(), block_jcc_creation=True, block_deploy_run=True,attempts_to_get_lock=0)
          app.session_id.add(R1)
          app.session_id.commit()
          flash('Success: SnaplogicLockRec successfully created in DB')
       except exc.SQLAlchemyError:
          print sys.exc_info()[0]
          syslog.syslog(str(sys.exc_info()[1]))
          flash(sys.exc_info()[0])
          app.session_id.rollback()
 
    activate_jcc_creation_val=request.values.get('activate_jcc_creation')
    if activate_jcc_creation_val != 'None' and activate_jcc_creation_val != None:
       key_fields_dict['activate_jcc_creation']=eval(activate_jcc_creation_val)

    activate_org_creation_val=request.values.get('activate_org_creation')
    if activate_org_creation_val != 'None' and activate_org_creation_val != None:
       key_fields_dict['activate_org_creation']=eval(activate_org_creation_val)

    if len(key_fields_dict) > 0:
       try:
          key_fields_dict['update_date_time']=datetime.datetime.now()
          obj1=app.session_id.query(app.SnaplogicControlsRec)
          obj1.update(key_fields_dict)  #update the record
          app.session_id.commit()
          flash("DB Status: System Controls record updated successfully")
       except exc.SQLAlchemyError:
          flash(sys.exc_info()[0])
          app.session_id.rollback()
    app.session_id.close()
    return render_template('system_controls.html',form=db_fields,activate_org_creation_menu=controls_menu,activate_jcc_creation_menu=controls_menu,db_list=db_list)

 
@appFlask.route('/getSpecialUpdatedOrgData',methods=['get','post'])
def get_and_process_special_updated_org_data():
    #--------------------------------------------------------------------------------------
    #-
    #--------------------------------------------------------------------------------------
    template_title=''
    submit_button='SubmitRec'
    update_view=True
    boolean_menu=['None','False', 'True']
    db_fields=dbSpecialUpdateOutputForm()
    special_keys=('user_email', 'requestor_email')
    db_list=app.session_id.query(app.SnaplogicOrgRec).all()
    key_fields_dict={}

    #flash('NOTE:')
    #flash('Org Create Status: success | failed | processing | go. If it is go, then the script will create the Org')
    #flash('Pod name: prodxl | prodxl2 | canaryxl | canaryxl2 | uatxl | qa |snap')
    #flash('Requestor type: admin | regular')
    #flash(' ')

    selected_records=request.form.getlist('box')
    for i in selected_records:
       obj1=app.session_id.query(app.SnaplogicOrgRec).filter_by(record_id=i)

       user_email_val=db_fields.user_email.data
       user_email_val=user_email_val.lower()

       requestor_email_val=db_fields.requestor_email.data
       requestor_email_val=requestor_email_val.lower()

       key_fields_dict={'user_email':user_email_val,'requestor_email':requestor_email_val,'groundplex_environment':db_fields.groundplex_environment.data,
                        'cloudplex_environment':db_fields.cloudplex_environment.data, 'hadooplex_environment':db_fields.hadooplex_environment.data
                       }
       key_fields_dict,error_message=sanitize_existing_fields_change(key_fields_dict,special_keys,db_fields)

       create_sidekick_val=request.values.get('create_sidekick')
       if create_sidekick_val is not None:
          create_sidekick_val=eval(create_sidekick_val)
          if create_sidekick_val is not None:
             key_fields_dict['create_sidekick']=create_sidekick_val

       create_cloud_val=request.values.get('create_cloud')
       if create_cloud_val is not None:
          create_cloud_val=eval(create_cloud_val)
          if create_cloud_val is not None:
             key_fields_dict['create_cloud']=create_cloud_val

       create_hadooplex_val=request.values.get('create_hadooplex')
       if create_hadooplex_val is not None:
          create_hadooplex_val=eval(create_hadooplex_val)
          if create_hadooplex_val is not None:
             key_fields_dict['create_hadooplex']=create_hadooplex_val

       print '>>>>>REC-DATA:',key_fields_dict

       try:
          key_list=key_fields_dict.keys()
          obj1.update(key_fields_dict)  #update the record
          app.session_id.commit()
          flash("DB Status: Org record successfully updated with modified columns: "+','.join(key_list))
       except exc.SQLAlchemyError:
          flash(sys.exc_info()[0])
          app.session_id.rollback()
       app.session_id.close()
       return render_template('db_update_special_entries_list.html',db_list=obj1,form=db_fields,bool_menu=boolean_menu) #only process 1 record
    app.session_id.close()
    return render_template('db_entries_list.html',db_list=db_list,form=db_fields,template_title=template_title, submit_button_name=submit_button,org_update_view=update_view)

#@login_manager.user_loader
#def load_user(user_id):
#    return User.get(user_id)
#
@appFlask.route('/loginTest', methods=['GET', 'POST'])
def login():
    #-------------------------------------------------------------------------------------------------------------
    #- https://pythonspot.com/en/login-authentication-with-flask/
    #- https://flask-login.readthedocs.io/en/latest/_modules/flask_login/utils.html#login_user
    #-------------------------------------------------------------------------------------------------------------
    form = loginForm()
 
    username=str(form.username.data)
    password=str(form.password.data)

    print 'Mysql-account:',app.mysql_account
    user_engine,user_ses=app.connect_to_mysql(app.mysql_account)

    #Session = sessionmaker(bind=engine)
    #user_ses = Session()
    query = user_ses.query(app.UserAuthorizationRec).filter_by(user_login_name=username,user_password=password)

    result = query.first()
    if result:
        session['logged_in'] = True
    else:
        flash('wrong password!')
    #return home()

    return render_template('login.html', form=form)

@appFlask.route("/logout")
def logout():
    session['logged_in'] = False
    return home()

