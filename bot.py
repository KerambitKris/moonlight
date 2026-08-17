import random
import time

ping_cache = {}

def get_ping(server_name):
    now = time.time()

    if server_name in ping_cache:
        ping, timestamp = ping_cache[server_name]

        # если не прошло 30 минут → вернуть старый
        if now - timestamp < 1800:
            return format_ping(ping)

        # прошло 30 мин → чуть изменить
        new_ping = ping + random.randint(-8, 8)
        new_ping = max(10, min(120, new_ping))

    else:
        # первый раз
        new_ping = random.randint(20, 80)

    ping_cache[server_name] = (new_ping, now)

    return format_ping(new_ping)


def format_ping(ping):
    if ping < 40:
        status = "🟢"
    elif ping < 70:
        status = "🟡"
    else:
        status = "🔴"

    return f"{ping}ms {status}"
