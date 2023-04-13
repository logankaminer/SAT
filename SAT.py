import re
import har
import json
import time
import random
import requests
import url_tools
import analytics
import urllib.parse
import user_agent_randomizer
from datetime import datetime
from collections import defaultdict
import concurrent.futures as futures

response = None
hook_dict = {}


def hook(url):
    """
    Hook a request url to obtain resulting response object for all requests made to that url.
    """

    def _hook(func):
        def wrapped(*args):
            hook_dict[url] = lambda response: func(*args, response)

        wrapped.hooked = True
        return wrapped

    return _hook


def get_instance_attr(attr: str):
    """
    Retrieve variable defined in your hook class's __init__ function outside of the hook class.
    """
    return get_instance_attr, attr


class Request:
    def __init__(self, _json, latency) -> None:
        self.latency = latency
        self.url = _json["url"]
        self.method = _json["method"]
        self.headers = _json["headers"]
        self.status_code = _json["status_code"]
        self.query_dict = _json["query_string"]

        self.payload = None
        self.content_type = None
        self.is_auxiliary = self._is_aux_req(self.url) # could bug with modifying url after-the-fact

        if self.is_auxiliary:
            self.latency = 0

        if "postData" in _json:
            post_data = (
                json.loads(_json["postData"])
                if type(_json["postData"]) != dict
                else _json["postData"]
            )
            self.content_type = post_data["mimeType"]

            params = (
                post_data["params"]
                if "application/json" not in self.content_type
                else None
            )
            text = json.loads(post_data["text"]) if not params else None

            if type(text) == list:
                text = text[0]
            self.payload = params or text

        self.format_request()

    def _is_aux_req(self, url):
        patterns = [
            r"\S*\.(?:js|png|woff2|ttf|jpg|ogg|mp3|mp4|gif|css)",
            r"^[-a-zA-Z0-9!$%^&*()_+|~=`{}\[\]:\";'<>?,.\/]{32,64}$",
        ]

        matches = [
            (True if re.compile(pattern).match(url) else False) for pattern in patterns
        ]
        return max(matches)

    def _zip_dict_arr(self, _dict):
        return {name: value for (name, value) in [d.values() for d in _dict]}

    def format_request(self):
        self.headers = self._zip_dict_arr(self.headers)
        self.payload = (
            self._zip_dict_arr(self.payload)
            if self.payload and type(self.payload) != dict
            else self.payload
        )
        self.query_dict = (
            self._zip_dict_arr(self.query_dict) if len(self.query_dict) > 0 else {}
        )

        if "cookie" in self.headers:
            self.headers.pop("cookie")


class Config:
    def __init__(
        self,
        har_file,
        url_dict={},
        headers_dict={},
        param_dict={},
        payload_dict={},
        hook_class=None,
        allow_redirects=True,
        _async_file_reqs=False,
        fingerprint_threshold=None,
    ):
        self.har_file = har_file
        self.url_dict = url_dict
        self.param_dict = param_dict
        self.hook_class = hook_class
        self.headers_dict = headers_dict
        self.payload_dict = payload_dict
        self.allow_redirects = allow_redirects
        self._async_file_reqs = _async_file_reqs
        self.fingerprint_threshold = fingerprint_threshold


