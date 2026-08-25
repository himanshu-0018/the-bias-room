import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, Application
)
from database import BiasDatabase
from messages import *

# ==========================================
# LOGGING & CONFIG
# ==========================================
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("TheBiasRoom")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PORT = int(os.getenv("PORT", 5000))

db = BiasDatabase()
bot_instance: Application = None

# ==========================================
# NON-BLOCKING BROADCAST ALERT
# ==========================================
async def broadcast_alert(text: str):
    if not bot_instance or not bot_instance.bot:
        return

    # Database read offloaded to thread to keep async loop running
    subscribers = await asyncio.to_thread(db.get_active_subscribers)
    if not subscribers:
        logger.warning("⚠️ No active bot subscribers found to broadcast to.")
        return

    logger.info(f"📢 Sending alerts to {len(subscribers)} users...")
    count = 0
    for uid in subscribers:
        try:
            await bot_instance.bot.send_message(
                chat_id=uid,
                text=text,
                disable_web_page_preview=True
            )
            count += 1
            await asyncio.sleep(0.04)  # Safeguard rate limiting
        except Exception as e:
            err_str = str(e).lower()
            if any(k in err_str for k in ["blocked", "chat not found", "deactivated"]):
                await asyncio.to_thread(db.remove_subscriber, uid)
            else:
                logger.error(f"Failed sending to {uid}: {e}")
    logger.info(f"✅ Alert successfully sent to {count}/{len(subscribers)} active chats.")

# ==========================================
# DECOUPLED ASYNC BACKGROUND WORKER
# ==========================================
async def process_webhook_payload(raw_text: str):
    """Processes, saves, and broadcasts webhook payloads on a background loop"""
    try:
        if not raw_text or not raw_text.strip():
            return

        data = None
        try:
            data = json.loads(raw_text)
        except Exception:
            try:
                # Fallback sanitation for single quotes or NaN values
                sanitized = raw_text.replace("'", '"').replace("NaN", "0").replace("nan", "0")
                data = json.loads(sanitized)
            except Exception:
                data = None

        if isinstance(data, dict) and 'coin' in data:
            data['coin'] = str(data.get('coin', 'UNKNOWN'))
            data['timeframe'] = str(data.get('timeframe', 'TF'))
            data['event'] = str(data.get('event', 'NEW_BIAS'))
            data['bias'] = str(data.get('bias', 'NEUTRAL'))
            data['timestamp'] = str(data.get('timestamp', datetime.utcnow().isoformat()))

            # Offload blocking database write operation to separate thread
            sid = await asyncio.to_thread(db.add_signal, data)
            logger.info(f"💾 Background task stored signal #{sid}: {data['coin']}")

            # Formulate telegram templates
            if data['event'] == 'NEW_BIAS':
                msg = format_new_bias(data)
            elif data['event'] == 'TARGET_HIT':
                msg = format_target_hit(data)
            elif data['event'] == 'INVALIDATION':
                msg = format_invalidation(data)
            else:
                msg = f"📊 Alert: {data['coin']} | {data['timeframe']} | {data['bias']}"

            await broadcast_alert(msg)
        else:
            logger.info("Broadcasting raw text payload directly...")
            await broadcast_alert(raw_text)

    except Exception as e:
        logger.error(f"❌ Error in background payload processor: {e}")

# ==========================================
# WEBHOOK ENDPOINT
# ==========================================
async def handle_webhook(request):
    try:
        raw_text = await request.text()
        logger.info(f"📥 Received Webhook Burst: {len(raw_text)} bytes")

        # ⚡ CRITICAL: Schedule execution to background, return 200 OK immediately (<5ms)
        asyncio.create_task(process_webhook_payload(raw_text))

        return web.json_response({"status": "received", "message": "processing in background"}, status=200)
    except Exception as e:
        logger.error(f"Error catching webhook request: {e}")
        return web.json_response({"status": "error_logged"}, status=200)

async def handle_health(request):
    total_users = len(await asyncio.to_thread(db.get_active_subscribers))
    return web.json_response({
        "status": "online",
        "subscribers": total_users,
        "time": datetime.utcnow().isoformat()
    })

