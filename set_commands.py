import asyncio, os
from telegram import Bot, BotCommand

with open('/home/sashok/.openclaw/workspace/garcia/.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

async def main():
    bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
    await bot.set_my_commands([
        BotCommand("start", "Привітання"),
        BotCommand("analyze", "Аналіз Pinterest-борду"),
        BotCommand("onboarding", "Онбординг: packaging design"),
        BotCommand("cur", "Навчальний план"),
        BotCommand("digest", "Дайджест новин packaging"),
    ])
    print("Команди встановлено!")

asyncio.run(main())
