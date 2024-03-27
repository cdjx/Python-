from PyQt5 import QtWidgets, QtCore, QtGui,Qt
from PyQt5.QtGui import QKeyEvent
import os
from enum import Enum,auto
import common as com
#from common import INS,Msg,Session,file_md5
from common import *
import socket
import traceback
import time
import sys


serverHost=socket.gethostname()
serverPort=12345
serverAddr=(serverHost,serverPort)
server=com.Session(addr=serverAddr)

help_str='''
client_version:1.0
指令列表:
help 打开帮助手册
cd [路径] 切换到对应路径并输出目录列表
register [用户名] [密码] 注册账号
login [用户名] [密码] 登录
retrieve_password [用户名] [管理员提供的验证码] [新密码] 找回密码
check_update 更新客户端
cloud_dir 查看网盘存储的文件列表
cloud_rename [文件名] [新文件名] 修改文件名,新文件名为空则删除文件
upload [文件路径] 上传文件
download [网盘文件路径] 下载文件
re 重新连接服务器
exit 退出程序
'''

def _print(*a,io=[sys.stdout],**k):
    print(*a,**k,file=io[0])

def bar(label,now,tot,time,length=50):
    p=now*length//tot
    per=now/tot
    bar='['+'-'*p+' '*(length-p)+']'
    predict='预计剩余时间:'
    if time>0:
        sec=time/now*tot-time
        min=sec//60
        hour=min//60
        predict+=('%2d小时'%(hour))if hour else ''
        predict+=('%2d分钟'%(min%60))if min else ''
        predict+=('%2.2f秒'%(sec%60))
    else:
        predict+='--'
    print(f'\r{label}:{bar} %.2f%%\t{now}/{tot}\t{predict}'%(per*100),end='')
    sys.stdout.flush()

def register(username:str,passwd:str,*,ui=None):#ui:UI_UserInfo
    server.send(Msg(encrypt=0,ins=INS.register.value))
    server.send(Msg(encrypt=0,ins=INS.data.value,data=bytes(username,encoding='utf-8')))
    server.send(Msg(encrypt=0,ins=INS.data.value,data=bytes(passwd,encoding='utf-8')))
    m=Msg.from_bytes(server.recv())
    data=getdata(m)
    if ui:
        ui.update(username)
    return data
def login(username:str,passwd:str,*,ui=None):#ui:UI_UserInfo
    server.send(Msg(encrypt=0,ins=INS.login.value))
    server.send(Msg(encrypt=0,ins=INS.data.value,data=bytes(username,encoding='utf-8')))
    server.send(Msg(encrypt=0,ins=INS.data.value,data=bytes(passwd,encoding='utf-8')))
    m=Msg.from_bytes(server.recv())
    data=getdata(m)
    if ui:
        ui.update(username)
    return data
def retrieve_password(username:str,captcha:str,newpasswd:str,*,ui=None):#ui:UI_UserInfo
    server.send(Msg(encrypt=0,ins=INS.retrieve_password.value))
    server.send(Msg(encrypt=0,ins=INS.data.value,data=bytes(username,encoding='utf-8')))
    server.send(Msg(encrypt=0,ins=INS.data.value,data=bytes(captcha,encoding='utf-8')))
    server.send(Msg(encrypt=0,ins=INS.data.value,data=bytes(newpasswd,encoding='utf-8')))
    m=Msg.from_bytes(server.recv())
    data=getdata(m)
    if ui:
        ui.update(username)
    return data
def update_client():
    server.send(Msg(0,INS.update_client))
    size1=getdata(Msg.from_bytes(server.recv())).decode();#common
    size1=int(size1)
    size2=getdata(Msg.from_bytes(server.recv())).decode();#client
    size2=int(size2)
    now=0
    common_path=os.path.abspath(os.path.join(__file__,'../common.py'))
    with open(common_path,'wb')as f:
        while now<size1:
            d=getdata(Msg.from_bytes(server.recv()))
            f.write(d)
            now+=len(d)
    now=0
    with open(__file__,'wb')as f:
        while now<size2:
            d=getdata(Msg.from_bytes(server.recv()))
            f.write(d)
            now+=len(d)
    with open(__file__,'r',encoding='utf-8')as f:
        context=f.read()
    return context

