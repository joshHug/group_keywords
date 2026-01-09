import sqlite3
import re
from flask import Flask, render_template, request, jsonify, g

app = Flask(__name__)
DATABASE = 'words.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- HELPER: Get User Email Robustly ---
def get_current_user():
    # 1. Try X-Auth-Email (set by our updated Nginx)
    email = request.headers.get('X-Auth-Email')
    
    # 2. Try X-Auth-User (often the email in oauth2-proxy google provider)
    if not email:
        email = request.headers.get('X-Auth-User')

    # 3. Fallback for debugging/local dev
    if not email:
        email = 'anonymous@dev.local'
        
    return email

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL UNIQUE,
                weight INTEGER NOT NULL DEFAULT 1,
                created_by TEXT
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS upvotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                word_id INTEGER NOT NULL,
                UNIQUE(user_email, word_id),
                FOREIGN KEY(word_id) REFERENCES words(id) ON DELETE CASCADE
            )
        ''')
        db.commit()

@app.route('/group_keywords/')
def index():
    return render_template('index.html')

@app.route('/group_keywords/api/words', methods=['GET'])
def get_words():
    db = get_db()
    cursor = db.execute('SELECT * FROM words')
    words = [dict(row) for row in cursor.fetchall()]
    return jsonify(words)

@app.route('/group_keywords/api/user_data', methods=['GET'])
def get_user_data():
    # --- DEBUG PRINT (Optional: Remove after verifying) ---
    print("\n--- DEBUG HEADERS ---")
    print(f"X-Auth-Email: {request.headers.get('X-Auth-Email')}")
    print(f"X-Auth-User:  {request.headers.get('X-Auth-User')}")
    # ----------------------------------------------------

    user_email = get_current_user()
    db = get_db()
    
    created_cursor = db.execute('SELECT id, text, weight FROM words WHERE created_by = ?', (user_email,))
    created_words = [dict(row) for row in created_cursor.fetchall()]
    
    upvoted_cursor = db.execute('''
        SELECT w.id, w.text, w.weight 
        FROM words w 
        JOIN upvotes u ON w.id = u.word_id 
        WHERE u.user_email = ?
    ''', (user_email,))
    upvoted_words = [dict(row) for row in upvoted_cursor.fetchall()]
    
    return jsonify({
        'user_id': user_email,
        'created': created_words,
        'upvoted': upvoted_words
    })

@app.route('/group_keywords/api/words', methods=['POST'])
def add_word():
    data = request.json
    raw_text = data.get('text', '').strip()
    
    text = raw_text.lower()
    text = text.replace(' ', '_')
    text = re.sub(r'[^a-z0-9_]', '', text)
    
    if len(text) > 32:
        text = text[:32]

    user_email = get_current_user()

    if not text:
        return jsonify({'error': 'Invalid text provided'}), 400

    db = get_db()
    cursor = db.execute('SELECT COUNT(*) as count FROM words WHERE created_by = ?', (user_email,))
    user_word_count = cursor.fetchone()['count']

    if user_word_count >= 3:
        return jsonify({'error': 'Limit reached', 'message': 'You have already contributed 3 words!'}), 403

    try:
        db.execute('INSERT INTO words (text, weight, created_by) VALUES (?, 1, ?)', (text, user_email))
        db.commit()
        return jsonify({'status': 'added', 'text': text})
    except sqlite3.IntegrityError:
        return jsonify({'status': 'exists', 'text': text, 'message': 'Word already exists'}), 200

@app.route('/group_keywords/api/words/<int:word_id>/delete', methods=['DELETE'])
def delete_created_word(word_id):
    user_email = get_current_user()
    db = get_db()
    
    cursor = db.execute('SELECT * FROM words WHERE id = ? AND created_by = ?', (word_id, user_email))
    word = cursor.fetchone()
    
    if not word:
        return jsonify({'error': 'Unauthorized or Not Found'}), 403
    
    weight = word['weight']
    
    if weight <= 2:
        try:
            db.execute('DELETE FROM upvotes WHERE word_id = ?', (word_id,))
            db.execute('DELETE FROM words WHERE id = ?', (word_id,))
        except Exception as e:
            db.rollback()
            return jsonify({'error': 'Database error'}), 500
    else:
        db.execute("UPDATE words SET weight = weight - 1, created_by = 'system_orphan' WHERE id = ?", (word_id,))
    
    db.commit()
    return jsonify({'status': 'removed'})

@app.route('/group_keywords/api/words/<int:word_id>/upvote', methods=['POST'])
def upvote_word(word_id):
    user_email = get_current_user()
    db = get_db()

    cursor = db.execute('SELECT COUNT(*) as count FROM upvotes WHERE user_email = ?', (user_email,))
    total_votes = cursor.fetchone()['count']

    if total_votes >= 10:
        return jsonify({'error': 'User limit reached', 'message': 'You have used all 10 of your upvotes!'}), 403

    cursor = db.execute('SELECT 1 FROM upvotes WHERE user_email = ? AND word_id = ?', (user_email, word_id))
    if cursor.fetchone():
        return jsonify({'error': 'Already voted', 'message': 'You can only upvote a word once.'}), 403

    cursor = db.execute('SELECT weight FROM words WHERE id = ?', (word_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({'error': 'Word not found'}), 404
    
    if row['weight'] >= 20:
        return jsonify({'error': 'Max weight reached', 'message': 'This word has reached the maximum rank.'}), 403

    try:
        db.execute('INSERT INTO upvotes (user_email, word_id) VALUES (?, ?)', (user_email, word_id))
        db.execute('UPDATE words SET weight = weight + 1 WHERE id = ?', (word_id,))
        db.commit()
        return jsonify({'status': 'upvoted'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/group_keywords/api/words/<int:word_id>/vote', methods=['DELETE'])
def remove_upvote(word_id):
    user_email = get_current_user()
    db = get_db()
    
    cursor = db.execute('SELECT 1 FROM upvotes WHERE user_email = ? AND word_id = ?', (user_email, word_id))
    if not cursor.fetchone():
        return jsonify({'error': 'Vote not found'}), 404
        
    try:
        db.execute('DELETE FROM upvotes WHERE user_email = ? AND word_id = ?', (user_email, word_id))
        db.execute('UPDATE words SET weight = weight - 1 WHERE id = ?', (word_id,))
        db.commit()
        return jsonify({'status': 'vote_removed'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
