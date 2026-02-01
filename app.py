
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
import os

app = Flask(__name__)

# Database initialization
def init_db():
    conn = sqlite3.connect('requests.db')
    c = conn.cursor()
    
    # Create requests table with episode tracking columns
    c.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_name TEXT NOT NULL,
            votes INTEGER DEFAULT 1,
            status TEXT DEFAULT 'Pending',
            total_episodes INTEGER DEFAULT 0,
            uploaded_episodes INTEGER DEFAULT 0
        )
    ''')
    
    # Create vote_logs table for IP tracking
    c.execute('''
        CREATE TABLE IF NOT EXISTS vote_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            user_ip TEXT NOT NULL,
            UNIQUE(request_id, user_ip)
        )
    ''')
    
    # Check if columns exist, if not add them (for existing databases)
    try:
        c.execute('SELECT total_episodes, uploaded_episodes FROM requests LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE requests ADD COLUMN total_episodes INTEGER DEFAULT 0')
        c.execute('ALTER TABLE requests ADD COLUMN uploaded_episodes INTEGER DEFAULT 0')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

@app.route('/')
def index():
    """Home page - Display all requests sorted by votes (highest first)"""
    conn = sqlite3.connect('requests.db')
    c = conn.cursor()
    c.execute('SELECT * FROM requests ORDER BY votes DESC')
    requests_data = c.fetchall()
    c.execute('SELECT COUNT(*) FROM requests')
    request_count = c.fetchone()[0]
    conn.close()
    return render_template('index.html', requests=requests_data, request_count=request_count)

@app.route('/add', methods=['POST'])
def add_request():
    """Add a new anime request (max 10 limit)"""
    anime_name = request.form.get('anime_name', '').strip()
    total_episodes = request.form.get('total_episodes', 0)
    
    if anime_name:
        conn = sqlite3.connect('requests.db')
        c = conn.cursor()
        
        # Check if limit reached (max 10 requests)
        c.execute('SELECT COUNT(*) FROM requests')
        count = c.fetchone()[0]
        
        if count < 10:
            try:
                total_episodes = int(total_episodes)
            except (ValueError, TypeError):
                total_episodes = 0
            
            c.execute('INSERT INTO requests (anime_name, votes, status, total_episodes, uploaded_episodes) VALUES (?, 1, ?, ?, 0)', 
                      (anime_name, 'Pending', total_episodes))
            conn.commit()
        
        conn.close()
    
    return redirect(url_for('index'))

@app.route('/vote/<int:id>')
def vote(id):
    """Increment vote count for a request (IP-based restriction)"""
    user_ip = request.remote_addr
    
    conn = sqlite3.connect('requests.db')
    c = conn.cursor()
    
    # Check if this IP has already voted for this request
    c.execute('SELECT * FROM vote_logs WHERE request_id = ? AND user_ip = ?', (id, user_ip))
    existing_vote = c.fetchone()
    
    if not existing_vote:
        # Increment vote count
        c.execute('UPDATE requests SET votes = votes + 1 WHERE id = ?', (id,))
        # Log the vote
        c.execute('INSERT INTO vote_logs (request_id, user_ip) VALUES (?, ?)', (id, user_ip))
        conn.commit()
    
    conn.close()
    return redirect(url_for('index'))

@app.route('/owner_panel')
def owner_panel():
    """Admin panel - Show all requests sorted by newest"""
    conn = sqlite3.connect('requests.db')
    c = conn.cursor()
    c.execute('SELECT * FROM requests ORDER BY id DESC')
    requests_data = c.fetchall()
    conn.close()
    return render_template('admin.html', requests=requests_data)

@app.route('/update_status/<int:id>/<new_status>')
def update_status(id, new_status):
    """Update the status of a request"""
    if new_status in ['Pending', 'Processing', 'Uploaded']:
        conn = sqlite3.connect('requests.db')
        c = conn.cursor()
        c.execute('UPDATE requests SET status = ? WHERE id = ?', (new_status, id))
        conn.commit()
        conn.close()
    
    return redirect(url_for('owner_panel'))

@app.route('/update_progress/<int:id>', methods=['POST'])
def update_progress(id):
    """Update episode progress for a request"""
    total_episodes = request.form.get('total_episodes', 0)
    uploaded_episodes = request.form.get('uploaded_episodes', 0)
    
    try:
        total_episodes = int(total_episodes)
        uploaded_episodes = int(uploaded_episodes)
        
        conn = sqlite3.connect('requests.db')
        c = conn.cursor()
        c.execute('UPDATE requests SET total_episodes = ?, uploaded_episodes = ? WHERE id = ?', 
                  (total_episodes, uploaded_episodes, id))
        conn.commit()
        conn.close()
    except ValueError:
        pass
    
    return redirect(url_for('owner_panel'))

@app.route('/delete/<int:id>')
def delete(id):
    """Delete a request"""
    conn = sqlite3.connect('requests.db')
    c = conn.cursor()
    c.execute('DELETE FROM requests WHERE id = ?', (id,))
    c.execute('DELETE FROM vote_logs WHERE request_id = ?', (id,))  # Clean up vote logs
    conn.commit()
    conn.close()
    return redirect(url_for('owner_panel'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