# ==========================================
# TELEGRAM BOT COMMANDS (FULLY THREAD-SAFE)
# ==========================================
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Active Biases", callback_data="active_all"),
         InlineKeyboardButton("🏆 Overall Stats", callback_data="overall_30")],
        [InlineKeyboardButton("📈 Stats by Coin", callback_data="stats_menu"),
         InlineKeyboardButton("⏰ Stats by TF", callback_data="tf_menu")],
        [InlineKeyboardButton("📅 Date Filter", callback_data="date_menu"),
         InlineKeyboardButton("📜 History", callback_data="history_menu")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leader_30"),
         InlineKeyboardButton("🔥 Streak", callback_data="streak")],
        [InlineKeyboardButton("ℹ️ Help / Commands", callback_data="help")]
    ])

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await asyncio.to_thread(db.add_subscriber, u.id, u.username)
    welcome_text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🏛️ 𝗧𝗛𝗘 𝗕𝗜𝗔𝗦 𝗥𝗢𝗢𝗠\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Welcome, {u.first_name}! 👋\n\n"
        "✅ **You are subscribed to Live Alerts!**\n"
        "New Biases, Target Hits, and Invalidations will be sent directly here in real time.\n\n"
        "Explore current trades, stats, and historical results below:\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "ℹ️ 𝗔𝗩𝗔𝗜𝗟𝗔𝗕𝗟𝗘 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔹 /start — Main interactive dashboard\n"
        "🔹 /active — View currently pending biases\n"
        "🔹 /stats — Total win rate & performance\n"
        "🔹 /stats_coin BTC/USDT — Coin specific stats\n"
        "🔹 /today — View today's signals & results\n"
        "🔹 /yesterday — Yesterday's signals\n"
        "🔹 /date 2024-03-25 — Filter signals by any date\n"
        "🔹 /history BTC/USDT — Recent trade log\n"
        "🔹 /leaderboard — Best & worst performing coins\n"
        "🔹 /streak — Current win/loss streak\n"
        "🔹 /coins — List of all tracked pairs\n"
        "🔹 /week — Performance in last 7 days\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(msg)

