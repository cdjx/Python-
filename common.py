import socket
from enum import Enum,auto
import hashlib
import os
import time
import traceback

class contextError(Exception):#上下文异常
    pass

def getdata(m):#接收data或抛出上下文异常
    if m.encrypt==0 and m.ins==INS.data.value:
        return m.data
    raise contextError(m)


def file_hash(path,hash_method):
    path=os.path.join(os.getcwd(),path)
    if not os.path.isfile(path):
        return ''
    h=hash_method()
    with open(path,'rb')as f:
        while b:=f.read(8192):
            h.update(b)
    return h.hexdigest()
def file_md5(path):
    return file_hash(path,hashlib.md5)


class INS(Enum):
    update_client=auto()#客户端请求更新
    ask_rsa=auto()#客户端请求rsa公钥
    send_aes=auto()#客户端发送aes秘钥

    register=auto()#客户端请求注册账号
    login=auto()#客户端请求登录账号
    login_with_token=auto()#客户端使用token登录
    retrieve_password=auto()#客户端请求找回密码
    
    ask_dir=auto()#客户端请求目录数据
    upload=auto()#客户端请求上传文件
    download=auto()#客户端请求下载文件
    update_dir=auto()#客户端请求更新网盘目录

    failed=auto()#服务器发送失败原因
    
    data=auto()#上下文数据
    end=auto()#传输结束

INS_SIZE=(len(hex(len(INS)*2-1))-1)//2#指令集占字节数量,加一位加密位

class Msg:
    def __init__(self,encrypt=0,ins:int=INS.data,data:bytes=b''):
        if type(ins)==INS:
            ins=ins.value
        if type(data)==str:
            data=bytes(data,encoding='utf-8')
        self.encrypt=encrypt
        self.ins=ins
        self.data=data
    def bytes(self):
        b=self.ins*2+self.encrypt
        b=b.to_bytes(INS_SIZE,'big')
        b+=self.data
        return b
    def from_bytes(b):#
        m=Msg()
        head=b[:INS_SIZE]
        head=int.from_bytes(head,'big')
        m.encrypt=head&1
        m.ins=head>>1
        m.data=b[INS_SIZE:]
        if m.encrypt:
            m.decryption()
        return m
    def decryption(self):#aes解密
        return self
    def __str__(self):
        return f'Msg(encrypt={self.encrypt},ins={self.ins})\ndata:{self.data}'
class Session:
    def __init__(self,addr=None):#初始化
        if addr:
            self.skt=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.addr=addr
    def settimeout(self,sec):#设置socket的超时时间
        self.skt.settimeout(sec)
    def connect(self):#主动连接
        self.skt=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.skt.connect(self.addr)
        print(f'成功连接到:{self.addr}')
    def listen(self,maxNum):#绑定地址,设置最大连接数
        self.skt.bind(self.addr)
        self.skt.listen(maxNum)
    def accept(self):#获取连接
        client=Session()
        client.skt,client.addr=self.skt.accept()
        return client
    def __sendint(self,x):#发送不定长int,用于传递数据包大小
        lis=[]
        while x>0:
            lis.append(x&127)
            x>>=7
        lis[0]|=128
        self.skt.send(bytes(reversed(lis)))
    def __recvint(self):#接收不定长int
        ans=0
        while 1:
            x=int.from_bytes(self.skt.recv(1),'big')
            ans<<=7
            ans|=x&127
            if x&128:
                break
        return ans 
    def send(self,data):#发送一个数据包
        if type(data)==Msg:#特判转bytes
            data=data.bytes()
        size=len(data)
        self.__sendint(size)
        p=0
        while p<size:
            r=self.skt.send(data[p:p+1024])
            p+=r
    def recv(self):#接收一个数据包
        size=self.__recvint()#;print(f'接收的大小为:{size}')
        data=bytes()
        while len(data)<size:
            data+=self.skt.recv(min(1024,size-len(data)))#最多接收1024字节,不会过量读入
        return data
    def close(self):#关闭连接
        self.skt.close()
    def __del__(self):
        self.close()
    def __exit__(self):
        self.close()
        
