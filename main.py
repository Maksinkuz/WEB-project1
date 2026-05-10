from flask import Flask, render_template, redirect, url_for, session, request
import random
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from data import db_session
from data.all_models import User, Location
from forms.user import RegisterForm, LoginForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tula_quiz_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)


@app.route("/") # / - путь к странице (например: https://наш_сервер/)
def index():
    db_sess = db_session.create_session()
    leaders = db_sess.query(User).order_by(User.score.desc()).limit(10).all() # выбираем 10 лучших из БД
    return render_template("index.html", leaders=leaders) # отображаем страницу


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/login', methods=['GET', 'POST'])
# /login - путь к странице (например: https://наш_сервер/register)
# methods=['GET', 'POST'] - может ПОЛУЧАТЬ и ОТПРАВЛЯТЬ данные со страницы
def login():
    form = LoginForm()  # используем созданную нами заранее форму
    if form.validate_on_submit(): # если ввели данные верно
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first() # выбираем пользователя с такими е данными
        if user and user.check_password(form.password.data): # проверяем пароль
            login_user(user, remember=form.remember_me.data) # логинимся
            return redirect("/") # на начальную страницу
        db_sess.close()
        return render_template('login.html', message="Неправильный логин или пароль", form=form)
    return render_template('login.html', title='Авторизация', form=form) # ввели данные неправильно - остаемся там же


@app.route('/logout')
@login_required # если уже зареганы
def logout(): # разлогинится
    logout_user()
    return redirect("/") # на начальную


@app.route('/register', methods=['GET', 'POST'])
# /register - путь к странице (например: https://наш_сервер/register)
# methods=['GET', 'POST'] - может ПОЛУЧАТЬ и ОТПРАВЛЯТЬ данные со страницы
def reqister():
    form = RegisterForm() # заранее созданная формочка
    if form.validate_on_submit(): # ввели верно
        if form.password.data != form.password_again.data: # проверили пароль
            return render_template('register.html', title='Регистрация', form=form, message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Такой пользователь уже есть")
        user = User( # создаем пользователя
            username=form.username.data,
            email=form.email.data,
        )

        user.set_password(form.password.data) # шифруем пароль
        db_sess.add(user) # добавили в БД
        db_sess.commit()
        db_sess.close()
        login_user(user, remember=form.remember_me.data)  # логинимся
        return redirect("/")  # на начальную страницу
    return render_template('register.html', title='Регистрация', form=form) # ввели не то


@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    db_sess = db_session.create_session()
    if 'quiz_locations' not in session:
        all_locs = db_sess.query(Location).all()
        # Если в базе меньше 10 вопросов, то берем все что есть
        sample_size = min(len(all_locs), 10)
        if sample_size == 0:
            db_sess.close()
            return redirect(url_for('index'))
        selected = random.sample(all_locs, sample_size)
        session['quiz_locations'] = [loc.id for loc in selected]
        session['quiz_score'] = 0
        session['quiz_index'] = 0
        session['total_questions'] = sample_size

    if session['quiz_index'] >= session['total_questions']:
        return redirect(url_for('quiz_result'))

    current_loc_id = session['quiz_locations'][session['quiz_index']]
    current_loc = db_sess.query(Location).get(current_loc_id)
    if request.method == 'POST':
        selected_answer = request.form.get('answer')
        if selected_answer == current_loc.answer:
            session['quiz_score'] += 10
        session['quiz_index'] += 1
        # Если это был последний вопрос
        if session['quiz_index'] >= session['total_questions']:
            if current_user.is_authenticated:
                user = db_sess.query(User).get(current_user.id)
                user.score = max(user.score, session['quiz_score'])
                db_sess.commit()
            db_sess.close()
            return redirect(url_for('quiz_result'))

        db_sess.close()
        return redirect(url_for('quiz'))
    choices = [c.strip() for c in current_loc.fake_answers.split('|') if c.strip()]
    choices.append(current_loc.answer)
    random.shuffle(choices)

    db_sess.close()
    return render_template('quiz.html',
                           location=current_loc,
                           choices=choices,
                           q_num=session['quiz_index'] + 1,
                           total=session['total_questions'],
                           score=session['quiz_score'])


@app.route('/quiz_result')
def quiz_result():
    if 'quiz_score' not in session: # играли ли мы в викторину? если нет, то и очков нет - на главную
        return redirect(url_for('index'))
    score = session['quiz_score'] # получаем набранное нами количество очков

    # Очищаем данные
    session.pop('quiz_locations', None)
    session.pop('quiz_score', None)
    session.pop('quiz_index', None)
    session.pop('total_questions', None)

    return render_template('quiz_result.html', score=score) # выводим результат


def main():
    db_session.global_init("db/tula_quiz.sqlite")
    app.run(port=8080, host='127.0.0.1', debug=True)


if __name__ == '__main__':
    main()