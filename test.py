# -*- coding: utf-8 -*-
# !/usr/bin/python
'''
author : c00228811
date   : 2017.01
'''
import os,sys,copy,time
import pwd

reload(sys)
sys.setdefaultencoding('utf-8')

tmpFile='right_tmp.txt'
tmpFile2='child_right_tmp.txt'
result_file='result.txt'
fileList=[]
result=[]
callList=[]
white_list=['/usr/bin/facter', '/usr/bin/keepalived', '/usr/bin/puppet']
dir_white_list=['/etc/sudoers', '/opt/controller/ha/', '/etc/profile']

class TraceLog:
    __fp = None
    def __init__(self,fname='trace.txt'):
        self.__fp = open(fname,'w')
        self.trace("#"*100,False)
    def trace(self,s,b=True):
        #if b:
            #print s
        t = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
        self.__fp.writelines(t+" | "+s+'\n')
        self.__fp.flush()
    def __del__(self):
        self.__fp.close()

def printlist(list):
    print '=======================Begin==============================='
    for e in list:
        print e
    print '=======================End================================='

def write_result(list):
    file=open(result_file,'wb')
    for e in list:
        file.write(e+"\n")
    file.close()

def check_exist(list):
    tmp_list=copy.deepcopy(list)
    for e in list:
        if os.path.exists(e) == False:
            result.append("file is not exist, "+e)
            tmp_list.remove(e)
    print "check_exist finished."
    return tmp_list

def check_right(list):
    tmp_list=copy.deepcopy(list)
    for e in list:
        stat_info=os.stat(e)
        uid=stat_info.st_uid
        if pwd.getpwuid(uid)[0] != 'root':
            result.append("file's right is not root, "+e)
            tmp_list.remove(e)
    print "check_right finished."
    return tmp_list
	
def check_parent_right(list):
    tmp_list=copy.deepcopy(list)
    for e in list:
        res=check_dir_right(e)
        if res.find('non-root') != -1:
            result.append("file's parent dir is not root, "+e+", "+res)
            tmp_list.remove(e)
    print "check_parent_right finished."
    return tmp_list			

def check_dir_right(path):
    log.trace("check_dir_right | path is "+path+".")
    dirIndex=path.rfind('/')
    if dirIndex == 0 or dirIndex == -1:
        log.trace("check_dir_right | no / found.")
        return 'True'
    if path in dir_white_list:
        log.trace("check_dir_right | e in dir_white_list.")
        return 'True'
    path=path.replace(';','\;')
    cmdline1='stat -c %U '+path
    cmdline2='stat -c %G '+path
    log.trace("check_dir_right | cmdline1 : "+cmdline1)
    log.trace("check_dir_right | cmdline2 : "+cmdline2)
    str1=os.popen(cmdline1).read()
    str2=os.popen(cmdline2).read()
    if str1.find('root') != -1 and str1.find('db_root') == -1 and str2.find('root') != -1:
        log.trace("check_dir_right | root dir, check parent dir.")
        return check_dir_right(path[0:dirIndex])
    elif str1 == '':
        log.trace("check_dir_right | No such file or dir: "+str1)
        return 'True'
    else:
        return 'non-root dir: '+path
		
def check_system_command(list):
    tmp_list=copy.deepcopy(list)
    for e in list:
        if e.startswith("/bin") or e.startswith("/usr") or e.startswith("/sbin"):
            if e not in white_list:
                result.append("system command in /etc/sudoers, "+e)
    print "check_system_command finished."
    return tmp_list

