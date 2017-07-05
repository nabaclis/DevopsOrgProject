#!/bin/bash

master_dir='/Users/cseymour/claude_scripts/ORG_PROJECT/JAVA1.8-MIGRATION-DIR'
backup_dir='/tmp/backup-config'
output_dir='/tmp/OUT-DIR'

for i in $(ls $backup_dir); do
    diff -r $master_dir/etc  $backup_dir/$i |grep -v api_key|grep -v username|grep -v subscriber_id|grep -v 'cc: Generated'|grep -v 'diff -r'|grep -v '^---'|grep -v "^[0-9]"|grep -v "^< $"| grep -v "^< #" > /tmp/OUT-DIR/$i
done

for i in $(ls $output_dir/*); do
    if [ $(cat $i|wc -l) -gt 0 ]; then
       echo `basename $i`
    fi
       
done
    
