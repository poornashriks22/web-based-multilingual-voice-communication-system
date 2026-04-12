from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import io
from gtts import gTTS
import tempfile
import uuid
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mail = Mail(app)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    preferred_language = db.Column(db.String(10), default='en')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(10), nullable=False, default='en')
    audio_filename = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Forms (Django-style form handling)
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', 
                                     validators=[DataRequired(), EqualTo('password')])
    preferred_language = SelectField('Preferred Language', 
                                     choices=[('en', 'English'), ('ta', 'Tamil'), 
                                             ('hi', 'Hindi'), ('ml', 'Malayalam'),
                                             ('te', 'Telugu'), ('kn', 'Kannada')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class MessageForm(FlaskForm):
    receiver_email = StringField('Receiver Email', validators=[DataRequired(), Email()])
    message_text = TextAreaField('Message Text (English Only)', 
                                 validators=[DataRequired(), Length(min=1, max=1000)])
    # Removed language selection - receiver's preferred language will be used
    submit = SubmitField('Send Message')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_password,
            preferred_language=form.preferred_language.data
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Login failed. Check your email and password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get unread messages count
    unread_count = Message.query.filter_by(
        receiver_id=current_user.id, 
        is_read=False
    ).count()
    
    # Get recent messages
    recent_messages = Message.query.filter(
        (Message.sender_id == current_user.id) | 
        (Message.receiver_id == current_user.id)
    ).order_by(Message.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                         unread_count=unread_count,
                         recent_messages=recent_messages)

from utils import text_to_speech, convert_english_to_language

from translation_tts import text_to_speech_safe

@app.route('/send_message', methods=['GET', 'POST'])
@login_required
def send_message():
    form = MessageForm()
    
    if form.validate_on_submit():
        receiver = User.query.filter_by(email=form.receiver_email.data).first()
        
        if not receiver:
            flash('Receiver not found!', 'danger')
            return render_template('send_message.html', form=form)
        
        if receiver.id == current_user.id:
            flash('You cannot send messages to yourself!', 'danger')
            return render_template('send_message.html', form=form)
        
        # Generate unique filename
        audio_filename = f"{uuid.uuid4().hex}_{receiver.preferred_language}.mp3"
        audio_path = os.path.join('static', 'audio', audio_filename)
        
        # Create audio directory if it doesn't exist
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        
        # Generate speech in RECEIVER'S preferred language
        try:
            # Use SAFE multilingual TTS function (in-memory)
            audio_data, error = text_to_speech_safe(
                form.message_text.data, 
                receiver.preferred_language,
                use_in_memory=True  # Use in-memory method for Windows
            )
            
            if audio_data:
                # Save the audio file
                with open(audio_path, 'wb') as f:
                    f.write(audio_data)
                
                # Create message record
                message = Message(
                    sender_id=current_user.id,
                    receiver_id=receiver.id,
                    original_text=form.message_text.data,
                    language=receiver.preferred_language,
                    audio_filename=audio_filename
                )
                db.session.add(message)
                db.session.commit()
                
                # Send email notification
                send_message_notification(receiver, current_user, message)
                
                if error:
                    flash(f'Message sent with note: {error}', 'info')
                else:
                    lang_name = app.config["LANGUAGES"][receiver.preferred_language]
                    flash(f'✅ Message sent successfully in {lang_name}!', 'success')
                
                return redirect(url_for('dashboard'))
            else:
                flash(f'❌ Error generating speech: {error}', 'danger')
                
        except Exception as e:
            flash(f'❌ Error: {str(e)}', 'danger')
            print(f"Error details: {str(e)}")
    
    return render_template('send_message.html', form=form)


@app.route('/convert_text', methods=['POST'])
@login_required
def convert_text():
    data = request.get_json()
    text = data.get('text', '')
    language = data.get('language', 'en')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        # Use SAFE multilingual TTS function (in-memory)
        audio_data, error = text_to_speech_safe(text, language, use_in_memory=True)
        
        if audio_data:
            response = {
                'audio': audio_data.hex(),
                'language': language,
                'language_name': app.config['LANGUAGES'].get(language, 'English'),
                'success': True
            }
            if error:
                response['warning'] = error
            return jsonify(response)
        else:
            return jsonify({'error': error or 'Conversion failed'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Add a test endpoint
@app.route('/test_tts/<language_code>')
def test_tts(language_code):
    """Test TTS for a specific language"""
    test_text = "This is a test message to verify text to speech conversion."
    
    audio_data, error = text_to_speech_safe(test_text, language_code, use_in_memory=True)
    
    if audio_data:
        # Return as downloadable file
        from io import BytesIO
        buffer = BytesIO(audio_data)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name=f'test_{language_code}.mp3'
        )
    else:
        return f"Error: {error}", 500
def send_message_notification(receiver, sender, message):
    try:
        msg = Message(
            subject=f"New Voice Message from {sender.username}",
            recipients=[receiver.email],
            body=f"""
            Hello {receiver.username},
            
            You have received a new voice message from {sender.username}.
            
            The message has been automatically converted to your preferred language: 
            {app.config['LANGUAGES'][receiver.preferred_language]}
            
            Message Preview: {message.original_text[:100]}...
            Date: {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            
            Login to your dashboard to listen to the message in {app.config['LANGUAGES'][receiver.preferred_language]}:
            {url_for('dashboard', _external=True)}
            
            You can also convert this message to other languages after receiving it.
            
            Best regards,
            Multilingual Voice Message System
            """
        )
        mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")
@app.route('/history')
@app.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    filter_type = request.args.get('filter', 'all')
    per_page = 10
    
    # Base query
    query = Message.query.filter(
        (Message.sender_id == current_user.id) | 
        (Message.receiver_id == current_user.id)
    )
    
    # Apply filters
    if filter_type == 'sent':
        query = query.filter(Message.sender_id == current_user.id)
    elif filter_type == 'received':
        query = query.filter(Message.receiver_id == current_user.id)
    # 'all' shows both sent and received
    
    # Order by latest first and paginate
    messages = query.order_by(Message.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('history.html', 
                         messages=messages,
                         filter_type=filter_type,
                         current_filter=filter_type)
@app.route('/receive_message/<int:message_id>')
@login_required
def receive_message(message_id):
    message = Message.query.get_or_404(message_id)
    
    # Check if current user is the receiver
    if message.receiver_id != current_user.id:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('dashboard'))
    
    # Mark as read
    if not message.is_read:
        message.is_read = True
        db.session.commit()
    
    return render_template('receive_message.html', message=message)

@app.route('/get_audio/<filename>')
@login_required
def get_audio(filename):
    audio_path = os.path.join('static', 'audio', filename)
    
    if os.path.exists(audio_path):
        return send_file(audio_path, mimetype='audio/mpeg')
    
    flash('Audio file not found!', 'danger')
    return redirect(url_for('dashboard'))


@app.route('/update_preferences', methods=['POST'])
@login_required
def update_preferences():
    language = request.form.get('language', 'en')
    
    if language in app.config['LANGUAGES']:
        current_user.preferred_language = language
        db.session.commit()
        flash('Preferences updated successfully!', 'success')
    
    return redirect(url_for('dashboard'))

# Add these routes to your app.py

@app.route('/resend_message/<int:message_id>', methods=['POST'])
@login_required
def resend_message(message_id):
    """Resend a message to the same recipient"""
    try:
        original_message = Message.query.get_or_404(message_id)
        
        # Check if user owns this message
        if original_message.sender_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Create new message record
        new_message = Message(
            sender_id=current_user.id,
            receiver_id=original_message.receiver_id,
            original_text=original_message.original_text,
            language=original_message.language,
            audio_filename=original_message.audio_filename  # Reuse same audio file
        )
        
        db.session.add(new_message)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Message resent successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_message/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    """Delete a single message"""
    try:
        message = Message.query.get_or_404(message_id)
        
        # Check if user owns this message
        if message.sender_id != current_user.id and message.receiver_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Delete the audio file if it exists
        if message.audio_filename:
            audio_path = os.path.join('static', 'audio', message.audio_filename)
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception as e:
                print(f"Error deleting audio file: {e}")
        
        db.session.delete(message)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Message deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/mark_as_read', methods=['POST'])
@login_required
def mark_as_read():
    """Mark multiple messages as read"""
    try:
        data = request.get_json()
        message_ids = data.get('message_ids', [])
        
        if not message_ids:
            return jsonify({'error': 'No messages selected'}), 400
        
        count = 0
        for msg_id in message_ids:
            message = Message.query.get(msg_id)
            if message and message.receiver_id == current_user.id and not message.is_read:
                message.is_read = True
                count += 1
        
        if count > 0:
            db.session.commit()
        
        return jsonify({'success': True, 'count': count})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_messages', methods=['POST'])
@login_required
def delete_messages():
    """Delete multiple messages"""
    try:
        data = request.get_json()
        message_ids = data.get('message_ids', [])
        
        if not message_ids:
            return jsonify({'error': 'No messages selected'}), 400
        
        count = 0
        for msg_id in message_ids:
            message = Message.query.get(msg_id)
            if message and (message.sender_id == current_user.id or message.receiver_id == current_user.id):
                
                # Only delete audio file if no other messages use it
                if message.audio_filename:
                    other_messages = Message.query.filter_by(audio_filename=message.audio_filename).count()
                    if other_messages == 1:  # This is the only message using this file
                        audio_path = os.path.join('static', 'audio', message.audio_filename)
                        try:
                            if os.path.exists(audio_path):
                                os.remove(audio_path)
                        except Exception as e:
                            print(f"Error deleting audio file: {e}")
                
                db.session.delete(message)
                count += 1
        
        db.session.commit()
        
        return jsonify({'success': True, 'count': count})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Initialize database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)