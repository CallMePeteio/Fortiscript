
from cryptography.fernet import Fernet

import datetime
import modules
import sqlite3
import json
import time
import os

INSTANCE_FOLDER_PATH = "./instance"
sqliteConn = sqlite3.connect(INSTANCE_FOLDER_PATH + '/db.db')
cursor = sqliteConn.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")

def start(folderPath="./instance"):
    with open(folderPath + "/config.json") as f:
        constants = json.load(f)
    cipherSuite = Fernet(bytes(constants["encryptionKey"], encoding="utf-8"))


    cursor.execute("SELECT * from fortigate")
    fortigates = cursor.fetchall()

    return fortigates, cipherSuite, constants



filter = modules.Filter()
allFortigates, cipher, constants = start(INSTANCE_FOLDER_PATH)


#___________________________ Get Sys Stat ___________________________

def getLastCommand(fortigateId):
    sql = """
        SELECT * FROM get_sys_stat
        WHERE command_id = (
            SELECT MAX(command_id)
            FROM get_sys_stat
            WHERE fortigate_id = ?
        ) AND fortigate_id = ?
        """
    cursor.execute(sql, (fortigateId, fortigateId))
    lastCommand = cursor.fetchall()

    command = {}
    commandId = None
    for aspect in lastCommand: 
        if len(aspect) == 6:
            commandId = aspect[2]
            command[aspect[3]] = aspect[4]

    return command, commandId

def getSysStat(channel, cursor, fortigateId):
    sysStat = channel.execute("get sys stat") 
    if sysStat != None:
        sysStatFiltered = filter.getSysStatFilter(sysStat) # GETS THE FILTERED KEYPOINTS (DICT)
        lastCommand, lastCommandId = getLastCommand(fortigateId) # GETS THE LAST COMMAND MADE FOR THAT FORTIGATE


        newTime = 0
        if "system_time" in sysStatFiltered:
            newTime = sysStatFiltered["system_time"]



    # ----- FINDS THE BIGGEST "command_id" THEN ADDS +1 TO GET A UNIQUE: "command_id"
        cursor.execute("SELECT MAX(command_id) FROM get_sys_stat")
        biggestCommandId = cursor.fetchone()[0] 

        if biggestCommandId != None:
            uniqueComId = biggestCommandId +1
        else:
            uniqueComId = 1


    # ----- STORES EATCH DATAPOINT INSIDE A LSIT, REDUCE UNNECCECARY WRITES TO DB
        data = []
        for statName, statVal in sysStatFiltered.items():
            if statName in lastCommand:
                if lastCommand[statName] != statVal and statName != "system_time": # DOSENT COMPARE "system_time" BECAUSE IT ALWAYS CHANGES, "system_time" IS UPDATED LATER
                    print(statName, statVal)
                    data.append((fortigateId, uniqueComId, statName, statVal))
            else:
                data.append((fortigateId, uniqueComId, statName, statVal))


    # ----- UPDATES SYSTEM TIME
        if len(data) == 0:
            try:
                cursor.execute('''UPDATE get_sys_stat SET stat_val = ? WHERE command_id = ? AND stat_name = ?''', (newTime, lastCommandId, "system_time"))
                return
            except sqlite3.OperationalError as error:
                print(f"gather.py:   Ther ws an error updating time in get_sys_stat: {error}")
        else:
            data.append((fortigateId, uniqueComId, "system_time", newTime)) # INSERTS TIME BACK IN



        sql = '''
        INSERT INTO get_sys_stat (fortigate_id, command_id, stat_name, stat_val)
        VALUES (?, ?, ?, ?);
        '''
        cursor.executemany(sql, data)

    # ----- UPDATES HOSTNAME AND VDOM_ENABLED INSIDE "fortigate" TABLE
        if "hostname" in sysStatFiltered and "virtual_domain_configuration" in sysStatFiltered:
            vdomEnabled = sysStatFiltered["virtual_domain_configuration"]

            if vdomEnabled == "multiple":
                vdomEnabled = 1
            elif vdomEnabled == "disable":
                vdomEnabled = 0
            else:
                vdomEnabled = 0
                print("gather.py:    There was an error figuring out vdomEnabled. Defaulting to disabled")

            cursor.execute('''UPDATE fortigate SET hostname = ?, vdom_enabled = ? WHERE fortigate_id = ?''', (sysStatFiltered["hostname"], vdomEnabled, fortigateId))
        else:
            print("gather.py:    There was a problem updating hostname and sysStatFiltered. Doesent exist!")



#_______________________________ Show _______________________________

listdirStarts = lambda folderPath, startsWith: [f for f in os.listdir(folderPath) if f.startswith(startsWith)]
def showFindDiffrence(oldFile, newFile, excludeLines):
    outputStr = ""
    if oldFile != newFile:
        prevLines = oldFile.splitlines()
        outputLine = newFile.splitlines()

        for i, (prevLine, outputLine) in enumerate(zip(prevLines, outputLine)):
            if prevLine != outputLine and i+1 not in excludeLines:
                outputStr += f"\nLine {i + 1} changed:\nFrom:   {prevLine}\nTo:   {outputLine} \n"
 
    if outputStr == "":
        return False, outputStr
    else: 
        return True, outputStr 

