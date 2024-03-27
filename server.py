import common as com
from common import *
import socket
import traceback
import os
import sqlite3
from threading import Thread

if not os.path.isdir('./cloud'):#云文件存储路径
    os.makedirs('./cloud')
os.chdir('./cloud')

dbpath='networkdisk.db'

def sqlexec(s):
    ans=[]
    with sqlite3.connect(dbpath)as conn:
        c=conn.cursor()
        rows=c.execute(s)
        for r in rows:
            ans.append(r)
        conn.commit()
    return ans

try:
    with sqlite3.connect(dbpath)as conn:
        print('数据库打开成功')
        c=conn.cursor()
        c.execute("""
create table users(
                  username text not null,
                  passwd_hash text not null
);
""")
        c.execute("""
create table files(
                  username text not null,
                  dir text not null,
                  hash text not null,
                  size int not null
);
""")
        conn.commit()
        print('建表成功')
except:
    print('表已存在')

serverHost=socket.gethostname()
serverPort=12345
serverAddr=(serverHost,serverPort)
server=com.Session(addr=serverAddr)



print('服务器已建立')
'''
def update_client(client):
    #clientHash=getdata(Msg.from_bytes(server.recv())).decode()
    #newest_clientpy_path=os.path.abspath(os.path.join(__file__,'../'))
    #newestHash=file_md5(newest_clientpy_path)
    #client.send(Msg(0,INS.data,newestHash))
    #op=Msg.from_bytes(client.recv()).decode()#客户端是否
'''
def update_client(client):
    path1=os.path.abspath(os.path.join(__file__,'../common.py'))
    path2=os.path.abspath(os.path.join(__file__,'../client.py'))
    size1=os.path.getsize(path1)
    size2=os.path.getsize(path2)
    client.send(Msg(0,INS.data,str(size1)))
    client.send(Msg(0,INS.data,str(size2)))
    now=0
    with open(path1,'rb')as f:
        while now<size1:
            d=f.read(1024)
            client.send(Msg(0,INS.data,d))
            now+=len(d)
    now=0
    with open(path2,'rb')as f:
        while now<size2:
            d=f.read(1024)
            client.send(Msg(0,INS.data,d))
            now+=len(d)

def register(client):
    username=getdata(Msg.from_bytes(client.recv())).decode()
    passwd=getdata(Msg.from_bytes(client.recv())).decode()
    #查找用户文件
    userfile=username+'.userlogin'
    userDirFile=username+'.userDir'
    if os.path.isfile(userfile):
        client.send(Msg(0,INS.failed,'用户已存在'))
    else:
        client.send(Msg(0,INS.data,userfile))#token
        with open(userfile,'w')as f:
            f.write(passwd)
        with open(userDirFile,'w')as f:
            pass
        return username#登录成功

def register_sql(client):
    username=getdata(Msg.from_bytes(client.recv())).decode()
    passwd=getdata(Msg.from_bytes(client.recv())).decode()
    if sqlexec(f'select username from users where username="{username}"'):
        client.send(Msg(0,INS.failed,'用户已存在'))
    else:
        client.send(Msg(0,INS.data,username))
        sqlexec(f'insert into users(username,passwd_hash) values("{username}","{passwd}")')
        return username
def login(client):
    username=getdata(Msg.from_bytes(client.recv())).decode()
    passwd=getdata(Msg.from_bytes(client.recv())).decode()
    #查找用户文件
    userfile=username+'.userlogin'
    if os.path.isfile(userfile):
        with open(userfile,'r')as f:
            p=f.read()
        print(f'文件密码:{p} 用户输入密码:{passwd}')
        if passwd==p:
            client.send(Msg(0,INS.data,userfile))#token
            return username#登录成功
        else:
            client.send(Msg(0,INS.failed,'密码错误'))
    else:
        client.send(Msg(0,INS.failed,'用户不存在'))

def login_sql(client):
    username=getdata(Msg.from_bytes(client.recv())).decode()
    passwd=getdata(Msg.from_bytes(client.recv())).decode()
    if r:=sqlexec(f'select passwd_hash from users where username="{username}"'):
        print(f'请求登录: 存储密码={r[0][0]} 用户输入密码={passwd}')
        if r[0][0]==passwd:
            client.send(Msg(0,INS.data,username))
            return username#登录成功
        else:client.send(Msg(0,INS.failed,'密码错误'))
    else:client.send(Msg(0,INS.failed,'用户不存在'))

