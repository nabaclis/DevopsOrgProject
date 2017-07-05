#!/usr/local/bin/python

import simplejson
import os, sys, syslog, datetime
import slutils.sladmin
import snapi.snapi_request
import snapi.snapi_asset
import argparse
import app.common_org_utility_functions

def add_new_user_to_system(pod_admin_user,a_username,f_name,l_name,org_path,is_admin):
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    config_file = None
    settings=None
    disallowed_auth=None

    admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_admin_user, config_file)
    session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
    asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)

    try:
      asset_api.create_user(None, a_username, f_name, l_name, org_path, is_admin)      
      print 'Sucessfully added user:',a_username
      return ('Sucessfully added user:'+a_username+' to the POD and Org...')
    except:
      x=str(sys.exc_info()[1]).split(':')[-2]
      results=x[:x.find('}')]
      print results
      return results
      
    
def find_user(pod_admin_user, a_username,flag):
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    config_file = None
    admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_admin_user, config_file)
    session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
    asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)

    try:
      if flag=='verify':
         asset_api.get_user(None, a_username)['username']
         return True
      elif flag=='details':
         x=asset_api.get_user(None, a_username)
         return x
      elif flag=='orgs':
         x=asset_api.get_user(None, a_username)
         return x
    except:
      print 'Username:',a_username,'is not in pod'
      return False

def delete_user_from_org(pod_admin_user, org_name, user_name):
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    user_type=''
    config_file=None
    error_messages=[]

    admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_admin_user, config_file)
    session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
    asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)

    user_type=None
    try:
       print '>>>>>>Removing user:'+user_name+' from Org:'+org_name
       asset_api.remove_user_from_phorg(None, user_name, org_name)
       return 'Removed user:'+user_name+' from Org:'+org_name
    except:
       print 'Warning: '+user_name+':'+str(sys.exc_info()[1]).split(':')[-2]
       syslog.syslog('Warning: '+user_name+':'+str(sys.exc_info()[1]).split(':')[-2])
       error_messages.append('Warning: '+user_name+':'+str(sys.exc_info()[1]).split(':')[-2])
       return error_messages

def add_user_to_group(pod_admin_user, org_name,user_group,user_name):
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    config_file=None

    admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_admin_user, config_file)
    session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
    asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)

    try:
      group_members=asset_api.get_group(None, '/'+org_name,user_group)['members']
      group_members.append(user_name)
      asset_api.update_group(None,'/'+org_name, user_group,group_members)
      return 'Added user:'+user_name+' to org:'+org_name+' and group:'+group_name
    except:
      print 'Could not add user:'+user_name+' to org:'+org_name+' and group:'+group_name
      return 'Could not add user:'+user_name+' to org:'+org_name+' and group:'+group_name

def add_users_to_org(pod_admin_user, org_name, user_name, user_group):
    #---------------------------------------------------------------------------------------------------
    #-
    #---------------------------------------------------------------------------------------------------
    config_file=None
    error_messages=[]

    admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_admin_user, config_file)
    session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
    asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)

    try:
       asset_api.add_user_to_phorg(None, user_name, org_name)     #first add the user to the Org
       #get current admin users and add new user to the list
       add_user_to_group(pod_admin_user, org_name,user_group,user_name)
       return 'Successfully added user:'+user_name+' to org:'+org_name+' and user group:'+user_group
    except:
       #print 'Warning: '+user_name+':'+str(sys.exc_info()[1]).split(':')[-2]
       syslog.syslog('Warning: '+user_name+':'+str(sys.exc_info()[1]))
       error_messages.append('Warning: '+user_name+':'+str(sys.exc_info()[1]))
       return error_messages

def do_user_processing(process_request, username, pod_name, feature, org=None, process_type=None):
   #---------------------------------------------------------------------------------------------------
   #-
   #---------------------------------------------------------------------------------------------------
   devops_admin_users={}
   pod_admin_user, the_uri=app.common_org_utility_functions.get_pod_admin_user(pod_name)
   if process_request=='GET_USER':
      response=find_user(pod_admin_user, username,feature)
      if response != False:
         if feature == 'verify':
            print 'User:',username,'exists...'
            return 'User:'+username+' exists...'
         elif feature == 'details':
            print 'User details:'
            return response
            #for i in response:
            #    print i,'==>',response[i]
         elif feature == 'orgs':
            print 'User exists in the following orgs:'
            return response['subscriber_ids']
            #for i in response['subscriber_ids']:
            #    print '\t',i
      else:
         return 'Username:'+username+' is not in pod' 
   elif process_request=='ADD_USER':
      print 'In ADD_USER routine...'
      response=find_user(pod_admin_user, username,'verify')
      if response:
         response=find_user(pod_admin_user, username,'details')
         if response != False:
            if response['groups'].has_key('/'+org):
               if process_type in response['groups']['/'+org]: 
                  print username+' is in group '+process_type+' so there is nothing to do'
                  return username+' is in group '+process_type+' so there is nothing to do'
               else:
                  print username+' is NOT in group '+process_type+' so ADDing it to the group...'
                  results=add_user_to_group(pod_admin_user, '/'+org,process_type,username)
                  return results
            else:
               print username+' is NOT part of the Org:'+org+' so adding'
               results=add_users_to_org(pod_admin_user, org, username,process_type) 
               return results
      else:
         print '>>>Add user to the system and Org...'
         a_name=username.split('@')[0]
         l_name=a_name[1:]
         f_name=a_name[0]
         results=add_new_user_to_system(pod_admin_user,username,f_name,l_name,org, True if process_type=='admins' else False)
         return results
   elif process_request=='REMOVE_USER':
      print 'In REMOVE_USER routine...'
      if find_user(pod_admin_user, username,'verify') == True:
         if '/'+org in find_user(pod_admin_user, username,'details')['subscriber_ids']:
            print 'Deleting user',username,'from Org:',org
            results=delete_user_from_org(pod_admin_user, org, username)
            print results
            return results
      else:
         print 'User:'+username+' does not exist so delete cannot be done...'
         return 'User:'+username+' does not exist so delete cannot be done...'
   elif process_request=='CREATE_USER':
      print 'Add new user to the system and org...'
      add_new_user_to_system(pod_admin_user,username,firstname,lastname,org,True if process_type=='admins' else False)


