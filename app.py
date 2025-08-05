from flask import Flask, render_template, redirect, request, session, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
from reportlab.pdfgen import canvas
import io
import os
import socket

app = Flask(__name__)
app.secret_key = "secret123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# ------------------ Models ------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))
    balance = db.Column(db.Float, default=0.0)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    type = db.Column(db.String(10))
    amount = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.now)

# ------------------ Routes ------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        if User.query.filter_by(username=username).first():
            return "User already exists!"
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_input = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password_input):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).all()


    if request.method == 'POST':
        action = request.form['action']
        amount = float(request.form['amount'])

        if action == 'deposit':
            user.balance += amount
            db.session.add(Transaction(user_id=user.id, type='Deposit', amount=amount))
        elif action == 'withdraw':
            if user.balance >= amount:
                user.balance -= amount
                db.session.add(Transaction(user_id=user.id, type='Withdraw', amount=amount))
            else:
                return "Insufficient Balance"
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('dashboard.html', user=user, transactions=transactions)

@app.route('/download_statement')
def download_statement():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).all()

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(200, 800, f"Transaction Statement for {user.username}")
    y = 760
    for txn in transactions:
        text = f"{txn.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {txn.type} ₹{txn.amount}"
        p.drawString(100, y, text)
        y -= 20
        if y < 50:
            p.showPage()
            y = 800
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="transaction_statement.pdf", mimetype='application/pdf')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))
@app.route('/admin/users')
def list_users():
    users = User.query.all()
    return "<br>".join([f"{u.id}: {u.username}, Balance: ₹{u.balance}" for u in users])    
ip = request.remote_addr
hostname = socket.gethostname()
print(f"User {username} logged in from {ip} ({hostname})")
@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.username != "Charan968":  # Only allow your login
        return "Unauthorized Access"

    users = User.query.all()
    transactions = Transaction.query.order_by(Transaction.timestamp.desc()).all()
    return render_template('admin.html', users=users, transactions=transactions)


# ------------------ Start App ------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
