from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
import tensorflow as tf
import numpy as np
from PIL import Image

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create necessary directories
os.makedirs('database', exist_ok=True)
os.makedirs('static/uploads', exist_ok=True)

# Database path
DATABASE = 'database/ewaste.db'

# E-waste categories (adjust these to match your model's classes)
CATEGORIES = [
    'battery', 'keyboard', 'mouse', 'monitor', 'phone',
    'laptop', 'tablet', 'printer', 'speaker', 'cable'
]

# Load AI model
MODEL_PATH = 'models/best_transfer_model.h5'
model = None

def load_model():
    global model
    try:
        model = tf.keras.models.load_model(MODEL_PATH)
        print("✅ Model loaded successfully!")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        print("⚠️  App will run but classification won't work until model is loaded")

# Load model on startup
load_model()

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, email, created_at):
        self.id = id
        self.username = username
        self.email = email
        self.created_at = created_at

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, created_at FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        # Convert created_at string to datetime object if needed
        created_at = user_data[3]
        if isinstance(created_at, str):
            created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
        return User(user_data[0], user_data[1], user_data[2], created_at)
    return None

# Database helper functions
def get_db():
    conn = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create classification history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classification_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            predicted_class TEXT NOT NULL,
            confidence REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized!")

# Initialize database
init_db()

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data['password'], password):
            # Convert created_at string to datetime object
            created_at = user_data['created_at']
            if isinstance(created_at, str):
                created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
            
            user = User(user_data['id'], user_data['username'], user_data['email'], created_at)
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!')
            return render_template('signup.html')
        
        hashed_password = generate_password_hash(password)
        
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                         (username, email, hashed_password))
            conn.commit()
            conn.close()
            
            flash('Account created successfully! Please login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists!')
    
    return render_template('signup.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()
    
    # Get total classifications
    cursor.execute('SELECT COUNT(*) as total FROM classification_history WHERE user_id = ?', 
                  (current_user.id,))
    total = cursor.fetchone()['total']
    
    # Get this week's classifications (simplified - last 7 days)
    cursor.execute('''
        SELECT COUNT(*) as week_count 
        FROM classification_history 
        WHERE user_id = ? AND timestamp >= datetime('now', '-7 days')
    ''', (current_user.id,))
    this_week = cursor.fetchone()['week_count']
    
    conn.close()
    
    stats = {
        'total': total,
        'this_week': this_week
    }
    
    return render_template('dashboard.html', stats=stats)

@app.route('/classify', methods=['GET', 'POST'])
@login_required
def classify():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if file:
            # Save the file
            filename = secure_filename(f"{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Classify the image
            try:
                predicted_class, confidence = predict_image(filepath)
                
                # Save to database
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO classification_history (user_id, image_path, predicted_class, confidence)
                    VALUES (?, ?, ?, ?)
                ''', (current_user.id, filepath, predicted_class, confidence))
                conn.commit()
                conn.close()
                
                return jsonify({
                    'success': True,
                    'class': predicted_class,
                    'confidence': f"{confidence:.2f}"
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
    
    return render_template('classify.html')

@app.route('/history')
@login_required
def history():
    conn = get_db()
    cursor = conn.cursor()
    
    # Get user's classification history
    cursor.execute('''
        SELECT * FROM classification_history 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 50
    ''', (current_user.id,))
    history_data = cursor.fetchall()
    
    # Convert history_data to list of dicts with proper data types
    history_list = []
    for row in history_data:
        item = dict(row)
        # Convert timestamp string to datetime object
        if isinstance(item['timestamp'], str):
            item['timestamp'] = datetime.strptime(item['timestamp'], '%Y-%m-%d %H:%M:%S')
        # Handle confidence - it might be bytes, string, or float
        confidence = item['confidence']
        if isinstance(confidence, bytes):
            # If it's bytes, try to decode or use struct to unpack
            import struct
            try:
                confidence = struct.unpack('f', confidence)[0]
            except:
                confidence = 0.0
        elif isinstance(confidence, str):
            try:
                confidence = float(confidence)
            except:
                confidence = 0.0
        item['confidence'] = float(confidence)
        history_list.append(item)
    
    # Get statistics
    cursor.execute('SELECT COUNT(*) as total FROM classification_history WHERE user_id = ?', 
                  (current_user.id,))
    total = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(DISTINCT predicted_class) as unique_count FROM classification_history WHERE user_id = ?',
                  (current_user.id,))
    unique = cursor.fetchone()['unique_count']
    
    cursor.execute('SELECT AVG(confidence) as avg_conf FROM classification_history WHERE user_id = ?',
                  (current_user.id,))
    avg_conf = cursor.fetchone()['avg_conf'] or 0
    
    cursor.execute('''
        SELECT predicted_class, COUNT(*) as count 
        FROM classification_history 
        WHERE user_id = ? 
        GROUP BY predicted_class 
        ORDER BY count DESC 
        LIMIT 1
    ''', (current_user.id,))
    most_common_row = cursor.fetchone()
    most_common = most_common_row['predicted_class'] if most_common_row else 'N/A'
    
    conn.close()
    
    return render_template('history.html',
                         history=history_list,
                         total_classifications=total,
                         unique_categories=unique,
                         avg_confidence=int(avg_conf),
                         most_common=most_common)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# AI Prediction function
def predict_image(image_path):
    if model is None:
        raise Exception("Model not loaded. Please check if model file exists.")
    
    # Load and preprocess image
    img = Image.open(image_path)
    img = img.convert('RGB')
    img = img.resize((224, 224))  # Adjust size to match your model's input
    img_array = np.array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    
    # Predict
    predictions = model.predict(img_array)
    predicted_class_index = np.argmax(predictions[0])
    confidence = predictions[0][predicted_class_index] * 100
    
    predicted_class = CATEGORIES[predicted_class_index]
    
    return predicted_class, confidence

if __name__ == '__main__':
    print("🚀 Starting E-Waste Classification Web App...")
    print("📍 Open your browser and go to: http://127.0.0.1:5000")
    app.run(debug=True)