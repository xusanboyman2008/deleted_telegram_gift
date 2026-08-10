import asyncio
import os
import random
import re
import time
import aiohttp
import orjson

try:
    import uvloop
    uvloop.install()
except ImportError:
    pass

# API Endpoints
TAP_URL = "https://server.margcoin.fun/api/game/tap"
ROCKET_URL = "https://server.margcoin.fun/api/game/boost/rocket"

HEADERS = {
    "Host": "server.margcoin.fun",
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/60.5 Safari/605.1.15",
    "Accept": "*/*",
    "Accept-Language": "en-US",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://app.margcoin.fun/",
    "Content-Type": "application/json",
    "Origin": "https://app.margcoin.fun",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0Z0lkIjo2ODU5OTU3MTM5LCJ1c2VybmFtZSI6IlJOR18yMDMwIiwiaXNBZG1pbiI6ZmFsc2UsImlhdCI6MTc4NjM1NTQxMSwiZXhwIjoxNzg4OTQ3NDExfQ.ctK31b98wVR4dmxrE-aowwhCRCdTl-njlRbA7UVBklo",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Connection": "keep-alive"
}

# Telegram Configuration
BOT_TOKEN = "8819330887:AAGXhLiUWnkL50H-t1bCy83QnpNiq64ZH7U"
TARGET_CHAT_IDS = ["6859957139", "6588631008"]

# Global State & Control
last_update_id = None
start_time = None
pause_event = asyncio.Event()
pause_event.set()

# Synchronization & Expiration Tracking
turbo_event = asyncio.Event()
turbo_event.clear()
turbo_active_until = 0  # Timestamp in seconds

auth_lock = asyncio.Lock()


def get_uptime() -> str:
    elapsed = int(time.time() - start_time)
    hours, remainder = divmod(elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


async def send_tg_message(tg_session, chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        async with tg_session.post(url, json=payload) as resp:
            data = await resp.json()
            if data.get("ok"):
                print(f"📩 Requested new auth from {chat_id}")
    except Exception as e:
        print(f"❌ Telegram message failure to {chat_id}: {e}")


async def handle_auth_failure(tg_session, active_sessions):
    global last_update_id
    
    async with auth_lock:
        if not pause_event.is_set():
            return

        pause_event.clear()
        print("\n⚠️ [AUTH ERROR DETECTED] Pausing all requests & requesting new token...")

        tasks = [send_tg_message(tg_session, cid, "send new auth") for cid in TARGET_CHAT_IDS]
        await asyncio.gather(*tasks)

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        new_token = None

        while not new_token:
            params = {"timeout": 30}
            if last_update_id is not None:
                params["offset"] = last_update_id + 1

            try:
                async with tg_session.get(url, params=params) as resp:
                    data = await resp.json()
                    if data.get("ok"):
                        for update in data.get("result", []):
                            last_update_id = update["update_id"]
                            msg = update.get("message", {})
                            sender_id = str(msg.get("chat", {}).get("id", ""))
                            message_text = msg.get("text", "")

                            if sender_id in TARGET_CHAT_IDS:
                                match = re.search(
                                    r"Bearer\s+(eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)",
                                    message_text,
                                )
                                if match:
                                    new_token = match.group(0).strip()
                                    print(f"🔑 Received valid token from {sender_id}!")
                                    break
            except Exception as e:
                print(f"⚠️ Telegram polling error: {e}")

            if not new_token:
                await asyncio.sleep(2)

        HEADERS["Authorization"] = new_token
        for s in active_sessions:
            s.headers.update({"Authorization": new_token})
            
        print("▶️ Tokens updated across all isolated sessions. Resuming operations...\n")
        pause_event.set()


async def rocket_worker(tg_session, active_sessions):
    """Triggers Rocket Boost every 16.5s to avoid 429 Rate Limits safely."""
    global turbo_active_until
    timeout = aiohttp.ClientTimeout(total=15.0)
    
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        active_sessions.append(session)
        idx = 1
        
        try:
            while True:
                await pause_event.wait()
                req_start = time.time()
                
                try:
                    async with session.post(ROCKET_URL, data=b"", ssl=False) as resp:
                        body = await resp.text()
                        
                        if resp.status in (401, 403):
                            await handle_auth_failure(tg_session, active_sessions)
                            continue

                        print(f"⏱️ [{get_uptime()}] [ROCKET #{idx}] Status: {resp.status} | Response: {body}")
                        
                        if resp.status == 200:
                            data = orjson.loads(body)
                            if data.get("turboActive"):
                                turbo_active_until = data.get("turboActiveUntil", 0) / 1000.0
                                turbo_event.set()
                        
                        idx += 1
                except Exception as e:
                    print(f"⏱️ [{get_uptime()}] [ROCKET #{idx}] Failed: {type(e).__name__}")

                elapsed = time.time() - req_start
                await asyncio.sleep(max(0.0, 16.5 - elapsed))
        except asyncio.CancelledError:
            pass


async def tap_worker(tg_session, active_sessions, total_taps):
    """Executes taps with strict timing boundaries."""
    global turbo_active_until
    connector = aiohttp.TCPConnector(limit=1, ssl=False)
    timeout = aiohttp.ClientTimeout(total=10.0)
    
    async with aiohttp.ClientSession(connector=connector, headers=HEADERS, timeout=timeout) as session:
        active_sessions.append(session)
        idx = 1
        
        while True:
            await pause_event.wait()
            
            if not turbo_event.is_set():
                await turbo_event.wait()

            if time.time() >= (turbo_active_until - 1.0):
                turbo_event.clear()
                continue

            # payload = orjson.dumps({"taps": random.randint(510, 520)})
            payload = orjson.dumps({"taps": random.randint(510, 520)})

            try:
                async with session.post(TAP_URL, data=payload, ssl=False) as resp:
                    body = await resp.text()

                    if resp.status in (401, 403):
                        await handle_auth_failure(tg_session, active_sessions)
                        continue

                    if resp.status == 200:
                        data = orjson.loads(body)
                        if not data.get("turboActive"):
                            turbo_event.clear()

                    print(f"⏱️ [{get_uptime()}] [TAP #{idx}/{total_taps}] Status: {resp.status} | Response: {body}")
                    idx += 1
            except Exception as e:
                print(f"⏱️ [{get_uptime()}] [TAP #{idx}/{total_taps}] Failed: {type(e).__name__}")

            await asyncio.sleep(0.2)


async def main():
    global start_time
    start_time = time.time()
    total_taps = int(os.getenv("TOTAL_REQUESTS", "100"))
    
    active_sessions = []

    async with aiohttp.ClientSession() as tg_session:
        print(f"⚡ Starting Isolated Workers | Total Taps: {total_taps} | Rocket Loop: 16.5s\n")
        
        rocket_task = asyncio.create_task(rocket_worker(tg_session, active_sessions))
        
        # Run tap_worker and cancel rocket_worker immediately when tapping ends
        try:
            await tap_worker(tg_session, active_sessions, total_taps)
        finally:
            rocket_task.cancel()
            await asyncio.gather(rocket_task, return_exceptions=True)
            print(f"\n✅ All {total_taps} taps completed. Shutting down active tasks cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n🛑 Stopped. Total uptime was {get_uptime()}.")