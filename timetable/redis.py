import redis

class RedisConnection:
    __handle = None

    @staticmethod
    def get_connection():
        if RedisConnection.__handle is None:
            RedisConnection.__handle = redis.Redis(host="redis", port=6379, decode_responses=True)

        return RedisConnection.__handle
