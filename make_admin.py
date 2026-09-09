import sqlite3
import database

database.init_db()

username_to_promote = "ashna"

conn = sqlite3.connect("meditrust.db")
conn.execute("UPDATE users SET role='admin' WHERE username=?", (username_to_promote,))
conn.commit()
conn.close()

print(f"{username_to_promote} is now an admin.")