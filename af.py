import random
import os
import textwrap

import requests
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

    def mean(self, branch, benchmark, field):
        query = f"""
        from(bucket:"{self.bucket}")
        |> range(start: -30d, stop: now())
        |> filter(fn: (r) => r["branch"] == "{branch}")
        |> filter(fn: (r) => r["_measurement"] == "{benchmark}")
        |> filter(fn: (r) => r["_field"] == "{field}")
        |> sort(columns: ["_stop"], desc: true)
        |> limit(n:10)
        |> mean(column: "_value")
        """
        print(query)
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
                self.mean(check_previous, benchmark, field),
            )

        return previous


def markdown_table(data, headers):
    # Find maximal length of all elements in list
    n = max(len(x) for l in data for x in l)
    # Print the rows
    headerLength = len(headers)

    lines = []

    header_line = ""
    for i in range(len(headers)):
        hn = n - len(headers[i])
        header_line += "|" + " " * hn + f"{headers[i]}"
        if i == headerLength - 1:
            header_line += "|"
    lines.append(header_line)

    sep_line = "|"
    for i in range(len(headers)):
        sep_line += "-" * n + "|"
    lines.append(sep_line)

    for row in data:
        line = ""
        for x in row:
            hn = n - len(x)
            line += "|" + " " * hn + x
        line += "|"
        lines.append(line)

    return "\n".join(lines)


def comment_pr(comment, repository, pr_number, github_token):
    url = f"https://api.github.com/repos/{repository}/issues/{pr_number}/comments"
    print(f"Calling `{url}`")

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    data = {
        "body": comment,
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 201:
        print("Comment created successfully")
    else:
        print(f"Failed to create comment: {response.text}")


def get_change(current, previous):
    if current == previous:
        return 100.0
    try:
        return (abs(current - previous) / previous) * 100.0
    except ZeroDivisionError:
        return 0


if __name__ == "__main__":
    main_branch = os.getenv("MAIN_BRANCH", "main")
    current_branch = os.getenv("GITHUB_REF", "main")
    print(f"GITHUB_REF IS {current_branch}")

    if current_branch.startswith("refs/pull"):
        pr_number = current_branch.split("/")[2]
    else:
        pr_number = None
    current_branch = current_branch.split("/")[-1].strip()
    benchmark = os.getenv("INFLUXDB_BUCKET", "speeds")
    repository = os.getenv("GITHUB_REPOSITORY")
    gh_token = os.getenv("GITHUB_TOKEN")

    print(f"Connecting to `{os.getenv('INFLUXDB_URL')}`")
    influx = MetricsServer(
        url=os.getenv("INFLUXDB_URL", "http://localhost:8086"),
        org=os.getenv("INFLUXDB_ORG", "acme"),
        bucket=os.getenv("INFLUXDB_BUCKET", "benchmarks"),
        token=os.getenv("INFLUXDB_TOKEN", TOKEN),
    )
    measure = [
        ("speed_1", float(random.randint(20, 24))),
        ("speed_2", float(random.randint(200, 240))),
        ("speed_3", float(random.randint(1, 10))),
    ]

    print(f"Current branch is `{current_branch}`")
    print(f"PR is `{pr_number}`")

    if pr_number is None:
        # metrics for main branch
        influx.send_measure(current_branch, benchmark, dict(measure))
    else:
        res = influx.send_measure(current_branch, benchmark, dict(measure), main_branch)

        if pr_number is not None:
            headers = ["Test", "PR benchmark", "Main benchmark", "%"]

            for test, (pr, main) in res.items():
                table.append([test, pr, main, get_change(pr, main)])

            table = markdown_table(table, headers)

            comment = textwrap.dedent(
                f"""\
            Benchmarks comparison to {main_branch} branch

            ```
            {table}
            ```

            Happy hacking!
            """
            )

            comment_pr(comment, repository, pr_number, gh_token)
