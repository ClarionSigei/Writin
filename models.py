import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class EssayOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id_string = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    guest_email = db.Column(db.String(100))
    
    timezone = db.Column(db.String(50), nullable=False)
    pages = db.Column(db.Integer, nullable=False)
    deadline = db.Column(db.String(20), nullable=False)
    price_per_page = db.Column(db.Float)
    total = db.Column(db.Float)
    format = db.Column(db.String(20))
    subject = db.Column(db.String(100))
    student_name = db.Column(db.String(100))
    class_name = db.Column(db.String(100))

    instructions_file = db.Column(db.String(200))
    instructions_link = db.Column(db.String(500))
    instructions_text = db.Column(db.Text)

    status = db.Column(db.String(20), default='pending_payment')
    partial_paid = db.Column(db.Boolean, default=False)
    full_paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_file = db.Column(db.String(200))

class GeneralRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id_string = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    guest_email = db.Column(db.String(100))
    
    description = db.Column(db.Text)
    file_path = db.Column(db.String(200))
    link = db.Column(db.String(200))
    text = db.Column(db.Text)
    subject = db.Column(db.String(100))
    deadline = db.Column(db.String(50), nullable=False)  # now required
    status = db.Column(db.String(20), default='quote_requested')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    quoted_price = db.Column(db.Float, nullable=True)
    user_accepted = db.Column(db.Boolean, default=False)
    paid = db.Column(db.Boolean, default=False)
    completed_file = db.Column(db.String(200))

class BookClassInquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id_string = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    guest_email = db.Column(db.String(100))
    
    subject = db.Column(db.String(100))
    level = db.Column(db.String(50))
    assignments_count = db.Column(db.Integer)  # label changed to "Submit Login" but field remains
    frequency = db.Column(db.String(100))
    details = db.Column(db.Text)
    status = db.Column(db.String(20), default='inquiry')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    quoted_price = db.Column(db.Float, nullable=True)
    user_accepted = db.Column(db.Boolean, default=False)
    paid = db.Column(db.Boolean, default=False)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_type = db.Column(db.String(20))          # essay, general, book
    order_id = db.Column(db.Integer)                # id in respective table
    amount = db.Column(db.Float)
    method = db.Column(db.String(20))               # paypal, cashapp, binance
    type = db.Column(db.String(20))                 # partial, full
    transaction_id = db.Column(db.String(100))      # user-provided transaction ID/code
    proof_image = db.Column(db.String(200))         # path to uploaded screenshot
    status = db.Column(db.String(20), default='pending')  # pending, verified, rejected
    verified = db.Column(db.Boolean, default=False)
    verified_by = db.Column(db.Integer)              # admin user id (optional)
    verified_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ArchivedOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_id = db.Column(db.Integer)
    order_type = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    guest_email = db.Column(db.String(100))
    data = db.Column(db.Text)                        # JSON of all order data
    archived_at = db.Column(db.DateTime, default=datetime.utcnow)
    archived_by = db.Column(db.Integer)               # admin user id (optional)
    deletion_scheduled = db.Column(db.DateTime)

class OrderCounter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_type = db.Column(db.String(10), unique=True)
    last_number = db.Column(db.Integer, default=0)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    type = db.Column(db.String(50))
    title = db.Column(db.String(200))
    message = db.Column(db.Text)
    link = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    token = db.Column(db.String(100), unique=True)
    expires_at = db.Column(db.DateTime)
    used = db.Column(db.Boolean, default=False)

# New Message model for admin-user communication
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_type = db.Column(db.String(20))          # general, book
    order_id = db.Column(db.Integer)                # id in respective table
    sender_type = db.Column(db.String(20))          # admin, user
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)