from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from prometheus_client.exposition import basic_auth_handler


class PrometheusServer:
    def __init__(self, **options):
        self.url = options["url"]
        self.username = options.get("username")
        self.password = options.get("password")

    def _auth_handler(self, url, method, timeout, headers, data):
        return basic_auth_handler(
            url, method, timeout, headers, data, self.username, self.password
        )

    def mean(self, branch, benchmark, field):
        raise NotImplementedError

    def send_measure(self, branch, benchmark, measure, check_previous=None):
        print(f"Sending metrics to {self.url}")

        registry = CollectorRegistry()
        g = Gauge(benchmark, benchmark, ["name", "branch"], registry=registry)

        for field, value in measure.items():
            g = Gauge("my_inprogress_requests", "Description of gauge")
            g.labels(name=field, branch=branch).set(value)

        if self.username is not None:
            auth_handler = self._auth_handler
        else:
            auth_handler = None

        push_to_gateway(self.url, job="batch", registry=registry, handler=auth_handler)
