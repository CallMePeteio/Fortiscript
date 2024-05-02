
from cryptography.fernet import Fernet

import modules
import sqlite3
import json
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

    return fortigates, cipherSuite



filter = modules.Filter()
allFortigates, cipher = start(INSTANCE_FOLDER_PATH)


def getSysStat(channel, cursor):
    sysStat = channel.execute("get sys stat") 
    sysStatFiltered = filter.getSysStatFilter(sysStat) # GETS THE FILTERED KEYPOINTS (DICT)

# ----- FINDS THE BIGGEST "command_id" THEN ADDS +1 TO GET A UNIQUE: "command_id"
    cursor.execute("SELECT MAX(command_id) FROM get_sys_stat")
    biggestCommandId = cursor.fetchone()[0] 

    if biggestCommandId != None:
        commandId = biggestCommandId +1
    else:
        commandId = 1

# ----- STORES EATCH DATAPOINT INSIDE A LSIT, REDUCE UNNECCECARY WRITES
    data = []
    for statName, statVal in sysStatFiltered.items():
        data.append((id, commandId, statName, statVal))

    # SQL INSERT statement
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

        cursor.execute('''UPDATE fortigate SET hostname = ?, vdom_enabled = ? WHERE fortigate_id = ?''', (sysStatFiltered["hostname"], vdomEnabled, id))
    else:
        print("gather.py:    There was a problem updating hostname and sysStatFiltered. Doesent exist!")

#def show(channel, fortigateId, vdomId, INSTANCE_FOLDER_PATH):
#    folderPath = INSTANCE_FOLDER_PATH + "/txt"
#
#    if os.path.exists(folderPath):
#        prevConfig = modules.readTxt(folderPath)
#
#    output = channel.execute("show")
#    with open('da', 'w') as f:
#        f.write(output)


    



for fortigate in allFortigates:

    id, ip, username, passwordEncrypted = fortigate[0], fortigate[1], fortigate[2], fortigate[3]
    con = modules.Connection(ip, username, cipher.decrypt(passwordEncrypted).decode())
    channel = modules.Channel(con.openChannel())
    channel.startup()


    #getSysStat(channel, cursor)
    #show(channel, id, 1, INSTANCE_FOLDER_PATH)





    sqliteConn.commit()
    channel.close() 
    con.close()

sqliteConn.close()
