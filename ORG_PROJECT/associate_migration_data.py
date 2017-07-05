#!/usr/local/bin/python

import os, sys, time
from  glob import *
import argparse

backup_dir='/tmp/BACKUP'
remote_dir='/tmp'
remote_dir='/opt/snaplogic'

#data_file_name='/Users/cseymour/Desktop/KEN_merge_20160726.csv'
#data_file_name= '/Users/cseymour/Desktop/KEN_jcc_list.txt'

#data_file_name= '/Users/cseymour/Desktop/RYCH_jcc_list.txt'


def help():
    return """The sequence of operations should be:\n
Open an input file and put the 2 test servers in it as follows:

('PPPPPPPPPPP', 'prodxl-jcc????.fullsail.snaplogic.com', '1.7.0_17')
('QQQQQQQQQQQQ', 'prodxl-jcc?????.fullsail.snaplogic.com', '1.7.0_17')

Change the "data_file_name" to point to this file


To get started you need to set "backup_dir" to where you will store the backup configs
I made it /tmp/BACKUP.

Set the remote directory where the ../etc files are located. Change "remote_dir" to /opt/snaplogic

Run the script and redirect the output to an output file. The script messes up the terminal display

Eecute the script in the following order:

\t1. Backup the Configs
\t2. Stop the JCCs
\t3. Run Puppet on the individual hosts
\t4. Restore the Config files
\t5. Start the JCCs on each host
"""

def get_backup_dirs(backup_dir):
    dir_list=glob(backup_dir+'/*')
    return dir_list

def get_remote_config_file(host_name):
    destination_dir=backup_dir+'/'+host_name
    os.system("mkdir -p %s"%(destination_dir))
    cmd="""scp -rp -i /Users/cseymour/.ssh/snap-id_rsa  snapuser@%s:/opt/snaplogic/etc %s"""%(host_name,destination_dir)
    print 'Executing:',cmd
    os.system(cmd)

def restore_config_files():
    list_of_dirs=get_backup_dirs(backup_dir)
    for i in list_of_dirs:
       push_files_to_remote(i+'/etc',os.path.basename(i),remote_dir)

def execute_jcc_service_command(remote_command):
    list_of_dirs=get_backup_dirs(backup_dir)
    for j in list_of_dirs:
        hostname=os.path.basename(j)
        cmd="""ssh -t -i /Users/cseymour/.ssh/tectonic4-24-12_rsa ec2-user@%s '%s' """%(hostname,remote_command)
        print 'Executing:',cmd
        os.system(cmd)

def list_java_version(remote_command):
    list_of_dirs=get_backup_dirs(backup_dir)
    for j in list_of_dirs:
        hostname=os.path.basename(j)
        cmd="""ssh -t -i /Users/cseymour/.ssh/tectonic4-24-12_rsa ec2-user@%s '%s' """%(hostname,remote_command)
        print 'Executing:',cmd
        os.system(cmd)

def launch_puppet_command(puppet_command,sleep_seconds,batch_size):
    list_of_dirs=get_backup_dirs(backup_dir)
    for k,j in enumerate(list_of_dirs):
        if ((k+1)%batch_size) > 0:
              print '>>waiting for ',sleep_seconds,'seconds before continuing'
              time.sleep(sleep_seconds)
        hostname=os.path.basename(j)
        cmd="""ssh -t -i /Users/cseymour/.ssh/tectonic4-24-12_rsa ec2-user@%s '%s' """%(hostname,puppet_command)
        print 'Executing:Item:',k+1,'Command:',cmd
        pid=os.fork()
        if pid==0:
           os.system(cmd)
        os._exit()

def fork_launch_puppet(puppet_command_list):
    #-----------------------------------------------------------------------------------------------------------------------
    #
    #-----------------------------------------------------------------------------------------------------------------------
    x={}
    y={}
    pid={}
    puppet_pid_list=[]
    pipes_to_read=[]
    for k,command in enumerate(puppet_command_list):
        x[k],y[k]=os.pipe()
        pid[k]=os.fork()
        if pid[k]==0:
           os.close(x[k])
           try:
              print '******Executing:Item:',k+1,'\n\t>>>Command:',command
              results=os.popen(command).read()
           except:
              results=sys.exc_info()[1]
              syslog.syslog(str(sys.exc_info()[1]))
           fd=os.fdopen(y[k],'w',0)
           fd.write('******'+command+'\n')
           fd.write(results)
           os._exit(0)
        else:
           puppet_pid_list.append(pid[k])
           pipes_to_read.append(x[k])
           os.close(y[k])
    return puppet_pid_list, pipes_to_read


