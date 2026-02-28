import time

MAX_AGE = 7 * 24 * 3600   # 7 days
MIN_WEIGHT = 0.3


def prune_prototypes(data: dict) -> dict:

    now = time.time()

    for label in list(data.keys()):
        protos = data[label]["prototypes"]

        # remove weak or old
        protos = [
            p for p in protos
            if p["weight"] >= MIN_WEIGHT
            and (now - p["last_updated"]) <= MAX_AGE
        ]

        if protos:
            data[label]["prototypes"] = protos
        else:
            del data[label]

    return data
