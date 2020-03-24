from flask import Flask,render_template,request,session,flash,redirect,url_for,logging
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from werkzeug import secure_filename
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from flask_mysqldb import  MySQL
import json
import os
import math
from datetime import datetime

with open('config.json','r') as c:
    params=json.load(c)['params']

local_server=True
app=Flask(__name__)

# config MySQL
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']=''
app.config['MYSQL_DB']='department'
app.config['MYSQL_CURSORCLASS']='DictCursor'

# init MySQL
mysql=MySQL(app)
app.secret_key='akash@123'
app.config['UPLOAD_FOLDER']=params['upload_location']
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail-user'],
    MAIL_PASSWORD=params['gmail-password']
)
mail=Mail(app)
if(local_server):
    app.config['SQLALCHEMY_DATABASE_URI']= params['local_url']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] =params['prod_url']
db=SQLAlchemy(app)

class Contacts(db.Model):
    sno=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(20),nullable=False)
    email=db.Column(db.String(20),nullable=False)
    phone_no=db.Column(db.String(12),nullable=False)
    message=db.Column(db.String(120),nullable=False)
    date=db.Column(db.String(20),nullable=True)


class Posts(db.Model):
    sno=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(20),nullable=False)
    slug =db.Column(db.String(50), nullable=False)
    content=db.Column(db.String(200),nullable=False)
    tagline=db.Column(db.String(200),nullable=False)
    date=db.Column(db.String(20),nullable=True)


# class Login(db.Model):
#     username=db.Column(db.String(50),primary_key=True,nullable=False)
#     user_password=db.Column(db.String(15),nullable=False)




@app.route("/")
def home():
    return render_template('index.html',params=params)


@app.route("/notices")
def notices():
    posts=Posts.query.filter_by().all()
    last=math.floor(len(posts)/int(params['no_of_posts']))

    page=request.args.get('page')
    if not str(page).isnumeric():
        page=1
        page=int(page)
    posts=posts[(page-1)*int(params['no_of_posts']):(page-1)*int(params['no_of_posts'])+int(params['no_of_posts'])]
    if page==1:
        prev="#"
        next="/?page="+ str(page+1)
    elif(page==last):
        prev="/?page="+ str(page-1)
        next="#"
    else:
        prev="/?page="+ str(page-1)
        next="/?page="+ str(page+1)

    return render_template('notices.html',params=params,post=posts,prev=prev,next=next)


@app.route("/edit/<string:sno>",methods=['GET','POST'])
def edit(sno):
    if 'user' in session and session['user']==params['admin_user']:
        if request.method=='POST':
            box_title=request.form.get('title')
            tagline=request.form.get('tagline')
            slug=request.form.get('slug')
            content=request.form.get('content')
            date=datetime.now()
            if sno=='0':
                post=Posts(title=box_title,slug=slug,tagline=tagline,content=content,date=date)
                db.session.add(post)
                db.session.commit()
            else:
                post=Posts.query.filter_by(sno=sno).first()
                post.title=box_title
                post.slug=slug
                post.content=content
                post.tagline=tagline
                post.date=date
                db.session.commit()
                return redirect('/edit/'+sno)

        post = Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html',params=params,post=post,sno=sno)




@app.route("/dashboard",methods=['GET','POST'])
def dashboard():
    if 'user' in session and session['user']==params['admin_user']:
        posts = Posts.query.all()
        return render_template('dashboard.html',params=params,posts=posts)

    if request.method=='POST':
        username=request.form.get('name')
        userpass=request.form.get('pass')
        if(username==params['admin_user'] and userpass==params['admin_password']):
            session['user']=username
            posts=Posts.query.all()
            return render_template('dashboard.html',params=params,posts=posts)

    return render_template('admin.html',params=params)

class RegisterForm(Form):
    # name=StringField('Name',[validators.Length(min=1,max=50)])
    user_name=StringField('Username',[validators.Length(min=4,max=25)])
    register_no=StringField('Register_no',[validators.Length(min=7,max=10)])
    email=StringField('Email',[validators.Length(min=6,max=50)])
    password=PasswordField('Password',[
        validators.DataRequired(),
        validators.EqualTo('confirm',message='Passwords do not match')
    ])
    confirm=PasswordField('Confirm Password')
    course=StringField('Course',[validators.Length(min=5, max=10)])
    phone_no=StringField('Phone',[validators.Length(min=10,max=12)])

@app.route("/register", methods=['GET','POST'])
def register():
    form=RegisterForm(request.form)
    if request.method=='POST' and form.validate():
        name=form.user_name.data
        regno=form.register_no.data
        email=form.email.data
        password=sha256_crypt.encrypt((str(form.password.data)))
        # confirm=sha256_crypt.encrypt((str(form.confirm.data)))
        course=form.course.data
        phone=form.phone_no.data
        # create cursor
        cur=mysql.connection.cursor()
        cur.execute("INSERT INTO register(user_name,register_no,email,password,course,phone_no) VALUES(%s,%s,%s,%s,%s,%s)",(name,regno,email,password,course,phone))
        # commit to db
        mysql.connection.commit()
                # close connection
        cur.close()
        flash('You are now registered and can log in','success')
        return redirect(url_for('login'))
    return render_template('register.html',form=form)

@app.route("/login",methods=['GET','POST'])
def login():
    if request.method=='POST':
        # get form fields
        username=request.form['username']
        password_candidate=request.form['password']

        # create cursor
        cur=mysql.connection.cursor()
        # get user by username
        result=cur.execute("SELECT * FROM register WHERE user_name = %s",[username])
        if result > 0:
            # get stored hash
            data=cur.fetchone()
            password=data['password']

            # compare password
            if sha256_crypt.verify(password_candidate, password):
                session['logged_in']=True
                session['username']=username
                flash('you are now logged in','success')
                return redirect(url_for('userhomepage'))
            else:
                error='Invalid login'
                return render_template('login.html',error=error)
             # close connection
            cur.close()
        else:
            error='Username not found'
            return render_template('login.html',error=error)

    return render_template('login.html')


@app.route("/uploader", methods=['GET','POST'])
def uploader():
    if 'user' in session and session['user']==params['admin_user']:

        if request.method=='POST':
            f=request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'],secure_filename(f.filename)))
            return "Uploaded Successfully"


@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/dashboard')

@app.route("/delete/<string:sno>",methods=['GET','POST'])
def delete(sno):
    if 'user' in session and session['user']==params['admin_user']:
        post=Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
        return redirect('/dashboard')





@app.route("/about")
def about():
    return render_template('about.html',params=params)


@app.route("/post/<string:post_slug>",methods=['GET'])
def post_route(post_slug):
    post=Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html',params=params,post=post)


@app.route("/contact",methods=['GET','POST'])
def contact():
    if(request.method=='POST'):
        '''Add entry to the db'''
        name=request.form.get('name')
        email=request.form.get('email')
        phone=request.form.get('phone')
        message=request.form.get('msg')

        entry=Contacts(name=name,email=email,date=datetime.now(),phone_no=phone,message=message)
        db.session.add(entry)
        db.session.commit()
        mail.send_message('New message from' + name,
                          sender=email,
                          recipients=[params['gmail-user']],
                          body=message + '\n' + phone)
    return render_template('contact.html',params=params)


@app.route("/faculty")
def faculty():
    return render_template('faculty.html',params=params)


@app.route("/academics")
def academics():
    return render_template('academics.html',params=params)

@app.route("/userpage")
def userhomepage():
    return render_template('userpage.html')

app.run(debug=True)

