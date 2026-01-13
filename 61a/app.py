import sqlite3
import re
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, g

app = Flask(__name__)
DATABASE = 'words.db'
DECAY_DURATION_SECONDS = 10000000  # 2 hours

# --- CONFIGURATION ---
ADMINS = {'kayo@berkeley.edu', 'h___@berkeley.edu'} 

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

def get_current_user():
    email = request.headers.get('X-Auth-Email')
    if not email:
        email = request.headers.get('X-Auth-User')
    if not email:
        email = 'anonymous@dev.local'
    return email

def init_db():
    with app.app_context():
        db = get_db()
        
        # 1. Create Tables
        db.execute('''
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL UNIQUE,
                weight REAL NOT NULL DEFAULT 1, 
                decay_start TIMESTAMP, -- New column to track when decay began
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
        
        # 2. Migration: Ensure existing DBs get the new column
        try:
            db.execute("ALTER TABLE words ADD COLUMN decay_start TIMESTAMP")
        except sqlite3.OperationalError:
            pass # Column likely already exists
    
        try:
            db.execute("ALTER TABLE words ADD COLUMN description TEXT")
        except sqlite3.OperationalError:
            pass

        db.commit()

# --- HELPER: Calculate Decay ---
def process_decay(word_dict):
    """
    Calculates the effective weight. 
    Returns modified dict and a boolean indicating if it should be deleted.
    """
    if word_dict['decay_start']:
        try:
            # Parse timestamp. format usually: YYYY-MM-DD HH:MM:SS.ssssss
            start_time = datetime.strptime(word_dict['decay_start'], '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            try:
                # Fallback for seconds without microseconds
                start_time = datetime.strptime(word_dict['decay_start'], '%Y-%m-%d %H:%M:%S')
            except:
                return word_dict, False # Error parsing, skip decay

        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Linear Decay Formula: 1.0 -> 0.0 over 2 hours
        decay_amount = elapsed / DECAY_DURATION_SECONDS
        new_weight = 1.0 - decay_amount

        if new_weight <= 0:
            return word_dict, True # Mark for deletion
        
        word_dict['weight'] = new_weight
        
    return word_dict, False

@app.route('/group_keywords/61a/')
def index():
    return render_template('index.html')

@app.route('/group_keywords/61a/float')
def float_view():
    return render_template('index.html')

@app.route('/group_keywords/61a/list')
def list_view():
    return render_template('list.html')

@app.route('/group_keywords/61a/api/words', methods=['GET'])
def get_words():
    user_email = get_current_user()
    db = get_db()
    cursor = db.execute('SELECT * FROM words')
    
    words = []
    is_admin = user_email in ADMINS
    ids_to_delete = []

    for row in cursor.fetchall():
        word_dict = dict(row)
        
        # ### NEW LOGIC: Calculate Decay
        word_dict, should_delete = process_decay(word_dict)
        
        if should_delete:
            ids_to_delete.append(word_dict['id'])
            continue

        if not is_admin:
            word_dict.pop('created_by', None)
        
        words.append(word_dict)

    # Lazy Deletion: Clean up dead words
    if ids_to_delete:
        for wid in ids_to_delete:
            db.execute('DELETE FROM upvotes WHERE word_id = ?', (wid,))
            db.execute('DELETE FROM words WHERE id = ?', (wid,))
        db.commit()

    return jsonify(words)

@app.route('/group_keywords/61a/api/user_data', methods=['GET'])
def get_user_data():
    user_email = get_current_user()
    db = get_db()
    
    # Need to process decay here too so user lists assume correct values
    created_cursor = db.execute('SELECT id, text, weight, decay_start FROM words WHERE created_by = ?', (user_email,))
    created_words = []
    for row in created_cursor.fetchall():
        w, delete = process_decay(dict(row))
        if not delete: created_words.append(w)
    
    upvoted_cursor = db.execute('''
        SELECT w.id, w.text, w.weight, w.decay_start
        FROM words w 
        JOIN upvotes u ON w.id = u.word_id 
        WHERE u.user_email = ?
    ''', (user_email,))
    
    upvoted_words = []
    for row in upvoted_cursor.fetchall():
        w, delete = process_decay(dict(row))
        if not delete: upvoted_words.append(w)
    
    return jsonify({
        'user_id': user_email,
        'created': created_words,
        'upvoted': upvoted_words,
        'is_admin': user_email in ADMINS
    })

@app.route('/group_keywords/61a/api/words', methods=['POST'])
def add_word():
    data = request.json
    raw_text = data.get('text', '').strip()
    
    text = raw_text.lower()
    text = text.replace(' ', '_')
    text = re.sub(r'[^a-z0-9_]', '', text)
    
    if len(text) > 20:
        text = text[:20]

    user_email = get_current_user()

    if not text:
        return jsonify({'error': 'Invalid text provided'}), 400

    db = get_db()

    if user_email not in ADMINS:
        cursor = db.execute('SELECT COUNT(*) as count FROM words WHERE created_by = ?', (user_email,))
        user_word_count = cursor.fetchone()['count']
        if user_word_count >= 3:
            return jsonify({'error': 'Limit reached', 'message': 'You have already contributed 3 words!'}), 403

    try:
        # ### NEW LOGIC: Start decay immediately upon creation (weight 1)
        now = datetime.now()
        db.execute('INSERT INTO words (text, weight, decay_start, created_by) VALUES (?, 1, ?, ?)', (text, now, user_email))
        db.commit()
        return jsonify({'status': 'added', 'text': text})
    except sqlite3.IntegrityError:
        return jsonify({'status': 'exists', 'text': text, 'message': 'Word already exists'}), 200

@app.route('/group_keywords/61a/api/words/<int:word_id>/delete', methods=['DELETE'])
def delete_created_word(word_id):
    user_email = get_current_user()
    db = get_db()
    
    cursor = db.execute('SELECT * FROM words WHERE id = ? AND created_by = ?', (word_id, user_email))
    word = cursor.fetchone()
    
    if not word:
        return jsonify({'error': 'Unauthorized or Not Found'}), 403
    
    # Process decay to get real weight
    w_dict, _ = process_decay(dict(word))
    weight = w_dict['weight']
    
    if weight <= 2:
        try:
            db.execute('DELETE FROM upvotes WHERE word_id = ?', (word_id,))
            db.execute('DELETE FROM words WHERE id = ?', (word_id,))
        except Exception as e:
            db.rollback()
            return jsonify({'error': 'Database error'}), 500
    else:
        # If manually removing ownership of a high weight word, we decrement logic?
        # Standard logic: weight - 1. If that hits 1, start decay.
        new_weight = weight - 1
        decay_val = None
        if new_weight <= 1:
             new_weight = 1
             decay_val = datetime.now()

        db.execute("UPDATE words SET weight = ?, decay_start = ?, created_by = 'system_orphan' WHERE id = ?", (new_weight, decay_val, word_id))
    
    db.commit()
    return jsonify({'status': 'removed'})

@app.route('/group_keywords/61a/api/words/<int:word_id>/upvote', methods=['POST'])
def upvote_word(word_id):
    user_email = get_current_user()
    db = get_db()

    if user_email not in ADMINS:
        cursor = db.execute('SELECT COUNT(*) as count FROM upvotes WHERE user_email = ?', (user_email,))
        total_votes = cursor.fetchone()['count']
        if total_votes >= 10:
            return jsonify({'error': 'User limit reached', 'message': 'You have used all 10 of your upvotes!'}), 403

    cursor = db.execute('SELECT 1 FROM upvotes WHERE user_email = ? AND word_id = ?', (user_email, word_id))
    if cursor.fetchone():
        return jsonify({'error': 'Already voted', 'message': 'You can only upvote a word once.'}), 403

    cursor = db.execute('SELECT weight, decay_start, created_by FROM words WHERE id = ?', (word_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({'error': 'Word not found'}), 404
    
    if row['created_by'] == user_email:
        return jsonify({'error': 'Self-voting', 'message': 'You cannot upvote your own word.'}), 403
    
    # Process current decay state
    w_dict, should_delete = process_decay(dict(row))
    if should_delete:
         return jsonify({'error': 'Word expired'}), 404

    current_weight = w_dict['weight']

    if current_weight >= 20:
        return jsonify({'error': 'Max weight reached', 'message': 'This word has reached the maximum rank.'}), 403

    try:
        db.execute('INSERT INTO upvotes (user_email, word_id) VALUES (?, ?)', (user_email, word_id))
        
        # ### NEW LOGIC: Snap to 2 if decaying, else add 1
        if row['decay_start'] is not None:
            # It was in the [0, 1] range (or exactly 1). Snap to 2. Stop decay.
            db.execute('UPDATE words SET weight = 2, decay_start = NULL WHERE id = ?', (word_id,))
        else:
            # Standard upvote
            db.execute('UPDATE words SET weight = weight + 1 WHERE id = ?', (word_id,))
            
        db.commit()
        return jsonify({'status': 'upvoted'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/group_keywords/61a/api/words/<int:word_id>/vote', methods=['DELETE'])
def remove_upvote(word_id):
    user_email = get_current_user()
    db = get_db()
    
    cursor = db.execute('SELECT 1 FROM upvotes WHERE user_email = ? AND word_id = ?', (user_email, word_id))
    if not cursor.fetchone():
        return jsonify({'error': 'Vote not found'}), 404
        
    try:
        db.execute('DELETE FROM upvotes WHERE user_email = ? AND word_id = ?', (user_email, word_id))
        
        # ### NEW LOGIC: Decrement. If <= 1, restart decay.
        # We need to check the current weight in the DB
        cursor = db.execute('SELECT weight FROM words WHERE id = ?', (word_id,))
        row = cursor.fetchone()
        if row:
            curr_db_weight = row['weight']
            new_weight = curr_db_weight - 1
            
            if new_weight <= 1:
                # Snap to 1 and start decaying
                now = datetime.now()
                db.execute('UPDATE words SET weight = 1, decay_start = ? WHERE id = ?', (now, word_id))
            else:
                # Just decrement
                db.execute('UPDATE words SET weight = weight - 1 WHERE id = ?', (word_id,))

        db.commit()
        return jsonify({'status': 'vote_removed'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/group_keywords/61a/api/words/<int:word_id>/description', methods=['POST'])
def update_description(word_id):
    user_email = get_current_user()
    data = request.json
    # Enforce max 40 chars
    description = data.get('description', '').strip()[:40] 

    db = get_db()
    # Verify ownership
    cursor = db.execute('SELECT created_by FROM words WHERE id = ?', (word_id,))
    row = cursor.fetchone()

    if not row or row['created_by'] != user_email:
        return jsonify({'error': 'Unauthorized'}), 403

    db.execute('UPDATE words SET description = ? WHERE id = ?', (description, word_id))
    db.commit()
    return jsonify({'status': 'updated', 'description': description})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)