def check_root_file(argv):
    dirs=['/opt/controller', '/etc/puppet', '/etc/nginx', '/opt/gaussdb', '/opt/gaussdb_local']
    log.trace("argv is : "+argv)
    if argv != '':
        dirs=argv.split(';')
    root_file_list=[]
    for dir in dirs:
        cmdline="find "+dir+" -type f -user root -executable -print0|xargs -0 -i ls -al \"{}\"|awk '{print $NF}' > "+tmpFile
        log.trace("check_root_file | cmdline is : "+cmdline)
        os.popen(cmdline)
        file=open(tmpFile,'r')
        for line in file.readlines():
            line=line.strip().replace("\n", "")
            log.trace("check_root_file | line is : "+line)
            res=check_dir_right(line)
            log.trace("check_root_file | res is : "+res)
            if res.find('non-root') != -1:
                result.append("root file in app dir , "+line)
            res=check_child_right(line, ' -> ')
            log.trace("check_root_file | res is : "+str(res))
            if str(type(res)).find('NoneType') != -1:
                continue
            if res.find('not exist') != -1 or res.find('not root') != -1:
                result.append("child file is error, "+line+", "+res)
    print "check_root_file finished."

def check_child(list):
    for e in list:
        res=check_child_right(e, ' -> ')
        if str(type(res)).find('NoneType') != -1:
            continue
        if res.find('not exist') != -1 or res.find('not root') != -1:
            result.append("child file is error, "+e+", "+res)
    print "check_child finished."
	
def check_child_right(e, printstr):
    log.trace("check_child_right | e is : "+e)
    if e in callList:
        log.trace("check_child_right | dead call")
    else:
        log.trace("check_child_right | no cycle, "+str(callList))
        callList.append(e)

    stuffix=['.sh','.rb','.py']
	
    dirIndex=e.rfind('/')
    if dirIndex == 0 or dirIndex == -1:
        log.trace("check_child_right | no / found.")
        return
    if e in dir_white_list:
        log.trace("check_child_right | in white list.")
        return

    for stu in stuffix:
        cmdline="grep -E \"^.*\\"+stu+"\" "+e+" > "+tmpFile2
        log.trace("check_child_right | cmdline is : "+cmdline+".")
        os.popen(cmdline)
        file=open(tmpFile2,'r')
        for line in file.readlines():
            if line.find('su - ') != -1 or line.find('/etc/sudoers') != -1:
                continue
            strA=line.strip().replace('"', ' ').replace('\'', ' ').split(' ')
            log.trace("check_child_right | strA is : "+str(strA)+".")
            for strB in strA:
                if strB.find('/') != -1:
                    #read the environment sets and output the file's real path
                    cmdline="source /etc/profile;export GSDB_SRC_HOME=/opt/controller/gaussdb;export TargetPath=/opt/controller/ha/ha-puppetmaster/ha/;export ha_module_root=/opt/controller/ha/ha-localdb/ha/module;echo "+strB
                    strB=os.popen(cmdline).read()
                    if strB.find('./') != -1:
                        print "check_child1:"+strB
                        filename=strB.split('./')[-1]
                        cmdline="dirname "+e
                        print "check_child2:"+cmdline
                        strB=os.popen(cmdline).read()+"/"+filename
                        print "check_child3:"+strB
                    sh_file=strB.replace("\n", "")
                    log.trace("check_child_right | sh_file is : "+sh_file+".")
                    if e == sh_file:
                        continue
                    if os.path.exists(sh_file) == False: #not exist files, check dir right
                        stat_info=check_dir_right(sh_file)
                        log.trace("check_child_right | not exist files, stat_info is "+stat_info)
                        if stat_info.find('True') == -1:
                            return e+printstr+sh_file+", not exist"
                    stat_info=check_dir_right(sh_file) #exist files, check dir right
                    log.trace("check_child_right | exist files, stat_info is "+stat_info)
                    if stat_info.find('True') != -1:
                        retr=check_child_right(sh_file, printstr) #dir right is ok, check child file
                        log.trace("check_child_right | retr is "+str(retr))
                        if str(type(retr)).find('NoneType') != -1:
                            continue
                        return e+printstr+str(check_child_right(sh_file, printstr))
                    else:
                        return e+printstr+sh_file+", not root"
	
def check_env_variables():
    #os.system('source /etc/profile')
    cmdline='source /etc/profile;echo $PATH'
    res=os.popen(cmdline).read().replace('\n','').strip()
    strA=res.split(':')
    flag=False
    for i in range(1,len(strA)+1):
        strB=strA[-i]
        if flag == True and strB  == '.':
            result.append("environment variable is error, "+strB)
        else:
            stat_info=check_dir_right(strB)
            if stat_info.find('True') != -1:
                flag=True
            if flag == True and stat_info.find('non-root') != -1:
                result.append("environment variable is error, "+stat_info)

