# sat (Session Automation Tool)

Session Automation Tool is a Python framework designed to replicate browser sessions from HAR request archives.

## Usage ##

SAT is built around the Framework class, which is responsible for orchestrating requests and responses. Here's an example of how you can use the framework to automate sessions:

```python

import sat

class MyHook:
    def __init__(self):
        self.cookies = []

    @sat.hook("http://example.com")
    def example_hook(self, response):
        self.cookies.extend(list(response.cookies.values()))

config = sat.Config(
    har_file="path/to/har/file.har",
    hook_class=MyHook
)

framework = sat.Framework(config)
framework.execute()
```

In the above example, we define a hook for http://example.com, which will print out the response text when called. We then create a Config object, which specifies the path to the HAR file, the hook class to use, and a silent flag to suppress output. Finally, we create an instance of the Framework class using our Config object and execute the session with `framework.execute()`.

## Hooks ##

Hooks are defined using the `@sat.hook decorator`. When a request is made to a URL that has a hook defined, the hook function is called with the resulting response object.

```python

@sat.hook("http://example.com")
def my_hook(response):
    print(response.text)
```

In the above example, we define a hook for http://example.com that simply prints out the response text. When a request is made to http://example.com, the `my_hook` function will be called with the response object.

## Note from the Author ##

I lazily generated this README using ChatGPT4.
