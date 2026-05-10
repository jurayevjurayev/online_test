from flask import Flask, render_template_string, request, redirect, session
import sqlite3
from reportlab.pdfgen import canvas
import io
from flask import send_file
import json
import os
import qrcode
import time
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.utils import ImageReader

try:
    from PyPDF2 import PdfReader, PdfWriter
except ImportError:
    PdfReader = None
    PdfWriter = None

from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
app.secret_key = "secret123"

with open("savollar.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

TESTS = {}
for name, filename in [("test1", "savollar_test1.json"), ("test2", "savollar_test2.json")]:
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            TESTS[name] = json.load(f)
    else:
        TESTS[name] = QUESTIONS

# DATABASE
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        score INTEGER DEFAULT 0,
        total INTEGER DEFAULT 0,
        has_taken_test INTEGER DEFAULT 0,
        spent_time INTEGER DEFAULT 0
    )
    """)

    for column_sql in [
        "ALTER TABLE users ADD COLUMN has_taken_test INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN test1_score INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN test1_total INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN test1_taken INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN test1_time INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN test2_score INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN test2_total INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN test2_taken INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN test2_time INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN last_test TEXT DEFAULT ''"
    ]:
        try:
            c.execute(column_sql)
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()

init_db()

# HOME
@app.route('/')
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
* {
    margin:0;
    padding:0;
    box-sizing:border-box;
}

body {
    font-family: Arial;
    height:100vh;
    display:flex;
    justify-content:center;
    align-items:center;
    background:url('https://dtpi.uz/wp-content/uploads/2025/01/asosiy.jpg') center/cover no-repeat;
    position:relative;
}

.overlay {
    position:absolute;
    inset:0;
    background:rgba(0,0,0,0.6);
}

.container {
    position:relative;
    z-index:2;
    width:90%;
    max-width:600px;
    text-align:center;
    color:white;
    padding:20px;
}

h1 {
    font-size:clamp(22px, 5vw, 42px);
    margin-bottom:10px;
}

p {
    font-size:clamp(12px, 3.5vw, 18px);
    opacity:0.8;
    margin-bottom:30px;
}

.buttons {
    display:flex;
    gap:15px;
    justify-content:center;
    flex-wrap:wrap;
}

.btn {
    padding:12px 20px;
    border-radius:8px;
    text-decoration:none;
    font-size:16px;
    width:180px;
    text-align:center;
    transition:0.3s;
}

.register {
    background:#2a5298;
    color:white;
}

.login {
    background:white;
    color:#2a5298;
}

.btn:hover {
    transform:scale(1.05);
}

@media (max-width:768px) {

    .buttons {
        flex-direction:column;
        align-items:center;
    }

    .btn {
        width:100%;
        max-width:300px;
    }
}
</style>
</head>

<body>

<div class="overlay"></div>

<div class="container">
    <h1>Platformaga xush kelibsiz</h1>
    <p>Dasturchi: Ixtiyor Jurayev</p>

    <div class="buttons">
        <a href="/register" class="btn register">Ro‘yxatdan o‘tish</a>
        <a href="/login" class="btn login">Kirish</a>
    </div>
</div>

</body>
</html>
""")

# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("users.db")
        c = conn.cursor()

        try:
            c.execute(
                "INSERT INTO users(username,password) VALUES(?,?)",
                (username, password)
            )

            conn.commit()

        except:
            conn.close()
            return "Bu foydalanuvchi mavjud!"

        conn.close()

        return redirect('/login')

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

