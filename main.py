from flask import Flask, render_template
from data import db_session
from data.all_models import User, Location

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tula_quiz_secret_key'


@app.route("/")
def index():
    db_sess = db_session.create_session()
    leaders = db_sess.query(User).order_by(User.score.desc()).limit(10).all()
    return render_template("index.html", leaders=leaders)


def main():
    db_session.global_init("db/tula_quiz.sqlite")
    app.run(port=8080, host='127.0.0.1', debug=True)


if __name__ == '__main__':
    main()