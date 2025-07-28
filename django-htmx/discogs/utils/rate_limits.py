import discogs_client
from functools import wraps
from time import time, sleep
from collections import deque
import logging
import math

logging.basicConfig(level=logging.INFO)

class RateLimitTracker:
    def __init__(self, target_rate=0.9):
        self.windows = deque([0, 0, 0], maxlen=3)
        self.current_window_start = time()
        self.current_count = 0
        self.sleep_time = 0.0
        self.logger = logging.getLogger(__name__)


    def add_request(self, endpoint):
        current_time = time()
        
        # Check if 15 seconds have passed
        if current_time - self.current_window_start >= 15:
            self.windows.append(self.current_count)
            total = sum(self.windows) + self.current_count
            self.logger.info(f"Window complete - Total requests: {total}")
            
            # Adjust sleep time based on total
            if total > 45:
                self.sleep_time += 0.1
            elif total < 40:
                self.sleep_time = max(0.0, self.sleep_time - 0.1)
                
            # Reset for new window
            self.current_count = 0
            self.current_window_start = current_time
            
        self.current_count += 1

def rate_limit_client(client):
    """Patches all API methods of the discogs client with rate limiting"""
    tracker = RateLimitTracker()
    original_get = client._get
    original_post = client._post

    @wraps(original_get)
    def rate_limited_get(*args, **kwargs):
        sleep(tracker.sleep_time)
        tracker.add_request(args[0] if args else "GET endpoint")
        return original_get(*args, **kwargs)

    @wraps(original_post)
    def rate_limited_post(*args, **kwargs):
        sleep(tracker.sleep_time)
        tracker.add_request(args[0] if args else "POST endpoint")
        return original_get(*args, **kwargs)

    client._get = rate_limited_get
    client._post = rate_limited_post
    return client