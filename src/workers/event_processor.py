"""Event processor worker — consumes events from Redis queue.

Stub for v1 — runs as a no-op loop until Redis queue integration is implemented in v2.
"""
import time
import os

def main():
    print("[event_processor] Starting BillingWatch event processor worker...")
    print("[event_processor] Redis URL:", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    print("[event_processor] v1 stub — polling loop active (full Redis consumer in v2)")
    while True:
        time.sleep(30)

if __name__ == "__main__":
    main()
