import datetime
import strings

from calendartelegram import telegramcalendar

from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply

from utils import calls, BotRequest, RequestQueue
from database import Database
from operatedatabase import DATABASE_OPERATIONS

TOKEN = open('TOKEN').read().strip()
ADMIN = open('ADMIN').read().strip()
DESC = open('HELP.md').read()
DATABASE = open('DATABASE').read().strip()

db = Database()

NAMING, DESCRIPTION, DATE, CANCEL, SELECT, CLOSE = range(6)

def start(update, context):
    chat_id = update.message.chat.id

    context.bot.sendMessage(chat_id = chat_id, text = DESC, parse_mode = 'MarkdownV2')

@calls
def cancel(update, context):

    chat_id = update.message.chat.id

    context.bot.sendMessage(chat_id = chat_id, text = "Annullo l'operazione.")

    return ConversationHandler.END

@calls
def newbot(update, context):

    chat_id = update.message.chat.id
    text = "Benvenuto nello strumento di creazione di un nuovo bot. Innanzitutto che nome vuoi dargli?"

    context.bot.sendMessage(chat_id = chat_id, text = text)

    return NAMING

@calls
def name(update, context):

    bot_name = update.message.text
    chat_id = update.message.chat.id

    text = 'Bene. Creerò un bot di nome {}. Che cosa vuoi che faccia? Cerca di descrivere in poche parole precise.'.format(bot_name)

    context.bot.sendMessage(chat_id = chat_id, text = text)

    req = BotRequest(bot_name)

    context.user_data['last_req'] = req

    return DESCRIPTION

@calls
def description(update, context):

    desc_text = update.message.text
    chat_id = update.message.chat.id

    req = context.user_data['last_req']

    req.desc = desc_text

    context.user_data['last_req'] = req

    context.bot.sendMessage(chat_id = chat_id, text = 'Ok. Hai una scadenza per la realizzazione del bot? Invia "Si" se così fosse, altrimenti invia /skip')

    return DATE

@calls
def select(update, context):

    chat_id = update.message.chat.id

    context.bot.sendMessage(chat_id = chat_id, text = 'Calendario', reply_markup=telegramcalendar.create_calendar())

    return SELECT

@calls
def date_selection(update, context):

    selected, _date = telegramcalendar.process_calendar_selection(update, context)

    if selected:

        req = context.user_data['last_req']

        req.date = _date.date()

        context.user_data['last_req'] = req

        context.bot.sendMessage(chat_id = update.callback_query.message.chat.id, text = 'Hai selezionato {}.\nInvia Ok per confermare.'.format(_date))

        return CLOSE

@calls
def close(update, context):

    global db

    req = context.user_data['last_req']

    if req is None:
        print('[close] req is None, exiting')
        context.bot.sendMessage(chat_id = update.message.chat_id, text = 'Si è verificato un errore nella tua richiesta, riprova.')
        return ConversationHandler.END

    req.create()

    print('[close] created bot with username: {}'.format(req.username))

    if not db.connect(DATABASE):
        print('[database] could not connect to database')

    if not db.insert(req):
        print('[database] error executing insert query')

    if not db.disconnect():
        print('[database] there are uncommitted changes')

    context.bot.sendMessage(chat_id = update.message.chat.id, text = strings.RIEPILOGO_UTENTE + '\n\n' + str(req) + strings.RIEPILOGO_RINGRAZIAMENTO, reply_markup = ReplyKeyboardRemove())
    context.bot.sendMessage(chat_id = ADMIN, text = strings.RIEPILOGO_ADMIN + '\n\n' + str(req))

    return ConversationHandler.END

def main():
    updater = Updater(TOKEN, use_context=True)

    newbot_handler = ConversationHandler(
        entry_points = [CommandHandler('newbot', newbot)],
        states = {
            NAMING : [MessageHandler(Filters.text & ~Filters.command, name)],
            DESCRIPTION : [MessageHandler(Filters.text & ~Filters.command, description)],
            DATE : [MessageHandler(Filters.regex('^(Si)$'), select), CommandHandler('skip', close)],
            SELECT : [CallbackQueryHandler(date_selection)],
            CLOSE : [MessageHandler(Filters.text & ~Filters.command, close)]
        },
        fallbacks = [CommandHandler('cancel', cancel)]
    )

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('help', start))
    updater.dispatcher.add_handler(newbot_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()