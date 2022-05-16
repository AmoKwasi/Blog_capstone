from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor   # makes the text boxes for comments etc
from datetime import date
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash # for password security
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship  # database relationships
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import LoginForm, RegisterForm, CreatePostForm, CommentForm   #imports from forms
from flask_gravatar import Gravatar    # creates avatar for users

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
# This will give user avatars / has jinja templating in post.html under div class="commenterImage"
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#  Works with login app route ton ensure user can login
# Configuring flask app to use Flask login
login_manager = LoginManager()
login_manager.init_app(app)


#  This callback is used to reload the user object from the user ID stored in the session. It should take the str ID of a user, and return the corresponding user object
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # user object created from string


##CONFIGURE TABLE
# class user is how we can refer to this code in the main.py / it will also set db in this class
class User(UserMixin, db.Model):  # Mixin is simply a way to provide multiple inheritance to Python.
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    ####### THIS  WILL CREATE A RELATIONAL DATABASE between User Table and BlogPost Table  WHERE USER IS THE PARENT AND BLOG POST IS THE CHILD ####
    # WILL LINK BLOGPOST(child) WITH USER(parent) SO WE CAN SEE WHICH USER(AUTHOR) HAS WRITTEN A PARTICULAR BLOGPOST
    # create a bidirectional One-to-Many relationship between the two tables to easily locate the BlogPosts a User has written and also the User of any BlogPost object.
    # THE USER IS THE ONE WHILE BLOGPOST IS THE MANY / SO ONE USER CAN MAKE MANY BLOGPOST
    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")


    # *******Add parent relationship*******#
    # EX OF RELATIONAL DB WHERE DB SHARE A PARENT CHILD RELATIONSHIP ALONG W ONE TO MANY Relationship
    # the child relationship will be declared in comment
    #  MAKES USER THE PARENT OF THE COMMENTS WHERE USER(paraent) IS THE ONE AND COMMENT(child) IS THE MANY
    # "comment_author" refers to the comment_author property in the Comment class.
    comments = relationship("Comment", back_populates="comment_author")

# Create all the tables in the database only need to use one
# When making changes to structure of db delete all of db in pycharm to allow bd to be restructured
db.create_all()


##CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    ### REALTIONAL DATABASE CHILD OBJECT ########
    # USING THE AUTHOR ID OR USER ID IT WILL CREATE A NEW DATA BASE COLUMN UNDER THE ID
    # Create Foreign Key, "users.id" the users refers to the table name of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    # THE USER CAN THEN CREATE POSTS UNDER THIER ID
    author = relationship("User", back_populates="posts")


    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    # ***************Parent Relationship*************#
    # creates a relational db with the BlogPost as the parent and the comment as the child
    # in this scenerio the BlogPost is the  one while the comments are the many / SO each individual blog post can have many comments
    comments = relationship("Comment", back_populates="parent_post")
db.create_all()



# Creates a Table called Comment where the tablename is "comments" contains an id and a text property which will be the primary key and the text entered into the CKEditor
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))

    # *******Add child relationship*******#
    #  Setting relational db ; Where comment is the child and the many and user is the parent and the one(datapoint)
    # "users.id" The users refers to the tablename of the Users class.
    # "comments" refers to the comments property in the User class.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    comment_author = relationship("User", back_populates="comments")

    text = db.Column(db.Text, nullable=False)
db.create_all()


#Create admin-only decorator to makse sure only admin can make new post delete post or edit post works with: from functools import wraps / from flask import abort
def admin_only(f):
    #if your arent the admin or first user then cant make changes spits flash method
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        #Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def get_all_posts():
    # says search through the entire db which is in the Blogpost class
    posts = BlogPost.query.all()
    # checks if user is authenticated and if they are if will have logout in nave bar if not register/login
    return render_template("index.html", all_posts=posts, current_user=current_user)


#Register new users into the User database
@app.route('/register', methods=["GET", "POST"])
def register():
    # for defined in forms.py which is imported into this main.py  that we can tap into
    form = RegisterForm()
    # if form valid when submitted
    if form.validate_on_submit():
        # will check if the user email already exists

        if User.query.filter_by(email=form.email.data).first():
            print(User.query.filter_by(email=form.email.data).first())
            # User already exists /   # Send flash messsage / will print user first name after they register
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        # says add this to the  db which is in the User class
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        #This line will authenticate the user with Flask-Login
        login_user(new_user)

        # when user is logged in go to homepage route
        return redirect(url_for("get_all_posts"))
    # checks if user is authenticated and if they are it will have logout in nave bar if not register/login
    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    # will import the login form from forms.py and this statement will make it work
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        # Email doesn't exist or password incorrect.
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    # checks if user is authenticated and if they are it will have logout in nave bar if not register/login
    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    # says search through the entire db which is in the Blogpost class and find the post_id
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    # Once blog is found by id in db then check if form is valid then if user is authenticated allow them to make comments
    #     If user not logged in will throw an error code
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        new_comment = Comment(
            text=form.comment_text.data,
            comment_author=current_user,
            parent_post=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()

    # checks if user is authenticated and if they are it will have logout in nave bar if not register/logi
    return render_template("post.html", post=requested_post, form=form, current_user=current_user)


@app.route("/about")
def about():
    # checks if user is authenticated and if they are it will have logout in nave bar if not register/login
    return render_template("about.html", current_user=current_user)


@app.route("/contact")
def contact():
    # checks if user is authenticated and if they are it will have logout in nave bar if not register/login
    return render_template("contact.html", current_user=current_user)


@app.route("/new-post", methods=["GET", "POST"])
#Mark with decorator  to make sure only adminn can access this pg
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))

    # checks if user is authenticated and if they are it will have logout in nave bar if not register/login
    return render_template("make-post.html", form=form, current_user=current_user)




@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
# Mark with decorator  to make sure only adminn can access this pg
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=current_user,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    # checks if user is authenticated and if they are it will have logout in nave bar if not register/login
    return render_template("make-post.html", form=edit_form, is_edit=True, current_user=current_user)


@app.route("/delete/<int:post_id>")
#Mark with decorator  to make sure only adminn can access this pg
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)