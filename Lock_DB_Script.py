import sqlite3
import time
try:
    conn = sqlite3.connect('instance/app.db', timeout=0.1) # Use a short timeout so it fails fast
    print('Database locked successfully.')
    time.sleep(30)
except sqlite3.OperationalError as e:
    print(f'Failed to lock database: {e}')
finally:
    if 'conn' in locals() and conn:
        conn.close()
    print('Database lock released.')
