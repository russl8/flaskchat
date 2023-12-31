from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
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

# Database Operations -----------------------------------------------------------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("PSQL_URI")
db = SQLAlchemy(app)


"""
    DATABASE SCHEMAS.
    TO CREATE:

    python
    from main import db
    db.create_all()
"""


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


# ROUTES --------------------------------------------------------------------------------------

"""
Home Route.
Retrieves the session user, then 
Renders the chat page if a session user exists. Otherwise, render the login page.
Logs user in by adding username to database and session,
"""


@app.route("/", methods=["GET", "POST"])
def login():
    sessionName = session.get("name")

    # if a logged in user tries to go back to login page, redirect them to the chat page.
    if sessionName:
        return redirect(url_for("chat"))

    if request.method == "POST":
        name = request.form["name"]

        # keep user on login page if they do not enter a valid name
        if (name == ""):
            return render_template("login.html", error="Please enter a name!")

        # check if the user already exists in database
        existingUser = User.query.filter_by(name=name).first()

        if existingUser:
            # set the user's name in the session because the user already exists
            session["name"] = name
            print("user exists already")
            return redirect(url_for("chat"))
        else:
            # create a new user instance in the database, since user does not exist
            newUser = User(name)
            db.session.add(newUser)
            db.session.commit()

            # set the user's name in session
            session["name"] = name
            print("new user!")
            return redirect(url_for("chat"))
    return render_template("login.html")


"""
Gets the session username to make sure user is logged in.
 If so, render all esisting messages from database and the chat page.
"""


@app.route("/chat")
def chat():
    sessionName = session.get("name")
    # redriect user to login if they are not signed in.
    if sessionName is None:
        return redirect(url_for("login"))

    # return render_template with the messages from DB
    # allMessages becomes an array with tuples (name, {messagecontents})
    allMessages = db.session.query(Message, User.name).join(User).all()

    return render_template("chat.html", allMessages=allMessages)


"""
Get the user messages only. (from database)
then render a page with only user messages
"""


@app.route("/history")
def history():
    sessionName = session.get("name")

    # redriect user to login if they are not signed in.
    if sessionName is None:
        return redirect(url_for("login"))

    # get all user messages and pass it to render template
    allMessages = db.session.query(Message, User.name).join(User).all()
    filteredMessages = [(message, user_name) for message,
                        user_name in allMessages if user_name == sessionName]

    return render_template("history.html", allUserMessages=filteredMessages)


"""
Removes the sesssion user and redirects user to login page.

"""


@app.route("/logout")
def logout():
    sessionName = session.get("name")
    session["name"] = None

    return redirect(url_for("login"))

# SOCKETIO EVENTS ------------------------------------------------------------


"""
    Joins a room if a session user exists.
"""


@socketio.on("connect")
def socketConnect():
    sessionName = session.get("name")

    # make sure sessionname actually exists
    if not sessionName or sessionName is None:
        return

    # join the room
    join_room(ROOM_CODE)


"""
    leaves the session room. logs to console.
"""


@socketio.on("disconnect")
def socketDisconnect():
    sessionName = session.get("name")
    leave_room(ROOM_CODE)

    # send message to room. forces message event
    print(f"{sessionName} has left the room ")


"""
    Get the session name to make sure an actual user is sending a message.
    Then a content dictionary with the message content is created.
    The message is then added to the messages table in postgres.
    After, send the nessage to the room, prompting the client-side code to add the message to the page.
"""


@socketio.on("message")
def handleUserSendMessage(formData):
    sessionName = session.get("name")
    # make sure sessionname exists
    if sessionName is None or not sessionName:
        return

    content = {
        "name": sessionName,
        "message": formData["content"],
        "dateSent": formData["dateSent"]
    }

    # get userid
    user = User.query.filter_by(name=sessionName).first()
    userid = user.id

    # save message to db
    newMessage = Message(content["message"], content["dateSent"], userid)
    db.session.add(newMessage)
    db.session.commit()

    # send message to room. forces message event
    send(content, to=ROOM_CODE)

    print("sent message!")
if __name__ == "__main__":
    socketio.run(app, debug=True)
