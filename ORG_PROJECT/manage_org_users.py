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
    except:
      x=str(sys.exc_info()[1]).split(':')[-2]
      print x[:x.find('}')]
    
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

    group_members=asset_api.get_group(None, '/'+org_name,user_group)['members']
    group_members.append(user_name)
    asset_api.update_group(None,'/'+org_name, user_group,group_members)

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
    except:
       print 'Warning: '+user_name+':'+str(sys.exc_info()[1]).split(':')[-2]
       syslog.syslog('Warning: '+user_name+':'+str(sys.exc_info()[1]).split(':')[-2])
       error_messages.append('Warning: '+user_name+':'+str(sys.exc_info()[1]).split(':')[-2])
       return error_messages

if __name__ == '__main__':
   pod_admin_user=''

   parser=argparse.ArgumentParser(description='This program is used to add/delete users to orgs in (prod| canary|qapod|uatxl)')
   subparsers=parser.add_subparsers(help='User sub-parser')
   
   parser.add_argument('-u', '--username', required=True, help='Username (email address) of the Org user')
   parser.add_argument('-p',required=True,choices=['salespod','spark','auditpod','budgy','qa','snapxl','perf','prod','canary','qapod','uat','portal','ux','ux2','ux3','prov-sldb','dev-sldb','stage'],help='The POD where the Org belongs')
   
   check_user_name=subparsers.add_parser('GET_USER')

   add_org_user=subparsers.add_parser('ADD_USER')
   create_new_user=subparsers.add_parser('CREATE_USER')
   delete_org_user=subparsers.add_parser('REMOVE_USER')

   add_org_user.add_argument('-o','--org',required=True, help='This specifies the Org name')
   add_org_user.add_argument('-t','--type',required=True, choices=['admins','members'], help='This specifies the type of user')
   create_new_user.add_argument('-o','--org',required=True, help='This specifies the Org name')
   create_new_user.add_argument('-t','--type',required=True, choices=['admins','members'], help='This specifies the Org type')
   create_new_user.add_argument('-f','--firstname',required=False, help='This specifies the first name')
   create_new_user.add_argument('-l','--lastname',required=False, help='This specifies the last type')
   check_user_name.add_argument('-f','--feature',choices=['verify','details','orgs'],required=True, help='Lists how much user info should be displayed')

   delete_org_user.add_argument('-o','--org',required=True, help='This specifies the Org name')

   delete_org_user.set_defaults(which='REMOVE_USER')
   create_new_user.set_defaults(which='CREATE_USER')
   add_org_user.set_defaults(which='ADD_USER')
   check_user_name.set_defaults(which='GET_USER')

   args=parser.parse_args()
   
   devops_admin_users={}

   pod_admin_user, the_uri=app.common_org_utility_functions.get_pod_admin_user(args.p)
   print '>>>>>USER:',pod_admin_user

   if args.which=='GET_USER':
      response=find_user(pod_admin_user, args.username,args.feature)
      if response != False:
         if args.feature == 'verify':
            print 'User:',args.username,'exists...'
         elif args.feature == 'details':
            print 'User details:'
            for i in response:
                print '>>>>KEY:',i,'\t==>',response[i]
         elif args.feature == 'orgs':
            print 'User exists in the following orgs:'
            for i in response['subscriber_ids']:
                print '\t',i
   elif args.which=='ADD_USER':
      print 'In ADD_USER routine...'
      response=find_user(pod_admin_user, args.username,'verify')
      if response:
         response=find_user(pod_admin_user, args.username,'details')
         if response != False:
            if response['groups'].has_key('/'+args.org):
               if args.type in response['groups']['/'+args.org]: 
                  print args.username+' is in group '+args.type+' so there is nothing to do'
               else:
                  print args.username+' is NOT in group '+args.type+' so ADDing it to the group...'
                  add_user_to_group(pod_admin_user, '/'+args.org,args.type,args.username)
            else:
               print args.username+' is NOT part of the Org:'+args.org+' so adding'
               add_users_to_org(pod_admin_user, args.org, args.username,args.type) 
      else:
         print '>>>Add user to the system and Org...'
         a_name=args.username.split('@')[0]
         l_name=a_name[1:]
         f_name=a_name[0]
         add_new_user_to_system(pod_admin_user,args.username,f_name,l_name,args.org, True if args.type=='admins' else False)
   elif args.which=='REMOVE_USER':
      print 'In REMOVE_USER routine...'
      if find_user(pod_admin_user, args.username,'verify') == True:
         if '/'+args.org in find_user(pod_admin_user, args.username,'details')['subscriber_ids']:
            print 'Deleting user',args.username,'from Org:',args.org
            delete_user_from_org(pod_admin_user, args.org, args.username)
   elif args.which=='CREATE_USER':
      print 'Add new user to the system and org...'
      add_new_user_to_system(pod_admin_user,args.username,args.firstname,args.lastname,args.org,True if args.type=='admins' else False)


