import sys

with open('server/database.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add security_whitelist table to init_db
init_db_marker = 'CREATE TABLE IF NOT EXISTS security_blocklist'
new_table = """CREATE TABLE IF NOT EXISTS security_whitelist (
        ip TEXT PRIMARY KEY,
        note TEXT,
        added_at INTEGER,
        added_by TEXT
    )
    """)

    cursor.execute(\"\"\"
    CREATE TABLE IF NOT EXISTS security_blocklist"""

content = content.replace(init_db_marker, new_table)

with open('server/database.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched database.py for whitelist table")
