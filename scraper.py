import asyncio
from telethon import TelegramClient, events

api_id = 36179933
api_hash = "5a745c4bd3365b7add3c0a8815cd0c87"

client = TelegramClient("session", api_id, api_hash)

@client.on(events.NewMessage(chats="groupnilesh"))
async def handler(event):
    sender = await event.get_sender()

    name = f"{sender.first_name or ''} {sender.last_name or ''}"
    username = sender.username if sender.username else "N/A"

    print("\n📩 New Message")
    print("Name:", name)
    print("Username:", username)
    print("Time:", event.message.date)
    print("Message:", event.message.text)


async def main():
    await client.start()
    print("🚀 Live streaming started... (Press CTRL+C to stop)")

    try:
        await client.run_until_disconnected()

    except asyncio.CancelledError:
        # 🔥 THIS FIXES YOUR ERROR
        print("\n⚠️ Cancelled safely")

    finally:
        await client.disconnect()
        print("✅ Client disconnected safely")


# 🔥 IMPORTANT CHANGE HERE
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Program stopped without error")