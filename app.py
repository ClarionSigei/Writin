import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from models import db, User, EssayOrder, GeneralRequest, BookClassInquiry, Payment, ArchivedOrder, OrderCounter, Notification, PasswordResetToken
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import secrets
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# ---------- Helper Functions ----------
def calculate_price(pages, deadline):
    rates = {'0-2': 12, '3-4': 10, '5+': 8}
    rate = rates.get(deadline, 8)
    return pages * rate

def generate_order_id(order_type):
    counter = OrderCounter.query.filter_by(order_type=order_type).first()
    if not counter:
        counter = OrderCounter(order_type=order_type, last_number=0)
        db.session.add(counter)
        db.session.commit()
    counter.last_number += 1
    db.session.commit()
    return f"{order_type}-{counter.last_number:07d}"

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):
            flash('Admin access required.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def create_notification(user_id, type, title, message, link=None):
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        link=link
    )
    db.session.add(notif)
    db.session.commit()

def send_simulated_email(to, subject, body):
    print(f"\n--- SIMULATED EMAIL ---\nTo: {to}\nSubject: {subject}\nBody:\n{body}\n--- END ---\n")

# ---------- Main Routes ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/essay', methods=['GET', 'POST'])
def essay():
    user = get_current_user()
    if request.method == 'POST':
        timezone = request.form['timezone']
        pages = int(request.form['pages'])
        deadline = request.form['deadline']
        format = request.form['format']
        subject = request.form.get('subject', '')
        student_name = request.form['student_name']
        class_name = request.form['class_name']

        guest_email = None
        if not user:
            guest_email = request.form.get('guest_email')
            if not guest_email:
                flash('Please provide your email for order tracking.', 'danger')
                return redirect(url_for('essay'))

        instructions_file_path = None
        instructions_link = ''
        instructions_text = ''
        
        instruction_type = request.form.get('instruction_type', 'none')
        if instruction_type == 'file':
            instructions_file = request.files.get('instructions_file')
            if instructions_file and instructions_file.filename:
                filename = secure_filename(instructions_file.filename)
                instructions_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                instructions_file.save(instructions_file_path)
        elif instruction_type == 'link':
            instructions_link = request.form.get('instructions_link', '')
        elif instruction_type == 'text':
            instructions_text = request.form.get('instructions_text', '')

        total = calculate_price(pages, deadline)
        price_per_page = total / pages

        order_id_string = generate_order_id('ESS')
        order = EssayOrder(
            order_id_string=order_id_string,
            user_id=user.id if user else None,
            guest_email=guest_email,
            timezone=timezone, pages=pages, deadline=deadline,
            price_per_page=price_per_page, total=total, format=format,
            subject=subject, student_name=student_name, class_name=class_name,
            instructions_file=instructions_file_path,
            instructions_link=instructions_link,
            instructions_text=instructions_text
        )
        db.session.add(order)
        db.session.commit()

        recipient = user.email if user else guest_email
        send_simulated_email(recipient, f"Essay Order Confirmation - {order_id_string}",
                             f"Thank you for your order.\n\nOrder ID: {order_id_string}\nTotal: ${total}\n\nYou can track your order at: {url_for('track_order', _external=True)}")

        session['pending_order'] = {'id': order.id, 'type': 'essay', 'amount_partial': total * 0.5}
        return redirect(url_for('payment'))

    return render_template('essay.html', user=user)

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/general', methods=['GET', 'POST'])
def general():
    user = get_current_user()
    if request.method == 'POST':
        description = request.form['description']
        subject = request.form.get('subject', '')
        deadline = request.form.get('deadline', '')

        guest_email = None
        if not user:
            guest_email = request.form.get('guest_email')
            if not guest_email:
                flash('Please provide your email for order tracking.', 'danger')
                return redirect(url_for('general'))

        file_path = None
        link = ''
        text = ''
        
        submission_type = request.form.get('submission_type', 'none')
        if submission_type == 'file':
            file = request.files.get('file')
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
        elif submission_type == 'link':
            link = request.form.get('link', '')
        elif submission_type == 'text':
            text = request.form.get('text', '')

        order_id_string = generate_order_id('GEN')
        req = GeneralRequest(
            order_id_string=order_id_string,
            user_id=user.id if user else None,
            guest_email=guest_email,
            description=description, file_path=file_path,
            link=link, text=text, subject=subject, deadline=deadline
        )
        db.session.add(req)
        db.session.commit()

        recipient = user.email if user else guest_email
        send_simulated_email(recipient, f"General Assignment Request - {order_id_string}",
                             f"We received your request.\n\nRequest ID: {order_id_string}\n\nWe will contact you with a quote shortly.\n\nTrack your request: {url_for('track_order', _external=True)}")

        flash('Your request has been submitted. We will contact you with a quote shortly.', 'success')
        return redirect(url_for('index'))
    return render_template('general.html', user=user)