class SATFramework:
    """
    Session-Request Automation Tool framework.
    """

    def __init__(self, Config) -> None:
        self.url_dict = Config.url_dict
        self.hook_class = Config.hook_class()
        self.param_dict = Config.param_dict
        self.payload_dict = Config.payload_dict
        self.allow_redirects = Config.allow_redirects
        self._async_file_reqs = Config._async_file_reqs

        if Config.fingerprint_threshold:
            Analyzer = analytics.Analyzer(
                fingerprint_threshold=Config.fingerprint_threshold
            )
            self.reference_data, self.tracker_count = Analyzer.omit_domains(
                har.export(Config.har_file)
            )
        else:
            self.reference_data, self.tracker_count = (har.export(Config.har_file), 0)

        self.default_headers_dict = defaultdict(lambda: self.get_dnt())
        self.headers_dict = (
            (Config.headers_dict | self.default_headers_dict)
            if Config.headers_dict
            else self.default_headers_dict
        )

        self.session = self.get_session()
        self.request = self.get_next_request(index=0)

        self.start_time = time.time()
        self.elapsed_time = None
        self.used_bandwidth = 0

    def _wrap_color(self, _str, color_esc):
        reset = "\033[0;0m"
        return f"[{color_esc}{_str}{reset}]"

    def _get_stats(self, request_index):
        latency = f"{self.request.latency:.4f}s"
        progress = f"{request_index}/{len(self.reference_data) - 1}"

        latency = self._wrap_color(latency, "\033[0;32m")
        progress = self._wrap_color(progress, "\033[1;36m")
        url_color = str()

        if self.request.is_auxiliary:
            url_color = "\033[33m"

        stats = f'{(f"{latency} ") if self.request.latency > 0 else str()}{progress}'
        output = f"{self.request.method}: {self._wrap_color(self.request.url, url_color)} {stats}"

        return output

    def _get_dict_size(self, headers):
        return sum(len(key) + len(value) for key, value in headers.items())

    def get_dnt(self):
        self.dnt = random.choice(["0", "1", "null"])
        return self.dnt

    def get_request_size(self):
        request_line_size = len(self.request.method) + len(self.request.url)
        request_size = request_line_size + self._get_dict_size(self.request.headers)

        return request_size

    def get_response_size(self, response):
        response_content_size = len(response.content.decode("utf-8", errors="ignore"))
        response_size = response_content_size + self._get_dict_size(
            self.request.headers
        )

        return response_size

    def get_session(self):
        session = requests.Session()
        session.headers["User-Agent"] = user_agent_randomizer.get_random()

        return session

    def get_next_request(self, index):
        _json = self.reference_data[index]
        next_req = (
            self.reference_data[index + 1]
            if index != (len(self.reference_data) - 1)
            else _json
        )

        latency = (
            datetime.strptime(next_req["startedDateTime"][:-6], "%Y-%m-%dT%H:%M:%S.%f")
            - datetime.strptime(_json["startedDateTime"][:-6], "%Y-%m-%dT%H:%M:%S.%f")
        ).microseconds / 100000
        latency += random.choice((random.uniform(-0.05, 0.05), -(latency / 2)))

        latency = 0 if latency < 0 else latency
        request = Request(_json, latency)

        return request

    def hook_request(self, request: Request):
        request.url = url_tools.modify_path(request.url, self.url_dict)
        request.headers = url_tools.modify_dict(
            request.headers, self.headers_dict, hook_class=self.hook_class
        )

        if len(request.query_dict) >= 1:
            query_string = urllib.parse.urlencode(
                url_tools.modify_dict(
                    request.query_dict, self.param_dict, hook_class=self.hook_class
                )
            )

            # FIXME: could bug out with "?"s in url
            request.url = f'{request.url.split("?")[0]}?{query_string}'

        if request.payload:
            request.payload = url_tools.modify_dict(
                request.payload, self.payload_dict, hook_class=self.hook_class
            )

        return request

    def hook_response(self, response: requests.Response):
        if self.hook_class:
            global hook_dict

            functions = [
                getattr(self.hook_class, attr)
                for attr in dir(self.hook_class)
                if not (attr.startswith("__"))
                and callable(getattr(self.hook_class, attr))
            ]
            for func in functions:
                if getattr(func, "hooked", False):
                    func()

            if response.request.url in hook_dict:
                hook_dict[response.request.url](response) # run decorated module function

            self.elapsed_time = int(time.time() - self.start_time)
            self.used_bandwidth += self.get_request_size() + self.get_response_size(
                response
            )

    def make_request(self):
        self.request = self.hook_request(self.request)

        url = self.request.url
        headers = self.request.headers
        payload = self.request.payload

        self.session.headers = headers

        request_func_dict = {
            "GET": lambda: self.session.get(url, allow_redirects=self.allow_redirects),
            "OPTIONS": lambda: self.session.options(
                url, allow_redirects=self.allow_redirects
            ),
            "POST": lambda: self.session.post(
                url, json=payload, allow_redirects=self.allow_redirects
            )
            if payload and "application/json" in self.request.content_type
            else (
                self.session.post(url, allow_redirects=self.allow_redirects)
                if not payload
                else self.session.post(
                    url, data=self.request.payload, allow_redirects=self.allow_redirects
                )
            ),
        }

        response = request_func_dict[self.request.method]()
        self.hook_response(response) # running this in background thread could pose a problem

        return response

    def main(self):
        global response

        executor = futures.ThreadPoolExecutor(max_workers=1)
        bg_executor = futures.ThreadPoolExecutor(max_workers=1)

        for i in range(1, len(self.reference_data)):
            output = self._get_stats(i)
            print(output)

            if not self.request.is_auxiliary:
                future = executor.submit(self.make_request)
                response = future.result()

                time.sleep(self.request.latency)
            else:
                future = bg_executor.submit(self.make_request)
                response = future.result()

            self.request = self.get_next_request(i)
