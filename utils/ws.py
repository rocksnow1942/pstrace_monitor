import websocket
import json
import time
"""
For testing multiple Websocket WSClients
And automate update tasks on multiple devices.
"""

class WSClient:
    def __init__(self,deviceID,app):
        self.id = deviceID
        self.wsAddr = f'ws://{deviceID}.local:8765'
        self.app = app
        self.con = None
        for i in range(3):            
            self.print(f'{i+1}-Connecting to {self}...')
            self.connect()
            if self.con:
                return
            else:
                time.sleep(1)

    def print(self,msg):
        if self.app:
            self.app.print(msg)
        else:
            print(msg)

    def connect(self):
        try:
            self.con = websocket.WebSocket()
            self.con.connect(self.wsAddr)
            self.print(f'{self} Connected.')
        except Exception as e:
            self.con=None
            self.print(f"{self} connection error: {e}")
    
    def __repr__(self):
        return self.id
    
    def close(self):
        if self.con:
            self.con.close()
            
    def reconnect(self):
        if not self.con:
            self.connect()
            res = 'Failed' if not self.con else 'Success'
            return f"{self} connection {res}."
        else:
            return f'{self} already connected.'

    def send(self,action,**kwargs):
        kwargs.update(action=action)
        try:
            self.con.send(json.dumps(kwargs))
            return self.con.recv()
        except Exception as e:
            return f'{self} send msg error: {e}'
        
            
    def updateDevice(self):
        return self.send('main.updateGit')

    def restartSystem(self):
        return self.send('main.restartSystem')
    
    def rebootSystem(self):
        return self.send('main.rebootSystem')

class Proxy:
    def __init__(self,items):
        self._items = items
    def __repr__(self):
        return '\n'.join(repr(i) for i in self._items)
    def __getattr__(self,name):
        return Proxy([getattr(i,name) for i in self._items])
    def __call__(self,*args,**kwargs):
        return Proxy([i(*args,**kwargs) for i in self._items])

class WSClients(Proxy):
    def __init__(self,IDs,app=None):
        self._items = [WSClient(id,self) for id in IDs]
        self.app = app

    def print(self,msg):
        if self.app:
            self.app.print(msg)
        else:
            print(msg)

    def updateDevices(self,):
        print('Before Update:')
        print(self.send('main.getVersion'))
        print(self.updateDevice())
    
     
        

if __name__ == "__main__":
    print('Enter the device name you want to sync:')
    default = "psf qhk axp xrc yon"
    devices = input(f"Spearate by space. default = {default} \n") or default
    devices = devices.strip().split()
    clients = WSClients(devices)
    while True:
        try:
            print("Enter command you want to do: (update,restart,reboot,reconnect)")
            action = input(">>>:  ")
            res = getattr(clients, {
                'update':'updateDevices',
                'restart': 'restartSystem',
                'reboot': 'rebootSystem',
                'reconnect': 'reconnect',
            }[action])()
            print(res)
        except KeyboardInterrupt:
            print('\nByebye.\n')
            break
        except Exception as e:
            print(f"Error: {e}")

     
     




