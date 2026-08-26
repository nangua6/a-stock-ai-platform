"""Background task worker stub. Implement APScheduler tasks in next phases."""
from __future__ import annotations
import asyncio

async def main():
    print("Task worker starting (stub)...")
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
