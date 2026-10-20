"""Read-only OpenRGB SDK v0 inspection, based on the release 1.1 protocol."""
import socket,struct

def read(sock,n):
    data=b''
    while len(data)<n:
        part=sock.recv(n-len(data))
        if not part:raise RuntimeError('SDK disconnected')
        data+=part
    return data

class Reader:
    def __init__(self,data):self.data=data;self.pos=0
    def take(self,fmt):
        fmt='<'+fmt;n=struct.calcsize(fmt)
        values=struct.unpack_from(fmt,self.data,self.pos);self.pos+=n
        return values[0] if len(values)==1 else values
    def string(self):
        n=self.take('H');data=self.data[self.pos:self.pos+n];self.pos+=n
        return data.rstrip(b'\0').decode('utf-8')

def packet(sock,device,kind,payload=b''):
    sock.sendall(struct.pack('<4sIII',b'ORGB',device,kind,len(payload))+payload)
    while True:
        magic,dev,pkt,size=struct.unpack('<4sIII',read(sock,16))
        assert magic==b'ORGB' and size<8388608
        data=read(sock,size)
        if dev==device and pkt==kind:return data

def controller(sock,idx):
    data=packet(sock,idx,1,struct.pack('<I',0));r=Reader(data)
    assert r.take('I')==len(data)
    item={'id':idx,'type':r.take('I'),'name':r.string(),
          'description':r.string(),'version':r.string(),'serial':r.string(),'location':r.string()}
    modes=r.take('H');item['active_mode']=r.take('i');item['modes']=[]
    for _ in range(modes):
        name=r.string();fields=r.take('9I');count=r.take('H')
        colors=[r.take('I') for _ in range(count)]
        item['modes'].append({'name':name,'colors':colors})
    item['zones']=[]
    for idx in range(r.take('H')):
        zone={'id':idx,'name':r.string()}
        zone['type'],zone['min'],zone['max'],zone['count']=r.take('4I')
        size=r.take('H');r.pos+=size;item['zones'].append(zone)
    item['leds']=[]
    for _ in range(r.take('H')):
        item['leds'].append(r.string());r.take('I')
    count=r.take('H');item['colors']=[r.take('I') for _ in range(count)]
    assert r.pos==len(data),(r.pos,len(data))
    return item

def snapshot():
    with socket.create_connection(('127.0.0.1',6743),timeout=3) as sock:
        count=struct.unpack('<I',packet(sock,0,0))[0]
        if count>16:raise RuntimeError('Unexpected controller count')
        return [controller(sock,i) for i in range(count)]
