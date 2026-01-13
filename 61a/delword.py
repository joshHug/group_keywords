import sys
from app import app, get_db

# USAGE: python delword.py <word_text>

def delete_word(target_text):
    # We must wrap DB operations in the app context so get_db() works
    with app.app_context():
        db = get_db()
        
        # 1. Find the word ID
        cursor = db.execute('SELECT id, text FROM words WHERE text = ?', (target_text,))
        row = cursor.fetchone()

        if row:
            word_id = row['id']
            try:
                # 2. Delete the word
                # (Your schema has ON DELETE CASCADE, so upvotes will auto-delete)
                db.execute('DELETE FROM words WHERE id = ?', (word_id,))
                db.commit()
                print(f"✅ Successfully deleted: '{target_text}' (ID: {word_id})")
            except Exception as e:
                print(f"❌ Database error: {e}")
        else:
            print(f"⚠️  Word '{target_text}' not found.")
            
            # Optional: Check for partial matches to be helpful
            cursor = db.execute("SELECT text FROM words WHERE text LIKE ?", (f"%{target_text}%",))
            matches = cursor.fetchall()
            if matches:
                print(f"   Did you mean: {', '.join([m['text'] for m in matches])}?")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delword.py <word_text>")
    else:
        # Handle multi-word inputs if necessary (though your app converts spaces to underscores)
        word_input = " ".join(sys.argv[1:])
        
        # Ensure we match the exact format stored in DB (lowercase)
        # Your app normally underscores spaces, but we'll trust the admin knows what to type.
        delete_word(word_input)