@app.route('/book-class', methods=['GET', 'POST'])
def book_class():
    user = get_current_user()
    if request.method == 'POST':
        subject = request.form['subject']
        level = request.form['level']
        assignments_count = int(request.form['assignments_count'])
        frequency = request.form.get('frequency', '')
        details = request.form.get('details', '')

        guest_email = None
        if not user:
            guest_email = request.form.get('guest_email')
            if not guest_email:
                flash('Please provide your email for order tracking.', 'danger')
                return redirect(url_for('book_class'))

        order_id_string = generate_order_id('BOK')
        inquiry = BookClassInquiry(
            order_id_string=order_id_string,
            user_id=user.id if user else None,
            guest_email=guest_email,
            subject=subject, level=level,
            assignments_count=assignments_count, frequency=frequency, details=details
        )
        db.session.add(inquiry)
        db.session.commit()

        recipient = user.email if user else guest_email
        send_simulated_email(recipient, f"Book Class Inquiry - {order_id_string}",
                             f"Thank you for your inquiry.\n\nInquiry ID: {order_id_string}\n\nWe will contact you to discuss a tailored plan.\n\nTrack your inquiry: {url_for('track_order', _external=True)}")

        flash('Your inquiry has been sent. We will contact you to discuss a tailored plan.', 'success')
        return redirect(url_for('index'))
    return render_template('book_class.html', user=user)

@app.route('/payment-methods')
def payment_methods():
    return render_template('payment_methods.html')

@app.route('/payment')
def payment():
    pending = session.get('pending_order')
    if not pending:
        return redirect(url_for('index'))
    return render_template('payment.html', amount=pending['amount_partial'])

@app.route('/payment/confirm/<int:order_id>')
def confirm_payment(order_id):
    order = EssayOrder.query.get(order_id)
    if order:
        order.partial_paid = True
        order.status = 'in_progress'
        db.session.commit()
        session.pop('pending_order', None)
        
        if order.user_id:
            create_notification(order.user_id, 'payment_received', 'Payment Received',
                                f'Your 50% payment for order {order.order_id_string} has been confirmed.')
        
        recipient = None
        if order.user_id:
            user = User.query.get(order.user_id)
            recipient = user.email if user else None
        else:
            recipient = order.guest_email
        
        if recipient:
            send_simulated_email(recipient, f"Payment Confirmed - {order.order_id_string}",
                                 f"Your 50% payment for order {order.order_id_string} has been received. We will start working on your essay.")
        
        flash('Payment recorded. We will start working on your order.', 'success')
    return redirect(url_for('index'))

@app.route('/payment/general/<int:order_id>')
def payment_general(order_id):
    order = GeneralRequest.query.get_or_404(order_id)
    if not order.user_accepted or order.paid:
        flash('Invalid payment request.', 'danger')
        return redirect(url_for('track_order'))
    session['pending_general_payment'] = {'id': order.id, 'amount': order.quoted_price}
    return render_template('payment_general.html', amount=order.quoted_price, order_id=order.id)

@app.route('/payment/general/confirm/<int:order_id>')
def confirm_general_payment(order_id):
    order = GeneralRequest.query.get_or_404(order_id)
    if order.user_accepted and not order.paid:
        order.paid = True
        order.status = 'paid'
        db.session.commit()
        if order.user_id:
            create_notification(order.user_id, 'payment_received', 'Payment Received',
                                f'Full payment for request {order.order_id_string} has been confirmed.')
        recipient = None
        if order.user_id:
            user = User.query.get(order.user_id)
            recipient = user.email if user else None
        else:
            recipient = order.guest_email
        if recipient:
            send_simulated_email(recipient, f"Payment Confirmed - {order.order_id_string}",
                                 f"Your full payment for request {order.order_id_string} has been received. We will start working on your assignment.")
        flash('Payment recorded. We will start working on your request.', 'success')
    return redirect(url_for('track_order'))

