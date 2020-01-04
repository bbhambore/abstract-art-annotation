from flask import Flask, render_template, flash, session, request, redirect
from flask_bootstrap import Bootstrap
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import io
import base64
import PIL.Image
from flask_ckeditor import CKEditor
from datetime import datetime

from PIL import Image
import io

import yaml
import os

app = Flask(__name__)
Bootstrap(app)

db = yaml.load(open('db.yaml'))
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

app.config['SECRET_KEY'] = os.urandom(24)
app.config['IMAGE_UPLOADS'] = 'static/img'

CKEditor(app)

@app.route('/')
def index():
    if session:
        cur = mysql.connection.cursor()
        # query = "SELECT * FROM ((SELECT * FROM question where user_id = " + str(session['userId']) + \
        # ") as q NATURAL JOIN (SELECT * FROM image) as i)"
        query = "SELECT * FROM ((SELECT * FROM question) as q NATURAL JOIN (SELECT * FROM image) as i) ORDER BY qid DESC"
        resultValue = cur.execute(query)
        if resultValue > 0:
            results = cur.fetchall()
            cur.close()
            for result in results:
                img = base64.b64encode(result["image_blob"]).decode("utf-8")
                result["image_blob"] = img
            return render_template('index.html', results = results)
        cur.close()
        return render_template('index.html', results = None)
    else:
        return redirect('/login')

@app.route('/questions/<int:id>', methods = ['GET', 'POST'])
def questions(id):

    if request.method == 'POST':
        response = "Response"
        print(request.form)
        for key,value in request.form.items():
            if key == "radio":
                response = value
            elif key == "new_conv":
                cur2 = mysql.connection.cursor()
                query = "INSERT INTO conversation(qid,status,logtime) VALUES (%s,%s,%s)"
                cur2.execute(query,(id,"Open",datetime.now())) ## Hard coding
                mysql.connection.commit()
                last_id_result = cur2.execute("SELECT LAST_INSERT_ID() as last_conv_id FROM conversation LIMIT 1")
                if last_id_result > 0:
                    last_id = cur2.fetchone()
                    conv_id = int(last_id["last_conv_id"])
                    reply = value
                cur2.close()
            else:
                conv_id = int(key)
                reply = value
        cur = mysql.connection.cursor()
        query = "INSERT INTO reply(user_id,conv_id,reply_type,reply,logtime) VALUES (%s,%s,%s,%s,%s)"
        cur.execute(query,(session['userId'],conv_id,response,reply,datetime.now()))
        mysql.connection.commit()
        cur.close()

    if id == 0:
        return "<h3>Select a question to view its replies</h3>"

    cur = mysql.connection.cursor()
    result = {}

    # query = "select * from question where qid = {}"
    query = "SELECT * FROM ((SELECT * FROM question where qid = " + str(id) + \
    ") as q NATURAL JOIN (SELECT * FROM image) as i)"
    res = cur.execute(query)
    # print(query)
    print("************************")
    # print(res)
    res = cur.fetchone()
    # print(res)
    # result['question'] = res['question']
    img = base64.b64encode(res["image_blob"]).decode("utf-8")
    res['image_blob'] = img
    res['userType'] = session['userType']
    # print(result)

    # query = "SELECT * FROM ((SELECT conv_id,qid,status,CAST(logtime AS char) as conv_logtime FROM conversation where qid = {} ) as A NATURAL JOIN "\
    # "(SELECT reply_id,user_id,conv_id,reply_type,reply,CAST(logtime AS char) as reply_logtime FROM reply) as B) " \
    # "ORDER BY conv_logtime DESC, reply_logtime ASC"

    query = "SELECT * FROM ((SELECT conv_id,qid,status,CAST(DATE_FORMAT(logtime, '%Y-%b-%d  %r') AS char) as conv_logtime FROM conversation where qid = {} ) as A NATURAL JOIN "\
    "(SELECT reply_id,user_id,conv_id,reply_type,reply,CAST(DATE_FORMAT(logtime, '%Y-%b-%d  %r') AS char) as reply_logtime FROM reply) as B) " \
    "ORDER BY conv_logtime DESC, reply_logtime ASC"

    user_query = "SELECT user_type,first_name,last_name,email from login WHERE user_id = {}"
    resultValue = cur.execute(query.format(id))
    # print("********************")
    print(resultValue)
    if resultValue > 0:
        results = cur.fetchall()
        new_conv = []
        not_found = True
        for result in results:
            cur1 = mysql.connection.cursor()
            userResultValue = cur1.execute(user_query.format(result["user_id"]))
            if userResultValue > 0:
                userResults = cur1.fetchone()
                user_name = userResults["first_name"] + " " + userResults["last_name"]
                user_email = userResults["email"]
                cur1.close()
            flag = 0
            for conv in new_conv:
                not_found = True
                if result['conv_id'] == conv['conv_id']:
                    not_found = False
                    # conv['replies'].append({"reply_id":result['reply_id'],"user_id":result['user_id'],"reply_type":result['reply_type'],"reply":result['reply'],"reply_logtime":result['reply_logtime']})
                    conv['replies'].append({"user_name":user_name,"user_email":user_email,"reply_id":result['reply_id'],"user_id":result['user_id'],"reply_type":result['reply_type'],"reply":result['reply'],"reply_logtime":result['reply_logtime']})
                    break
            if not_found:
                # new_conv.append({"conv_id":result['conv_id'], "qid":result['qid'], "status":result['status'],\
                # "conv_logtime":result['conv_logtime'],"replies":[{"reply_id":result['reply_id'],"user_id":result['user_id'],\
                # "reply_type":result['reply_type'],"reply":result['reply'],"reply_logtime":result['reply_logtime']}]})
                new_conv.append({"started_by":user_name,"conv_id":result['conv_id'], "qid":result['qid'], "status":result['status'],\
                "conv_logtime":result['conv_logtime'],"replies":[{"user_name":user_name,"user_email":user_email,"reply_id":result['reply_id'],"user_id":result['user_id'],\
                "reply_type":result['reply_type'],"reply":result['reply'],"reply_logtime":result['reply_logtime']}]})
        cur.close()
        return render_template('test1.html', conversations = new_conv , result = res)
    cur.close()
    return render_template('test1.html', result = res)