body{
    margin:0;
    font-family:Arial;
    height:100vh;
    display:flex;
    justify-content:center;
    align-items:center;
    background:linear-gradient(135deg,#141e30,#243b55);
}

.card{
    background:white;
    width:90%;
    max-width:400px;
    padding:30px;
    border-radius:15px;
    text-align:center;
}

input{
    width:100%;
    padding:12px;
    margin:10px 0;
    border-radius:8px;
    border:1px solid #ccc;
    box-sizing:border-box;
}

button{
    width:100%;
    padding:12px;
    border:none;
    border-radius:8px;
    background:#243b55;
    color:white;
    font-size:16px;
}

h2{
    margin-bottom:20px;
}

</style>
</head>

<body>

<div class="card">

<h2>Ro‘yxatdan o‘tish</h2>

<form method="POST">

<input type="text" name="username" placeholder="Foydalanuvchi nomi" required>

<input type="password" name="password" placeholder="Parol" required>

<button type="submit">Ro‘yxatdan o‘tish</button>

</form>

</div>

</body>
</html>
""")

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():

    error = None

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("users.db")
        c = conn.cursor()

        c.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = c.fetchone()
        conn.close()

        if user:
            session['user'] = username
            return redirect('/profile')
        else:
            error = "❌ Login yoki parol noto‘g‘ri!"

    return render_template_string("""

<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

body{
    margin:0;
    font-family:Arial;
    height:100vh;
    display:flex;
    justify-content:center;
    align-items:center;
    background:linear-gradient(135deg,#141e30,#243b55);
}

.card{
    background:white;
    width:90%;
    max-width:400px;
    padding:30px;
    border-radius:15px;
    text-align:center;
}

input{
    width:100%;
    padding:12px;
    margin:10px 0;
    border-radius:8px;
    border:1px solid #ccc;
    box-sizing:border-box;
}

button{
    width:100%;
    padding:12px;
    border:none;
    border-radius:8px;
    background:#243b55;
    color:white;
    font-size:16px;
    cursor:pointer;
}

.error{
    color:white;
    background:red;
    padding:10px;
    margin-top:10px;
    border-radius:8px;
    font-size:14px;
}

</style>
</head>

<body>

<div class="card">

<h2>Kirish</h2>

<form method="POST">

<input type="text" name="username" placeholder="Foydalanuvchi nomi" required>

<input type="password" name="password" placeholder="Parol" required>

<button type="submit">Kirish</button>

</form>

{% if error %}
<div class="error">{{error}}</div>
{% endif %}

</div>

</body>
</html>

""", error=error)

@app.route('/profile')
def profile():

    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("SELECT score, total, last_test FROM users WHERE username=?", (session['user'],))
    data = c.fetchone()

    score = data[0] if data else 0
    total = data[1] if data else 0
    last_test = data[2] if data and data[2] else "—"

    percent = int((score / total) * 100) if total > 0 else 0

    conn.close()

    return render_template_string("""

<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

body{
    margin:0;
    font-family:Arial;
    background:linear-gradient(135deg,#f4f4f4,#e9ecef);
}

.container{
    width:90%;
    max-width:750px;
    margin:50px auto;
}

.card{
    background:white;
    padding:35px;
    border-radius:15px;
    box-shadow:0 10px 25px rgba(0,0,0,0.1);
    text-align:center;
}

.avatar{
    width:80px;
    height:80px;
    background:#243b55;
    color:white;
    font-size:30px;
    display:flex;
    justify-content:center;
    align-items:center;
    border-radius:50%;
    margin:0 auto 15px;
}

h1{
    color:#243b55;
}

.info{
    margin-top:25px;
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:15px;
}

.box{
    background:#f1f3f5;
    padding:15px;
    border-radius:10px;
}

.btn{
    display:inline-block;
    margin-top:20px;
    padding:12px 20px;
    background:#243b55;
    color:white;
    text-decoration:none;
    border-radius:8px;
    margin-right:10px;
}

.logout{
    background:red;
}

.cert{
    background:green;
}

@media(max-width:600px){
    .info{
        grid-template-columns:1fr;
    }
}

</style>

</head>

<body>

<div class="container">

<div class="card">

<div class="avatar">
{{user[0].upper()}}
</div>

<h1>Xush kelibsiz {{user}} 🚀</h1>

<div class="info">

<div class="box">
<b>Foydalanuvchi nomi</b><br>
{{user}}
</div>

<div class="box">
<b>Status</b><br>
Foydalanuvchi
</div>

<div class="box">
<b>Natija</b><br>
{{score}} / {{total}} ({{percent}}%)
</div>

<div class="box">
<b>So'nggi test</b><br>
{{last_test}}
</div>

<div class="box">
<b>Testlar</b><br>
2 ta
</div>

</div>

<a href="/test-info" class="btn">Test ishlash</a>
                                  
<a href="/certificate-pdf" class="btn cert">📄Sertifikat olish</a> 

<a href="/ranking" class="btn">🏆 Reyting</a>                               

<a href="/logout" class="btn logout">Chiqish</a>
                                  
</div>

</div>

</body>
</html>

""", user=session['user'],
    score=score,
    total=total,
    percent=percent,
    last_test=last_test)

@app.route('/ranking')
def ranking():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

*{
    margin:0;
    padding:0;
    box-sizing:border-box;
}

body{
    font-family:Arial;
    background:linear-gradient(135deg,#141e30,#243b55);
    min-height:100vh;
    padding:20px;
}

.container{
    max-width:950px;
    margin:auto;
}

.title{
    text-align:center;
    color:white;
    margin-bottom:25px;
    font-size:35px;
}

.card{
    background:white;
    border-radius:20px;
    overflow:hidden;
    box-shadow:0 10px 30px rgba(0,0,0,0.3);
    padding:40px;
    text-align:center;
}

.btn{
    display:inline-block;
    margin:15px 10px;
    padding:14px 24px;
    background:#243b55;
    color:white;
    text-decoration:none;
    border-radius:10px;
    font-weight:bold;
}

</style>
</head>
<body>

<div class="container">

<h1 class="title">🏆 REYTING TANLASH</h1>

<div class="card">
    <p>Qaysi test bo‘yicha reytingni ko‘rmoqchisiz?</p>
    <a href="/ranking/test1" class="btn">Test 1 Reyting</a>
    <a href="/ranking/test2" class="btn">Test 2 Reyting</a>
    <div style="margin-top:20px;">
        <a href="/profile" class="btn">🏠 Profilga qaytish</a>
    </div>
</div>

</div>

</body>
</html>
""")

@app.route('/ranking/<test_name>')
def ranking_test(test_name):
    if test_name not in TESTS:
        return redirect('/ranking')

    test_label = "Test 1" if test_name == "test1" else "Test 2"
    score_col = f"{test_name}_score"
    total_col = f"{test_name}_total"
    time_col = f"{test_name}_time"

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute(f"SELECT username, {score_col}, {total_col}, {time_col} FROM users WHERE {total_col} > 0 ORDER BY {score_col} DESC, {time_col} ASC")
    users = c.fetchall()
    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

*{
    margin:0;
    padding:0;
    box-sizing:border-box;
}

body{
    font-family:Arial;
    background:linear-gradient(135deg,#141e30,#243b55);
    min-height:100vh;
    padding:20px;
}

.container{
    max-width:950px;
    margin:auto;
}

.title{
    text-align:center;
    color:white;
    margin-bottom:25px;
    font-size:35px;
}

.card{
    background:white;
    border-radius:20px;
    overflow:hidden;
    box-shadow:0 10px 30px rgba(0,0,0,0.3);
}

.table-head{
    background:#243b55;
    color:white;
    display:grid;
    grid-template-columns:80px 1fr 160px 160px;
    padding:18px;
    font-weight:bold;
}

.row{
    display:grid;
    grid-template-columns:80px 1fr 160px 160px;
    padding:18px;
    border-bottom:1px solid #eee;
    align-items:center;
    transition:0.3s;
}
                                 
.row:hover{
    background:#f5f7fa;
}

.rank{
    font-size:22px;
    font-weight:bold;
}
                                 
.user{
    font-weight:bold;
    color:#243b55;
}

.score{
    color:green;
    font-weight:bold;
}

.time{
    color:#dc3545;
    font-weight:bold;
}
                                 
.top1{
    background:#fff3cd;
}

.top2{
    background:#e2e3e5;
}

.top3{
    background:#f8d7da;
}
                                 
.btn{
    display:inline-block;
    margin:20px 10px;
    padding:14px 24px;
    background:white;
    color:#243b55;
    text-decoration:none;
    border-radius:10px;
    font-weight:bold;
}
                                 
@media(max-width:700px){

.table-head,
.row{
    grid-template-columns:60px 1fr;
    gap:10px;
}

.hide-mobile{
    display:none;
}

}
                                 
</style>
</head>
<body>

<div class="container">

<h1 class="title">🏆 {{test_label}} REYTING</h1>

<div class="card">

<div class="table-head">
<div>#</div>
<div>Foydalanuvchi</div>
<div class="hide-mobile">To‘g‘ri javob</div>
<div class="hide-mobile">Sarflagan vaqt</div>
</div>
                                  
{% for user in users %}

<div class="row
{% if loop.index == 1 %}top1
{% elif loop.index == 2 %}top2
{% elif loop.index == 3 %}top3
{% endif %}">

<div class="rank">
{% if loop.index == 1 %}
🥇
{% elif loop.index == 2 %}
🥈
{% elif loop.index == 3 %}
🥉
{% else %}
{{loop.index}}
{% endif %}
</div>
                                  
<div class="user">
{{user[0]}}
</div>

<div class="score hide-mobile">
{{user[1]}} / {{user[2]}}
</div>

<div class="time hide-mobile">
⏱ {{user[3]}} sek
</div>

</div>

{% endfor %}

</div>
                                  
<center>
<a href="/ranking" class="btn">
◀️ Testni tanlash
</a>
<a href="/profile" class="btn">
🏠 Profilga qaytish
</a>
</center>

</div>

</body>
</html>
""", users=users, test_label=test_label)


@app.route('/test-info')
def test_info():

    if 'user' not in session:
        return redirect('/login')

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

body{
    margin:0;
    font-family:Arial;
    background:linear-gradient(135deg,#141e30,#243b55);
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
    padding:15px;
}

.card{
    background:white;
    color:black;
    width:100%;
    max-width:500px;
    padding:25px;
    border-radius:15px;
    text-align:center;
    box-sizing:border-box;
}

h1{
    font-size:clamp(20px,4vw,28px);
    margin-bottom:10px;
}

ul{
    text-align:left;
    padding-left:20px;
    font-size:clamp(14px,3.5vw,16px);
    line-height:1.6;
}

.btn{
    display:inline-block;
    margin-top:20px;
    padding:12px 18px;
    background:#243b55;
    color:white;
    text-decoration:none;
    border-radius:8px;
    width:100%;
    max-width:250px;
}

.btn:hover{
    transform:scale(1.03);
}

</style>

</head>

<body>

<div class="card">

<h1>DIQQAT❗️</h1>

<div style="display:flex;justify-content:center;gap:15px;flex-wrap:wrap;margin-bottom:20px;">
    <a href="/test-start/test1" class="btn">Test 1</a>
    <a href="/test-start/test2" class="btn">Test 2</a>
</div>

<ul>
    <li>Har bir savol uchun 30 sekunt vaqt ajratilgan bo'lib jami 30 ta savol mavjud</li>
    <li>Test oxirida natija foizda chiqadi</li>
    <li>Testni faqat 1 marta ishlash imkoniyati mavjud</li>
    <li>Savollarga javob berilgandan so'ng navbatdagi savolga o'tiladi</li>
</ul>

</div>

</body>
</html>
""")

@app.route('/test-start')
@app.route('/test-start/<test_name>')
def test_start(test_name=None):

    if 'user' not in session:
        return redirect('/login')

    if test_name not in TESTS:
        return redirect('/test-info')

    session['q_index'] = 0
    session['score_temp'] = 0
    session['start_time'] = time.time()
    session['test_name'] = test_name

    return redirect('/test')

# TEST PAGE
@app.route('/test', methods=['GET', 'POST'])
def test():

    if 'user' not in session:
        return redirect('/login')

    if 'test_name' not in session:
        return redirect('/test-info')

    test_name = session['test_name']
    questions = TESTS.get(test_name, QUESTIONS)
    test_label = "Test 1" if test_name == "test1" else "Test 2"
    taken_col = f"{test_name}_taken"

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute(
        f"SELECT {taken_col} FROM users WHERE username=?",
        (session['user'],)
    )

    data = c.fetchone()
    conn.close()

    if data and data[0] == 1:

        return render_template_string("""
<!DOCTYPE html>
<html>

<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

body{
    margin:0;
    font-family:Arial;
    background:linear-gradient(135deg,#141e30,#243b55);
    display:flex;
    justify-content:center;
    align-items:center;
    height:100vh;
    padding:15px;
}

.card{
    background:white;
    width:100%;
    max-width:500px;
    padding:40px 30px;
    border-radius:20px;
    text-align:center;
}

.title{
    font-size:28px;
    font-weight:bold;
    color:#243b55;
}

.text{
    margin-top:15px;
    font-size:18px;
}

.btn{
    display:inline-block;
    margin-top:25px;
    padding:14px 24px;
    background:#243b55;
    color:white;
    text-decoration:none;
    border-radius:10px;
}

</style>
</head>

<body>

<div class="card">

<div class="title">
❌ Test yakunlangan
</div>

<div class="text">
Siz allaqachon {{test_label}} topshirgansiz
</div>

<a href="/profile" class="btn">
Profilga qaytish
</a>

</div>

</body>
</html>
""", test_label=test_label)

    if 'q_index' not in session:
        session['q_index'] = 0
        session['score_temp'] = 0

    index = session['q_index']

    # TEST TUGASHI (eng to‘g‘ri joyga ko‘chirildi)
    if index >= len(questions):

        final_score = session['score_temp']
        total = len(questions)

        percent = int((final_score / total) * 100) if total > 0 else 0
        spent_time = int(time.time() - session['start_time'])

        conn = sqlite3.connect("users.db")
        c = conn.cursor()

        c.execute(f"""
         UPDATE users
         SET {test_name}_score=?, {test_name}_total=?, {test_name}_taken=1, {test_name}_time=?, score=?, total=?, has_taken_test=1, spent_time=?, last_test=?
         WHERE username=?
        """, (final_score, total, spent_time, final_score, total, spent_time, test_label, session['user']))

        conn.commit()
        conn.close()

        session.pop('q_index', None)
        session.pop('score_temp', None)
        session.pop('start_time', None)
        session.pop('test_name', None)

        return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

body{
    margin:0;
    font-family:Arial;
    background:linear-gradient(135deg,#141e30,#243b55);
    display:flex;
    justify-content:center;
    align-items:center;
    height:100vh;
}

.card{
    background:white;
    width:90%;
    max-width:500px;
    padding:40px;
    border-radius:15px;
    text-align:center;
    box-shadow:0 10px 30px rgba(0,0,0,0.3);
}

.title{
    font-size:28px;
    font-weight:bold;
    color:#243b55;
    margin-bottom:20px;
}

.result{
    font-size:22px;
    margin:15px 0;
    color:#333;
}

.percent{
    font-size:28px;
    font-weight:bold;
    color:green;
    margin:10px 0;
}

.btn{
    display:inline-block;
    margin-top:20px;
    padding:12px 20px;
    background:#243b55;
    color:white;
    text-decoration:none;
    border-radius:8px;
    transition:0.3s;
}

.btn:hover{
    transform:scale(1.05);
}

</style>

</head>

<body>

<div class="card">

<div class="title">🎉 TEST YAKUNLANDI</div>

<div class="result">
    To‘g‘ri javoblar: <b>{{final_score}}</b> / {{total}}
</div>

<div class="percent">
    {{percent}}%
</div>

<a href="/profile" class="btn">🏠 Profilga qaytish</a>

</div>

</body>
</html>
""", final_score=final_score, total=total, percent=percent)

    # JAVOB QABUL QILISH
    if request.method == 'POST':

     answer = request.form.get('answer')  # 🔥 MUHIM

     # agar user javob bergan bo‘lsa
     if answer is not None:
        answer = int(answer)
        correct = questions[index]['correct']

        if answer == correct:
            session['score_temp'] += 1

     # har qanday holatda keyingi savolga o‘tadi
     session['q_index'] += 1
     return redirect('/test')

    # SAVOL KO‘RSATISH (RESPONSIVE UI)
    q = questions[index]
    total = len(questions)

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

body{
    margin:0;
    font-family:Arial;
    background:linear-gradient(135deg,#141e30,#243b55);
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
    padding:15px;
}

.card{
    background:white;
    width:100%;
    max-width:600px;
    padding:25px;
    border-radius:15px;
    box-sizing:border-box;
}

.progress{
    font-size:14px;
    color:gray;
    margin-bottom:10px;
}

.question{
    font-size:20px;
    font-weight:bold;
    margin-bottom:20px;
}

.btn{
    display:block;
    width:100%;
    padding:12px;
    margin:8px 0;
    border:none;
    border-radius:8px;
    background:#243b55;
    color:white;
    font-size:16px;
    cursor:pointer;
}

.btn:hover{
    background:#1a2a3a;
}

</style>
</head>

<body>

<div class="card">

    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;gap:10px;flex-wrap:wrap;">

    <div class="progress">
        Savol {{ index + 1 }} / {{ total }}
    </div>

    <div id="timer" style="
        background:#dc3545;
        color:white;
        padding:8px 14px;
        border-radius:8px;
        font-weight:bold;
        font-size:18px;
    ">
        30
    </div>

</div>

    <div class="question">
        {{ q['q'] }}
    </div>

    <form method="POST">
        {% for i in range(4) %}
            <button class="btn" name="answer" value="{{i}}">
                {{ q['a'][i] }}
            </button>
        {% endfor %}
    </form>

</div>

                                  <script>

let time = 30;

let timer = document.getElementById("timer");

let countdown = setInterval(function(){

    time--;

    timer.innerHTML = time;

    if(time <= 0){

        clearInterval(countdown);

        document.forms[0].submit();

    }

},1000);

</script>
</body>
</html>
""", q=q, index=index, total=total)

@app.route('/verify/<username>')
def verify(username):

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("SELECT score, total, last_test FROM users WHERE username=?", (username,))
    data = c.fetchone()
    conn.close()

    if not data:
        return "❌ Sertifikat topilmadi"

    score, total, last_test = data
    percent = int((score / total) * 100) if total > 0 else 0
    last_test = last_test or "Test"

    return f"""
    <h2>✔ Sertifikat tasdiqlandi</h2>
    <p>Foydalanuvchi: {username}</p>
    <p>Test turi: {last_test}</p>
    <p>Natija: {percent}%</p>
    """


@app.route('/certificate-pdf')
def certificate_pdf():

    if 'user' not in session:
        return redirect('/login')

    # Positions (qo'lda sozlash uchun)
    name_y = 640  # Nom uchun y pozitsiyasi
    name_x_offset = -300  # Nom uchun x offset (markazdan)
    result_y = 850  # Natija uchun y pozitsiyasi
    result_x_offset = -600  # Natija uchun x offset (markazdan)
    qr_x_offset = 400  # QR kodning o'ngdan masofasi
    qr_y_offset = 330  # QR kodning pastdan masofasi
    font_size_name = 50  # Nom uchun shrift o'lchami
    font_size_result = 20  # Natija uchun shrift o'lchami
    qr_size = 170  # QR kod o'lchami

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("SELECT score, total, last_test FROM users WHERE username=?", (session['user'],))
    data = c.fetchone()
    conn.close()

    if not data:
        return "Sertifikat topilmadi"

    score, total, last_test = data
    if not last_test:
        last_test = "Test"

    if not total:
        total = 1

    percent = int((score / total) * 100)
    name = session['user']
    result = f"{score} / {total} ({percent}%)"
    verify_url = f"https://online-test-hxts.onrender.com/verify/{name}"

    width, height = landscape(A4)

    overlay_buffer = io.BytesIO()
    overlay = canvas.Canvas(overlay_buffer, pagesize=landscape(A4))

    overlay.setFillColorRGB(0.06, 0.27, 0.36)
    overlay.setFont("Helvetica-Bold", 42)
    overlay.drawCentredString(width / 2, height - 200, "SERTIFIKAT")

    overlay.setFont("Helvetica", 18)
    overlay.drawCentredString(width / 2, height - 240, "Sizning test natijalaringiz asosida beriladi")

    overlay.setFont("Helvetica-Bold", 36)
    overlay.setFillColorRGB(0.08, 0.32, 0.22)
    overlay.drawCentredString(width / 2, height - 320, name.upper())

    overlay.setFont("Helvetica-Bold", 28)
    overlay.setFillColorRGB(0, 0, 0)
    overlay.drawCentredString(width / 2, height - 380, result)

    overlay.setFont("Helvetica", 18)
    overlay.drawCentredString(width / 2, height - 430, f"Test turi: {last_test}")

    overlay.setFont("Helvetica", 14)
    overlay.drawCentredString(width / 2, height - 460, "Siz ushbu sertifikatni onlayn test natijalari asosida oldingiz.")

    overlay.setFont("Helvetica", 12)
    overlay.setFillColorRGB(0.06, 0.27, 0.36)
    overlay.drawString(55, 55, "Tekshirish uchun: ")
    overlay.drawString(190, 55, verify_url)

    qr = qrcode.make(verify_url)
    qr = qr.resize((170, 170))
    qr_buffer = io.BytesIO()
    qr.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    overlay.drawImage(
        ImageReader(qr_buffer),
        width - 235,
        55,
        width=170,
        height=170,
        mask='auto'
    )

    overlay.save()
    overlay_buffer.seek(0)

    template_path = "certificate_template.png"

    if os.path.exists(template_path):
        img = Image.open(template_path)

        draw = ImageDraw.Draw(img)

        # Font yuklash
        font_path = r"C:\Windows\Fonts\arial.ttf"
        if os.path.exists(font_path):
            font_name = ImageFont.truetype(font_path, font_size_name)
            font_result = ImageFont.truetype(font_path, font_size_result)
            font_test = ImageFont.truetype(font_path, 22)
        else:
            font_name = ImageFont.load_default()
            font_result = ImageFont.load_default()
            font_test = ImageFont.load_default()

        # Name
        name_text = name.upper()
        bbox = draw.textbbox((0, 0), name_text, font=font_name)
        text_width = bbox[2] - bbox[0]
        x_name = (img.width - text_width) // 2 + name_x_offset
        draw.text((x_name, name_y), name_text, fill=(0, 0, 0), font=font_name)

        # Result
        bbox = draw.textbbox((0, 0), result, font=font_result)
        text_width = bbox[2] - bbox[0]
        x_result = (img.width - text_width) // 2 + result_x_offset
        draw.text((x_result, result_y), result, fill=(0, 0, 0), font=font_result)

        # Test label
        test_text = f"Test turi: {last_test}"
        bbox = draw.textbbox((0, 0), test_text, font=font_test)
        text_width = bbox[2] - bbox[0]
        x_test = (img.width - text_width) // 2 + result_x_offset
        draw.text((x_test, result_y + 50), test_text, fill=(0, 0, 0), font=font_test)

        # QR
        qr = qrcode.make(verify_url)
        qr = qr.resize((qr_size, qr_size))
        img.paste(qr, (img.width - qr_x_offset, img.height - qr_y_offset))

        # Save img

        img_buffer = io.BytesIO()

        img.save(img_buffer, format="PNG")

        img_buffer.seek(0)

        # PDF

        pdf_buffer = io.BytesIO()

        c = canvas.Canvas(pdf_buffer, pagesize=landscape(A4))

        page_width, page_height = landscape(A4)

        img_width, img_height = img.size

        scale = min(page_width / img_width, page_height / img_height)

        c.drawImage(ImageReader(img_buffer), 0, 0, width=img_width * scale, height=img_height * scale)

        c.save()

        pdf_buffer.seek(0)

        return send_file(pdf_buffer, as_attachment=True, download_name="sertifikat.pdf", mimetype="application/pdf")

    return send_file(
        overlay_buffer,
        as_attachment=True,
        download_name="sertifikat.pdf",
        mimetype="application/pdf"
    )
# LOGOUT
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")