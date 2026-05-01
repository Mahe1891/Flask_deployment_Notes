from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import random
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- EMAIL CONFIG ----------------
SENDER_EMAIL = "kmahendra1891@gmail.com"
APP_PASSWORD = "gteypxpdjsclozse"


def send_email(to_email, subject, body):
    print("EMAIL SENT")
    print("TO:", to_email)
    print("SUBJECT:", subject)
    print("BODY:", body)


# ---------------- DB CONNECTION (SQLite) ----------------
def get_connection():
    con = sqlite3.connect("notes.db")
    con.row_factory = sqlite3.Row  # access like dict
    return con


# ---------------- CREATE TABLE (RUN ONCE) ----------------
def create_table():
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT,
            password TEXT
        )
    """)
    con.commit()
    con.close()

create_table()


# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        con = get_connection()
        cur = con.cursor()

        try:
            cur.execute(
                "INSERT INTO users(username,email,password) VALUES(?,?,?)",
                (username, email, password)
            )
            con.commit()
            flash("Registered Successfully", "success")
            return redirect('/')
        except:
            flash("User already exists", "danger")

        con.close()

    return render_template('register.html')


# ---------------- LOGIN ----------------
@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        con.close()

        if user and check_password_hash(user["password"], password):
            session['user_id'] = user["id"]
            flash("Login Successful", "success")
            return redirect('/dashboard')
        else:
            flash("Invalid Credentials", "danger")

    return render_template('login.html')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')

    search = request.args.get('search')

    con = get_connection()
    cur = con.cursor()

    if search:
        cur.execute(
            "SELECT * FROM notes WHERE user_id=? AND title LIKE ?",
            (session['user_id'], f"%{search}%")
        )
    else:
        cur.execute(
            "SELECT * FROM notes WHERE user_id=?",
            (session['user_id'],)
        )

    notes = cur.fetchall()
    con.close()

    return render_template('dashboard.html', notes=notes)


# ---------------- ADD NOTE ----------------
@app.route('/add_note', methods=['GET','POST'])
def add_note():
    if 'user_id' not in session:
        return redirect('/')

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        con = get_connection()
        cur = con.cursor()

        cur.execute(
            "INSERT INTO notes(title, content, created_at, user_id) VALUES(?, ?, datetime('now'), ?)",
            (title, content, session['user_id'])
        )

        con.commit()
        con.close()

        flash("Note Added", "success")
        return redirect('/dashboard')

    return render_template('add_note.html')


# ---------------- DELETE NOTE ----------------
@app.route('/delete_note/<int:id>', methods=['POST'])
def delete_note(id):
    if 'user_id' not in session:
        return redirect('/')

    con = get_connection()
    cur = con.cursor()

    cur.execute(
        "DELETE FROM notes WHERE id=? AND user_id=?",
        (id, session['user_id'])
    )

    con.commit()
    con.close()

    flash("Note Deleted","danger")
    return redirect('/dashboard')


# ---------------- VIEW NOTE ----------------
@app.route('/view_note/<int:id>')
def view_note(id):
    if 'user_id' not in session:
        return redirect('/')

    con = get_connection()
    cur = con.cursor()

    cur.execute(
        "SELECT * FROM notes WHERE id=? AND user_id=?",
        (id, session['user_id'])
    )

    note = cur.fetchone()
    con.close()

    return render_template('view_note.html', note=note)


# ---------------- EDIT NOTE ----------------
@app.route('/edit_note/<int:id>', methods=['GET','POST'])
def edit_note(id):
    if 'user_id' not in session:
        return redirect('/')

    con = get_connection()
    cur = con.cursor()

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        cur.execute(
            "UPDATE notes SET title=?, content=? WHERE id=? AND user_id=?",
            (title, content, id, session['user_id'])
        )

        con.commit()
        con.close()

        flash("Note Updated","success")
        return redirect('/dashboard')

    cur.execute(
        "SELECT * FROM notes WHERE id=? AND user_id=?",
        (id, session['user_id'])
    )

    note = cur.fetchone()
    con.close()

    return render_template('edit_note.html', note=note)

# ---------------- FORGOT PASSWORD (EMAIL OTP) ----------------
otp_store = {}

@app.route('/forgot', methods=['GET','POST'])
def forgot():
    if request.method == 'POST':
        email = request.form['email']

        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone()

        if user:
            otp = random.randint(100000,999999)
            otp_store[email] = otp
            session['reset_email'] = email

            send_email(email, "Notes App OTP Verification",
                       f"Hello,\n\nYour OTP is: {otp}\n\nDo not share this OTP.\n\nThank you.")

            flash("OTP sent to your email","success")
            con.close()
            return redirect('/otp')

        else:
            flash("Email not found","danger")
            con.close()
            return redirect('/forgot')

    return render_template('forgot.html')


# ---------------- OTP ----------------
@app.route('/otp', methods=['GET','POST'])
def otp():
    email = session.get('reset_email')

    if not email:
        return redirect('/forgot')

    if request.method == 'POST':
        entered = request.form['otp']

        if email in otp_store and str(otp_store[email]) == entered:
            return redirect('/reset')
        else:
            flash("Invalid OTP","danger")

    return render_template('otp.html')


# ---------------- RESEND OTP ----------------
@app.route('/resend-otp')
def resend_otp():
    email = session.get('reset_email')

    if not email:
        return redirect('/forgot')

    otp = random.randint(100000, 999999)
    otp_store[email] = otp

    send_email(email, "Notes App OTP Verification",
               f"Hello,\n\nYour new OTP is: {otp}\n\nDo not share this OTP.")

    flash("OTP resent successfully!", "success")
    return redirect('/otp')


# ---------------- RESET PASSWORD ----------------
@app.route('/reset', methods=['GET','POST'])
def reset():
    email = session.get('reset_email')

    if not email:
        return redirect('/forgot')

    if request.method == 'POST':
        password = request.form['password']
        confirm = request.form['confirm']

        if password != confirm:
            flash("Passwords do not match","danger")
            return redirect('/reset')

        hashed_password = generate_password_hash(password)

        con = get_connection()
        cur = con.cursor()

        cur.execute(
            "UPDATE users SET password=? WHERE email=?",
            (hashed_password, email)
        )

        con.commit()
        con.close()

        otp_store.pop(email, None)
        session.pop('reset_email', None)

        flash("Password Updated Successfully","success")
        return redirect('/')

    return render_template('reset.html')


# ---------------- CONTACT (REAL EMAIL) ----------------
@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        full_message = f"""
New Contact Message

Name: {name}
Email: {email}

Message:
{message}
"""

        send_email(SENDER_EMAIL, "New Contact Message", full_message)

        flash("Message sent successfully!", "success")
        return redirect('/contact')

    return render_template('contact.html')


# ---------------- ABOUT ----------------
@app.route('/about')
def about():
    return render_template('about.html')


# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)