def retrieve_password(client):
    username=getdata(Msg.from_bytes(client.recv())).decode()
    captcha=getdata(Msg.from_bytes(client.recv())).decode()
    newpasswd=getdata(Msg.from_bytes(client.recv())).decode()
    #查找用户文件
    userfile=username+'.userlogin'
    if os.path.isfile(userfile):
        if captcha=='123456':#管理员密码(验证码)
            with open(userfile,'w')as f:
                f.write(newpasswd)
            client.send(Msg(0,INS.data,userfile))#token
            return username#登录成功
        else:
            client.send(Msg(0,INS.failed,'验证失败'))
    else:
        client.send(Msg(0,INS.failed,'用户不存在'))

def retrieve_password_sql(client):
    username=getdata(Msg.from_bytes(client.recv())).decode()
    captcha=getdata(Msg.from_bytes(client.recv())).decode()
    newpasswd=getdata(Msg.from_bytes(client.recv())).decode()
    if r:=sqlexec(f'select passwd_hash from users where username="{username}"'):
        if captcha=='123456':
            sqlexec(f'update users set passwd_hash="{newpasswd}" where username="{username}"')
            client.send(Msg(0,INS.data,username))
            return username#登录成功
        else:client.send(Msg(0,INS.failed,'验证失败'))
    else:client.send(Msg(0,INS.failed,'用户不存在'))

def get_userDir(username):#->str
    userfile=username+'.userlogin'
    userDirFile=username+'.userDir'
    with open(userDirFile,'r')as f:
        li=f.read()
    li=li.split('\n')
    ans=''
    for i in li:
        i=i.split()
        if len(i)==3:#path hash size
            ans+=i[0]+'\n'
    if ans:
        return ans
    else:
        return '没有文件'

def get_userDir_sql(username):
    r=sqlexec(f'select dir from files where username="{username}"')
    if not r:return '没有文件'
    return '\n'.join(map(lambda x:x[0],r))

def map_userDir(username):#返回用户目录的自定义dict对象
    userDirFile=username+'.userDir'
    with open(userDirFile,'r')as f:
        li=f.read()
    li=li.split('\n')
    class Dir(dict):
        def write(self):
            with open(userDirFile,'w')as f:
                for v in self.values():
                    f.write(f'{v[0]} {v[1]} {v[2]}\n')
    mp=Dir()
    for i in li:
        file=i.split()
        if len(file)==3:#有效的文件摘要
            mp[file[0]]=file
    return mp

def map_userDir_sql(username):
    li=sqlexec(f'select dir,hash,size from files where username="{username}"')
    class Dir(dict):
        def write(self):
            sqlexec(f'delete from files where username="{username}"')
            for v in self.values():
                sqlexec(f'insert into files(username,dir,hash,size) values("{username}","{v[0]}","{v[1]}",{v[2]})')#
    mp=Dir()
    for i in li:
        mp[i[0]]=i
    return mp

def upload(client,username):
    #文件名,哈希,文件大小
    fileName=getdata(Msg.from_bytes(client.recv())).decode()
    fileHash=getdata(Msg.from_bytes(client.recv())).decode()
    fileSize=int(getdata(Msg.from_bytes(client.recv())).decode())
    downName,cloudFile=f'{fileHash}.down',f'{fileHash}.file'
    if os.path.isfile(cloudFile):
        client.send(Msg(0,INS.failed,'服务器已存储相同哈希文件,秒传成功'))
    else:
        with open(downName,'ab') as f:#创建.down文件
            nowSize=os.path.getsize(downName)
            client.send(Msg(0,INS.data,str(nowSize)))#发送本地存在的下载量
            while nowSize<fileSize:
                d=getdata(Msg.from_bytes(client.recv()))
                f.write(d)
                nowSize+=len(d)
        os.rename(downName,cloudFile)
        client.send(Msg(0,INS.data,'ok'))
    #创建用户目录映像
    mp=map_userDir(username)
    mp[fileName]=[fileName,fileHash,str(fileSize)]
    mp.write()#重写目录映像

def upload_sql(client,username):
    #文件名,哈希,文件大小
    fileName=getdata(Msg.from_bytes(client.recv())).decode()
    fileHash=getdata(Msg.from_bytes(client.recv())).decode()
    fileSize=int(getdata(Msg.from_bytes(client.recv())).decode())
    downName,cloudFile=f'{fileHash}.down',f'{fileHash}.file'
    if os.path.isfile(cloudFile):
        client.send(Msg(0,INS.failed,'服务器已存储相同哈希文件,秒传成功'))
    else:
        with open(downName,'ab') as f:#创建.down文件
            nowSize=os.path.getsize(downName)
            client.send(Msg(0,INS.data,str(nowSize)))#发送本地存在的下载量
            while nowSize<fileSize:
                d=getdata(Msg.from_bytes(client.recv()))
                f.write(d)
                nowSize+=len(d)
        os.rename(downName,cloudFile)
        client.send(Msg(0,INS.data,'ok'))
    #创建用户目录映像
    mp=map_userDir_sql(username)
    mp[fileName]=[fileName,fileHash,str(fileSize)]
    mp.write()#重写目录映像