def cloud_dir(*,ui=None):#ui:UI_Tab_Files
    server.send(Msg(encrypt=0,ins=INS.ask_dir.value))
    data=getdata(Msg.from_bytes(server.recv())).decode()
    if ui:
        li=[]
        if data!='没有文件':
            li=data.split('\n')
        ui.update(li)
    return data

def upload(path):
    absPath=os.path.join(os.getcwd(),path)
    fileName=os.path.basename(absPath)
    fileHash=file_md5(absPath)
    fileSize=os.path.getsize(absPath)
    server.send(Msg(encrypt=0,ins=INS.upload.value))#文件名,哈希,文件大小
    server.send(Msg(encrypt=0,ins=INS.data.value,data=bytes(fileName,encoding='utf-8')))
    server.send(Msg(encrypt=0,ins=INS.data.value,data=bytes(fileHash,encoding='utf-8')))
    server.send(Msg(encrypt=0,ins=INS.data.value,data=bytes(str(fileSize),encoding='utf-8')))
    nowSize=int(getdata(Msg.from_bytes(server.recv())).decode())#str->int
    with open(path,'rb')as f:
        f.seek(nowSize)
        t0=time.time()
        while nowSize<fileSize:
            d=f.read(1024)
            server.send(Msg(encrypt=0,ins=INS.data.value,data=d))
            nowSize+=len(d)
            bar('上传进度',nowSize,fileSize,time.time()-t0)
    return getdata(Msg.from_bytes(server.recv())).decode()=='ok'

def download(path):
    server.send(Msg(encrypt=0,ins=INS.download.value))
    server.send(Msg(encrypt=0,ins=INS.data.value,data=path))#发送需要下载的文件的网盘路径
    #获得文件名,哈希,文件大小
    fileName=getdata(Msg.from_bytes(server.recv())).decode()
    fileHash=getdata(Msg.from_bytes(server.recv())).decode()
    fileSize=int(getdata(Msg.from_bytes(server.recv())).decode())
    #比对本地.down文件
    downName=f'{fileHash}.down'
    if not os.path.isfile(downName):
        with open(downName,'ab')as f:
            pass
    nowSize=os.path.getsize(downName)
    print(f'本地存在的下载量={nowSize}')
    server.send(Msg(encrypt=0,ins=INS.data.value,data=bytes(str(nowSize),encoding='utf-8')))#发送本地存在的下载量
    with open(downName,'ab')as f:
        t0=time.time()
        while nowSize<fileSize:
            d=getdata(Msg.from_bytes(server.recv()))
            f.write(d)
            nowSize+=len(d)
            bar('下载进度',nowSize,fileSize,time.time()-t0)
    os.rename(downName,fileName)
    return getdata(Msg.from_bytes(server.recv())).decode()=='ok'

def update_dir(old_path,new_path):#cloud path
    server.send(Msg(0,INS.update_dir.value))
    server.send(Msg(0,INS.data.value,old_path))
    server.send(Msg(0,INS.data.value,new_path))
    return getdata(Msg.from_bytes(server.recv())).decode()=='ok'

class EXIT(Enum):#客户端shell的退出状态码
    normal=auto()#正常结束
    update=auto()#发生更新
    err=auto()#发生异常









