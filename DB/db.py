import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "database": os.getenv('DB_DATABASE'),
}


conn = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor()
cursor.execute("SELECT DATABASE();")
print("Connected to: ",
cursor.fetchone()[0])

cursor.execute("SHOW TABLES;")
tables = [table[0] for table in cursor.fetchall()]
print("Tables in Database:")
for table in tables:
    print(table)
    cursor.execute(f"DESCRIBE {table}")
    for column in cursor.fetchall():
        name,dtype,null,key, default, extra = column
        print (f" - {name} ({dtype}) {('NULLABLE' if null == 'YES' else 'NOT NULL')} {extra}")

cursor.close()
conn.close()