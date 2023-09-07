from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random as rand
from string import ascii_uppercase
import os
from dotenv import load_dotenv

from flask_sqlalchemy import SQLAlchemy

# room code
ROOM_CODE = "myRoom"

# load environment variables
load_dotenv()


# initialize flask and socketio
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)

# initialize database.
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("PSQL_URI")
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40))

    def __init__(self, name):
        self.name = name


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String)
    dateCreated = db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __init__(self, message, dateCreated, user_id):
        self.message = message
        self.dateCreated = dateCreated
        self.user_id = user_id





@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form["name"]

        # keep user on login page if they do not enter a valid name
        if (name == ""):
            return render_template("login.html", error="Please enter a name!")

        # check if the user already exists in database
        existing_user = User.query.filter_by(name=name).first()

        if existing_user:
            # set the user's name in the session because the user already exists
            session["name"] = name
            print("user exists already")
            return redirect(url_for("chat"))
        else:
            # create a new user instance in the database, since user does not exist
            new_user = User(name)
            db.session.add(new_user)
            db.session.commit()

            # set the user's name in session
            session["name"] = name
            print("new user!")
            return redirect(url_for("chat"))
    return render_template("login.html")


@app.route("/chat")
def chat():
    sessionName = session.get("name")
    # redriect user to login if they are not signed in.
    if sessionName is None:
        return redirect(url_for("login"))

    return render_template("chat.html")



@socketio.on("connect")
def socketConnect():
    sessionName = session.get("name")

    # make sure sessionname actually exists
    if not sessionName : return

    join_room(ROOM_CODE)
    print(sessionName + " has joined the room")



if __name__ == "__main__":
    socketio.run(app, debug=True)