def check_process(list = []):
    tmp_list=get_process()
    monitor_list=copy.deepcopy(list)
    for e in tmp_list:
        e=e.strip()
        res=check_dir_right(e)
        if res.find('non-root') != -1:
            if e in monitor_list:
                monitor_list.append(e)
            result.append("app file used by root process  , "+e)
            print "app file used by root process  , "+e
    return monitor_list

def check_os_config():
    cmdline="grep ALWAYS_SET_PATH /etc/default/su > "+tmpFile
    os.popen(cmdline)
    file=open(tmpFile,'r')
    for line in file.readlines():
        value=line.split('=')[-1]
        if value.find('yes') == -1:
            result.append("ALWAYS_SET_PATH's value should be yes, /etc/default/su")
	
def get_sudo():	
    #get file from /etc/sudoers
    cmdline="cat /etc/sudoers |grep \(root\) > "+tmpFile
    os.popen(cmdline)
    file=open(tmpFile,'r')
    for line in file.readlines():
        strA = line.split(':')
        for strB in strA[1].split(','):
            strB=strB.strip()
            if strB.find('!') == -1:
                fileList.append(strB)

def get_crontab():	
    #get file from /etc/crontab
    cmdline="cat /etc/crontab |grep ' root ' > "+tmpFile
    os.popen(cmdline)
    cmdline="crontab -l >> "+tmpFile
    os.popen(cmdline)
    file=open(tmpFile,'r')
    for line in file.readlines():
        strA = line.split(' ')
        for strB in strA:
            strB=strB.strip()
            if strB.startswith('/'):
                if strB.find(';') >= 0:
                    strC=strB.split(';')
                    for strD in strC:
                        if strD.strip() != '':
                            fileList.append(strD)
                else:
                    fileList.append(strB)

def get_process():
    #get file from root process
    tmp_list=[]
    cmdline="ps aux | awk '{if($1==\"root\"){{for(i=11;i<=NF;++i) printf $i \" \";printf \"\\n\"}}}' |grep -v \"\[\" |grep -v tty |grep -v \"awk\" |grep -v \"ps\" |grep -v \"/dev/sr\" |grep -v \"/dev/fd0\" > "+tmpFile
    os.popen(cmdline)
    file=open(tmpFile,'r')
    for line in file.readlines():
        strA = line.split(' ')
        for strB in strA:
            strB=strB.strip()
            for strC in strB.split(';'):
                if strC.startswith('/'):
                    tmp_list.append(strC)
    return tmp_list

log = TraceLog()
	
if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == '-h':
        print "Usage:"
        print "    python right.py '/opt/controller;/etc/puppet;/opt/SNC_Files'"
        print "        param1 : app dir."
        print "    python right.py check_process"
        print "        param1 : process monitor function."
        print "        stop by Ctrl+C"
        sys.exit()
    if len(sys.argv) == 2 and sys.argv[1] == 'check_process':
        while(1):
            check_process()
            os.system('sleep 1')
	
    get_sudo()
    fileList=list(set(fileList))
    
    #check 1
    fileList=check_system_command(fileList)
    
    get_crontab()    
    fileList=list(set(fileList))
    
    #check 2
    fileList=check_exist(fileList)
    
    #check 3
    fileList=check_right(fileList)

    #check 4
    fileList=check_parent_right(fileList)

    #check 5	
    check_env_variables()
    
    #check 6, need input the application directory
    if len(sys.argv) == 2 and sys.argv[1].find('-h') == -1 and sys.argv[1].find('check_process') == -1:
        check_root_file(sys.argv[1])
    else:
        print "no app dir input, check_root_file will not be execute."
    
    #check 7
    check_child(fileList)
    
    #check 8
    check_process()
	
    #check 9
    check_os_config()
	
    result=list(set(result))
    result.sort()
    printlist(result)
    write_result(result)

