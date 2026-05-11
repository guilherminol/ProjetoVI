"""
P95 latency load test — simulates 4 concurrent chat users.

Prerequisites:
  pip install httpx
  docker compose up -d
  # ensure at least one PDF is indexed (status=ready)

Usage:
  python scripts/load_test.py --url http://localhost:8000 \
      --email user@example.com --password secret \
      --concurrency 4 --requests 20
"""
import argparse
import asyncio
import statistics
import time

import httpx


async def login(client: httpx.AsyncClient, base_url: str, email: str, password: str) -> str:
    r = await client.post(
        f"{base_url}/auth/login",
        data={"username": email, "password": password},
    )
    r.raise_for_status()
    return r.json()["access_token"]


async def chat_request(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    question: str,
) -> float:
    t0 = time.monotonic()
    async with client.stream(
        "POST",
        f"{base_url}/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": question},
        timeout=30,
    ) as resp:
        resp.raise_for_status()
        async for _ in resp.aiter_bytes():
            pass
    return time.monotonic() - t0


async def worker(
    base_url: str,
    email: str,
    password: str,
    questions: list[str],
    results: list[float],
) -> None:
    async with httpx.AsyncClient() as client:
        token = await login(client, base_url, email, password)
        for q in questions:
            try:
                latency = await chat_request(client, base_url, token, q)
                results.append(latency)
                status = "ok"
            except Exception as exc:
                results.append(30.0)
                status = f"error: {exc}"
            print(f"  [{status}] {latency:.2f}s — {q[:60]}")


async def run(base_url: str, email: str, password: str, concurrency: int, total: int) -> None:
    questions = [
        "Como configurar a rede no sistema?",
        "Qual o procedimento de backup?",
        "Como resetar a senha do administrador?",
        "Quais são os requisitos mínimos de hardware?",
        "Como instalar atualizações do sistema?",
    ]
    per_worker = total // concurrency
    results: list[float] = []

    print(f"\nLoad test: {concurrency} concurrent users × {per_worker} requests each\n")
    t_start = time.monotonic()

    tasks = [
        worker(base_url, email, password, (questions * (per_worker // len(questions) + 1))[:per_worker], results)
        for _ in range(concurrency)
    ]
    await asyncio.gather(*tasks)

    total_time = time.monotonic() - t_start
    if not results:
        print("No results collected.")
        return

    results.sort()
    p50 = statistics.median(results)
    p95 = results[int(len(results) * 0.95)]
    p99 = results[int(len(results) * 0.99)] if len(results) >= 100 else results[-1]

    print(f"\n{'='*40}")
    print(f"Requests:   {len(results)}")
    print(f"Total time: {total_time:.1f}s")
    print(f"P50:        {p50:.2f}s")
    print(f"P95:        {p95:.2f}s  {'✓ PASS' if p95 < 5 else '✗ FAIL (target <5s)'}")
    print(f"P99:        {p99:.2f}s")
    print(f"Min/Max:    {min(results):.2f}s / {max(results):.2f}s")
    print(f"{'='*40}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--requests", type=int, default=20)
    args = parser.parse_args()
    asyncio.run(run(args.url, args.email, args.password, args.concurrency, args.requests))
