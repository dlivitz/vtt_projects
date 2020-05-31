import requests
from bottle import route, run, template,ServerAdapter,redirect
import subprocess
from html.parser import HTMLParser
import threading
import time

ssl_cert=None #'fullchain.pem' 
ssl_key=None #'privkey.pem'


world_mapping={"strahd":["curse-of-strahd","Curse of Strahd"],"assorted_encounters":["ds","Assorted Enconters"]}  ##Future will populate this automatically from module configuration, can probably get pictures etc but who has time?
foundry_base="https://example.com"
foundry_port=30000
foundry_url=foundry_base+":"+str(foundry_port)
foundry_directory="PATH/FoundryVTT/resources/app"

idle_logout=300 #Seconds - time to shut down foundry if at login screen and 0 users



class SSLWrapper(ServerAdapter):
    def __init__(self, ssl_certfile = None, ssl_keyfile = None, host='0.0.0.0', port=8080):
        self._ssl_certfile = ssl_certfile
        self._ssl_keyfile = ssl_keyfile
        
        super().__init__(host, port)
        
    
    def run(self, handler):
        from  cheroot.ssl.builtin import BuiltinSSLAdapter
        from cheroot import wsgi
        server = wsgi.Server((self.host, self.port), handler)  
        self.srv = server
        
        server.ssl_adapter = BuiltinSSLAdapter(self._ssl_certfile, self._ssl_keyfile)
        try:  
            server.start()  
        finally:  
            server.stop()  
                
    def shutdown(self):
        self.srv.stop()




class AwfulScrape_nPlayers(HTMLParser):
    #This is why javascript was invented 
    
    def __init__(self):
        super().__init__()
        
        
        self.in_label=False #We are searching for a "Current Players:" label
        self.previous_label_players=False  #If we found it, grab the first input field 
        self.nPlayers=None  #If nothing is found crash 
        
    def handle_starttag(self, tag, attrs):
        if tag == "label":
            self.in_label=True
        if (tag == "input") and self.previous_label_players:
            self.nPlayers=int(dict(attrs)["value"])
            self.previous_label_players=False

            
    def handle_endtag(self, tag):
        if tag == "label":
            self.in_label=False
        if tag == "header":
            self.in_header=False

    def handle_data(self, data):
        if self.in_label:
            if "Current Players:" in data:  
                self.previous_label_players=True
            else:
                self.previous_label_players=False


## A bunch of threading stuff 

class monitorPlayers(object):
    def __init__(self, foundry_proccess):
        self.foundry_proccess = foundry_proccess

        thread = threading.Thread(target=self.run, args=())
        thread.daemon = False
        thread.start()      

    def run(self):
        #Keep checking number of players 
        #If it's been 0 for 5 minutes, return to setup 

        zero_players=False
        while True:
            n_players=get_logged_in_players(timeout=30.) #Returns "None" if in setup etc so it's safe
            if (n_players == 0) and zero_players:
                self.foundry_proccess.send_signal(2)
                self.foundry_proccess.send_signal(2) ##I think I need to send this twice? 
                self.foundry_proccess.wait()
                break
                
            time.sleep(idle_logout) #Wait five minutes 
            if n_players == 0:
                
                zero_players=True
        server.start()
        

class runServer(object):
    def __init__(self):
        self.server=SSLWrapper(ssl_certfile = ssl_cert, ssl_keyfile = ssl_key,port=foundry_port)

        thread = threading.Thread(target=self.run, args=([self.server]))
        thread.daemon = False                      
        thread.start()                                 
    def run(self,server):
        run(server=server)


class bottleManager: #this is bascially just a global variable
    def __init__(self): 
        self.bottle_server=runServer()
    def shutdown(self):
        self.bottle_server.server.shutdown()
        self.bottle_server = None
    def start(self):
        self.bottle_server=runServer()


        
class startFoundryWorld(object):
    def __init__(self, world):
        self.world = world

        thread = threading.Thread(target=self.run, args=([world]))
        thread.daemon = False                            
        thread.start()                                 

    def run(self,world):
        server.shutdown()
        process_obj= subprocess.Popen(["node","main.js","--port={}".format(foundry_port),"--world=%WORLD%".replace("%WORLD%",world)],cwd=foundry_directory)
        monitorPlayers(process_obj)

def get_logged_in_players(timeout=0.1):
    r=requests.get(foundry_url+"/join",timeout=timeout)

    par=AwfulScrape_nPlayers()
    par.feed(r.text)
    return par.nPlayers

def _get_world_url(item):
    return "<p><a href='/"+item[0]+"' >" + item[1][1]+"</a> </p>"


@route('/')
@route('/<world>')
def index(world=None):
    if (world == "join") or (world is None):
        return '<h1> Foundry not running - pick a world to start: </h1>'+"".join([_get_world_url(x) for x in world_mapping.items()])
                        
    requested_world_path,requested_world = world_mapping.get(world,[None,None])
    
    if requested_world is None:
        return template('<h1>Cannot find world <b> {{world}} </b></h1>',world=world)

    startFoundryWorld(requested_world_path)
    return """<html>
     <h1> Loading ... </h1> 
      <script>
        var timer = setTimeout(function() {
            window.location='"""+foundry_url+"""'
        }, 3000);
     </script>
     </html>"""

server=bottleManager()