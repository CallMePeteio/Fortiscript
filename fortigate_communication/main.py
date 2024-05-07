
from cryptography.fernet import Fernet

import threading
import maintain
import logging
import modules
import sqlite3
import gather
import json
import time
import os

def start(folderPath="./instance"):
    with open(folderPath + "/config.json") as f:
        constants = json.load(f)
    cipherSuite = Fernet(bytes(constants["encryptionKey"], encoding="utf-8"))

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)  # Set the logger to handle DEBUG and higher level logs

    # Create handlers
    handlers = []
    if "logToFile" in constants and constants["logToFile"]:
        file_handler = logging.FileHandler(f'{folderPath}/log.log', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        handlers.append(file_handler)

    # Always add a stream handler to output to console
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    handlers.append(stream_handler)

    # Set formatter
    formatter = logging.Formatter('%(asctime)s  |%(levelname)s|%(message)s')
    for handler in handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return cipherSuite, constants, logger



INSTANCE_FOLDER_PATH = "./instance"

sqliteConn = sqlite3.connect(INSTANCE_FOLDER_PATH + "/db.db", check_same_thread=False)
cursor = sqliteConn.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")
cipher, constants, logger = start(INSTANCE_FOLDER_PATH)



thread = threading.Thread(target=maintain.main, args=(sqliteConn, logger))
thread.start()


while True:
    cursor.execute("SELECT * from fortigate")
    allFortigates = cursor.fetchall()
    
    for fortigate in allFortigates:
        logger.info(f"   Connecting to {fortigate[1]}")
        startTime = time.time()



    
        id, ip, username, passwordEncrypted = fortigate[0], fortigate[1], fortigate[2], fortigate[3]
        con = modules.Connection(ip, username, cipher.decrypt(passwordEncrypted).decode())
        channel = modules.Channel(con.openChannel(), logger)
        channel.startup()

        gather.getSysStat(channel, cursor, id, logger)
        gather.show(channel, id, ip, 7, constants["confSaltLines"], INSTANCE_FOLDER_PATH, logger)
        gather.getSysPerfStat(channel, cursor, id, logger)
        gather.diagSysTopMem(channel, cursor, id, logger)



        sqliteConn.commit()
        channel.close() 
        con.close()





        logger.info(f"   Disconnected!")
        logger.info(f"   Time elapsed: {time.time() - startTime}\n{"_"*100}\n ")
sqliteConn.close()