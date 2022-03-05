from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
from markupsafe import escape
import smtplib
import os

my_mail_id = "sreeeeeeenivas@gmail.com"
password = os.environ.get("MY_PW")
frm = "sreeeeeeenivas@gmail.com"
my_key = os.environ.get("MY_KEY")
c_year = datetime.today().year

app = Flask(__name__)
app.config['SECRET_KEY'] = my_key
ckeditor = CKEditor(app)
Bootstrap(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL",  "sqlite:///blog.db")
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    # authors = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="parent_post")


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    # *******Add parent relationship*******#
    # "comment_author" refers to the comment_author property in the Comment class.
    comments = relationship("Comment", back_populates="comment_author")


class Comment(db.Model):
    __tablename__ ="comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    #*******Add child relationship*******#
    #"users.id" The users refers to the tablename of the Users class.
    #"comments" refers to the comments property in the User class.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")

    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")

db.create_all()


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, current_user=current_user, current_year=c_year)


@app.route('/register', methods= ["GET", "POST"])
def register():
    r_form = RegisterForm()
    if r_form.validate_on_submit():
        u_name = r_form.name.data
        u_email = r_form.email.data
        if User.query.filter_by(email=u_email).first():
            flash(f'This email, "{u_email}", is already registered. You may login below or use a new email ID to register ')
            return redirect(url_for("login"))
        else:
            u_pw = generate_password_hash(r_form.password.data, method="pbkdf2:sha256", salt_length=8)
            new_user = User(name=u_name, email=u_email, password=u_pw)
            db.session.add(new_user)
            db.session.commit()
            #This line will authenticate the user with Flask-Login
            login_user(new_user)
            return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=r_form, current_user=current_user, current_year=c_year)


@app.route('/login', methods=["GET", "POST"])
def login():
    l_form = LoginForm()
    if l_form.validate_on_submit():
        u_email = l_form.email.data
        u_pw = l_form.password.data
        user = User.query.filter_by(email=u_email).first()
        if not user:
            flash(f'That email, "{u_email}", does not exist in the system. Please try again.')
            return redirect(url_for("login"))
        elif check_password_hash(user.password, u_pw):
            login_user(user)
            return redirect(url_for('get_all_posts'))
        else:
            flash("Password is incorrect. Please try again.")
            return redirect(url_for("login"))
    return render_template("login.html", form=l_form, current_user=current_user, current_year=c_year)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods= ["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    c_form = CommentForm()
    if c_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to Log-in or Register to comment on the post.")
            return redirect(url_for("login"))
        else:
            new_comment = Comment(text=c_form.comment_text.data,
                                  comment_author=current_user,
                                  parent_post=requested_post)
            db.session.add(new_comment)
            db.session.commit()
    return render_template("post.html", post=requested_post, current_user=current_user, current_year=c_year, form=c_form)


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user, current_year=c_year)


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        data = request.form
        print(data)
        Name = escape(data['name'])
        print(Name)
        Email = escape(data['email'])
        Phone = escape(data['phone'])
        Message = escape(data['message'])
        print(data, Name, Email, Phone, Message)
        msg = f"Subject:New Message\n\nName:{Name}\nEmail:{Email}\nPhone:{Phone}\nMessage:{Message}"
        connection = smtplib.SMTP("smtp.gmail.com")
        connection.starttls()
        connection.login(user=my_mail_id, password=password)
        connection.sendmail(from_addr=frm, to_addrs=my_mail_id, msg=msg)
        connection.close()
        return render_template('contact.html', msg_sent=True)
    return render_template("contact.html", current_user=current_user, current_year=c_year)


@app.route("/new-post", methods= ["GET", "POST"])
# @admin_only
def add_new_post():
    if current_user.is_authenticated:
        form = CreatePostForm()
        if form.validate_on_submit():
            new_post = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                body=form.body.data,
                img_url=form.img_url.data,
                author_id=current_user.id,
                date=date.today().strftime("%B %d, %Y")
            )
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for("get_all_posts"))
        return render_template("make-post.html", form=form, current_user=current_user, current_year=c_year)
    else:
        flash("You need to Log-in or Register to create a post.")
        return redirect(url_for("login"))


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        # author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, current_user=current_user, is_edit=True, current_year=c_year)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
    # app.run(host='localhost', port=5000, debug=True)