class UI_DictDialog(QtWidgets.QDialog):
    def __init__(self,mp,*keys):
        super().__init__()
        self.mp=mp
        self.keys=keys
        #控件
        self.labels=[QtWidgets.QLabel(i) for i in keys]
        self.edits=[QtWidgets.QLineEdit() for i in keys]
        self.button_ok=QtWidgets.QPushButton('确定')
        self.button_ok.clicked.connect(self.ok)
        self.button_cancel=QtWidgets.QPushButton('取消')
        self.button_cancel.clicked.connect(self.cancel)
        #布局
        self.box=QtWidgets.QGridLayout()
        #插入
        for i in range(len(keys)):
            self.box.addWidget(self.labels[i],i,0)
            self.box.addWidget(self.edits[i],i,1)
        self.box.addWidget(self.button_ok,len(keys),0)
        self.box.addWidget(self.button_cancel,len(keys),1)

        self.setLayout(self.box)
    def ok(self):
        for i in range(len(self.keys)):
            self.mp[self.keys[i]]=self.edits[i].text()
        self.close()
    def cancel(self):
        self.close()
def dictDialog(*keys):
    mp={}
    ui=UI_DictDialog(mp,*keys)
    ui.exec_()
    return mp
def msgBox(s:str):
    QtWidgets.QMessageBox.information(None,' ',s)
class UI_UserInfo(QtWidgets.QWidget):
    def __init__(self,root):
        super().__init__()
        self._root=root
        #控件
        self.label_username=QtWidgets.QLabel()
        self.button_login=QtWidgets.QPushButton('登录')
        self.button_register=QtWidgets.QPushButton('注册')
        #设置
        self.label_username.setText('未登录')
        self.button_login.clicked.connect(self.login)
        self.button_register.clicked.connect(self.register)
        #布局
        self.gridbox=QtWidgets.QGridLayout()
        #添加控件
        self.gridbox.addWidget(self.label_username,0,0)
        self.gridbox.addWidget(self.button_login,0,1)
        self.gridbox.addWidget(self.button_register,0,2)

        self.setLayout(self.gridbox)
    def login(self):
        mp=dictDialog('用户名','密码')
        if not mp:return
        self._root.paging.tab_shell.command(f'login {mp["用户名"]} {mp["密码"]}',prompt='UI:>>')
    def register(self):
        mp=dictDialog('用户名','密码','确认密码')
        if not mp:return
        if mp['密码']!=mp['确认密码']:
            msgBox('密码不一致')
            return
        self._root.paging.tab_shell.command(f'register {mp["用户名"]} {mp["密码"]}',prompt='UI:>>')
    def update(self,username):
        self.label_username.setText(username)
class UI_File_Item(QtWidgets.QWidget):
    def __init__(self,root,filename):
        super().__init__()
        self.filename=filename
        self._root=root
        #控件
        self.label=QtWidgets.QLabel(f'{filename:<20}')
        self.button_download=QtWidgets.QPushButton('下载')
        self.button_download.clicked.connect(self.download)
        self.button_rename=QtWidgets.QPushButton('重命名')
        self.button_rename.clicked.connect(self.rename)
        self.button_delete=QtWidgets.QPushButton('删除')
        self.button_delete.clicked.connect(self.delete)
        #布局
        self.box=QtWidgets.QHBoxLayout()
        #插入
        self.box.addWidget(self.label)
        self.box.addWidget(self.button_download)
        self.box.addWidget(self.button_rename)
        self.box.addWidget(self.button_delete)
        self.setLayout(self.box)
    def download(self):
        path=QtWidgets.QFileDialog.getExistingDirectory(None,'选择下载目录',os.getcwd())
        self._root.paging.tab_shell.command(f'cd {path}',prompt='UI:>>')
        self._root.paging.tab_shell.command(f'download {self.filename}',prompt='UI:>>')
    def rename(self):
        newname=dictDialog('新文件名')
        if not newname:return
        self._root.paging.tab_shell.command(f'cloud_rename {self.filename} {newname["新文件名"]}',prompt='UI:>>')
    def delete(self):
        self._root.paging.tab_shell.command(f'cloud_rename {self.filename}',prompt='UI:>>')
