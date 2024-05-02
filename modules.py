


import paramiko
import socket
import rich
import time
import re

#------- Wait for data to be available on the channel within a specified timeout
# Minimum func return time is: burstTimeout
# Maximum func return time is: timeout
#def terminalScreen(channel, stopString=None, timeout=10, burstTimeout=0.8):
#    output = ""
#    totalTimeoutTime = time.time() + timeout
#
#
## ----- STOPS IF END STRING (most reliable, for big data. Cant be used for evrything)
#    if stopString != None:
#        while time.time() < totalTimeoutTime:
#            if channel.recv_ready():
#                output += channel.recv(9999).decode('utf-8')
#                totalTimeoutTime = time.time() + timeout
#
#            if output.endswith(stopString) == True:
#                #print("IT WORKED :) \n \n \n \n")
#                break
#
#            time.sleep(0.1)
#
#
#
## ----- STOPS BASED ON TIME
#    else:
#        burstTimeoutTime = time.time() + burstTimeout
#        while time.time() < totalTimeoutTime:
#            if channel.recv_ready():
#                output += channel.recv(9999).decode('utf-8')
#                burstTimeoutTime = time.time() + burstTimeout # RESETS THE BURST TIMEOUT
#
#            elif time.time() > burstTimeoutTime:
#                break
#            
#            time.sleep(0.2)  # Short sleep to prevent busy waiting
#   
#
#
#    if output != "":
#        return output
#    else:
#        return None  
#



def getTableColumns(cursor, tableName, onlyNames=True):
    cursor.execute(f"PRAGMA table_info({tableName});")
    columns = cursor.fetchall()

    if onlyNames == True:
        columns = [column[1] for column in columns]

    return columns


#------- Wait for data to be available on the channel within a specified timeout
# Minimum func return time is: burstTimeout
# Maximum func return time is: timeout
def terminalScreen(channel, timeout=10, burstTimeout=0.8):
    output = ""

    burstTimeoutTime = time.time() + burstTimeout
    totalTimeoutTime = time.time() + timeout

    while time.time() < totalTimeoutTime:
        if channel.recv_ready():
            output += channel.recv(9999).decode('utf-8')
            burstTimeoutTime = time.time() + burstTimeout # RESETS THE BURST TIMEOUT

        elif time.time() > burstTimeoutTime:
            break
       
        time.sleep(0.1)  # Short sleep to prevent busy waiting
    

    if output != "":
        return output
    else:
        return None    


class Channel:

    def __init__(self, channel):
        self.channel = channel

        
    def execute(self, command, enter=True, filter=True):
        if enter == True:
            self.channel.send(command + "\n")
        else: 
            self.channel.send(command)

        output = terminalScreen(self.channel)

        if filter == True:
            if output.endswith("# ") : # SMALL FILTER, REMOVES: VDOMS NAME # FROM THE END
                lastNewline = output.rfind("\n")
                output = output[:lastNewline]

            if command in output: # REMOVES THE TERMINAL COMMAND
                output = output.replace(command, "")

        return output



    def terminal(self):
        return terminalScreen(self.channel)

    def startup(self):
        initalPromt = self.terminal()
        if "Press 'a' to accept" in initalPromt:
            self.execute("a")
         

    def close(self):
        self.channel.close()

class Connection:
        
    def __init__(self, ipAddr, username, password):

        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(ipAddr, username=username, password=password)

        except paramiko.ssh_exception.AuthenticationException as error:
            raise Exception(f"modules.py:   Authentication error: {error}")

        except socket.gaierror as error:
            raise Exception(f"modules.py:   There was an error connecting to fortigate (Wrong ip): {error}")
    

    #gaierror

    def openChannel(self):
        channel = self.client.get_transport().open_session()
        channel.get_pty()
        channel.invoke_shell()
        return channel

    def execute(self, command):
        stdin, stdout, stderr = self.client.exec_command(command)
        return stdout, stderr
    
    def close(self):
        self.client.close()



class Filter:

    def __init__(self):
        pass


    def replaceChar(self, string, replaceWith, replaceList):
        for replaceChar in replaceList: # REPLACES CHARS IN LIST WITH _ 
            if replaceChar in string:
                string = string.replace(replaceChar, replaceWith)

        return string


    def getSysStatFilter(self, input):

        aspects = input.split("\n")
        output = {}

        for aspect in aspects:
            aspect = aspect.replace("\r", "")
            if len(aspect) >= 3:

                splittedAspect = aspect.split(":")
                value = ":".join(splittedAspect[1:]).lower() # JOINS THE REST OF THE ASPECT
                
                key = splittedAspect[0] # FIRST WILL ALWAYS BE KEY
                key = self.replaceChar(key, "_", ["-", " ", "/"]) # REPLACES THE LIST WITH THE SECOND STRING (_)

                if " " == key[0]:
                    key = key[1:]

                if " " == value[0]:
                    value = value[1:]
            
                output[key.lower()] = value

        return output