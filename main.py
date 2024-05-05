
from cryptography.fernet import Fernet

import modules
import sqlite3
import gather
import json


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



allFortigates, cipher, constants = start(INSTANCE_FOLDER_PATH)

for fortigate in allFortigates:

    id, ip, username, passwordEncrypted = fortigate[0], fortigate[1], fortigate[2], fortigate[3]
    con = modules.Connection(ip, username, cipher.decrypt(passwordEncrypted).decode())
    channel = modules.Channel(con.openChannel())
    channel.startup()

    gather.getSysStat(channel, cursor, id)
    gather.show(channel, id, ip, 7, constants["confSaltLines"], INSTANCE_FOLDER_PATH)
    gather.getSysPerfStat(channel, cursor, id)
    gather.diagSysTopMem(channel, cursor, id)

    sqliteConn.commit()
    channel.close() 
    con.close()
sqliteConn.close()