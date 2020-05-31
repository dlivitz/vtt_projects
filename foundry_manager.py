
import requests
from bottle import route, run, template
import subprocess
from html.parser import HTMLParser
import threading
import time


foundry_url="YOUR FOUNDRY URL"

class AwfulScrape_nPlayers_worldname(HTMLParser):
    #This is why javascript was invented 
    
    def __init__(self):
        super().__init__()
        
        
        self.in_header=False
        self.in_label=False #We are searching for a "Current Players:" label
        self.previous_label_players=False  #If we found it, grab the first input field 
        self.nPlayers=None  #If nothing is found crash 
        self.worldName=None
        
    def handle_starttag(self, tag, attrs):
        if tag == "header":
            self.in_header=True
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
        if self.in_header:
            if len(data.strip()) > 0:
                self.worldName=data
        if self.in_label:
            if "Current Players:" in data:  
                self.previous_label_players=True
            else:
                self.previous_label_players=False

class monitorPlayers(object):
    #We're just gonna check every five minutes..

    def __init__(self, foundry_proccess):
        self.foundry_proccess = foundry_proccess

        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True 
        thread.start() 
    def run(self):
        #Keep checking number of players 
        #If it's been 0 for 5 minutes, return to setup 

        zero_players=False
        while True:
            n_players,world_name=get_logged_in_players_world() #Returns "None" if in setup etc so it's safe
            if (n_players == 0) and zero_players:
                self.foundry_proccess.send_signal(2)
                self.foundry_proccess.send_signal(2) ##I think I need to send this twice? 
                self.foundry_proccess.wait()
                break
                
            time.sleep(300) #Wait five minutes 
            if n_players == 0:

                zero_players=True
            

def get_logged_in_players_world():
    r=requests.get(foundry_url+"/join",timeout=0.1) #This is so we don't wait too long for the world to start

    par=AwfulScrape_nPlayers_worldname()
    par.feed(r.text)
    return par.nPlayers,par.worldName


def start_foundry_world(world):
    process_obj= subprocess.Popen(["node","main.js","--world=%WORLD%".replace("%WORLD%",world)],cwd="whatever")
    monitorPlayers(process_obj)
    return process_obj

world_mapping={"strahd":["curse-of-strahd","Curse of Strahd"]}

@route('/<world>')
def index(world):
    requested_world_path,requested_world = world_mapping.get(world,[None,None])
    if requested_world is None:
        return template('<h1>Cannot find world <b> {{world}} </b></h1>',world=world)
    
    else:
        try:
            n_players,world_name=get_logged_in_players_world()
            if world_name != requested_world:
                return template('<h1><b>Currently {{n_players}} user[s] logged into {{world_name}}, please check back in a bit. </b></h1>', n_players=n_players,world_name=world_name)
        except: #Foundry is not running or something whatever 
            start_foundry_world(requested_world_path)
        return bottle.redirect(foundry_url+"/join")    
        
run(host='localhost', port=8085)
