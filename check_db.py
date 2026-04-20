import sqlite3, os

DB_PATH = os.path.join("backend", "douyin_data.db")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print("Tables:", tables)

for t in [r[0] for r in tables]:
    c.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  {t}: {c.fetchone()[0]} rows")

c.execute("SELECT search_keyword, COUNT(*) FROM videos GROUP BY search_keyword")
print("\nVideos by keyword:")
for row in c.fetchall():
    print(f"  [{row[0]}] -> {row[1]} rows")

conn.close()
