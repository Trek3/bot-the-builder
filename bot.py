import datetime
import strings

from calendartelegram import telegramcalendar

from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply

from utils import calls, BotRequest
from database import Database
from operatedatabase import DATABASE_OPERATIONS

TOKEN = open('TOKEN').read().strip()
ADMIN = open('ADMIN').read().strip()
DESC = open('HELP.md').read()
DATABASE = open('DATABASE').read().strip()

db = Database()

NAMING, DESCRIPTION, DATE, CANCEL, SELECT, CLOSE = range(6)

REPORT_SELECTION, REPORT_DESCRIPTION = range(2)

def start(update, context):
    chat_id = update.message.chat.id

    context.bot.sendMessage(chat_id = chat_id, text = DESC, parse_mode = 'MarkdownV2')

@calls
def cancel(update, context):

    chat_id = update.message.chat.id

    context.bot.sendMessage(chat_id = chat_id, text = "Annullo l'operazione.")

    return ConversationHandler.END

#------------------------------------------- NEWBOT --------------------------------------------#

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

    req = BotRequest(name = bot_name, chat_id = chat_id)

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

    if not db.connect(DATABASE):
        print('[database] could not connect to database')

    ret, bot_id = db.insert(req)
    if not ret:
        print('[database] error executing insert query')

    if not db.disconnect():
        print('[database] there are uncommitted changes')

    context.bot.sendMessage(chat_id = update.message.chat.id, text = strings.RIEPILOGO_UTENTE + '\n\n' + str(req) + strings.RIEPILOGO_RINGRAZIAMENTO, reply_markup = ReplyKeyboardRemove())
    context.bot.sendMessage(chat_id = ADMIN, text = strings.RIEPILOGO_ADMIN + '\n\n' + str(req) + '\n\nREQUEST ID: ' + str(bot_id))

    return ConversationHandler.END

#------------------------------------------- REPORT --------------------------------------------#

def prepare_markup(ls):

    ls = list(sum(ls, ()))

    n = len(ls)
    k = 4

    return ReplyKeyboardMarkup([ls[i * (n // k) + min(i, n % k):(i+1) * (n // k) + min(i+1, n % k)] for i in range(k)])

@calls
def report(update, context):

    global db

    chat_id = update.message.chat.id

    if not db.connect(DATABASE):
        print('[report] error connnecting to the database')
        return ConversationHandler.END

    ret, entries = db.select(query = DATABASE_OPERATIONS['report'], params = (chat_id,))

    if not db.disconnect():
        print('[report] error disconnecting')

    if not ret:
        context.bot.sendMessage(chat_id = chat_id, text = 'Sembra che tu non abbia creato ancora bot. Puoi utilizzare /newbot per crearne uno.')
        ConversationHandler.END

    markup = prepare_markup(entries)
    
    context.bot.sendMessage(chat_id = chat_id, text = 'Hai riscontrato un problema o vuoi cambiare qualcosa. Seleziona il bot di cui vuoi fare la segnalazione.', reply_markup = markup)

    return REPORT_SELECTION

@calls
def report_selection(update, context):

    chat_id = update.message.chat.id
    msg = update.message.text

    context.user_data['bot_name'] = msg

    context.bot.sendMessage(chat_id = chat_id, text = 'Vuoi riportare qualcosa per {}. Scrivi la tua segnalazione.'.format(msg), reply_markup = ReplyKeyboardRemove())

    return REPORT_DESCRIPTION

@calls
def report_description(update, context):

    chat_id = update.message.chat.id
    msg = update.message.text

    bot_name = context.user_data['bot_name']

    context.bot.sendMessage(chat_id = chat_id, text = 'Grazie per la segnalazione, spero di poterti aiutare al più presto.')
    context.bot.sendMessage(chat_id = ADMIN, text = 'Hai ricevuto la seguente segnalazione per {}:\n\n{}'.format(bot_name, msg))

    return ConversationHandler.END

#------------------------------------------- DELIVER -------------------------------------------#

@calls
def deliver(update, context):

    bot_id, bot_username = update.message.text.split()[1:]

    if not db.connect(DATABASE):
        print('[deliver] error connecting database')

    params = (bot_username, bot_id, )

    ret = db.deliver(params)
    if not ret:
        print('[deliver] error inserting in database')

    ret, entries = db.select(query = DATABASE_OPERATIONS['deliver'], params = (bot_id,))
    if not ret:
        print('[deliver] error executing on database')

    if not db.disconnect():
        print('[deliver] error disconnecting database')

    if len(entries) != 1:
        print('[deliver] multiple bots with same id in database')

    bot_name, bot_username, chat_id = entries[0]

    context.bot.sendMessage(chat_id = chat_id, text = 'Il tuo {} è completo! Puoi iniziare a usarlo scrivendo a {}.\n\nSpero ti piaccia e ricorda, se hai problemi, puoi segnalarli inviando il comando /report.\n\nGrazie per aver usato Bot the Builder.'.format(bot_name, bot_username))

#-------------------------------------------- MAIN ---------------------------------------------#

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

    report_handler = ConversationHandler(
        entry_points = [CommandHandler('report', report)],
        states = {
            REPORT_SELECTION : [MessageHandler(Filters.text & ~Filters.command, report_selection)],
            REPORT_DESCRIPTION : [MessageHandler(Filters.text & ~Filters.command, report_description)]
        },
        fallbacks = [CommandHandler('cancel', cancel)]

    )

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('help', start))
    updater.dispatcher.add_handler(newbot_handler)
    updater.dispatcher.add_handler(report_handler)
    updater.dispatcher.add_handler(CommandHandler('deliver', deliver))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()