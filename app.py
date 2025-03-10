# app.py

from dotenv import load_dotenv
import os
from itertools import islice  # Add this import

load_dotenv()  # Load variables from .env file

# Then replace this line
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import google.generativeai as genai
import PyPDF2
import uuid
from datetime import datetime
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_key_for_development_only')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pdf_qa.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# Add your template filter here
@app.template_filter('slice')
def slice_filter(iterable, start, length=None):
    if length is None:
        return islice(iterable, start)
    return islice(iterable, start, start + length)

# Make sure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db = SQLAlchemy(app)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
# Database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    pdfs = db.relationship('PDF', backref='owner', lazy=True)

class PDF(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    original_filename = db.Column(db.String(100), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    conversations = db.relationship('Conversation', backref='pdf', lazy=True)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdf.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    messages = db.relationship('Message', backref='conversation', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    is_user = db.Column(db.Boolean, nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# Create database tables
with app.app_context():
    db.create_all()

# Helper functions
def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text

def get_gemini_response(question, context):
    model = genai.GenerativeModel('gemini-pro')
    
    # Limit context length to avoid token limit issues
    max_context_length = 15000  # Reduced from 30000 to stay within Gemini's limits
    if len(context) > max_context_length:
        context = context[:max_context_length]
    
    prompt = f"""
    Based on the following document content, please answer the question below.
    If the answer cannot be found in the document, say "I don't have enough information to answer this question."
    
    Document content:
    {context}
    
    Question: {question}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        # Return a user-friendly error message
        return "I'm sorry, I couldn't process the document content properly. This might be due to the document size or format. Try with a shorter or s" \
        "impler document, or ask a more specific question about a particular section."
# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if username or email already exists
        existing_user = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()
        
        if existing_user:
            flash('Username already exists')
            return redirect(url_for('register'))
        if existing_email:
            flash('Email already exists')
            return redirect(url_for('register'))
        
        # Create new user
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', pdfs=user.pdfs)

@app.route('/upload', methods=['GET', 'POST'])
def upload_pdf():
    if 'user_id' not in session:
        flash('Please login first')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['pdf_file']
        
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if file and file.filename.endswith('.pdf'):
            # Generate a unique filename
            filename = str(uuid.uuid4()) + '.pdf'
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Extract text from PDF
            try:
                pdf_text = extract_text_from_pdf(filepath)
                
                # Save PDF info to database
                new_pdf = PDF(
                    filename=filename,
                    original_filename=secure_filename(file.filename),
                    content=pdf_text,
                    user_id=session['user_id']
                )
                db.session.add(new_pdf)
                db.session.commit()
                
                flash('PDF uploaded successfully!')
                return redirect(url_for('dashboard'))
            except Exception as e:
                os.remove(filepath)  # Clean up if processing fails
                flash(f'Error processing PDF: {str(e)}')
                return redirect(request.url)
        else:
            flash('Only PDF files are allowed')
            return redirect(request.url)
    
    return render_template('upload.html')

@app.route('/pdfs/<int:pdf_id>')
def view_pdf(pdf_id):
    if 'user_id' not in session:
        flash('Please login first')
        return redirect(url_for('login'))
    
    pdf = PDF.query.get_or_404(pdf_id)
    
    # Check if user owns this PDF
    if pdf.user_id != session['user_id']:
        flash('You do not have permission to view this PDF')
        return redirect(url_for('dashboard'))
    
    # Get or create a conversation
    conversation = Conversation.query.filter_by(pdf_id=pdf_id).order_by(Conversation.timestamp.desc()).first()
    
    if not conversation:
        conversation = Conversation(pdf_id=pdf_id)
        db.session.add(conversation)
        db.session.commit()
    
    return render_template('view_pdf.html', pdf=pdf, conversation=conversation)

@app.route('/api/ask', methods=['POST'])
def ask_question():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    pdf_id = data.get('pdf_id')
    question = data.get('question')
    conversation_id = data.get('conversation_id')
    
    if not pdf_id or not question or not conversation_id:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    pdf = PDF.query.get_or_404(pdf_id)
    
    # Check if user owns this PDF
    if pdf.user_id != session['user_id']:
        return jsonify({'error': 'Permission denied'}), 403
    
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # Save user question
    user_message = Message(
        conversation_id=conversation_id,
        is_user=True,
        content=question
    )
    db.session.add(user_message)
    
    # Get response from Gemini API
    try:
        answer = get_gemini_response(question, pdf.content)
        
        # Save AI response
        ai_message = Message(
            conversation_id=conversation_id,
            is_user=False,
            content=answer
        )
        db.session.add(ai_message)
        db.session.commit()
        
        return jsonify({
            'answer': answer,
            'user_message_id': user_message.id,
            'ai_message_id': ai_message.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/conversations')
def conversations():
    if 'user_id' not in session:
        flash('Please login first')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    pdfs_with_conversations = []
    
    for pdf in user.pdfs:
        if pdf.conversations:
            pdfs_with_conversations.append(pdf)
    
    return render_template('conversations.html', pdfs=pdfs_with_conversations)

@app.route('/conversation/<int:conversation_id>')
def view_conversation(conversation_id):
    if 'user_id' not in session:
        flash('Please login first')
        return redirect(url_for('login'))
    
    conversation = Conversation.query.get_or_404(conversation_id)
    pdf = conversation.pdf
    
    # Check if user owns this PDF/conversation
    if pdf.user_id != session['user_id']:
        flash('You do not have permission to view this conversation')
        return redirect(url_for('dashboard'))
    
    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.timestamp).all()
    
    return render_template('conversation.html', conversation=conversation, messages=messages, pdf=pdf)

if __name__ == '__main__':
    app.run(debug=True)