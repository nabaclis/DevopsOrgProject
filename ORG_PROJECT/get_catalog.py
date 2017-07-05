#!/usr/local/bin/python

import os, sys

import slutils.sladmin
import slcommon.schema_manager
import slcommon.sl_exceptions
import slcommon.uri_utils
import slserver.test
import sltest
import snapi.snapi_admin
import snapi.snapi_asset
import snapi.snapi_audit
import snapi.snapi_catalog
import snapi.snapi_context
import snapi_base.exceptions
import snapi_base.keys as keys

from slcommon.jsonpath import JsonPath

def get_premium_snaps(org_name, sysadmin_snapi_snap_pack):
    snap_list_dict={}

    org_snid=asset_api.lookup_org(org_name)['snode_id']
    subs = sysadmin_snapi_snap_pack.check_subscriptions(org_snid)[keys.SNAP_PACK_SUBSCRIPTIONS]
    for i in subs:
        snap_list_dict[i['snap_pack_label']]=i
    return snap_list_dict

def modify_subscription(org_name, sysadmin_snapi_snap_pack, subs):
    #########################################################################

    org_snid=asset_api.lookup_org(org_name)['snode_id']
    sysadmin_snapi_snap_pack.modify_subscriptions(org_snid, {keys.SNAP_PACK_SUBSCRIPTIONS: subs})


def get_subscription(org_name, sysadmin_snapi_snap_pack):
    #########################################################################
    subscribed_snap_list=[]

    org_snid=asset_api.lookup_org(org_name)['snode_id']
    subs = sysadmin_snapi_snap_pack.check_subscriptions(org_snid)[keys.SNAP_PACK_SUBSCRIPTIONS]
    for i in subs:
        print i
        if i['is_sub']==True:
            subscribed_snap_list.append(i['snap_pack_label'])
    return subscribed_snap_list
    #########################################################################

    #cat_snode = snapi_asset.lookup_and_check_asset(
    #    None, keys.ASSET_READ_PERM, '/internal/catalogs/Catalog/catalog', keys.ASSET_TYPE_CATALOG)
    #catalog = snapi.snapi_asset.get_catalog(cat_snode[keys.ASSET_SNODE_ID])
#
#    # subscribe
#    subs[0][keys.SNAP_PACK_IS_SUB] = True
#    sysadmin_snapi_snap_pack.modify_subscriptions(org_snid, {keys.SNAP_PACK_SUBSCRIPTIONS: subs})
#    subs = sysadmin_snapi_snap_pack.check_subscriptions(org_snid)[keys.SNAP_PACK_SUBSCRIPTIONS]
#    assertTrue(subs[0][keys.SNAP_PACK_IS_SUB])
#
#    premium_pack_path = '/premium/snaps/%s' % (subs[0][keys.SNAP_PACK_LABEL],)
#    snapi_asset.lookup_and_check_asset(
#        'catalog@catalog.com', keys.ASSET_READ_PERM, premium_pack_path, keys.ASSET_TYPE_DIR)
#    catalog = snapi_catalog.get_catalog(cat_snode[keys.ASSET_SNODE_ID])
#    assertEqual(1, len(catalog[keys.CATALOG_SUBS]))

if __name__ == '__main__':
   if len(sys.argv) > 2:
      config_file=None
      org_name='/%s'%sys.argv[1]
      pod_prefix=sys.argv[2]
      admin_name, api_key, admin_uri = slutils.sladmin.init_sladmin(pod_prefix, config_file)
      session = snapi.snapi_request.SnapiRequest(admin_name, api_key)
      asset_api = snapi.snapi_asset.SnapiAsset(session, admin_uri)

      sysadmin_context = snapi.snapi_context.SnapiContext(admin_name,
                                                        api_key,
                                                        admin_uri,
                                                        sldb_uri=admin_uri)

      sysadmin_snapi_snap_pack = sysadmin_context.schema_manager


      #list_org_subscribe_snaps(org_name)
      #org_subscriptions=get_subscription(org_name, sysadmin_snapi_snap_pack)
      #print org_subscriptions

      premium_snaps_dict=get_premium_snaps(org_name, sysadmin_snapi_snap_pack)
      premium_snaps_dict_sorted=premium_snaps_dict.keys()
      premium_snaps_dict_sorted.sort()
      print premium_snaps_dict_sorted
      for i in premium_snaps_dict_sorted:
          print '\t',i
      for i in premium_snaps_dict:
          print i,'==>',premium_snaps_dict[i]

      x={'is_sub': False, 'snap_pack_label': 'Reltio', 'versions': [{'pack_build_tag': 'reltio-snap-1', 'org_build_tag': None, 'premium_build_tag': 'dummy', 'pack_vqid': 'reltio-snap-1'}]}
      x={'is_sub': True, 'snap_pack_label': 'Google Spreadsheet', 'versions': [{'pack_build_tag': 'spreadsheet-snap-1', 'org_build_tag': None, 'premium_build_tag': 'dummy', 'pack_vqid': 'spreadsheet-snap-1'}]}
      #modify_subscription(org_name, sysadmin_snapi_snap_pack, [x])
   else:
      print 'org-name and pod-name required...'
