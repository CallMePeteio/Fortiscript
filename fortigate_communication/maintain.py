import logging
import sqlite3
import time



INSTANCE_FOLDER_PATH = "./instance"
sqliteConn = sqlite3.connect(INSTANCE_FOLDER_PATH + '/db.db')
cursor = sqliteConn.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")


#################################################################################
# This file is supposed to do some needed backend maintenence, it right now does:
#
# Removes old data from pref_stat table
# Removes old data from top_mem table
#################################################################################








MAINTANENCE_SLEEP = 60
DELETE_SLACK_MULTIPLIER = 0.1 # DETERMENS THE NUMBER OF ROWS TO BE DELETED AT ONCE (maxAmount * this var) 
REMOVE_INFO = {"pref_stat": 400, "top_mem": 1000}


def deleteOldestEntry(sqliteConn, cursor, tableName, numberOfRows):
    query = f"""
                DELETE FROM {tableName}
                WHERE id IN (
                    SELECT id FROM {tableName}
                    ORDER BY data_timestamp ASC
                    LIMIT {numberOfRows}
                )
            """
    cursor.execute(query)
    sqliteConn.commit()

def main(sqliteConn, logger):
    cursor = sqliteConn.cursor()
    while True:

        for table, maxAmount in REMOVE_INFO.items():
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            tableLength = cursor.fetchone()[0]

            deleteSlack = maxAmount * DELETE_SLACK_MULTIPLIER
            if tableLength > maxAmount + deleteSlack:
                deleteOldestEntry(sqliteConn, cursor, table, int(deleteSlack))


                logger.info(f"   Deleted {int(deleteSlack)} rows from: {table}")
            
            time.sleep(MAINTANENCE_SLEEP / len(REMOVE_INFO)) # MORE CONSTANT LOAD




if __name__ == "__main__":
    sqliteConn = sqlite3.connect(INSTANCE_FOLDER_PATH + '/db.db', check_same_thread=False)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)  # Set the logger to handle DEBUG and higher level logs

    logging.info("   Starting Maintain script")
    main(sqliteConn, logger)





