import subprocess
import time
import sqlite3
import sys
import urllib.request
import urllib.parse

sys.stdout.reconfigure(encoding='utf-8')

python_exe = r"C:\Users\Orange Zhouhao Pang\.conda\envs\douyin-scrawl\python.exe"

keywords = ["人工智能", "自驾游", "美食制作"]

for kw in keywords:
    print(f"\n--- Testing keyword: {kw} ---")
    
    # 1. Scrape
    print("1. Running spider...")
    cmd_spider = [python_exe, "backend/spider.py", "--keyword", kw, "--limit", "10"]
    # We use open explicitly just in case Playwright needs to show captcha, but we'll print stdout
    process = subprocess.Popen(cmd_spider, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    for line in process.stdout:
        print("SPIDER:", line, end="")
    process.wait()
    
    # 2. Clean
    print("2. Running cleaner...")
    cmd_cleaner = [python_exe, "backend/cleaner.py"]
    process = subprocess.Popen(cmd_cleaner, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    for line in process.stdout:
        print("CLEANER:", line, end="")
    process.wait()
    
    # Check DB
    try:
        conn = sqlite3.connect("backend/douyin_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM videos WHERE search_keyword = ?", (kw,))
        count = cursor.fetchone()[0]
        print(f"   Database check: {count} records found for '{kw}'.")
    except Exception as e:
        print(f"   Database check failed: {e}")
    finally:
        conn.close()
        
    # 3. API
    print("3. Checking API...")
    try:
        url = "http://127.0.0.1:8000/api/videos?keyword=" + urllib.parse.quote(kw)
        req = urllib.request.urlopen(url)
        print(f"   API verified: {req.getcode()} OK")
    except Exception as e:
        print(f"   API request failed: {e}")

print("\n--- Workflow finished! ---")
