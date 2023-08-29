import random
import json

measure = [
    ("speed_1", float(random.randint(20, 24))),
    ("speed_2", float(random.randint(200, 240))),
    ("speed_3", float(random.randint(1, 10))),
]

with open("metrics.json") as f:
    f.write(json.dumps(measure))