@app.route('/payment/book/<int:inquiry_id>')
def payment_book(inquiry_id):
    inquiry = BookClassInquiry.query.get_or_404(inquiry_id)
    if not inquiry.user_accepted or inquiry.paid:
        flash('Invalid payment request.', 'danger')
        return redirect(url_for('track_order'))
    session['pending_book_payment'] = {'id': inquiry.id, 'amount': inquiry.quoted_price}
    return render_template('payment_book.html', amount=inquiry.quoted_price, inquiry_id=inquiry.id)

@app.route('/payment/book/confirm/<int:inquiry_id>')
def confirm_book_payment(inquiry_id):
    inquiry = BookClassInquiry.query.get_or_404(inquiry_id)
    if inquiry.user_accepted and not inquiry.paid:
        inquiry.paid = True
        inquiry.status = 'paid'
        db.session.commit()
        if inquiry.user_id:
            create_notification(inquiry.user_id, 'payment_received', 'Payment Received',
                                f'Full payment for inquiry {inquiry.order_id_string} has been confirmed.')
        recipient = None
        if inquiry.user_id:
            user = User.query.get(inquiry.user_id)
            recipient = user.email if user else None
        else:
            recipient = inquiry.guest_email
        if recipient:
            send_simulated_email(recipient, f"Payment Confirmed - {inquiry.order_id_string}",
                                 f"Your full payment for inquiry {inquiry.order_id_string} has been received. We will start working on your class plan.")
        flash('Payment recorded. We will start working on your class plan.', 'success')
    return redirect(url_for('track_order'))

