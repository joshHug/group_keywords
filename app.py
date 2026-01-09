import sqlite3
from flask import Flask, render_template, request, jsonify, g

app = Flask(__name__)
DATABASE = 'words.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        # Added 'created_by' column
        db.execute('''
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL UNIQUE,
                weight INTEGER NOT NULL DEFAULT 1,
                created_by TEXT
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

@app.route('/group_keywords/api/words', methods=['POST'])
def add_word():
    data = request.json
    text = data.get('text', '').strip()
    
    # 1. GET THE USER ID (EMAIL)
    # We use a default for local testing, but in production, this comes from Nginx
    user_email = request.headers.get('X-Email', 'anonymous@dev.local')

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    db = get_db()

    # 2. CHECK SUBMISSION COUNT
    # Count how many words this specific email has already added
    cursor = db.execute('SELECT COUNT(*) as count FROM words WHERE created_by = ?', (user_email,))
    result = cursor.fetchone()
    user_word_count = result['count']

    if user_word_count >= 3:
        return jsonify({
            'error': 'Limit reached', 
            'message': 'You have already contributed 3 words!'
        }), 403

    try:
        # 3. INSERT WITH USER ID
        # We add user_email to the INSERT statement
        db.execute('INSERT INTO words (text, weight, created_by) VALUES (?, 1, ?)', (text, user_email))
        db.commit()
        return jsonify({'status': 'added', 'text': text})
    except sqlite3.IntegrityError:
        # If word exists, we don't count it against their limit, but we don't add it either
        return jsonify({'status': 'exists', 'text': text, 'message': 'Word already exists'}), 200

@app.route('/group_keywords/api/words/<int:word_id>/upvote', methods=['POST'])
def upvote_word(word_id):
    db = get_db()
    db.execute('UPDATE words SET weight = weight + 1 WHERE id = ?', (word_id,))
    db.commit()
    return jsonify({'status': 'upvoted'})

if __name__ == '__main__':
    init_db()  # Ensure DB exists on startup
    app.run(debug=True)
