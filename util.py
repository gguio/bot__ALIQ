from dataclasses import dataclass, field
import sqlite3
from sqlite3 import Error
from telebot import types
from datetime import date
import os.path
import pygsheets


def createKeyboard(chat, bot):
    k = types.InlineKeyboardMarkup(row_width=1)
    ruFIO = types.InlineKeyboardButton(
        "Фамилия имя отчество на русском языке", callback_data="ruFIO"
    )
    amFIO = types.InlineKeyboardButton(
        "Фамилия имя отчество на армянском языке", callback_data="amFIO"
    )
    photo = types.InlineKeyboardButton("Фотография", callback_data="photo")
    lastContactDate = types.InlineKeyboardButton(
        "Дата последнего выхода на связь", callback_data="lastContactDate"
    )
    livingPlace = types.InlineKeyboardButton(
        "Место постоянного проживания", callback_data="livingPlace"
    )
    comment = types.InlineKeyboardButton(
        "Дополнительная информация", callback_data="comment"
    )
    contactInfo = types.InlineKeyboardButton(
        "Контактная информация", callback_data="contactInfo"
    )
    cancel = types.InlineKeyboardButton("Отмена", callback_data="cancel")
    submit = types.InlineKeyboardButton("Отправить", callback_data="submit")

    k.add(ruFIO, amFIO, photo, lastContactDate, livingPlace, comment, contactInfo)
    k.row(cancel, submit)
    bot.send_message(chat, "Выберите поле", reply_markup=k)


@dataclass
class Requester:
    chatID: int
    userName: str
    ruFIO: str = "-"
    amFIO: str = "-"
    photo: str = "-"
    livingPlace: str = "-"
    comment: str = "-"
    contactInfo: str = "-"
    messagesStack: list = field(default_factory=list)

    def __str__(self) -> str:
        return (
            "ФИО на русском :  "
            + self.ruFIO
            + "\nФИО на армянском :  "
            + self.amFIO
            + "\nФото :  "
            + self.photo
            + "\nМесто проживания :  "
            + self.livingPlace
        )

    def setRuFIO(self, message, bot):
        self.messagesStack.append(message)
        self.ruFIO = message.text
        mes = bot.send_message(message.chat.id, self)
        createKeyboard(message.chat.id, bot=bot)
        self.messagesStack.append(mes)

    def setAmFIO(self, message, bot):
        self.messagesStack.append(message)
        self.amFIO = message.text
        mes = bot.send_message(message.chat.id, self)
        createKeyboard(message.chat.id, bot=bot)
        self.messagesStack.append(mes)

    def setLivingPlace(self, message, bot):
        self.messagesStack.append(message)
        self.livingPlace = message.text
        mes = bot.send_message(message.chat.id, self)
        createKeyboard(message.chat.id, bot=bot)
        self.messagesStack.append(mes)

    def setComment(self, message, bot):
        self.messagesStack.append(message)
        self.comment = message.text
        mes = bot.send_message(message.chat.id, self)
        createKeyboard(message.chat.id, bot=bot)
        self.messagesStack.append(mes)

    def setPhoto(self, message, bot):
        self.messagesStack.append(message)
        if message.photo:
            self.photo = bot.get_file_url(message.photo[-1].file_id)
        elif message.document:
            self.photo = bot.get_file_url(message.document.file_id)
        mes = bot.send_message(message.chat.id, self)
        createKeyboard(message.chat.id, bot=bot)
        self.messagesStack.append(mes)

    def setContactInfo(self, message, bot):
        self.messagesStack.append(message)
        self.contactInfo = message.text
        mes = bot.send_message(message.chat.id, self)
        createKeyboard(message.chat.id, bot=bot)
        self.messagesStack.append(mes)

    def clearMessages(self, bot):
        for message in self.messagesStack:
            bot.delete_message(message.chat.id, message.id)
        self.messagesStack = []


@dataclass
class Missing(Requester):
    lastContactDate: str = "-"

    def __str__(self) -> str:
        return (
            super().__str__()
            + "\nДата последнего выхода на связь :  "
            + self.lastContactDate
            + "\nДополнительная информация :  "
            + self.comment
            + "\nКонтактная информация :  "
            + self.contactInfo
        )

    def setLastContactDate(self, message, bot):
        self.messagesStack.append(message)
        self.lastContactDate = message.text
        mes = bot.send_message(message.chat.id, self)
        createKeyboard(message.chat.id, bot=bot)
        self.messagesStack.append(mes)


class SQLite:
    DB_NAME = "db.sqlite"

    def __init__(self):
        self.conn = self.create_connection()
        self._get_or_create_table()

    def create_connection(self):
        """
        create a database connection to the SQLite database specified by db_name
        :return: Connection object or None
        """
        conn = None
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(BASE_DIR, self.DB_NAME)
        try:
            # connects or creates a sqlite3 file
            conn = sqlite3.connect(db_path)
            return conn
        except Error as e:
            print(e)

        # returns the connection object
        return conn

    def _get_or_create_table(self):
        """Creates the table if it does not exists"""

        # sql query to create a details table
        create_table_sql = """CREATE TABLE IF NOT EXISTS missings (
            userName text NOT NULL,
            chatID integer NOT NULL,
            ruFIO text,
            amFIO text,
            photo text,
            lastContactDate text,
            livingPlace text,
            comment text,
            contactInfo text
        )"""
        try:
            # initializing the query cursor
            c = self.conn.cursor()

            # executes the create table query
            c.execute(create_table_sql)
        except Error as e:
            # prints the exception if any errors
            # occurs during runtime
            print(e)

    def get_requests(self, username):
        data = {"username": username}

        try:
            c = self.conn.cursor()

            c.execute("SELECT * FROM missings WHERE userName = :username", data)

            answer = c.fetchall()
        except Error as e:
            print(e)
            return "error"

        return answer

    def add_data_to_table(self, obj):
        """Inserts the data from sheets to the table"""

        # initializing sql cursor
        c = self.conn.cursor()

        # excluding the first row because it
        # contains the headers
        insert_table_sql = """INSERT OR IGNORE INTO missings (userName, chatID, ruFIO, amFIO, photo, lastContactDate, livingPlace, comment, contactInfo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"""  # noqa: E501

        # inserts the data into the table
        # NOTE: the data needs to be in the order
        # which the values are provided into the
        # sql statement
        row = (
            obj.userName,
            obj.chatID,
            obj.ruFIO,
            obj.amFIO,
            obj.photo,
            obj.lastContactDate,
            obj.livingPlace,
            obj.comment,
            obj.contactInfo,
        )
        c.execute(insert_table_sql, tuple(row))

        # committing all the changes to the database
        self.conn.commit()

        # closing the connection to the database
        c.close()

    def add_data_to_GS(self, obj):
        gc = pygsheets.authorize(service_file="secret.json")
        sh = gc.open_by_url(
            "https://docs.google.com/spreadsheets/d/17b6zModqTzpUZnHwMFON0f4xGwyJoFEBxASTGxOKhT4/edit?usp=sharing"
        )
        wk = sh[0]
        cols = wk.get_col(1)
        last = 0
        for i, val in enumerate(cols):
            if val == "":
                last = i
                break

        today = date.today()
        dt_string = today.strftime("%d.%m.%Y")

        wk.update_col(
            1,
            [
                [dt_string],
                [obj.userName],
                [obj.chatID],
                [obj.ruFIO],
                [obj.amFIO],
                [obj.photo],
                [obj.lastContactDate],
                [obj.livingPlace],
                [obj.comment],
                [obj.contactInfo],
            ],
            row_offset=last,
        )
