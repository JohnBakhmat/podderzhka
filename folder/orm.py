from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from settings import db_settings
from database.models import Base, User, BlockedUser, Problem, Otziv
from datetime import datetime
from openpyxl import Workbook

engine = create_engine(db_settings.URL, echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def add_user(tg_id, username):
    session = Session()
    user = session.query(User).filter(User.tg_id == str(tg_id)).first()
    if user is None:
        new_user = User(tg_id=tg_id, username=username)
        session.add(new_user)
        session.commit()
        return 1
    else:
        return -1

def add_problem(tg_id, username, text, mess_id):
    session = Session()
    new_problem = Problem(tg_id=tg_id, username=username, problem_text=text, message_id=mess_id)
    session.add(new_problem)
    session.commit()

def add_otziv(tg_id, username, text, mess_id):
    session = Session()
    new_otziv = Otziv(tg_id=tg_id, username=username, otziv_text=text, message_id=mess_id)
    session.add(new_otziv)
    session.commit()

#def add_problem(tg_id, text):
#    session = Session()
#    user = session.query(User).filter(User.tg_id == str(tg_id)).first()
#    if user:
#        user.problem_text = text
#        session.commit()
#       return 1
#    else:
#       return -1
def delete_problem(mess_id):
    session = Session()
    complete = session.query(Problem).filter_by(message_id=mess_id).first()
    if complete:
        complete.complete_date = datetime.now()
        complete.complete = True
        session.commit()

def delete_otziv(mess_id):
    session = Session()
    complete = session.query(Otziv).filter_by(message_id=mess_id).first()
    if complete:
        complete.complete_date = datetime.now()
        complete.complete = True
        session.commit()


def add_typing(us_id):
    session = Session()
    complete = session.query(User).filter_by(tg_id=str(us_id)).first()
    if complete:
        complete.typing = True
        session.commit()


def check_typing(tg_id):
    session = Session()
    user = session.query(User).filter(User.tg_id == str(tg_id)).first()
    if user.typing == True:
        return 1
    else:
        return -1

def remove_typing(us_id):
    session = Session()
    complete = session.query(User).filter_by(tg_id=str(us_id)).first()
    if complete:
        complete.typing = False
        session.commit()

def get_problem(mess_id):
    session = Session()
    complete = session.query(Problem).filter_by(message_id=mess_id).first()
    if complete:
        text = complete.problem_text
        user_id = complete.tg_id
        username = complete.username
        id = complete.id
        date = complete.date.strftime("%Y-%m-%d %H:%M")
        return text, user_id, username, id, date

def get_mess_id(text):
    session = Session()
    complete = session.query(Problem).filter_by(problem_text=text).first()
    if complete:
        mess_id = complete.message_id
        return mess_id
def get_otziv(mess_id):
    session = Session()
    complete = session.query(Otziv).filter_by(message_id=mess_id).first()
    if complete:
        text = complete.otziv_text
        user_id = complete.tg_id
        username = complete.username
        id = complete.id
        date = complete.date.strftime("%Y-%m-%d %H:%M")
        return text, user_id, username, id, date
def add_reshenie(mess_id, text):
    session = Session()
    try:
        # Ищем запись с указанным message_id
        otziv = session.query(Otziv).filter_by(message_id=mess_id).first()
        if otziv:
            # Обновляем текст решения
            otziv.complete_text = text
            session.commit()
            return True
        else:
            print(f"Задача с 11111111111message_id {mess_id} не найдена.")
            return False
    except Exception as e:
        print(f"Ошибка при обновлении complete_text: {e}")
        session.rollback()  # Откат транзакции при ошибке
        return False
    finally:
        session.commit()

def add_otvet(mess_id, text):
    session = Session()
    try:
        # Ищем запись с указанным message_id
        problem = session.query(Problem).filter_by(message_id=mess_id).first()
        if problem:
            # Обновляем текст решения
            problem.complete_text = text
            session.commit()
            return True
        else:
            print(f"Задача с2222222222222222 message_id {mess_id} не найдена.")
            return False
    except Exception as e:
        print(f"Ошибка при обновлении complete_text: {e}")
        session.rollback()  # Откат транзакции при ошибке
        return False
    finally:
        session.commit()
def spisok_problem():
    session = Session()
    problems = session.query(Problem).filter_by(complete=False).all()
    return problems

def spisok_otziv():
    session = Session()
    otzivs = session.query(Otziv).filter_by(complete=False).all()
    return otzivs

def vse_problems():
    session = Session()
    # Сортируем проблемы по id
    problems = session.query(Problem).order_by(Problem.id.asc()).all()

    # Запись в текстовый файл
    txt_file_path = "problems.txt"
    with open(txt_file_path, "w", encoding="utf-8") as txt_file:
        for problem in problems:
            txt_file.write(f"ID: {problem.id}\n")
            txt_file.write(f"Username: {problem.username or 'Без username'}\n")
            txt_file.write(f"Дата: {problem.date.strftime('%Y-%m-%d %H:%M:%S')}\n")
            txt_file.write(f"TG ID: {problem.tg_id}\n")
            txt_file.write(f"ID сообщения: {problem.message_id}\n")
            txt_file.write(f"Текст проблемы: {problem.problem_text or 'Нет текста'}\n")
            txt_file.write(f"Завершено: {'Да' if problem.complete else 'Нет'}\n")
            txt_file.write(f"Дата завершения: {problem.complete_date.strftime('%Y-%m-%d %H:%M:%S') if problem.complete_date else '-'}\n")
            txt_file.write(f"Ответ поддержки: {problem.complete_text or 'Нет текста'}\n")
            txt_file.write("-" * 50 + "\n")

    # Запись в Excel файл
    excel_file_path = "problems.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Проблемы"

    # Добавляем заголовки
    ws.append(
        ["ID", "Username", "Date", "TG ID", "ID сообщения", "Текст проблемы", "Завершено", "Дата завершения", "Ответ поддержки"])

    # Записываем данные
    for problem in problems:
        ws.append([
            problem.id,
            problem.username or "",
            problem.date.strftime("%Y-%m-%d %H:%M:%S"),
            problem.tg_id,
            problem.message_id,
            problem.problem_text or "Нет текста",
            "Да" if problem.complete else "Нет",
            problem.complete_date.strftime("%Y-%m-%d %H:%M:%S") if problem.complete_date else "-",
            problem.complete_text or "Нет текста"
        ])

    wb.save(excel_file_path)
    return txt_file_path, excel_file_path


def vse_otziv():
    session = Session()
    # Сортируем отзывы по id
    problems = session.query(Otziv).order_by(Otziv.id.asc()).all()

    # Запись в текстовый файл
    txt_file_path = "otziv.txt"
    with open(txt_file_path, "w", encoding="utf-8") as txt_file:
        for problem in problems:
            txt_file.write(f"ID: {problem.id}\n")
            txt_file.write(f"Username: {problem.username or 'Без username'}\n")
            txt_file.write(f"Дата: {problem.date.strftime('%Y-%m-%d %H:%M:%S')}\n")
            txt_file.write(f"TG ID: {problem.tg_id}\n")
            txt_file.write(f"ID сообщения: {problem.message_id}\n")
            txt_file.write(f"Текст отзыва: {problem.otziv_text or 'Нет текста'}\n")
            txt_file.write(f"Завершено: {'Да' if problem.complete else 'Нет'}\n")
            txt_file.write(f"Дата завершения: {problem.complete_date.strftime('%Y-%m-%d %H:%M:%S') if problem.complete_date else '-'}\n")
            txt_file.write(f"Ответ поддержки: {problem.complete_text or 'Нет текста'}\n")
            txt_file.write("-" * 50 + "\n")

    # Запись в Excel файл
    excel_file_path = "otziv.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Отзывы"

    # Добавляем заголовки
    ws.append(
        ["ID", "Username", "Дата", "TG ID", "ID сообщения", "Текст отзыва", "Завершено", "Дата завершения", "Ответ поддержки"])

    # Записываем данные
    for problem in problems:
        ws.append([
            problem.id,
            problem.username or "",
            problem.date.strftime("%Y-%m-%d %H:%M:%S"),
            problem.tg_id,
            problem.message_id,
            problem.otziv_text or "Нет текста",
            "Да" if problem.complete else "Нет",
            problem.complete_date.strftime("%Y-%m-%d %H:%M:%S") if problem.complete_date else "-",
            problem.complete_text or "Нет текста"
        ])

    wb.save(excel_file_path)
    return txt_file_path, excel_file_path


def get_admins():
    session = Session()
    users = session.query(User).filter_by(admin=True).all()
    return users

def check_admin(tg_id):
    session = Session()
    user = session.query(User).filter(User.tg_id == str(tg_id)).first()
    if user.admin == True:
        return 1
    else:
        return -1

def add_blocked(count):
    session = Session()
    number = session.query(BlockedUser).first()
    number.block_count = count
    session.commit()

def get_all_users():
    session = Session()
    users = session.query(User).all()
    return users

def stat():
    session = Session()
    users = session.query(User).count()
    blocked = session.query(BlockedUser).count()
    return [users, blocked]


def get_problem_order_number(mess_id):
    """
    Получает порядковый номер записи в таблице 'problems' для заданного message_id.
    """
    session = Session()
    try:
        # Преобразуем mess_id в строку
        mess_id = str(mess_id)

        # Получаем все ID в отсортированном порядке
        problems = session.query(Problem.id).order_by(Problem.id).all()

        # Находим индекс записи с заданным message_id
        target_id = session.query(Problem.id).filter_by(message_id=mess_id).scalar()
        if target_id:
            order_number = [row.id for row in problems].index(target_id) + 1  # Порядковый номер (начиная с 1)
            return order_number
    finally:
        session.close()
    return None


def get_otziv_order_number(mess_id):
    """
    Получает порядковый номер записи в таблице 'otzivi' для заданного message_id.
    """
    session = Session()
    try:
        # Преобразуем mess_id в строку
        mess_id = str(mess_id)

        # Получаем все ID в отсортированном порядке
        otzivi = session.query(Otziv.id).order_by(Otziv.id).all()

        # Находим индекс записи с заданным message_id
        target_id = session.query(Otziv.id).filter_by(message_id=mess_id).scalar()
        if target_id:
            order_number = [row.id for row in otzivi].index(target_id) + 1  # Порядковый номер (начиная с 1)
            return order_number
    finally:
        session.close()
    return None