def download(client,username):
    
    filePath=getdata(Msg.from_bytes(client.recv())).decode()
    mp=map_userDir(username)
    file=mp[filePath]
    
    fileName=os.path.basename(file[0])
    fileHash=file[1]
    fileSize=file[2]#str
    cloudFile=file[1]+'.file'
    if not os.path.isfile(cloudFile):
        client.send(Msg(0,INS.failed,'文件不存在'))
        return
    client.send(Msg(0,INS.data,fileName))
    client.send(Msg(0,INS.data,fileHash))
    client.send(Msg(0,INS.data,fileSize))
    nowSize=int(getdata(Msg.from_bytes(client.recv())).decode())#获取客户端下载进度
    with open(cloudFile,'rb')as f:
        while nowSize<int(fileSize):
            d=f.read(1024)
            client.send(Msg(0,INS.data,d))
            nowSize+=len(d)
    client.send(Msg(0,INS.data,'ok'))

def download_sql(client,username):
    filePath=getdata(Msg.from_bytes(client.recv())).decode()
    mp=map_userDir_sql(username)
    file=mp[filePath]
    
    fileName=os.path.basename(file[0])
    fileHash=file[1]
    fileSize=str(file[2])#str
    cloudFile=file[1]+'.file'
    if not os.path.isfile(cloudFile):
        client.send(Msg(0,INS.failed,'文件不存在'))
        return
    client.send(Msg(0,INS.data,fileName))
    client.send(Msg(0,INS.data,fileHash))
    client.send(Msg(0,INS.data,fileSize))
    nowSize=int(getdata(Msg.from_bytes(client.recv())).decode())#获取客户端下载进度
    with open(cloudFile,'rb')as f:
        while nowSize<int(fileSize):
            d=f.read(1024)
            client.send(Msg(0,INS.data,d))
            nowSize+=len(d)
    client.send(Msg(0,INS.data,'ok'))

def update_dir_sql(client,username):
    old_path=getdata(Msg.from_bytes(client.recv())).decode()
    new_path=getdata(Msg.from_bytes(client.recv())).decode()
    mp=map_userDir_sql(username)
    file=mp.get(old_path)
    if not file:return
    mp.pop(old_path)#删除文件
    if new_path:#修改文件名
        file=list(file)
        file[0]=new_path
        mp[new_path]=tuple(file)
    mp.write()
    client.send(Msg(0,INS.data,'ok'))

def connect(client):
    #client.settimeout(60*3)#超时设置
    username=None
    while 1:
        try:
            m=Msg.from_bytes(client.recv())
            match m.ins:
                case INS.update_client.value:
                    update_client(client)
                case INS.register.value:
                    username=register_sql(client)
                case INS.login.value:
                    username=login_sql(client)
                case INS.login_with_token.value:
                    pass
                case INS.retrieve_password.value:
                    username=retrieve_password_sql(client)
                case INS.ask_dir.value:
                    if username==None:
                        client.send(Msg(0,INS.failed,'未登录,无法查看用户目录'))
                    else:
                        client.send(Msg(0,INS.data,get_userDir_sql(username)))
                case INS.upload.value:
                    if username==None:
                        client.send(Msg(0,INS.failed,'未登录,无法上传文件'))
                    else:
                        upload_sql(client,username)
                case INS.download.value:
                    if username==None:
                        client.send(Msg(0,INS.failed,'未登录,无法下载文件'))
                    else:
                        download_sql(client,username)
                case INS.update_dir.value:
                    if username==None:
                        client.send(Msg(0,INS.failed,'未登录,无法修改文件'))
                    else:
                        update_dir_sql(client,username)
                
        except Exception as e:
            print('err:发生错误,断开连接')
            client.send(Msg(0,INS.failed.value,'服务器已断开连接:'+str(e)))#发送失败原因
            traceback.print_exc()
            client.close()
            break


server.listen(10)
tasklist=[]
while 1:
    client=server.accept()
    print(f'连接到客户端:{client.addr}')
    thd=Thread(target=connect,args=(client,))
    tasklist.append(thd)
    # connect(client)
    thd.start()