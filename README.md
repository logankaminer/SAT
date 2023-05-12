# SAT (Session Automation Toolkit)

The Session Automation Toolkit is an open-source Python framework designed for HTTP request preparation and automation using HAR request archives. SAT includes multiple interfaces to aid in the process, omitting the busy-work of replicating network activity in a browser session.

### Todo ###
- ~~Verify that default values can be overidden with Config parameters~~
- ~~Background requests on a separate thread (images, css, .js files)~~
- Fix fingerprinting logic / implement an optional auto-update for DuckDuckGo's Tracker-Radar data.
- Complete Flask-based session-monitoring dashboard
- Build HAR editor

## Installation ##

The Session Automation Toolkit currently requires local installation and is only available at this repository.

## Usage ##

### Framework Configuration ###

To instantiate an instance of the SAT framework, you need to define a Config object. Compatible parameters are as follows:
| parameter             |  value                                                       |
| --------              |  --------                                                    |
| har_file              |  HAR file path                                               |
| url_dict              |  k:v pairs to map archived urls to custom strings            |
| headers_dict          |  k:v pairs to map archived headers to custom strings         |
| param_dict            |  k:v pairs to map archived request parameters to custom ones |
| payload_dict          |  k:v pairs to map archived request payloads to custom ones   |
| hook_class            |  class reference to handle response objects                  |
| fingerprint_threshold |  unimplemented                                               |
| allow_redirects       |  boolean flag to globally allow/disallow redirects           |
| silent                |  boolean flag to allow/disallow print output                 |


### Framework Behavior ###

Upon instantiation, SAT creates a session object with a randomized Mozilla user-agent and a random DNT (Do Not Track) value. Both of these values can be overidden with Config parameters.

### Framework Execution ###

SAT is built around the Framework class, which is responsible for orchestrating requests and responses. Here's an example of a proper instantiation of the SAT framework:

```python

import sat

config = sat.Config(har_file="path/to/har/file.har")

framework = sat.Framework(config)
framework.main()
```

In the code above, the SAT framework replicates the requests archived in your HAR file, with no alterations in the data or request latency. This is the most bare-bones usage of the SAT framework.

### Hook Classes ###

Perhaps to be renamed in the future, hook classes are currently responsible for handling response objects per each request. Though, in the future, there will be more available actions to perform per request.

```python

import sat

class MyHooks:
    def __init__(self):
        self.target_cookie = 'key'

    def _append_cookie(self, v):
        with open('cookies.txt', 'a') as f:
            f.write(v)

    @sat.hook("http://example.com/login")
    def example_hook(self, response):
        target_cookie = response.cookies[self.target_cookie]
        self._append_cookie(target_cookie)

config = sat.Config(
    har_file="path/to/har/file.har",
    hook_class=MyHook
)

framework = sat.Framework(config)
framework.main()
```

In the above example, we define a hook for http://example.com, which will call an external function that appends a specified cookie value to a file (`cookies.txt`). Upon the execution of any request to http://example.com, the decorated `example_hook` function will run.

### get_instance_attr ###

`sat.get_instance_attr` is a function often used when building Config objects. It retrieves the value of a Hook class attribute by name.

### Handling Multiple Sessions ###

Assume in the context of the following code that the HAR file in-use contains a POST request necessary to authenticate with a service.

```python

import sat
from bs4 import BeautifulSoup

class MyHook:
    def __init__(self):
        self.x_csrf_token = None
        self.target_cookie = 'key'

    def _append_cookie(self, v):
        with open('cookies.txt', 'a') as f:
            f.write(v)

    @sat.hook("http://example.com")
    def get_token(self, response):
        soup = BeautifulSoup(response.text, 'html.parser')
        self.x_csrf_token = soup.find('csrf-token').text

    @sat.hook("http://example.com/login")
    def example_hook(self, response):
        target_cookie = response.cookies[self.target_cookie]
        self._append_cookie(target_cookie)

class SessionHandler:
    def __init__(self, har_file):
        self.config = sat.Config(
            har_file=har_file,
            hook_class=MyHook,
        )
        self.accounts = {
            "test_0": "password",
            "test_1": "password"
        }

    def make_session(self, username, password):
        password = self.accounts[username]
        payload_dict={
            "username": username,
            "password": password
        }

        self.config.payload_dict.update(payload_dict)
        self.config.headers_dict['x-csrf-token'] = sat.get_instance_attr('x_csrf_token')

        framework = sat.Framework(self.config)
        framework.main()
        
        return framework.session

    def gen_sessions(self):
        return (self.make_session(username, self.accounts[username]) for username in self.accounts)

session_handler = SessionHandler(har_file='path/to/har/file')
sessions = session_handler.gen_sessions()
```

Here, we see a more involved implementation of the SAT framework. A `SessionHandler` class has been created that generates mulitple sessions, each authenticating with unique account data. The same hooks are processed for every request in each session.
