import random
import os
import time

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

TOKEN = "hbqYn-htS8hdZC-omUIUL95T0EqU-OhGuQszlaUJlYYBZMzkt-bVoVeYCkKkBpSVYT41_yLUVD9iWwRqUxOn1A=="


class MetricsServer:
    def __init__(
        self, url="http://localhost:8086", org="acme", bucket="benchmarks", token=None
    ):
        if token is None:
            self.token = os.environ["INFLUXDB_TOKEN"]
        else:
            self.token = token

        self.bucket = bucket
        self.url = url
        self.org = org
        self.client = InfluxDBClient(url=self.url, org=self.org, token=self.token)

    def mean(self, bucket, branch, benchmark, field):
        query = f"""
        from(bucket:"{bucket}")
        |> range(start: -30d, stop: now())
        |> filter(fn: (r) => r["branch"] == "{branch}")
        |> filter(fn: (r) => r["_measurement"] == "{benchmark}")
        |> filter(fn: (r) => r["_field"] == "{field}")
        |> sort(columns: ["_stop"], desc: true)
        |> limit(n:10)
        |> mean(column: "_value")
        """
        query_api = self.client.query_api()
        previous = query_api.query(query)
        if len(previous) == 0:
            return None
        if len(previous[0].records) == 0:
            return None

        return previous[0].records[0].values["_value"]

    def send_measure(self, branch, benchmark, measure, check_previous=None):
        write_api = self.client.write_api(write_options=SYNCHRONOUS)

        previous = {}

        for field, value in measure.items():
            point = Point(benchmark).tag("branch", branch).field(field, value)
            write_api.write(bucket=self.bucket, record=point)

            if check_previous is None:
                continue

            previous[field] = (
                value,
                self.mean(self.bucket, check_previous, benchmark, field),
            )

        return previous


influx = MetricsServer(org="nuclia", bucket="nuclia", token=TOKEN)


for i in range(100):
    measure = [
        ("speed_1", float(random.randint(20, 24))),
        ("speed_2", float(random.randint(200, 240))),
        ("speed_3", float(random.randint(1, 10))),
    ]
    influx.send_measure("main", "speeds", dict(measure))
    # time.sleep(0.1)


for i in range(100):
    measure = [
        ("speed_1", float(random.randint(20, 24))),
        ("speed_2", float(random.randint(200, 240))),
        ("speed_3", float(random.randint(1, 10))),
    ]
    print(influx.send_measure("tarek/feature-1", "speeds", dict(measure), "main"))
    time.sleep(0.1)
