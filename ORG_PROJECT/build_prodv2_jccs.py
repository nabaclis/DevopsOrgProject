#!/usr/local/bin/python

#http://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Subnet.create_instances

import os, sys

from  datetime import datetime

import boto3

#ec2.create_instances(ImageId='<ami-image-id>', MinCount=1, MaxCount=5)
#     test or add to command: SecurityGroups=['secgroup', ..]
#        test InstanceType="c3.xlarge"

config_file='/Users/cseymour/.aws/config'
config_region=[]

for i in open(config_file):
    i=i.strip()
    if len(i) > 0 and i[0]=='[' and i.find('profile') >= 0:
       i=i.replace('[','')
       i=i.replace('profile','')
       i=i.replace(' ','')
       if i.find(']') >= 0:
          i=i.replace(']','')
       config_region.append(i)


chef_command="""sudo chef-client -o "role[sl_techops_prodv2_jcc_servers]" """
SQL="""select sl_dns_name, internal_ip from aws_instances where data_collection_date_time=(select max(data_collection_date_time) from aws_instances) and sl_dns_name like  'pa23sl-jccs-%';"""

def help():
    #------------------------------------------------------------------------------------------------
    #
    #------------------------------------------------------------------------------------------------
    print '-->Build instance using Boto'
    print '-->SSh to instance and run the Chef command above'
    print '-->Generate Groundplex keys for the Org and copy to /opt/snaplogic/etc/keys.properties'
    print '-->Make a provisioned.properties file and copy to /opt/snaplogic/etc/provisioned.properties'


if __name__ == '__main__':
   print 'Hello world...'
   help()
