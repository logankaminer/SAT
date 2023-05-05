import re
import har
import json
import time
import random
import requests
import url_tools
import analytics
import user_agent_randomizer
from datetime import datetime
from collections import defaultdict
import concurrent.futures as futures

hook_dict = {}


def hook(url):
    """
    Hook a request url to obtain resulting response object for all requests made to that url.
    """

    def _hook(func):
        def wrapper(*args, **kwargs):
            global hook_dict
            hook_dict[url] = lambda response: func(*args, response, **kwargs)

        wrapper.hooked = True
        return wrapper

    return _hook


def get_instance_attr(attr: str):
    """
    Retrieve variable defined in your hook class's __init__ function outside of the hook class.
    """
    return get_instance_attr, attr


class Request:
    def __init__(self, _json, latency, index) -> None:
        global hook_dict

        self.index = index
        self.latency = latency
        self.url = _json["url"]
        self.method = _json["method"]
        self.headers = _json["headers"]
        self.status_code = _json["status_code"]
        self.query_dict = _json["query_string"]

        self.payload = None
        self.content_type = None
        self.is_auxiliary = (
            True
            if self._is_aux_req(self.url) and (self.url not in hook_dict)
            else False
        )

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
            r"\S*\.(?:js|png|woff2|ttf|jpg|ogg|mp3|mp4|gif|css|svg)",
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
        fingerprint_threshold=None,
        silent=False,
    ):
        self.silent = silent
        self.har_file = har_file
        self.url_dict = url_dict
        self.param_dict = param_dict
        self.hook_class = hook_class
        self.headers_dict = headers_dict
        self.payload_dict = payload_dict
        self.allow_redirects = allow_redirects
        self.fingerprint_threshold = fingerprint_threshold


class Framework:
    """
    Session-Request Automation Tool framework.
    """

    def __init__(self, Config) -> None:
        self.url_dict = Config.url_dict
        self.hook_class = Config.hook_class()
        self.param_dict = Config.param_dict
        self.payload_dict = Config.payload_dict
        self.allow_redirects = Config.allow_redirects
        self.silent = Config.silent

        self.default_headers_dict = defaultdict(lambda: self.get_dnt())
        self.headers_dict = (
            (Config.headers_dict | self.default_headers_dict)
            if Config.headers_dict
            else self.default_headers_dict
        )

        self.session = self.get_session()
        self.request_reference = {}

        if Config.fingerprint_threshold:
            Analyzer = analytics.Analyzer(
                fingerprint_threshold=Config.fingerprint_threshold
            )
            self.reference_data, self.tracker_count = Analyzer.omit_domains(
                har.export(Config.har_file)
            )
        else:
            self.reference_data, self.tracker_count = (
                har.export(Config.har_file),
                None,
            )

        self._hook_urls()

    def _wrap_color(self, _str, color_esc):
        reset = "\033[0;0m"
        return f"[{color_esc}{_str}{reset}]"

    def _get_stats(self, request: Request):
        global hook_dict

        latency = f"{request.latency:.4f}s"
        progress = f"{request.index + 1}/{len(self.reference_data) - 1}"

        latency = self._wrap_color(latency, "\033[0;32m")
        progress = self._wrap_color(progress, "\033[1;36m")

        url_color = str()
        if request.is_auxiliary:
            url_color = "\033[33m"
        elif request.url in hook_dict:
            url_color = "\033[1;34m"

        stats = f'{(f"{latency} ") if request.latency > 0 else str()}{progress}'
        output = f"{request.method}: {self._wrap_color(request.url, url_color)} {stats}"

        return output

    def _hook_urls(self):
        global hook_dict

        functions = [
            actual
            for attr in dir(self.hook_class)
            if not (attr.startswith("__"))
            and callable(actual := getattr(self.hook_class, attr))
        ]
        for func in functions:
            if getattr(func, "hooked", False):
                func()

    def get_dnt(self):
        self.dnt = random.choice(["0", "1", "null"])
        return self.dnt

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
        request = Request(_json, latency, index)

        return request

    def hook_request(self, request: Request):
        request.url = url_tools.modify_path(request.url, self.url_dict)
        request.headers = url_tools.modify_dict(
            request.headers, self.headers_dict, hook_class=self.hook_class
        )

        if len(request.query_dict) >= 1:
            args = [request.query_dict, self.param_dict, self.hook_class]
            request.url = url_tools.modify_qs(request.url, *args)

        if request.payload:
            request.payload = url_tools.modify_dict(
                request.payload, self.payload_dict, hook_class=self.hook_class
            )

        return request

    def hook_response(self, response: requests.Response):
        global hook_dict
        if response.request.url in hook_dict:
            hook_dict[response.request.url](response)  # run decorated module function

    def make_request(self, request_index):
        request = self.hook_request(self.request_reference[request_index])

        if not self.silent:
            output = self._get_stats(request)
            print(output)

        url = request.url
        headers = request.headers
        payload = request.payload

        self.session.headers = headers

        request_func_dict = {
            "GET": lambda: self.session.get(url, allow_redirects=self.allow_redirects),
            "OPTIONS": lambda: self.session.options(
                url, allow_redirects=self.allow_redirects
            ),
            "POST": lambda: self.session.post(
                url, json=payload, allow_redirects=self.allow_redirects
            )
            if payload and "application/json" in request.content_type
            else (
                self.session.post(url, allow_redirects=self.allow_redirects)
                if not payload
                else self.session.post(
                    url, data=request.payload, allow_redirects=self.allow_redirects
                )
            ),
        }

        response = request_func_dict[request.method]()
        if self.hook_class:
            self.hook_response(response)

        return response

    def main(self):
        st_time = time.time()
        bg_executor = futures.ThreadPoolExecutor(max_workers=1)

        for i in range(0, len(self.reference_data)):
            request = self.get_next_request(index=i)
            self.request_reference[i] = request

            if not request.is_auxiliary:
                self.make_request(i)
                time.sleep(request.latency)
            else:
                future = bg_executor.submit(self.make_request, i)
                future.done()

        bg_executor.shutdown()
        print(f"session duration: {time.time() - st_time:.1f}s")
