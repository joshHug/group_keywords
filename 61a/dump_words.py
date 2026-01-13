import sqlite3
import os

DATABASE = 'words.db'

def print_all_words():
    # Check if db exists
    if not os.path.exists(DATABASE):
        print(f"Error: {DATABASE} not found in the current directory.")
        return

    try:
        # Connect to the database
        conn = sqlite3.connect(DATABASE)
        # Allows accessing columns by name (like row['text'])
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()

        # Select all words
        cursor.execute("SELECT * FROM words")
        rows = cursor.fetchall()

        if not rows:
            print("The database exists, but there are no words in the 'words' table.")
            return

        # Print Header
        print(f"{'ID':<5} | {'Text':<20} | {'Weight':<6} | {'Created By':<20} | {'Decay Start'}")
        print("-" * 80)

        # Iterate and print rows
        for row in rows:
            # Handle potential NULLs in decay_start or created_by
            decay = row['decay_start'] if row['decay_start'] else "Active (No Decay)"
            creator = row['created_by'] if row['created_by'] else "Unknown"
            
            print(f"{row['id']:<5} | {row['text']:<20} | {row['weight']:<6} | {creator:<20} | {decay}")

    except sqlite3.Error as e:
        print(f"An error occurred accessing the database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print_all_words()