@app.route('/AcceptReject',methods = ['GET','POST'])
def foo():
    if request.method == 'POST':
        data = request.get_json(force=True)
        status = str(data["buttonID"]).split(".")[0]
        conv_id = str(data["buttonID"]).split(".")[1]
        cur = mysql.connection.cursor()
        query = "UPDATE conversation SET conversation.status = %s WHERE conv_id = %s"
        cur.execute(query,(status,conv_id))
        mysql.connection.commit()
        cur.close()
    return render_template('test1.html')

@app.route('/register/', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            userDetails = request.form
            print(userDetails['last_name'])
            if userDetails['password'] != userDetails['confirm_password']:
                flash('Passwords do not match! Try again.', 'danger')
                return render_template('register.html')
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO login (password, user_type, first_name, last_name, email)" \
            "VALUES(%s, %s, %s, %s, %s)", (generate_password_hash(userDetails['password']), \
            userDetails['user_type'], userDetails['first_name'], userDetails['last_name'], userDetails['email']))
            mysql.connection.commit()
            cur.close()
            flash('Registration successful! Please login.', 'success')
            return redirect('/login')
        except:
            flash('User could not be registered', 'danger')
            return render_template('register.html')
    return render_template('register.html')

@app.route('/login/', methods = ['GET', 'POST'])
def login():
    if request.method == "POST":
        userDetails = request.form
        email = userDetails['email']
        cur = mysql.connection.cursor()
        resultValue = cur.execute("SELECT * FROM login WHERE email = %s", ([email]))
        if resultValue > 0:
            user = cur.fetchone()
            # print(user)
            if check_password_hash(user['password'], userDetails['password']):
                session['login'] = True
                session['firstName'] = user['first_name']
                session['lastName'] = user['last_name']
                session['userId'] = user['user_id']
                if user['user_type'] == "Requestor":
                    session.clear()
                    cur.close()
                    flash('Only Responders can login', 'info')
                    return redirect('/login')
                session['userType'] = user['user_type']
                # print(session)
                flash('Welcome ' + session['firstName'] + '! You have been successfully logged in', 'success')
            else:
                cur.close()
                flash('Password do not match', 'danger')
                return render_template('login.html')
        else:
            cur.close()
            flash('User not found', 'danger')
            return render_template('login.html')
        cur.close()
        return redirect('/')
    return render_template('login.html')

@app.route('/upload-question/', methods = ['GET', 'POST'])
def write_blog():
    if session:
        if request.method == "POST":
            post = request.form
            question = post['question']
            author = session['userId']
            print('Post values')
            print(post)

            if request.files:
                image = request.files["photo"]
                imagePath = os.path.join(app.config["IMAGE_UPLOADS"], image.filename)
                image.save(imagePath)
                print("Image saved")
                cur = mysql.connection.cursor()
                imageId = insertBLOB(post['name'], imagePath, post['category'])

                query = "INSERT INTO question (image_id, user_id, question, status, created_dt)" \
                "VALUES (%s, %s, %s, %s, %s)"
                tuple = (imageId, author, question, "New", datetime.now())
                cur.execute(query, tuple)
                mysql.connection.commit()
                cur.close()
                flash("Successfully posted new question", 'success')
                os.remove(imagePath)
                return redirect('/')
        return render_template('upload-question.html')
    else:
        return redirect('/login')

@app.route('/logout/')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect('/login')

# @app.route('/upload/')
# def upload():
#     insertBLOB("Terrain", "D:/PGDBA/sem-1/fundamentals-of-database-systems/project/abstract-art/images/img_5terre.jpg","nature")
    # insertBLOB("Forest", "D:/PGDBA/sem-1/fundamentals-of-database-systems/project/abstract-art/images/img_forest.jpg","nature")
    # insertBLOB("Lights", "D:/PGDBA/sem-1/fundamentals-of-database-systems/project/abstract-art/images/img_lights.jpg","lights")
    # insertBLOB("Mountains", "D:/PGDBA/sem-1/fundamentals-of-database-systems/project/abstract-art/images/img_mountains.jpg","nature")
    # return render_template('login.html')
    # insertBLOB("Bharath", "D:/PGDBA/courses/udemy/flog/joker.jfif")
    # return render_template('login.html')

def convertToBinaryData(filename):
    # Convert digital data to binary format
    with open(filename, 'rb') as file:
        binaryData = file.read()
    return binaryData

def insertBLOB(name, photo, category):
    print("Inserting BLOB into IMAGE table")
    try:
        cur = mysql.connection.cursor();
        # sql_insert_blob_query = "INSERT INTO python_employee(name, photo) VALUES (%s,%s)"
        sql_insert_blob_query = "INSERT INTO image(image_blob, image_catg, image_name) VALUES (%s,%s,%s)"
        empPicture = convertToBinaryData(photo)

        # Convert data into tuple format
        insert_blob_tuple = (empPicture, category, name)
        result = cur.execute(sql_insert_blob_query, insert_blob_tuple)
        mysql.connection.commit()

        print("Image inserted successfully as a BLOB into IMAGE table", result)
        id = cur.lastrowid
    except mysql.connection.Error as error:
        print("Failed inserting BLOB data into IMAGE table {}".format(error))

    finally:
            cur.close()
            # connection.close()
            print("MySQL connection is closed")
            return id

if __name__ == '__main__':
    app.run(debug = True, host='0.0.0.0', port='5000')
