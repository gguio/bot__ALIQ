from util import Missing, SQLite
from util import *  # noqa: F403
import telebot
from telebot import types
from threading import Timer


bot = telebot.TeleBot("6134750445:AAHbSBWhjlP1neBQSkm99fpGOf0hJAArOso")
m: dict[str, Missing] = {}
requestsListener: dict[str, Timer] = {}


def cleaning(bot, message):
    global m
    global requestsListener
    try:
        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.send_message(
            message.chat.id, "Запрос отменен из-за слишком долгого ожидания"
        )
        del m[message.chat.id]
        del requestsListener[message.chat.id]
    except Exception as e:
        print("Cleaning error : ", type(e))


def setTimer(bot: telebot, message: types.Message):
    global requestsListener

    time = 300

    if message.chat.id not in requestsListener.keys():
        requestsListener[message.chat.id] = Timer(time, cleaning, args=(bot, message))
        requestsListener[message.chat.id].start()
        return 0

    requestsListener[message.chat.id].cancel()
    del requestsListener[message.chat.id]
    requestsListener[message.chat.id] = Timer(time, cleaning, args=(bot, message))
    requestsListener[message.chat.id].start()


@bot.message_handler(content_types=["text"])
def start(message):
    global m
    if message.text == "/start":
        bot.send_message(
            message.chat.id,
            "/find - отправить запрос на поиск человека\n/get - история запросов",
        )
    elif message.text == "/get":
        s = SQLite()
        requests = s.get_requests(message.from_user.username)
        answer = ""
        if requests:
            for req in requests:
                missing = Missing(
                    userName=req[0],
                    chatID=req[1],
                    ruFIO=req[2],
                    amFIO=req[3],
                    photo=req[4],
                    lastContactDate=req[5],
                    livingPlace=req[6],
                    comment=req[7],
                    contactInfo=req[8],
                )
                answer += str(missing) + "\n\n"
        else:
            answer = "У Вас еще нет запросов"
        bot.send_message(message.chat.id, answer)
    elif message.text == "/find":
        mes = bot.send_message(
            message.chat.id,
            "Мы запишем информацию о человеке. Постарайтесь ответить на как можно большее количество вопросов",  # noqa: E501
        )
        m[message.chat.id] = Missing(message.chat.id, message.from_user.username)
        m[message.chat.id].messagesStack.append(mes)
        createKeyboard(message.chat.id, bot=bot)  # noqa: F405
        setTimer(bot=bot, message=message)
    else:
        bot.send_message(
            message.chat.id,
            "/find - отправить запрос на поиск человека\n/get - история запросов",
        )


@bot.callback_query_handler(lambda call: True)
def callback_worker(call):
    global m
    try:
        m[call.message.chat.id].messagesStack.append(call.message)
        m[call.message.chat.id].clearMessages(bot=bot)

        setTimer(bot=bot, message=call.message)

        match call.data:
            case "ruFIO":
                mes = bot.send_message(
                    call.message.chat.id, "Напишите ФИО на русском языке"
                )
                bot.register_next_step_handler(
                    call.message, m[call.message.chat.id].setRuFIO, bot=bot
                )
                m[call.message.chat.id].messagesStack.append(mes)
            case "amFIO":
                mes = bot.send_message(
                    call.message.chat.id, "Напишите ФИО на армянском языке"
                )
                bot.register_next_step_handler(
                    call.message, m[call.message.chat.id].setAmFIO, bot=bot
                )
                m[call.message.chat.id].messagesStack.append(mes)
            case "lastContactDate":
                mes = bot.send_message(
                    call.message.chat.id, "Напишите дату последнего выхода на связь"
                )
                bot.register_next_step_handler(
                    call.message, m[call.message.chat.id].setLastContactDate, bot=bot
                )
                m[call.message.chat.id].messagesStack.append(mes)
            case "livingPlace":
                mes = bot.send_message(
                    call.message.chat.id, "Напишите место постоянного проживания"
                )
                bot.register_next_step_handler(
                    call.message, m[call.message.chat.id].setLivingPlace, bot=bot
                )
                m[call.message.chat.id].messagesStack.append(mes)
            case "photo":
                mes = bot.send_message(call.message.chat.id, "Отправьте фото человека")
                bot.register_next_step_handler(
                    call.message, m[call.message.chat.id].setPhoto, bot=bot
                )
                m[call.message.chat.id].messagesStack.append(mes)
            case "comment":
                mes = bot.send_message(
                    call.message.chat.id,
                    "Напишите одним сообщением любую информацию, которая может помочь найти человека",  # noqa: E501
                )
                bot.register_next_step_handler(
                    call.message, m[call.message.chat.id].setComment, bot=bot
                )
                m[call.message.chat.id].messagesStack.append(mes)
            case "contactInfo":
                mes = bot.send_message(
                    call.message.chat.id,
                    "Напишите свой телефон или email, чтобы мы могли с Вами связаться",  # noqa: E501
                )
                bot.register_next_step_handler(
                    call.message, m[call.message.chat.id].setContactInfo, bot=bot
                )
                m[call.message.chat.id].messagesStack.append(mes)

            case "cancel":
                bot.send_message(call.message.chat.id, "Запрос отменен")
                del m[call.message.chat.id]
                requestsListener[call.message.chat.id].cancel()
                del requestsListener[call.message.chat.id]
            case "submit":
                bot.send_message(call.message.chat.id, "Информация записана")

                sqlite_util = SQLite()
                sqlite_util.add_data_to_table(m[call.message.chat.id])
                sqlite_util.add_data_to_GS(m[call.message.chat.id])

                del m[call.message.chat.id]
                requestsListener[call.message.chat.id].cancel()
                del requestsListener[call.message.chat.id]

            case _:
                pass

    except KeyError:
        print("Warning : trying to access undefined request")
        print("Error occured in chat " + str(call.message.chat.id))

    except Exception as e:
        print("Warning : while handeling request an error occured")
        print("Error occured in chat " + str(call.message.chat.id))
        print("Error type : ", type(e))


bot.polling(non_stop=True, interval=0)
