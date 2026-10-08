import ccxt
import requests
import time
from collections import deque
from statistics import mean, stdev

# === НАСТРОЙКИ ===
BYBIT_API_KEY = ""  # Не нужен для публичных данных, можно оставить пустым
BYBIT_SECRET = ""

# Telegram (создайте бота через @BotFather, чтобы получить токен и chat_id)
TELEGRAM_TOKEN = "7818662190:AAFcLsb05XDSDttbYdiKis4GAFKK_KI7aqg"
TELEGRAM_CHAT_ID = "959864500"

# Параметры стратегии
SYMBOL_XLM = "XLM/USDT"
SYMBOL_XRP = "XRP/USDT"
LOOKBACK = 200      # Сколько последних точек хранить для расчета статистики
Z_ENTRY = 2.0       # Порог входа (Z-score)
CHECK_INTERVAL = 60 # Проверка раз в 60 секунд

# === ИНИЦИАЛИЗАЦИЯ ===
exchange = ccxt.bybit({
    "apiKey": BYBIT_API_KEY,
    "secret": BYBIT_SECRET,
    "options": {"defaultType": "spot"}  # Важно: спотовый рынок
})

ratios = deque(maxlen=LOOKBACK)  # Храним историю соотношения цен

def send_telegram(message):
    """Отправка уведомления в Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Ошибка Telegram: {e}")

def calculate_z_score(current_ratio):
    """Считает Z-score: насколько текущее соотношение отклонилось от нормы."""
    if len(ratios) < LOOKBACK:
        return None  # Недостаточно данных
    mu = mean(ratios)
    sigma = stdev(ratios)
    if sigma == 0:
        return 0
    return (current_ratio - mu) / sigma

def analyze():
    """Главный цикл: получаем цены, считаем соотношение, проверяем сигналы."""
    try:
        # Получаем цены (используем 'last' — последняя цена сделки)
        ticker_xlm = exchange.fetch_ticker(SYMBOL_XLM)
        ticker_xrp = exchange.fetch_ticker(SYMBOL_XRP)
        
        price_xlm = ticker_xlm["last"]
        price_xrp = ticker_xrp["last"]
        
        # Соотношение: сколько XRP стоит один XLM (или наоборот)
        # XRP дороже XLM, поэтому делим XRP на XLM
        ratio = price_xrp / price_xlm
        ratios.append(ratio)
        
        z = calculate_z_score(ratio)
        
        print(f"[{time.strftime('%H:%M:%S')}] XLM={price_xlm:.4f} XRP={price_xrp:.4f} Ratio={ratio:.4f} Z={z if z else '...'}")
        
        # === СИГНАЛЫ ===
        if z is not None:
            if z >= Z_ENTRY:
                msg = (
                    f"🔔 *СИГНАЛ НА ПРОДАЖУ XLM*\n"
                    f"Z-score: `{z:.2f}` (порог {Z_ENTRY})\n"
                    f"XLM: `{price_xlm:.4f}` | XRP: `{price_xrp:.4f}`\n"
                    f"Соотношение XRP/XLM: `{ratio:.4f}`\n"
                    f"👉 XLM переоценён относительно XRP"
                )
                send_telegram(msg)
                print(">>> Сигнал: XLM переоценён")
                
            elif z <= -Z_ENTRY:
                msg = (
                    f"🔔 *СИГНАЛ НА ПОКУПКУ XLM*\n"
                    f"Z-score: `{z:.2f}` (порог {-Z_ENTRY})\n"
                    f"XLM: `{price_xlm:.4f}` | XRP: `{price_xrp:.4f}`\n"
                    f"Соотношение XRP/XLM: `{ratio:.4f}`\n"
                    f"👉 XLM недооценён относительно XRP"
                )
                send_telegram(msg)
                print(">>> Сигнал: XLM недооценён")

    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    print("Бот запущен. Наблюдаем за XLM/XRP...")
    send_telegram("🤖 Бот XLM/XRP запущен и следит за рынком.")
    while True:
        analyze()
        time.sleep(CHECK_INTERVAL)