def show(channel, fortigateId, fortigateIp, vdomId, confSaltLines, INSTANCE_FOLDER_PATH):
    confLogFileName = str(vdomId) + "_" + "log"
    
    fileStart = str(vdomId) + "_"
    fileName = fileStart + str(time.time())
    folderName = str(fortigateId) + "_" + fortigateIp
    folderPath = INSTANCE_FOLDER_PATH + "/txt/" + folderName


    lastMadeConfFile = None
    if not os.path.exists(folderPath):
        os.mkdir(folderPath)


# ----- FINDS THE LAST FILE MADE, WITH THE CORRECT ID (why so robust?)
    configs = listdirStarts(folderPath, fileStart)
    if len(configs) > 0:
        lastMadeConfTime = 0
        for configName in configs:
            if "_" in configName and os.path.isfile(folderPath + "/" + configName): # CHECKS VALID FILE NAME
                timeCreated = configName.split("_")[1] # GETS THE TIME.TIME STAMP (GRATER = CREATED LAST)

                try: # IF IT ISNT A CORRECT FLOAT
                    if float(timeCreated) > lastMadeConfTime: 
                        lastMadeConfTime = float(timeCreated)                
                except ValueError as error:
                    if configName != confLogFileName:
                        print(f"gather.py:    There was an error converting to float: {error}")
            else:
                print(f"gather.py    There was an error with a file: {configName}")


            lastMadeConfFile = str(vdomId) + "_" + str(lastMadeConfTime)



# ----- RUNS THE SHOW COMMAND & FILTERS IT
    output = channel.execute("show")
    outputFiltered = filter.showFilter(output)


# ----- CHECKS FOR DIFFRENCE BETWEEN NEW AND OLD CONF, if:True THEN IT SAVES THE NEW CONF & APPEND THE UPDATES TO THE LOG FILE.
# NOTE: need to write this code cleaner/better
    if lastMadeConfFile != None and outputFiltered != None: 
        
        prevConfFile = modules.readTxt(folderPath + "/" + lastMadeConfFile) # READS THE PREVIUS MADE CONF FILE
        diffrenceBool, diffrenceSTR = showFindDiffrence(prevConfFile, outputFiltered, confSaltLines) # CHECKS THE DIFFRNECE

        if diffrenceBool == True:
            modules.writeTXT(folderPath + "/" + fileName, outputFiltered) # SAVES THE NEWEST CONF

            diffrenceSTR = f"\n \n{'_'*80} \n" + str(datetime.datetime.now()) + diffrenceSTR
            modules.writeTXT(folderPath + "/" + confLogFileName, diffrenceSTR, method="a") # APPENDS CHANGES TO THE LOG FILE
    
    elif outputFiltered != None:
        with open(folderPath + "/" + fileName, 'w') as f: # THIS CODE IS RUN WHEN THERE IS NO FILE TO BEGIN WITH
            f.write(outputFiltered)



#_________________________ Get Sys Perf Stat ________________________

def getSysPerfStat(channel, cursor, fortigateId):
    perfStat = channel.execute("get sys perf stat")

    if perfStat != None:
        perfStatFiltered = filter.perfStatFilter(perfStat)

        if len(perfStatFiltered) >= 3:
            cpuData = perfStatFiltered[0].get('cpu', {})
            memoryData = perfStatFiltered[1].get('memory', {})
            uptime = perfStatFiltered[2].get('uptime', "")

            dataToInsert = (
                fortigateId,
                cpuData.get('user', None),
                cpuData.get('system', None),
                cpuData.get('nice', None),
                cpuData.get('idle', None),
                cpuData.get('iowait', None),
                cpuData.get('irq', None),
                memoryData.get('total', None),
                memoryData.get('used', None),
                memoryData.get('free', None),
                memoryData.get('freeable', None),
                uptime
            )

            sql = '''
                INSERT INTO pref_stat (
                    fortigate_id, cpu_user, cpu_system, cpu_nice, cpu_idle, cpu_iowait, cpu_irq,
                    memory_total, memory_used, memory_free, memory_freeable, uptime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                '''    
            cursor.execute(sql, dataToInsert)
            cursor.execute('''UPDATE fortigate SET uptime = ? WHERE fortigate_id = ?''', (uptime, fortigateId))


while True:
    for fortigate in allFortigates:
        startTime = time.time()

        print("Connecting")
        id, ip, username, passwordEncrypted = fortigate[0], fortigate[1], fortigate[2], fortigate[3]
        con = modules.Connection(ip, username, cipher.decrypt(passwordEncrypted).decode())
        channel = modules.Channel(con.openChannel())
        channel.startup()


        print("Get Sys stat!")
        getSysStat(channel, cursor, id)
        print("Show!")
        show(channel, id, ip, 7, constants["confSaltLines"], INSTANCE_FOLDER_PATH)
        print("Get pref stat!")
        getSysPerfStat(channel, cursor, id)


        print("closing")
        sqliteConn.commit()
        channel.close() 
        con.close()

        print(f"\n \n Elapsed time: {time.time() - startTime}")

        print("\n\n______________________________________________________________")


sqliteConn.close()
