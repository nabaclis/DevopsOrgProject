#!/bin/bash 

#if [ $# -eq 0 ]; then
#   echo Use: $0 'AWS VEGAS'
#   exit
#fi

#Add the multiplicity of paths for Python to find them
source /home/orguser/cron_python_script_paths.sh

vpn_started=No

passphrase=hpYnvtgyi3f27apyZB@fJm#ZxTDbfm
a_date=$(date "+%Y-%m-%dTIME-%H-%M-%S")
eval `ssh-agent` >/tmp/ssh-agent-pid.${a_date}
#ssh-add /home/orguser/.ssh/sl_root_access.pem < /home/orguser/ORG_PROJECT/SSH-PASSPHRASE.txt
expect << EOF
  spawn ssh-add /home/orguser/.ssh/sl_root_access.pem
  expect "Enter passphrase"
  send "${passphrase}\r"
  expect eof
EOF

datacenters='AWS VEGAS'
script_dir='/home/orguser/ORG_PROJECT'
open_vpn_pid_file=/tmp/SL-MetaPOD-MISC77.ovpn-$(basename $0)-${a_date}.pid

sudo rm -rf /tmp/CONFIG_BACKUP_DIR.*
mkdir /tmp/CONFIG_BACKUP_DIR.${a_date}

echo '>>>Started data collection at '$(date)

for k in ${datacenters}; do
    echo '>>>Getting data for environment:'${k}
    if [ "${k}" = "AWS" -o "${k}" = "aws" ]; then 
       echo '>>>Gathering AWS config files...'
       remote_user='centos'
       pod_name=prodv2
       PEM="-i ${HOME}/.ssh/aws-ec2-west2-user.pem"
       node_list=($("${script_dir}"/manage_project_jccs.py  -p prodv2 LIST_JCCS -f all|awk -F, '{print $3"|"$4}'|sed -ne s/\'//gp|sed -ne 's/ //gp'))  #get hostname and ip address pair
       sudo /usr/sbin/openvpn --config /home/orguser/.open_vpn/SL-PRODv2-JCCFM-VPN.ovpn --writepid ${open_vpn_pid_file} 2>/dev/null >/dev/null&
    elif [ "${k}" = "VEGAS" -o "${k}" = "vegas" ]; then
       echo '>>>Gathering VEGAS config files...'
       remote_user='cloud'
       PEM=''
       pod_name=SL_PROD_23_001
       node_list=($("${script_dir}"/manage_project_jccs.py  -p SL_PROD_23_001 LIST_JCCS -f all|awk -F, '{print $3"|"$4}'|sed -ne s/\'//gp|sed -ne 's/ //gp'))  #get hostname and ip address pair
       sudo /usr/sbin/openvpn --config /home/orguser/.open_vpn/SL-MetaPOD-MISC77.ovpn --writepid ${open_vpn_pid_file} 2>/dev/null >/dev/null& 
    else
       echo '>>>Nothing to do...'
       exit
    fi
    echo 'Starting Open VPN...'
    vpn_started=Yes
    for x in "${node_list[@]}"; do
        remote_host=($(echo "${x}"|awk -F\| '{print $1,$2}'))    #get hostname , ip pair
        echo '>>>Collecting data from:' "$1" ${remote_host[0]}
        config_tar_file=/tmp/"${remote_host[0]}"_properties_backup.${a_date}.tgz
        echo '>>>>'ssh -tt ${PEM} -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${remote_user}@${remote_host[1]} "if ls /opt/snaplogic/etc/*.properties >/dev/null 2>/dev/null; then sudo rm -f /tmp/*jccs-*_properties_backup\.*TIME*.tgz; sudo tar cvzf \"${config_tar_file}\" /opt/snaplogic/etc/*.properties; fi" 
        ssh -tt ${PEM} -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${remote_user}@${remote_host[1]} "if ls /opt/snaplogic/etc/*.properties >/dev/null 2>/dev/null; then sudo rm -f /tmp/*jccs-*_properties_backup\.*TIME*.tgz; sudo tar cvzf \"${config_tar_file}\" /opt/snaplogic/etc/*.properties; fi"
        echo '>>>>>>>>'scp ${PEM} -o StrictHostKeyChecking=no ${remote_user}@${remote_host[1]}:${config_tar_file} /tmp/CONFIG_BACKUP_DIR.${a_date}
        scp ${PEM} -o StrictHostKeyChecking=no ${remote_user}@${remote_host[1]}:${config_tar_file} /tmp/CONFIG_BACKUP_DIR.${a_date}
    done
    echo '>>>'Killing VP at cat ${open_vpn_pid_file}
    sudo kill $(cat ${open_vpn_pid_file})  #kill the running VPN started above
    sudo rm ${open_vpn_pid_file}     #remove the pid file
done

echo '>>>Ended data collection at '$(date)
echo '>>>Started Loading the Config files in the Db at '$(date)
"${script_dir}"/load_configs_to_db.py /tmp/CONFIG_BACKUP_DIR.${a_date} "${pod_name}"

echo '>>>Ended loading configs at '$(date)
/home/orguser/ORG_PROJECT/manage_org_names.sh        #now resolve the Org names vs the JCC instances in the Db

if [ -f /tmp/ssh-agent-pid.${a_date} ]; then
   ssh_agent_pid=$(cat /tmp/ssh-agent-pid.${a_date}|awk '{print $3}')
   echo 'Killing the ssh-agent sub-process...'
   sudo kill ${ssh_agent_pid}
   echo 'Removing the PID file for the ssh-agent sub-process...'
   sudo rm /tmp/ssh-agent-pid.${a_date}
fi

