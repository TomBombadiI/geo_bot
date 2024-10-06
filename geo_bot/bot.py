import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from geopy.distance import geodesic

# Точка назначения (координаты загаданной точки)
TARGET_LOCATION = (51.850499, 107.574509)

# Переменные состояния
is_tracking = False  # Флаг, указывающий, что бот отслеживает геопозицию
tracking_task = None  # Хранит задачу трансляции координат

# Функция для расчета расстояния
def calculate_distance(user_location):
    return geodesic(user_location, TARGET_LOCATION).meters

# Команда старт: приветствие и клавиатура с кнопками
async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        ["начать", "стоп"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
    await update.message.reply_text("Привет! Управляйте ботом с помощью кнопок ниже.", reply_markup=reply_markup)

# Команда для начала работы бота
async def begin_tracking(update: Update, context: CallbackContext) -> None:
    global is_tracking, tracking_task
    if is_tracking:
        await update.message.reply_text("Отслеживание уже запущено.")
        return

    is_tracking = True
    await update.message.reply_text("Отслеживание началось! Отправьте трансляцию вашей геопозиции.")
    
    # Запускаем задачу отслеживания
    tracking_task = context.application.create_task(track_location(update, context))

# Команда для остановки работы бота
async def stop_tracking(update: Update, context: CallbackContext) -> None:
    global is_tracking, tracking_task
    if not is_tracking:
        await update.message.reply_text("Отслеживание не запущено.")
        return

    is_tracking = False
    if tracking_task:
        tracking_task.cancel()  # Останавливаем задачу отслеживания
    await update.message.reply_text("Отслеживание остановлено.")

# Отслеживание геопозиции каждые 10 секунд
async def track_location(update: Update, context: CallbackContext):
    while is_tracking:
        if 'last_location' in context.user_data:
            user_location = context.user_data['last_location']
            distance = calculate_distance(user_location)
            await update.message.reply_text(f"Вы находитесь в {int(distance)} метрах от секретной точки.")
        await asyncio.sleep(10)  # Интервал 10 секунд

# Обработка трансляции геопозиции
async def handle_location(update: Update, context: CallbackContext) -> None:
    global is_tracking
    if update is None: return

    if not is_tracking:
        await update.message.delete()  # Удаляем сообщение, если отслеживание не включено
        return
    
    message = None
    if update.edited_message:
        message = update.edited_message
    else:
        message = update.message

    is_single_coord = message.location.live_period is None
    
    # Если пользователь отправил не трансляцию геопозиции
    if is_single_coord:
        await handle_single_coordinates(message, context)
    # Иначе сохраняем последнюю геопозицию пользователя
    else:
        user_location = (message.location.latitude, message.location.longitude)
        context.user_data['last_location'] = user_location

# Обработка одиночных координат (не трансляции)
async def handle_single_coordinates(message, context: CallbackContext) -> None:
    global is_tracking, tracking_task
    await message.reply_text('Работа бота остановлена, для возобновления нажмите кнопу "начать" и отправьте трансляцию геопозиции')
    
    is_tracking = False
    if tracking_task:
        tracking_task.cancel() 

    await message.delete()  # Удаляем сообщение с одиночной геопозицией

# Обработка нажатий кнопок
async def handle_button(update: Update, context: CallbackContext) -> None:
    text = update.message.text.lower()  # Приводим текст к нижнему регистру для обработки команд
    if text == "начать":
        await begin_tracking(update, context)
    elif text == "стоп":
        await stop_tracking(update, context)

def main():
    
    # Ваш токен бота
    TOKEN = ''

    # Создаем объект Application
    application = Application.builder().token(TOKEN).build()

    # Обработчик команды /start
    application.add_handler(CommandHandler("start", start))

    # Обработчик текстовых команд (кнопки)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button))

    # Обработка трансляции геопозиции (location update)
    application.add_handler(MessageHandler(filters.LOCATION | filters.VENUE, handle_location))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