async def cmd_active(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    biases = await asyncio.to_thread(db.get_active_biases)
    await update.message.reply_text(format_active_biases(biases))

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    stats = await asyncio.to_thread(db.get_overall_stats, 30)
    await update.message.reply_text(format_overall(stats, 30))

async def cmd_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = datetime.utcnow().strftime('%Y-%m-%d')
    signals = await asyncio.to_thread(db.get_signals_by_date, d)
    await update.message.reply_text(format_date_signals(signals, d))

async def cmd_yesterday(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
    signals = await asyncio.to_thread(db.get_signals_by_date, d)
    await update.message.reply_text(format_date_signals(signals, d))

async def cmd_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("💡 Usage: `/date 2024-03-25`", parse_mode="Markdown")
        return
    d = ctx.args[0]
    signals = await asyncio.to_thread(db.get_signals_by_date, d)
    await update.message.reply_text(format_date_signals(signals, d))

async def cmd_stats_coin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        coins = await asyncio.to_thread(db.get_all_coins)
        if not coins:
            await update.message.reply_text("📭 No coins tracked yet.")
            return
        kb, row = [], []
        for c in coins:
            row.append(InlineKeyboardButton(c, callback_data=f"coin_stats_{c}"))
            if len(row) == 2:
                kb.append(row)
                row = []
        if row:
            kb.append(row)
        await update.message.reply_text("Select a coin:", reply_markup=InlineKeyboardMarkup(kb))
        return
    coin = ctx.args[0].upper()
    stats = await asyncio.to_thread(db.get_stats, coin, None, 30)
    await update.message.reply_text(format_stats(stats, f"📊 {coin}", 30))

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        coins = await asyncio.to_thread(db.get_all_coins)
        if not coins:
            await update.message.reply_text("📭 No history yet.")
            return
        kb, row = [], []
        for c in coins:
            row.append(InlineKeyboardButton(c, callback_data=f"history_{c}"))
            if len(row) == 2:
                kb.append(row)
                row = []
        if row:
            kb.append(row)
        await update.message.reply_text("Select a coin:", reply_markup=InlineKeyboardMarkup(kb))
        return
    coin = ctx.args[0].upper()
    signals = await asyncio.to_thread(db.get_coin_history, coin)
    await update.message.reply_text(format_coin_history(signals, coin))

async def cmd_leaderboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    best = await asyncio.to_thread(db.get_best_performers, 30)
    worst = await asyncio.to_thread(db.get_worst_performers, 30)
    await update.message.reply_text(format_leaderboard(best, worst, 30))

async def cmd_streak(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    count, st = await asyncio.to_thread(db.get_streak)
    e = "🟢" if st == "WIN" else "🔴" if st == "LOSS" else "⚪"
    await update.message.reply_text(
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔥 𝗦𝗧𝗥𝗘𝗔𝗞\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{e} {count}x {st} Streak!\n"
        f"{'🔥' * min(count, 10)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

async def cmd_coins(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    coins = await asyncio.to_thread(db.get_all_coins)
    if not coins:
        await update.message.reply_text("📭 No coins tracked yet.")
        return
    msg = "━━━━━━━━━━━━━━━━━━━━\n🪙 𝗧𝗥𝗔𝗖𝗞𝗘𝗗 𝗖𝗢𝗜𝗡𝗦\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, c in enumerate(coins, 1):
        msg += f"  {i}. {c}\n"
    msg += f"\n📊 Total: {len(coins)}\n━━━━━━━━━━━━━━━━━━━━"
    await update.message.reply_text(msg)

async def cmd_week(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    stats = await asyncio.to_thread(db.get_overall_stats, 7)
    await update.message.reply_text(format_overall(stats, 7))

# ==========================================
# BUTTON HANDLERS (THREAD-SAFE ASYNC)
# ==========================================
async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data

    if d == "main_menu":
        await q.edit_message_text("🏛️ 𝗧𝗛𝗘 𝗕𝗜𝗔𝗦 𝗥𝗢𝗢𝗠\n\nChoose an option:", reply_markup=main_menu_keyboard())

    elif d == "active_all":
        biases = await asyncio.to_thread(db.get_active_biases)
        kb = [[InlineKeyboardButton("🔄 Refresh", callback_data="active_all"),
               InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]]
        await q.edit_message_text(format_active_biases(biases), reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("overall_"):
        days = int(d.split("_")[1])
        stats = await asyncio.to_thread(db.get_overall_stats, days)
        kb = [
            [InlineKeyboardButton("7D", callback_data="overall_7"),
             InlineKeyboardButton("14D", callback_data="overall_14"),
             InlineKeyboardButton("30D", callback_data="overall_30"),
             InlineKeyboardButton("90D", callback_data="overall_90"),
             InlineKeyboardButton("ALL", callback_data="overall_3650")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
        ]
        await q.edit_message_text(format_overall(stats, days), reply_markup=InlineKeyboardMarkup(kb))

    elif d == "stats_menu":
        coins = await asyncio.to_thread(db.get_all_coins)
        kb, row = [], []
        for c in coins[:20]:
            row.append(InlineKeyboardButton(c[:12], callback_data=f"coin_stats_{c}"))
            if len(row) == 2:
                kb.append(row)
                row = []
        if row:
            kb.append(row)
        kb.append([InlineKeyboardButton("🔙 Menu", callback_data="main_menu")])
        await q.edit_message_text("📈 Select coin for stats:", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("coin_stats_"):
        coin = d.replace("coin_stats_", "")
        stats = await asyncio.to_thread(db.get_stats, coin, None, 30)
        kb = [
            [InlineKeyboardButton("📜 History", callback_data=f"history_{coin}"),
             InlineKeyboardButton("📊 Active", callback_data=f"coin_active_{coin}")],
            [InlineKeyboardButton("🔙 Back", callback_data="stats_menu"),
             InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
        ]
        await q.edit_message_text(format_stats(stats, f"📊 {coin}", 30), reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("coin_active_"):
        coin = d.replace("coin_active_", "")
        biases = await asyncio.to_thread(db.get_active_biases, coin)
        kb = [[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]]
        await q.edit_message_text(format_active_biases(biases), reply_markup=InlineKeyboardMarkup(kb))

    elif d == "tf_menu":
        kb = [
            [InlineKeyboardButton("4H ⏰", callback_data="tf_stats_4H"),
             InlineKeyboardButton("Daily 📅", callback_data="tf_stats_DAILY"),
             InlineKeyboardButton("Weekly 📆", callback_data="tf_stats_WEEKLY")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
        ]
        await q.edit_message_text("⏰ Select timeframe:", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("tf_stats_"):
        tf = d.replace("tf_stats_", "")
        stats = await asyncio.to_thread(db.get_stats, None, tf, 30)
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="tf_menu"),
               InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]]
        await q.edit_message_text(format_stats(stats, f"⏰ {tf}", 30), reply_markup=InlineKeyboardMarkup(kb))

    elif d == "date_menu":
        today = datetime.utcnow()
        kb = []
        for i in range(7):
            dt = today - timedelta(days=i)
            ds = dt.strftime('%Y-%m-%d')
            lbl = "Today" if i == 0 else ("Yesterday" if i == 1 else dt.strftime('%a'))
            kb.append([InlineKeyboardButton(f"📅 {lbl} ({ds})", callback_data=f"date_{ds}")])
        kb.append([InlineKeyboardButton("🔙 Menu", callback_data="main_menu")])
        await q.edit_message_text("📅 Select date:", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("date_"):
        date = d.replace("date_", "")
        signals = await asyncio.to_thread(db.get_signals_by_date, date)
        kb = [[InlineKeyboardButton("🔙 Dates", callback_data="date_menu"),
               InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]]
        await q.edit_message_text(format_date_signals(signals, date), reply_markup=InlineKeyboardMarkup(kb))

    elif d == "history_menu":
        coins = await asyncio.to_thread(db.get_all_coins)
        kb, row = [], []
        for c in coins[:20]:
            row.append(InlineKeyboardButton(c[:12], callback_data=f"history_{c}"))
            if len(row) == 2:
                kb.append(row)
                row = []
        if row:
            kb.append(row)
        kb.append([InlineKeyboardButton("🔙 Menu", callback_data="main_menu")])
        await q.edit_message_text("📜 Select coin:", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("history_"):
        coin = d.replace("history_", "")
        signals = await asyncio.to_thread(db.get_coin_history, coin)
        kb = [[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]]
        await q.edit_message_text(format_coin_history(signals, coin), reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("leader_"):
        days = int(d.split("_")[1])
        best = await asyncio.to_thread(db.get_best_performers, days)
        worst = await asyncio.to_thread(db.get_worst_performers, days)
        kb = [
            [InlineKeyboardButton("7D", callback_data="leader_7"),
             InlineKeyboardButton("30D", callback_data="leader_30"),
             InlineKeyboardButton("90D", callback_data="leader_90")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
        ]
        await q.edit_message_text(format_leaderboard(best, worst, days), reply_markup=InlineKeyboardMarkup(kb))

    elif d == "streak":
        count, st = await asyncio.to_thread(db.get_streak)
        e = "🟢" if st == "WIN" else "🔴" if st == "LOSS" else "⚪"
        kb = [[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]]
        await q.edit_message_text(
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔥 𝗦𝗧𝗥𝗘𝗔𝗞\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{e} {count}x {st} Streak!\n"
            f"{'🔥' * min(count, 10)}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif d == "help":
        kb = [[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]]
        await q.edit_message_text("ℹ️ Type /help to view all bot commands.", reply_markup=InlineKeyboardMarkup(kb))

# ==========================================
# MAIN LIFECYCLE
# ==========================================
async def main():
    global bot_instance
    if not BOT_TOKEN:
        logger.error("❌ ERROR: BOT_TOKEN is missing! Add it in Railway Variables.")
        return

    # 1. Start Bot Polling Loop
    logger.info("🤖 Initializing Telegram Bot...")
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("help", cmd_help))
    bot_app.add_handler(CommandHandler("active", cmd_active))
    bot_app.add_handler(CommandHandler("stats", cmd_stats))
    bot_app.add_handler(CommandHandler("stats_coin", cmd_stats_coin))
    bot_app.add_handler(CommandHandler("date", cmd_date))
    bot_app.add_handler(CommandHandler("today", cmd_today))
    bot_app.add_handler(CommandHandler("yesterday", cmd_yesterday))
    bot_app.add_handler(CommandHandler("history", cmd_history))
    bot_app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    bot_app.add_handler(CommandHandler("streak", cmd_streak))
    bot_app.add_handler(CommandHandler("coins", cmd_coins))
    bot_app.add_handler(CommandHandler("week", cmd_week))
    bot_app.add_handler(CallbackQueryHandler(button_handler))

    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    bot_instance = bot_app
    logger.info("✅ Bot is polling successfully!")

    # 2. Start Decoupled HTTP Webhook Server (aiohttp)
    logger.info(f"🌐 Starting Webhook server on port {PORT}...")
    web_app = web.Application()
    web_app.router.add_post('/webhook', handle_webhook)
    web_app.router.add_get('/health', handle_health)

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info("🚀 Everything is live! Listening for burst webhooks at /webhook")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
