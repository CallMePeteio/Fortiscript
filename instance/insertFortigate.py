from cryptography.fernet import Fernet
import sqlite3
import json


conn = sqlite3.connect('./instance/db.db')
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")
print("Connection established.")



with open('./instance/config.json') as f:
    constants = json.load(f)
cipher_suite = Fernet(bytes(constants["encryptionKey"], encoding="utf-8"))


def makeDb():
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fortigate (
            fortigate_id INTEGER PRIMARY KEY,
            ip_addr TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            hostname TEXT,
            vdom_enabled INTEGER,
            uptime TEXT
        );
    ''')




    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vdom (
            vdom_id INTEGER PRIMARY KEY,
            fortigate_id INTEGER,
            FOREIGN KEY (fortigate_id) REFERENCES fortigate (fortigate_id)
        );
    ''')
    #print("Tables created successfully.")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS get_sys_stat (
            id INTEGER PRIMARY KEY,
            fortigate_id INTEGER,
            command_id INTEGER,
            stat_name TEXT,
            stat_val TEXT,
            data_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fortigate_id) REFERENCES fortigate (fortigate_id)
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS top_mem (
            id INTEGER PRIMARY KEY,
            fortigate_id INTEGER,
            command_id INTEGER,
            process_name TEXT,
            process_id INTEGER,
            memory_usage INTEGER,
            data_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fortigate_id) REFERENCES fortigate (fortigate_id)
        );
    ''')


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pref_stat (
            id INTEGER PRIMARY KEY,
            fortigate_id INTEGER,
            cpu_user FLOAT,
            cpu_system FLOAT,
            cpu_nice FLOAT,
            cpu_idle FLOAT,
            cpu_iowait FLOAT,
            cpu_irq FLOAT,
            memory_total FLOAT,
            memory_used FLOAT,
            memory_free FLOAT,
            memory_freeable FLOAT,
            uptime TEXT,
            data_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fortigate_id) REFERENCES fortigate (fortigate_id)
        );
    ''')

makeDb()

def insertFortigate(ipAddr, username, password):
    encryptedPassword = cipher_suite.encrypt(password.encode())

    cursor.execute('''INSERT INTO fortigate(ip_addr, username, password) VALUES(?,?,?)''', (ipAddr, username, sqlite3.Binary(encryptedPassword)))
    conn.commit()

insertFortigate("Fortigate_ip_address", "fortigate_user", "fortigate_password_plaintext")

def deleteFortigate(id):
    cursor.execute('DELETE FROM fortigate WHERE fortigate_id = ?', (id,))
    conn.commit()


conn.close()

