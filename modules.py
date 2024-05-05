

import paramiko
import logging
import socket
import time
import os


def readTxt(path):
    if os.path.exists(path):
        with open (path, "r") as myfile:
            data = myfile.read()
        return data
    return None

def writeTXT(path, text, method="w"):
    try:
        with open(path, method) as f: # SAVES THE NEWEST CONF
            f.write(text)
    except Exception as error:
        print("modules.py    There was an error writing to TXT: {error}")

def findNum(text):
    outputNum = []

    numStr = ""
    hasStartedNum = False
    length = len(text)
    for i, char in enumerate(text):
        if char.isdigit():
            numStr += char
            hasStartedNum = True

        elif char == '.' and i + 1 < length and text[i+1].isdigit() and hasStartedNum == True: # HANDLES FLOATS
            numStr += char

        elif numStr: 
            if "." in numStr:
                outputNum.append(float(numStr))
            elif numStr.isdigit():
                outputNum.append(int(numStr))

            numStr = ""
            hasStartedNum = False

    if numStr:  # Check after the loop to catch any trailing numbers
        outputNum.append(numStr)

    if len(outputNum) == 0:
        return None
    return outputNum



def getTableColumns(cursor, tableName, onlyNames=True):
    cursor.execute(f"PRAGMA table_info({tableName});")
    columns = cursor.fetchall()

    if onlyNames == True:
        columns = [column[1] for column in columns]

    return columns


#------- Wait for data to be available on the channel within a specified timeout
# Minimum func return time is: burstTimeout
# Maximum func return time is: timeout
def terminalScreen(channel, timeout=10, burstTimeout=0.9):
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
        return [None]   


class Channel:

    def __init__(self, channel):
        self.channel = channel

        
    def execute(self, command, enter=True, filter=True):
        if enter == True:
            self.channel.send(command + "\n")
        else: 
            self.channel.send(command)

        output = terminalScreen(self.channel)

        if filter == True and output != None:
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
        if initalPromt != None:
            if "Press 'a' to accept" in initalPromt:
                self.execute("a")
         

    def close(self):
        self.channel.close()

class Connection:
        
    def __init__(self, ipAddr, username, password):


        while True:
            try:
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.client.connect(ipAddr, username=username, password=password)
                break

            except paramiko.ssh_exception.AuthenticationException as error:
                raise Exception(f"modules.py:   Authentication error: {error}")

            except socket.gaierror as error:
                print(f"modules.py:   There was an error connecting to fortigate (Wrong ip, internett?): {error}")

            except TimeoutError as error:
                print("modules.py:   Got timed out while trying to connect to fortigate! Retrying in 10 sec")
                
            time.sleep(10)
    


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

                if len(splittedAspect) >= 2: 
                    value = ":".join(splittedAspect[1:]) # JOINS THE REST OF THE ASPECT

                    key = splittedAspect[0] # FIRST WILL ALWAYS BE KEY
                    key = self.replaceChar(key, "_", ["-", " ", "/"]) # REPLACES THE LIST WITH THE SECOND STRING (_)

                    key = key.strip()
                    value = value.strip()

                    output[key.lower()] = value.lower()

        return output
    
    def showFilter(self, text): # REMOVES \n
        
        if text != None:
            cleanedLines = []
            for line in text.strip().splitlines():
                cleaned_line = line.strip()
                cleanedLines.append(cleaned_line)

            result = '\n'.join(cleanedLines)
            return result
        
        return None
    
    
    def perfStatFilter(self, text):
        cleanedLines = []

        if text != None:
            for line in text.strip().splitlines():

                if line.startswith("Memory: "):
                    memStats = line.lower().split(",")
                    if len(memStats) >= 4:
                        total = findNum(memStats[0])[0]
                        used = findNum(memStats[1])[1]
                        free = findNum(memStats[2])[1]
                        freeable = findNum(memStats[3])[1]

                        cleanedLines.append({"memory": {"total": total, "used": used, "free": free, "freeable": freeable}})

                elif line.startswith("CPU states:"):
                    cpuStats = line.replace("CPU states:", "").strip()
                    cpuStats = cpuStats.lower().split(" ") # MAKES ['0%', 'user', '0%', 'system', '0%' OSV. FIRST VAL IS THE STRINGS VAL FOR SOME REASON

                    if len(cpuStats) >= 14:
                        cpuDict = {}
                        for i in range(1, len(cpuStats)-1, 2): # COUNTS: 1, 3, 5, 7 OSV   
                            label = cpuStats[i]
                            cpuStat = findNum(cpuStats[i-1])[0] # -1 BECAUSE THE FIRST % IS TIED TO THE SECOND LABEL
                            cpuDict[label] = cpuStat


                        cleanedLines.append({"cpu": cpuDict})

                elif line.startswith("Uptime:"):

                    uptime = line.replace("Uptime:", "")
                    uptime = [text for text in uptime.split(" ") if text != ""] # REMOVES UNECCECARY SPACES 
                    uptime = " ".join(uptime)

                    cleanedLines.append({"uptime": uptime.lower()})

            return cleanedLines 

        else:
            return text   

    def topMemFilter(self, text):

        outputDict = {}

        if text != None:
            for line in text.strip().split("\n"):
                line = line.replace("\r", "")
                processMemUsage = line.split(":") # EKS: ["node (192)", "1024563KB"]
    
                if len(processMemUsage) >= 2:
                    processName = processMemUsage[0].strip().split(" ")[0] # FINDS THE PROCESS NAME BY SPLITTING THE STRING BY " " AND TAKING THE FIRST INDEX
                    processName = self.replaceChar(processName, "_", ["-", " ", "/"]) # REPLACES THE LIST WITH THE SECOND STRING (_)
                                        
                    processId = findNum(processMemUsage[0]) # THE ONLY NUMBER IN THE FIRST STRING == PROCESSID
                    memUsage = findNum(processMemUsage[1]) # THE ONLY NUMBER IN THE SECOND STRING == MEMUSAGE

                    outputDict[processName.lower()] = {"processId": processId[0], "memUsage": memUsage[0]}
            
            if len(outputDict) != 0: # IF WE GATHERED SOM DATA
                return outputDict
        return None