class UI_Tab_Files(QtWidgets.QWidget):
    def __init__(self,root):
        super().__init__()
        self._root=root
        self.itemlist=[]
        #控件
        self.button_upload=QtWidgets.QPushButton('上传文件')
        self.button_upload.clicked.connect(self.upload)
        self.spring=QtWidgets.QSpacerItem(20,20,QtWidgets.QSizePolicy.Minimum,QtWidgets.QSizePolicy.Expanding)
        #布局
        self.box_up=QtWidgets.QVBoxLayout()
        self.box=QtWidgets.QVBoxLayout()
        #添加控件
        self.box_up.addWidget(self.button_upload)
        self.box.addLayout(self.box_up)
        self.box.addItem(self.spring)
        # for i in range(1):#测试文件列表
        #     self.box_up.addWidget(UI_File_Item(self._root,f'{i}'))
        self.setLayout(self.box)
    def update(self,li):
        for item in self.itemlist:
            item.deleteLater()
        self.itemlist=[]
        for name in li:
            item=UI_File_Item(self._root,name)
            self.box_up.addWidget(item)
            self.itemlist.append(item)
            # print(f'::name={name}')
        # self.adjustSize()
        self.resize(400,400)
    def upload(self):
        path,_=QtWidgets.QFileDialog.getOpenFileName(self,"选取文件",os.getcwd())
        if not path:return
        path=os.path.split(path)
        print(path)
        self._root.paging.tab_shell.command(f'cd {path[0]}',prompt='UI:>>')
        self._root.paging.tab_shell.command(f'upload {path[1]}',prompt='UI:>>')
        self._root.paging.tab_shell.command(f'cloud_dir {path[1]}',prompt='UI:>>')
class UI_Tab_shell_InputBox(QtWidgets.QLineEdit):
    def __init__(self,parent):
        super().__init__()
        self._parent=parent
    def keyPressEvent(self,e):
        super().keyPressEvent(e)
        # print(e.key(),type(e.key()))
        if e.key()in [16777220,16777221]:#回车
            self.send()
    def send(self):
        s=self.text()
        if not s:return
        self._parent.command(s)
        self.setText('')
