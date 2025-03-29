from collections import defaultdict
from datetime import datetime, timedelta
from typing import Union


class MockRedis:
    def __init__(self):
        self.data = defaultdict(bytes)
        self.expires = defaultdict(float)

    async def get(self, key: str):
        if self.expires[key] < datetime.now().timestamp():
            await self.delete(key)
        return self.data.get(key)

    async def setex(self, key: str, ttl: Union[timedelta, int], value: str):
        self.data[key] = value.encode()
        real_ttl = ttl if isinstance(ttl, timedelta) else timedelta(seconds=ttl)
        self.expires[key] = (datetime.now() + real_ttl).timestamp()

    async def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                del self.expires[key]
                count += 1
        return count

    def pipeline(self, *args, **kwargs):
        class MockPipeline:
            def __init__(self, redis):
                self.redis = redis
                self.commands = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def execute(self):
                results = []
                for cmd in self.commands:
                    fn, args, kwargs = cmd
                    results.append(await getattr(self.redis, fn)(*args, **kwargs))
                return results

            def __getattr__(self, name):
                async def wrapper(*args, **kwargs):
                    self.commands.append((name, args, kwargs))
                    return self

                return wrapper

        return MockPipeline(self)
