from datetime import datetime


def format_new_bias(data: dict) -> str:
    e = "🟢" if data['bias'] == "BULLISH" else "🔴"
    return (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔔 𝗡𝗘𝗪 𝗕𝗜𝗔𝗦 𝗔𝗟𝗘𝗥𝗧 {e}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🪙 𝗖𝗼𝗶𝗻: {data['coin']}\n"
        f"⏰ 𝗧𝗶𝗺𝗲𝗳𝗿𝗮𝗺𝗲: {data['timeframe']}\n"
        f"📊 𝗕𝗶𝗮𝘀: {e} {data['bias']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 𝗦𝘁𝗮𝗿𝘁: {data.get('entry', 'N/A')}\n"
        f"🎯 𝗧𝗮𝗿𝗴𝗲𝘁: {data.get('target', 'N/A')}\n"
        f"❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱𝗮𝘁𝗶𝗼𝗻: {data.get('invalidation', 'N/A')}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 𝗪𝗶𝗻 𝗥𝗮𝘁𝗲: {data.get('win_rate', 0)}%"
        f" ({data.get('wins', 0)}/{data.get('total', 0)})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ 𝗧𝗿𝗮𝗱𝗲 𝘄𝗶𝘁𝗵 𝗰𝗮𝘂𝘁𝗶𝗼𝗻 | 𝗡𝗙𝗔\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )


def format_target_hit(data: dict) -> str:
    e = "🟢" if data['bias'] == "BULLISH" else "🔴"
    entry = data.get('entry', 0) or 0
    target = data.get('target', 0) or 0
    profit = abs((target - entry) / entry * 100) if entry else 0
    return (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ 𝗧𝗔𝗥𝗚𝗘𝗧 𝗛𝗜𝗧 🎯\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🪙 𝗖𝗼𝗶𝗻: {data['coin']}\n"
        f"⏰ 𝗧𝗶𝗺𝗲𝗳𝗿𝗮𝗺𝗲: {data['timeframe']}\n"
        f"📊 𝗕𝗶𝗮𝘀: {e} {data['bias']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 𝗘𝗻𝘁𝗿𝘆: {entry}\n"
        f"🎯 𝗧𝗮𝗿𝗴𝗲𝘁: {target} ✅\n"
        f"💰 𝗣𝗿𝗼𝗳𝗶𝘁: {profit:.2f}%\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎉 𝗕𝗶𝗮𝘀 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹!\n"
        f"📈 𝗨𝗽𝗱𝗮𝘁𝗲𝗱 𝗪𝗥: {data.get('win_rate', 0)}%"
        f" ({data.get('wins', 0)}/{data.get('total', 0)})\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )


def format_invalidation(data: dict) -> str:
    e = "🟢" if data['bias'] == "BULLISH" else "🔴"
    entry = data.get('entry', 0) or 0
    inval = data.get('invalidation', 0) or 0
    loss = abs((inval - entry) / entry * 100) if entry else 0
    return (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"❌ 𝗜𝗡𝗩𝗔𝗟𝗜𝗗𝗔𝗧𝗜𝗢𝗡 𝗛𝗜𝗧 ⚠️\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🪙 𝗖𝗼𝗶𝗻: {data['coin']}\n"
        f"⏰ 𝗧𝗶𝗺𝗲𝗳𝗿𝗮𝗺𝗲: {data['timeframe']}\n"
        f"📊 𝗕𝗶𝗮𝘀: {e} {data['bias']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 𝗘𝗻𝘁𝗿𝘆: {entry}\n"
        f"❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱𝗮𝘁𝗲𝗱: {inval}\n"
        f"📉 𝗟𝗼𝘀𝘀: {loss:.2f}%\n"
        f"🎯 𝗠𝗶𝘀𝘀𝗲𝗱 𝗧𝗮𝗿𝗴𝗲𝘁: {data.get('target', 'N/A')}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ 𝗕𝗶𝗮𝘀 𝗙𝗮𝗶𝗹𝗲𝗱\n"
        f"📈 𝗨𝗽𝗱𝗮𝘁𝗲𝗱 𝗪𝗥: {data.get('win_rate', 0)}%"
        f" ({data.get('wins', 0)}/{data.get('total', 0)})\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )


def format_active_biases(biases: list) -> str:
    if not biases:
        return (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📊 𝗔𝗖𝗧𝗜𝗩𝗘 𝗕𝗜𝗔𝗦𝗘𝗦\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚪ No active biases right now\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
    now = datetime.utcnow()
    msg = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📊 𝗔𝗖𝗧𝗜𝗩𝗘 𝗕𝗜𝗔𝗦𝗘𝗦\n"
        f"🕐 Live: {now.strftime('%H:%M:%S')} UTC\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    for b in biases:
        e = "🟢" if b['bias'] == "BULLISH" else "🔴"
        msg += (
            f"{e} {b['coin']} | {b['timeframe']}\n"
            f"   📊 {b['bias']}\n"
            f"   📍 Start: {b['entry']}\n"
            f"   🎯 Target: {b['target']}\n"
            f"   ❌ Inval: {b['invalidation']}\n"
            f"   📈 WR: {b['win_rate']}%"
            f" ({b['wins']}/{b['total']})\n"
            f"   🕐 Since: {b['timestamp'][:16]}\n\n"
        )
    msg += "━━━━━━━━━━━━━━━━━━━━"
    return msg


def format_stats(stats: list, title: str = "📊 STATS",
                 days: int = 30) -> str:
    if not stats:
        return (
            f"━━━━━━━━━━━━━━━━━━━━\n{title}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📭 No data yet\n━━━━━━━━━━━━━━━━━━━━"
        )
    msg = (
        f"━━━━━━━━━━━━━━━━━━━━\n{title}\n"
        f"📅 Last {days} days\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    for s in stats:
        wr = s.get('win_rate', 0) or 0
        bar = "🟩" * int(wr / 10) + "⬜" * (10 - int(wr / 10))
        msg += (
            f"🪙 {s['coin']} | {s['timeframe']}\n"
            f"   {bar}\n"
            f"   📈 WR: {wr}%\n"
            f"   ✅ {s.get('wins', 0)} |"
            f" ❌ {s.get('losses', 0)} |"
            f" 📊 {s.get('total', 0)}\n"
            f"   💰 Avg: {s.get('avg_profit', 0)}%\n\n"
        )
    msg += "━━━━━━━━━━━━━━━━━━━━"
    return msg


def format_overall(stats: dict, days: int = 30) -> str:
    wr = stats.get('win_rate', 0) or 0
    bar = "🟩" * int(wr / 10) + "⬜" * (10 - int(wr / 10))
    return (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 𝗢𝗩𝗘𝗥𝗔𝗟𝗟 𝗦𝗧𝗔𝗧𝗦\n"
        f"📅 Last {days} days\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Signals: {stats.get('total', 0)}\n"
        f"✅ Wins: {stats.get('wins', 0)}\n"
        f"❌ Losses: {stats.get('losses', 0)}\n"
        f"🪙 Coins: {stats.get('coins_tracked', 0)}\n\n"
        f"📈 Win Rate:\n   {bar} {wr}%\n\n"
        f"💰 Avg P/L: {stats.get('avg_profit', 0)}%\n"
        f"💎 Total P/L: {stats.get('total_profit', 0)}%\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )


def format_date_signals(signals: list, date: str) -> str:
    if not signals:
        return (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 {date}\n━━━━━━━━━━━━━━━━━━━━\n"
            f"📭 No signals\n━━━━━━━━━━━━━━━━━━━━"
        )
    msg = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 𝗦𝗜𝗚𝗡𝗔𝗟𝗦 — {date}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    for s in signals:
        if s['event'] == 'NEW_BIAS':
            e = "🟢" if s['bias'] == "BULLISH" else "🔴"
            res = {"WIN": "✅", "LOSS": "❌"}.get(
                s.get('result'), "⏳")
            msg += (
                f"🔔 {s['timestamp'][:16]}\n"
                f"   {e} {s['coin']} | {s['timeframe']}"
                f" | {s['bias']}\n"
                f"   📍{s['entry']} → 🎯{s['target']}\n"
                f"   Result: {res}\n\n"
            )
        elif s['event'] == 'TARGET_HIT':
            msg += (
                f"✅ {s['timestamp'][:16]}\n"
                f"   🎯 {s['coin']} | {s['timeframe']}"
                f" Target Hit!\n\n"
            )
        elif s['event'] == 'INVALIDATION':
            msg += (
                f"❌ {s['timestamp'][:16]}\n"
                f"   ⚠️ {s['coin']} | {s['timeframe']}"
                f" Invalidated\n\n"
            )
    msg += "━━━━━━━━━━━━━━━━━━━━"
    return msg


def format_leaderboard(best: list, worst: list,
                       days: int = 30) -> str:
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    msg = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 𝗟𝗘𝗔𝗗𝗘𝗥𝗕𝗢𝗔𝗥𝗗\n"
        f"📅 Last {days} days\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🟢 𝗧𝗼𝗽 𝗣𝗲𝗿𝗳𝗼𝗿𝗺𝗲𝗿𝘀:\n"
    )
    for i, b in enumerate(best[:5]):
        m = medals[i] if i < len(medals) else "▪️"
        msg += (
            f"{m} {b['coin']} ({b['timeframe']})"
            f" — {b['win_rate']}% WR"
            f" ({b['wins']}/{b['total']})\n"
        )
    msg += "\n🔴 𝗪𝗼𝗿𝘀𝘁 𝗣𝗲𝗿𝗳𝗼𝗿𝗺𝗲𝗿𝘀:\n"
    for w in worst[:5]:
        msg += (
            f"⚠️ {w['coin']} ({w['timeframe']})"
            f" — {w['win_rate']}% WR"
            f" ({w.get('losses', 0)}L)\n"
        )
    msg += "\n━━━━━━━━━━━━━━━━━━━━"
    return msg


def format_coin_history(signals: list, coin: str) -> str:
    if not signals:
        return (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📜 {coin}\n━━━━━━━━━━━━━━━━━━━━\n"
            f"📭 No history\n━━━━━━━━━━━━━━━━━━━━"
        )
    msg = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📜 {coin} 𝗛𝗜𝗦𝗧𝗢𝗥𝗬\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    for s in signals[:15]:
        ev = {"NEW_BIAS": "🔔", "TARGET_HIT": "✅",
              "INVALIDATION": "❌"}.get(s['event'], "▪️")
        be = "🟢" if s['bias'] == "BULLISH" else "🔴"
        msg += (
            f"{ev} {s['timestamp'][:16]}\n"
            f"   {be} {s['timeframe']} |"
            f" {s['bias']} | {s['event']}\n"
        )
        if s.get('profit_pct') is not None:
            p = s['profit_pct']
            msg += f"   {'💰' if p > 0 else '📉'} P/L: {p:.2f}%\n"
        msg += "\n"
    msg += "━━━━━━━━━━━━━━━━━━━━"
    return msg