@app.route('/payment/proof', methods=['GET', 'POST'])
def payment_proof():
    if request.method == 'POST':
        order_type = request.form['order_type']
        order_id = int(request.form['order_id'])
        payment_type = request.form['payment_type']
        method = request.form['method']
        transaction_id = request.form['transaction_id']
        proof_image = request.files.get('proof_image')
        
        if not proof_image or not proof_image.filename:
            flash('Please upload a screenshot.', 'danger')
            return redirect(request.url)
        
        # Save proof image
        filename = secure_filename(f"proof_{order_type}_{order_id}_{datetime.utcnow().timestamp()}.{proof_image.filename.split('.')[-1]}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        proof_image.save(filepath)
        
        # Determine amount based on order type
        amount = 0
        order = None
        if order_type == 'essay':
            order = EssayOrder.query.get(order_id)
            if order:
                if payment_type == 'partial':
                    amount = order.total * 0.5
                elif payment_type == 'full':
                    amount = order.total * 0.5  # balance
        elif order_type == 'general':
            order = GeneralRequest.query.get(order_id)
            if order:
                amount = order.quoted_price
        elif order_type == 'book':
            order = BookClassInquiry.query.get(order_id)
            if order:
                amount = order.quoted_price
        
        if not order:
            flash('Order not found.', 'danger')
            return redirect(url_for('index'))
        
        # Create payment record
        payment = Payment(
            order_type=order_type,
            order_id=order_id,
            amount=amount,
            method=method,
            type=payment_type,
            transaction_id=transaction_id,
            proof_image=filepath,
            status='pending',
            verified=False
        )
        db.session.add(payment)
        
        # Update order status to indicate payment pending (optional)
        if order_type == 'essay':
            order.status = 'payment_pending'  # new status we might need to add
        elif order_type == 'general':
            order.status = 'payment_pending'
        elif order_type == 'book':
            order.status = 'payment_pending'
        
        db.session.commit()
        
        # Notify admin via simulated email
        send_simulated_email('admin@example.com', f"New Payment Proof Submitted - {order.order_id_string}",
                             f"A new payment proof has been submitted for order {order.order_id_string}. Please verify in admin panel.")
        
        flash('Payment proof submitted successfully. Admin will verify shortly.', 'success')
        return redirect(url_for('track_order'))
    
    # GET request - show form
    order_type = request.args.get('order_type')
    order_id = request.args.get('order_id')
    payment_type = request.args.get('payment_type')
    amount = request.args.get('amount')
    order_id_string = ''
    
    if order_type == 'essay':
        order = EssayOrder.query.get(order_id)
        if order:
            order_id_string = order.order_id_string
            amount = order.total * 0.5 if payment_type == 'partial' else order.total * 0.5
    elif order_type == 'general':
        order = GeneralRequest.query.get(order_id)
        if order:
            order_id_string = order.order_id_string
            amount = order.quoted_price
    elif order_type == 'book':
        order = BookClassInquiry.query.get(order_id)
        if order:
            order_id_string = order.order_id_string
            amount = order.quoted_price
    
    return render_template('payment_proof.html', 
                           order_type=order_type, 
                           order_id=order_id, 
                           payment_type=payment_type, 
                           amount=amount,
                           order_id_string=order_id_string)

# ---------- User Authentication Routes ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']
        
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))
        
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email already registered. Please log in.', 'warning')
            return redirect(url_for('login'))
        
        user = User(full_name=full_name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        send_simulated_email(email, "Welcome to Online Writing Website",
                             f"Hi {full_name},\n\nYour account has been created successfully.\n\nYou can now log in and track your orders.\n\nBest regards,\nThe Team")
        
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Welcome back, {user.full_name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(32)
            expires = datetime.utcnow() + timedelta(hours=1)
            reset = PasswordResetToken(user_id=user.id, token=token, expires_at=expires)
            db.session.add(reset)
            db.session.commit()
            
            reset_link = url_for('reset_password', token=token, _external=True)
            send_simulated_email(email, "Password Reset Request",
                                 f"Hi {user.full_name},\n\nClick the link to reset your password: {reset_link}\n\nThis link expires in 1 hour.\n\nIf you didn't request this, ignore this email.")
        flash('If your email is registered, you will receive a password reset link.', 'info')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset = PasswordResetToken.query.filter_by(token=token, used=False).first()
    if not reset or reset.expires_at < datetime.utcnow():
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form['password']
        confirm = request.form['confirm_password']
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('reset_password', token=token))
        
        user = User.query.get(reset.user_id)
        user.set_password(password)
        reset.used = True
        db.session.commit()
        
        flash('Password reset successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', token=token)

# ---------- User Dashboard ----------
@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    essays = EssayOrder.query.filter_by(user_id=user.id).order_by(EssayOrder.created_at.desc()).all()
    generals = GeneralRequest.query.filter_by(user_id=user.id).order_by(GeneralRequest.created_at.desc()).all()
    books = BookClassInquiry.query.filter_by(user_id=user.id).order_by(BookClassInquiry.created_at.desc()).all()
    notifications = Notification.query.filter_by(user_id=user.id, is_read=False).order_by(Notification.created_at.desc()).all()
    return render_template('dashboard.html', user=user, essays=essays, generals=generals, books=books, notifications=notifications)

@app.route('/dashboard/order/<order_type>/<order_id>')
@login_required
def view_order(order_type, order_id):
    user = get_current_user()
    if order_type == 'essay':
        order = EssayOrder.query.filter_by(order_id_string=order_id, user_id=user.id).first_or_404()
        return render_template('order_detail.html', order=order, type='essay')
    elif order_type == 'general':
        order = GeneralRequest.query.filter_by(order_id_string=order_id, user_id=user.id).first_or_404()
        return render_template('order_detail.html', order=order, type='general')
    elif order_type == 'book':
        order = BookClassInquiry.query.filter_by(order_id_string=order_id, user_id=user.id).first_or_404()
        return render_template('order_detail.html', order=order, type='book')
    else:
        abort(404)

@app.route('/accept-quote/<order_type>/<int:order_id>')
@login_required
def accept_quote(order_type, order_id):
    user = get_current_user()
    if order_type == 'general':
        order = GeneralRequest.query.get_or_404(order_id)
        if order.user_id != user.id:
            abort(403)
        if order.status == 'quoted' and not order.user_accepted:
            order.user_accepted = True
            order.status = 'accepted'
            db.session.commit()
            flash('Quote accepted. You can now make payment.', 'success')
    elif order_type == 'book':
        order = BookClassInquiry.query.get_or_404(order_id)
        if order.user_id != user.id:
            abort(403)
        if order.status == 'quoted' and not order.user_accepted:
            order.user_accepted = True
            order.status = 'accepted'
            db.session.commit()
            flash('Quote accepted. You can now make payment.', 'success')
    return redirect(url_for('view_order', order_type=order_type, order_id=order.order_id_string))

@app.route('/decline-quote/<order_type>/<int:order_id>')
@login_required
def decline_quote(order_type, order_id):
    user = get_current_user()
    if order_type == 'general':
        order = GeneralRequest.query.get_or_404(order_id)
        if order.user_id != user.id:
            abort(403)
        if order.status == 'quoted' and not order.user_accepted:
            order.status = 'declined'
            db.session.commit()
            flash('Quote declined. You may contact admin for further negotiation.', 'info')
    elif order_type == 'book':
        order = BookClassInquiry.query.get_or_404(order_id)
        if order.user_id != user.id:
            abort(403)
        if order.status == 'quoted' and not order.user_accepted:
            order.status = 'declined'
            db.session.commit()
            flash('Quote declined. You may contact admin for further negotiation.', 'info')
    return redirect(url_for('view_order', order_type=order_type, order_id=order.order_id_string))

@app.route('/dashboard/notifications/mark-read/<int:notif_id>')
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id == session['user_id']:
        notif.is_read = True
        db.session.commit()
    return redirect(url_for('dashboard'))

# ---------- Public Order Tracking ----------
@app.route('/track', methods=['GET', 'POST'])
def track_order():
    if request.method == 'POST':
        order_id = request.form['order_id'].strip()
        email = request.form['email'].strip()
        
        order = None
        order_type = None
        
        if order_id.startswith('ESS-'):
            order = EssayOrder.query.filter_by(order_id_string=order_id).first()
            order_type = 'essay'
        elif order_id.startswith('GEN-'):
            order = GeneralRequest.query.filter_by(order_id_string=order_id).first()
            order_type = 'general'
        elif order_id.startswith('BOK-'):
            order = BookClassInquiry.query.filter_by(order_id_string=order_id).first()
            order_type = 'book'
        
        if order:
            user_email = None
            if order.user_id:
                user = User.query.get(order.user_id)
                if user:
                    user_email = user.email
            if (order.guest_email and order.guest_email.lower() == email.lower()) or (user_email and user_email.lower() == email.lower()):
                return render_template('order_status.html', order=order, order_type=order_type)
        
        flash('Order not found or email does not match.', 'danger')
        return redirect(url_for('track_order'))
    return render_template('track_order.html')

# ---------- Admin Routes ----------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if password == 'admin123':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Incorrect password', 'danger')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    essays = EssayOrder.query.order_by(EssayOrder.created_at.desc()).all()
    generals = GeneralRequest.query.order_by(GeneralRequest.created_at.desc()).all()
    books = BookClassInquiry.query.order_by(BookClassInquiry.created_at.desc()).all()
    return render_template('admin/dashboard.html', essays=essays, generals=generals, books=books)

@app.route('/admin/order/<int:order_id>', methods=['GET', 'POST'])
@admin_required
def admin_order(order_id):
    order = EssayOrder.query.get_or_404(order_id)
    if request.method == 'POST':
        if 'mark_partial' in request.form:
            order.partial_paid = True
            order.status = 'in_progress'
        if 'mark_full' in request.form:
            order.full_paid = True
            order.status = 'completed'
        if 'file' in request.files:
            file = request.files['file']
            if file.filename:
                filename = secure_filename(f"order_{order_id}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                order.completed_file = filepath
        db.session.commit()
        flash('Order updated', 'success')
        return redirect(url_for('admin_order', order_id=order_id))
    return render_template('admin/order.html', order=order, User=User)

@app.route('/admin/general/<int:req_id>', methods=['GET', 'POST'])
@admin_required
def admin_general(req_id):
    req = GeneralRequest.query.get_or_404(req_id)
    if request.method == 'POST':
        new_status = request.form['status']
        req.status = new_status
        if new_status == 'quoted':
            quoted_price = request.form.get('quoted_price')
            if quoted_price:
                req.quoted_price = float(quoted_price)
        if 'completed_file' in request.files:
            file = request.files['completed_file']
            if file.filename:
                filename = secure_filename(f"general_{req_id}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                req.completed_file = filepath
        db.session.commit()
        flash('Request updated', 'success')
        return redirect(url_for('admin_general', req_id=req_id))
    return render_template('admin/general_detail.html', request=req, User=User)

@app.route('/admin/inquiry/<int:inquiry_id>', methods=['GET', 'POST'])
@admin_required
def admin_inquiry(inquiry_id):
    inquiry = BookClassInquiry.query.get_or_404(inquiry_id)
    if request.method == 'POST':
        new_status = request.form['status']
        inquiry.status = new_status
        if new_status == 'quoted':
            quoted_price = request.form.get('quoted_price')
            if quoted_price:
                inquiry.quoted_price = float(quoted_price)
        db.session.commit()
        flash('Inquiry updated', 'success')
        return redirect(url_for('admin_inquiry', inquiry_id=inquiry_id))
    return render_template('admin/inquiry_detail.html', inquiry=inquiry, User=User)

@app.route('/admin/delete/<order_type>/<int:order_id>', methods=['POST'])
@admin_required
def admin_delete_order(order_type, order_id):
    order = None
    if order_type == 'essay':
        order = EssayOrder.query.get_or_404(order_id)
    elif order_type == 'general':
        order = GeneralRequest.query.get_or_404(order_id)
    elif order_type == 'book':
        order = BookClassInquiry.query.get_or_404(order_id)
    else:
        abort(400)
    
    order_dict = {c.name: getattr(order, c.name) for c in order.__table__.columns}
    order_dict['_type'] = order_type
    order_json = json.dumps(order_dict, default=str)
    
    archived = ArchivedOrder(
        original_id=order.id,
        order_type=order_type,
        user_id=order.user_id if hasattr(order, 'user_id') else None,
        guest_email=order.guest_email if hasattr(order, 'guest_email') else None,
        data=order_json,
        archived_by=1,
        deletion_scheduled=datetime.utcnow() + timedelta(days=180)
    )
    db.session.add(archived)
    
    if request.form.get('delete_files') == 'yes':
        if hasattr(order, 'instructions_file') and order.instructions_file and os.path.exists(order.instructions_file):
            os.remove(order.instructions_file)
        if hasattr(order, 'completed_file') and order.completed_file and os.path.exists(order.completed_file):
            os.remove(order.completed_file)
        if hasattr(order, 'file_path') and order.file_path and os.path.exists(order.file_path):
            os.remove(order.file_path)
    
    db.session.delete(order)
    db.session.commit()
    
    flash(f'Order {order.order_id_string} moved to archive.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/cleanup', methods=['POST'])
@admin_required
def admin_cleanup():
    cutoff = datetime.utcnow() - timedelta(days=14)
    unpaid_essays = EssayOrder.query.filter(
        EssayOrder.status == 'pending_payment',
        EssayOrder.created_at < cutoff
    ).all()
    for order in unpaid_essays:
        order_dict = {c.name: getattr(order, c.name) for c in order.__table__.columns}
        order_dict['_type'] = 'essay'
        archived = ArchivedOrder(
            original_id=order.id,
            order_type='essay',
            user_id=order.user_id,
            guest_email=order.guest_email,
            data=json.dumps(order_dict, default=str),
            deletion_scheduled=datetime.utcnow() + timedelta(days=180)
        )
        db.session.add(archived)
        db.session.delete(order)
    
    cutoff_completed = datetime.utcnow() - timedelta(days=30)
    completed_essays = EssayOrder.query.filter(
        EssayOrder.status == 'completed',
        EssayOrder.created_at < cutoff_completed
    ).all()
    for order in completed_essays:
        order_dict = {c.name: getattr(order, c.name) for c in order.__table__.columns}
        order_dict['_type'] = 'essay'
        archived = ArchivedOrder(
            original_id=order.id,
            order_type='essay',
            user_id=order.user_id,
            guest_email=order.guest_email,
            data=json.dumps(order_dict, default=str),
            deletion_scheduled=datetime.utcnow() + timedelta(days=180)
        )
        db.session.add(archived)
        db.session.delete(order)
    
    cutoff_archive = datetime.utcnow() - timedelta(days=180)
    old_archives = ArchivedOrder.query.filter(ArchivedOrder.archived_at < cutoff_archive).all()
    for arch in old_archives:
        db.session.delete(arch)
    
    db.session.commit()
    flash(f'Cleanup completed. {len(unpaid_essays)} unpaid essays archived, {len(completed_essays)} completed essays archived, {len(old_archives)} old archives deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

# Download routes (admin only)
@app.route('/admin/instructions/<int:order_id>')
@admin_required
def download_instructions(order_id):
    order = EssayOrder.query.get_or_404(order_id)
    if order.instructions_file and os.path.exists(order.instructions_file):
        return send_file(order.instructions_file, as_attachment=False)
    else:
        flash('File not found', 'danger')
        return redirect(url_for('admin_order', order_id=order_id))

@app.route('/admin/general/file/<int:req_id>')
@admin_required
def download_general_file(req_id):
    req = GeneralRequest.query.get_or_404(req_id)
    if req.file_path and os.path.exists(req.file_path):
        return send_file(req.file_path, as_attachment=False)
    else:
        flash('File not found', 'danger')
        return redirect(url_for('admin_general', req_id=req_id))

@app.route('/admin/general/completed/<int:req_id>')
@admin_required
def download_general_completed(req_id):
    req = GeneralRequest.query.get_or_404(req_id)
    if req.completed_file and os.path.exists(req.completed_file):
        return send_file(req.completed_file, as_attachment=False)
    else:
        flash('File not found', 'danger')
        return redirect(url_for('admin_general', req_id=req_id))

@app.route('/admin/payments')
@admin_required
def admin_payments():
    pending = Payment.query.filter_by(status='pending').order_by(Payment.created_at.desc()).all()
    verified = Payment.query.filter_by(status='verified').order_by(Payment.created_at.desc()).all()
    return render_template('admin/payment_verification.html', 
                           pending_payments=pending, 
                           verified_payments=verified,
                           EssayOrder=EssayOrder,
                           GeneralRequest=GeneralRequest,
                           BookClassInquiry=BookClassInquiry)

@app.route('/admin/payment/view/<int:payment_id>')
@admin_required
def admin_view_proof(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    if payment.proof_image and os.path.exists(payment.proof_image):
        return send_file(payment.proof_image, as_attachment=False)
    else:
        flash('File not found', 'danger')
        return redirect(url_for('admin_payments'))

@app.route('/admin/payment/verify/<int:payment_id>/<action>')
@admin_required
def admin_verify_payment(payment_id, action):
    payment = Payment.query.get_or_404(payment_id)
    if action == 'verify':
        payment.status = 'verified'
        payment.verified = True
        payment.verified_at = datetime.utcnow()
        # Update the corresponding order based on payment type
        if payment.order_type == 'essay':
            order = EssayOrder.query.get(payment.order_id)
            if order:
                if payment.type == 'partial':
                    order.partial_paid = True
                    order.status = 'in_progress'
                elif payment.type == 'full':
                    order.full_paid = True
                    order.status = 'completed'
                db.session.add(order)
        elif payment.order_type == 'general':
            order = GeneralRequest.query.get(payment.order_id)
            if order:
                order.paid = True
                order.status = 'paid'
                db.session.add(order)
        elif payment.order_type == 'book':
            order = BookClassInquiry.query.get(payment.order_id)
            if order:
                order.paid = True
                order.status = 'paid'
                db.session.add(order)
        flash('Payment verified and order updated.', 'success')
    elif action == 'reject':
        payment.status = 'rejected'
        flash('Payment rejected.', 'info')
    db.session.commit()
    return redirect(url_for('admin_payments'))

# Download for client after full payment
@app.route('/download/<int:order_id>')
def download(order_id):
    order = EssayOrder.query.get_or_404(order_id)
    if order.full_paid and order.completed_file:
        return send_file(order.completed_file, as_attachment=True)
    else:
        flash('Payment required or file not ready', 'danger')
        return redirect(url_for('index'))

@app.route('/download/general/<int:req_id>')
def download_general(req_id):
    req = GeneralRequest.query.get_or_404(req_id)
    if req.paid and req.completed_file:
        return send_file(req.completed_file, as_attachment=True)
    else:
        flash('Payment required or file not ready', 'danger')
        return redirect(url_for('track_order'))

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    app.run(debug=debug, port=port)
