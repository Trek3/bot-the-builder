import datetime
import strings

from calendartelegram import telegramcalendar

from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply

from utils import calls, BotRequest, RequestQueue

TOKEN = open('TOKEN').read().strip()
ADMIN = open('ADMIN').read().strip()
DESC = open('HELP.md').read()

NAMING, DESCRIPTION, DATE, CANCEL, SELECT, CLOSE = range(6)

def start(update, context):
    chat_id = update.message.chat.id

    if 'queue' not in context.bot_data:
        context.bot_data['queue'] = RequestQueue()

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

        req.date = _date

        context.user_data['last_req'] = req

        context.bot.sendMessage(chat_id = update.callback_query.message.chat.id, text = 'Hai selezionato {}.\nInvia Ok per confermare.'.format(_date.date()))

        return CLOSE

@calls
def close(update, context):

    req = context.user_data['last_req']

    if req is None:
        print('[close] req is None, exiting')
        return ConversationHandler.END
        
    print('[close] pushed request on queue')

    if req.date is None:
        text = '\n\nNome: {}\nDescrizione: {}\n\nGrazie per aver utilizzato Bot the Builder!'.format(req.name, req.desc)
        req.date = datetime.datetime(2099, 12, 31)
    else:
        text = '\n\nNome: {}\nDescrizione: {}\nLa deadline per la consegna è per il {}.\n\nGrazie per aver utilizzato Bot the Builder!'.format(req.name, req.desc, str(req.date.date()))   

    context.bot_data['queue'].push(req)

    context.bot.sendMessage(chat_id = update.message.chat.id, text = strings.RIEPILOGO_UTENTE + text, reply_markup = ReplyKeyboardRemove())
    context.bot.sendMessage(chat_id = ADMIN, text = strings.RIEPILOGO_ADMIN + text)

    return ConversationHandler.END

def main():
    updater = Updater(TOKEN, use_context=True)

    newbot_handler = ConversationHandler(
        entry_points = [CommandHandler('newbot', newbot)],
        states = {
            NAMING : [MessageHandler(Filters.text, name)],
            DESCRIPTION : [MessageHandler(Filters.text, description)],
            DATE : [MessageHandler(Filters.regex('^(Si)$'), select), CommandHandler('skip', close)],
            SELECT : [CallbackQueryHandler(date_selection)],
            CLOSE : [MessageHandler(Filters.all, close)]
        },
        fallbacks = [MessageHandler(Filters.all, cancel)]
    )

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(newbot_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()