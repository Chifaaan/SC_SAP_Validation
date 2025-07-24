import mysql.connector
from config import DB_CONFIG

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