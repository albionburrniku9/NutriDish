import sqlite3

def migrate():
    conn = sqlite3.connect('instance/nutridish_v2.db')
    cursor = conn.cursor()
    
    try:
        # Add is_pro column
        cursor.execute('ALTER TABLE user ADD COLUMN is_pro BOOLEAN DEFAULT 0')
        print("Added is_pro column.")
    except sqlite3.OperationalError as e:
        print(f"Error adding is_pro (might already exist): {e}")

    try:
        # Add generations_used column
        cursor.execute('ALTER TABLE user ADD COLUMN generations_used INTEGER DEFAULT 0')
        print("Added generations_used column.")
    except sqlite3.OperationalError as e:
        print(f"Error adding generations_used (might already exist): {e}")

    try:
        # Add profile_image column
        cursor.execute('ALTER TABLE user ADD COLUMN profile_image TEXT')
        print("Added profile_image column.")
    except sqlite3.OperationalError as e:
        print(f"Error adding profile_image (might already exist): {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