def backup_config_files():
    unique_org_pod_set=set()
    for record in open(data_file_name):
       unique_org_pod_set.add(record.strip())

    for element in unique_org_pod_set:
        org_name,host_name, java_version=eval(element)
        if host_name is not None:
           print '>>>>Connecting to host:',host_name
           get_remote_config_file(host_name)

def push_files_to_remote(source_dir,host_name,remote_dir):
    cmd="""scp -rp -i /Users/cseymour/.ssh/snap-id_rsa  %s snapuser@%s:%s"""%(source_dir,host_name,remote_dir)
    print '>>>',cmd
    os.popen(cmd)
    

if __name__ == '__main__':
   if len(sys.argv) == 1:
      print help()
      sys.exit()
   parser=argparse.ArgumentParser(description='Script to help with the migration of Java from 1.7 to 1.8')
   parser.add_argument('-b', action='store_true', help='Backup the /opt/snaplogic/etc files')
   parser.add_argument('-r', action='store_true',  help='Restore the /opt/snaplogic/etc files"')
   parser.add_argument('-s', action='store_true', help='Stop the JCC service on the nodes')
   parser.add_argument('-a', action='store_true', help='Start the JCC process on the node')
   parser.add_argument('-p', action='store_true', help='Run the Puppet command ')
   parser.add_argument('-l', action='store_true', help='List the Java version ')
   args=parser.parse_args()

   if args.b is True:
      backup_config_files()
   elif args.r is True:
      restore_config_files()
   elif args.s is True:
      #execute_jcc_service_command('sudo hostname') 
      execute_jcc_service_command('sudo service jcc stop')    #stop jcc service
   elif args.a is True:
      #execute_jcc_service_command('sudo pwd')  
      execute_jcc_service_command('sudo service jcc restart')    #start jcc service
   elif args.l is True:
      #execute_jcc_service_command('sudo pwd')
      list_java_version('sudo ls -al /opt/java')    #start jcc service
   elif args.p is True:
      sleep_seconds=3
      batch_count=1
      command_list=[]
      puppet_command='whoami'
      puppet_command='sudo puppet agent --test --environment=prod'
      list_of_dirs=get_backup_dirs(backup_dir)
      for k,j in enumerate(list_of_dirs):
          if ((k+1)%batch_count) == 0:
             pids,pipes_to_read=fork_launch_puppet(command_list)
             for ret_pipe in pipes_to_read:
                 fd=os.fdopen(ret_pipe,'r',0)
                 z=fd.read()
                 print '>>>RESULTS:\n\t', z   

             print '>>>',pids
             print '>>Waiting for PIDs to complete in sub-processes'
             for i in pids:
                 the_pid, pid_results=os.waitpid(i,0)
                 print '>>>>>PID:',the_pid,'Results:',pid_results
             print '>>>Waiting for ',sleep_seconds,'..'
             time.sleep(sleep_seconds)
             command_list=[]
          hostname=os.path.basename(j)
          cmd="""ssh -t -i /Users/cseymour/.ssh/tectonic4-24-12_rsa ec2-user@%s '%s' """%(hostname,puppet_command)
          command_list.append(cmd)
      if len(command_list) > 0:
         pids,pipes_to_read= fork_launch_puppet(command_list)
         for ret_pipe in pipes_to_read:
             fd=os.fdopen(ret_pipe,'r',0)
             z=fd.read()
             print '>>>RESULTS:\n\t', z
         for i in pids:
             the_pid, pid_results=os.waitpid(i,0)
             print '>>>>>PID:',the_pid,'Results:',pid_results
         print pids


      #pid_list,pipes=fork_launch_puppet('whoami',sleep_seconds,batch_count)
      #launch_puppet_command('sudo puppet agent --test --environment=prod')
      #print pid_list