class UI_Tab_shell(QtWidgets.QWidget):
    def __init__(self,root):
        super().__init__()
        self.context=''
        self._root=root
        #控件
        self.inputbox=UI_Tab_shell_InputBox(self)
        self.button=QtWidgets.QPushButton('Enter')
        self.button.clicked.connect(lambda:self.inputbox.send())

        self.label_text=QtWidgets.QLabel()
        self.area=QtWidgets.QScrollArea()
        #布局
        self.mainbox=QtWidgets.QVBoxLayout()
        self.bottomBox=QtWidgets.QHBoxLayout()
        #设置滚动区域
        self.area.setWidget(self.label_text)
        #插入
        self.bottomBox.addWidget(self.inputbox)
        self.bottomBox.addWidget(self.button)
        self.mainbox.addWidget(self.area)
        self.mainbox.addLayout(self.bottomBox)
        #设置
        self.setLayout(self.mainbox)
    def write(self,s:str,*,static_last=[time.time()]):#用于重定向print
        self.context+=s
        self.context='\n'.join(map(lambda x:x.split('\r')[-1],self.context.split('\n')))
        if time.time()-static_last[0]<0.1:
            return
        self.label_text.setText(self.context)
        self.label_text.adjustSize()
        bar=self.area.verticalScrollBar()
        bar.setValue(bar.maximum())
        # self.scrollBar.setValue(self.scrollBar.maximum())
    def flush(self):
        pass
    def command(self,cmd,*,prompt='>>'):
        print(f'{prompt}{cmd}')
        try:
            cmd=cmd.split()
            if cmd[0] in ['?','help']:
                print(help_str)
            elif cmd[0] in ['cd','chdir']:
                if len(cmd)!=2:
                    print('参数错误')
                    return
                os.chdir(cmd[1])
                print(f'当前路径:{os.getcwd()}\n目录列表:\n')
                for i in os.listdir():
                    print(i)
            elif cmd[0] in ['register']:
                token=register(cmd[1],cmd[2],ui=self._root.userinfo)
                print(f'注册成功 token:{token}')
                cloud_dir(ui=self._root.paging.tab_files)#
            elif cmd[0] in ['login']:
                token=login(cmd[1],cmd[2],ui=self._root.userinfo)
                print(f'登录成功 token:{token}')
                cloud_dir(ui=self._root.paging.tab_files)#
            elif cmd[0] in ['retrieve_password','newpassw']:
                token=retrieve_password(cmd[1],cmd[2],cmd[3],ui=self._root.userinfo)
                print(f'修改密码成功 token:{token}')
                cloud_dir(ui=self._root.paging.tab_files)#
            elif cmd[0] in ['check_update']:
                code=update_client()#返回热更新后执行的代码
                print('已更新至最新版客户端')
                return [EXIT.update,code]#重启shell
            elif cmd[0] in ['cloud_dir']:
                print(cloud_dir(ui=self._root.paging.tab_files))
            elif cmd[0] in ['upload']:
                r=upload(cmd[1])
                if r:
                    print('上传成功')
                else:
                    print('上传失败')
            elif cmd[0] in ['download']:
                r=download(cmd[1])
                if r:
                    print('下载成功')
                else:
                    print('下载失败')
            elif cmd[0] in ['cloud_rename']:
                if len(cmd)==3:#重命名
                    update_dir(cmd[1],cmd[2])
                elif len(cmd)==2:#删除
                    update_dir(cmd[1],'')
                else:
                    print('参数错误')
                cloud_dir(ui=self._root.paging.tab_files)#
            elif cmd[0] =='re':
                server.connect()
            else:
                print('?(指令格式不对)')
        except contextError as e:
            m=e.args[0]
            print(f'上下文异常(未收到预期数据):\n收到服务器报文:{m}')
            if m.encrypt==1:
                print('无法解读服务器加密数据')
            elif m.ins==INS.failed.value:
                print(m.data.decode())#输出失败原因
        except Exception as e:
            print('err:',e)
            print(traceback.print_exc())
            for i in range(3):
                try:
                    print('请等待三秒,正在重新连接服务器')
                    time.sleep(3)
                    server.connect()
                    break
                except Exception as e:
                    print('连接失败')
                    print(e)
                    traceback.print_exc()
            return [EXIT.err,'发生错误,且服务器无法重新连接']
class UI_Paging(QtWidgets.QTabWidget):
    def __init__(self,root):
        super().__init__()
        self._root=root
        #控件
        self.tab_files=UI_Tab_Files(root=root)
        # self.tab_files.resize(1000,1000)
        self.tab_shell=UI_Tab_shell(root=root)
        #插入控件
        self.tab_files_area=QtWidgets.QScrollArea()
        self.tab_files_area.setWidget(self.tab_files)
        self.addTab(self.tab_files_area,'所有文件')
        self.addTab(self.tab_shell,'shell')
        #设置样式
        self.setTabPosition(QtWidgets.QTabWidget.West)

class ClientMainWin(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        #设置布局和创建控件
        #控件
        self.userinfo=UI_UserInfo(root=self)
        self.paging=UI_Paging(root=self)
        #布局
        self.box=QtWidgets.QVBoxLayout()
        #向布局添加控件
        self.box.addWidget(self.userinfo)
        self.box.addWidget(self.paging)

        self.setLayout(self.box)

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    mainwin = ClientMainWin()
    mainwin.resize(500,400)
    sys.stdout=mainwin.paging.tab_shell
    mainwin.show()
    mainwin.paging.tab_shell.command('help',prompt='UI:>>')
    mainwin.paging.tab_shell.command('re',prompt='UI:>>')
    # mainwin.paging.tab_shell.command('login cdjx 123',prompt='>>')
    # mainwin.paging.tab_shell.command('cloud_dir',prompt='>>')
    app.exec_()
