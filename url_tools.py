import urllib.parse as parse


def _get_final_val(val, hook_class=None):
    if hook_class and type(val) == tuple:
        func, attr = val
        if callable(func) and func.__name__ == "get_instance_attr":
            return getattr(hook_class, attr)
    else:
        return val if not callable(val) else val()


def modify_path(url: str, url_dict: dict):
    parse_result = parse.urlparse(url)  # TODO: what if url path has "/" in it?
    path = parse_result.path.split("/")

    for loc in path:
        if loc != str() and loc in url_dict:
            new_loc = _get_final_val(url_dict[loc])
            loc_i = path.index(loc)

            path.pop(loc_i)
            path.insert(loc_i, new_loc)

    path = "/".join(path)
    url = f"{parse_result.scheme}://{parse_result.netloc}{path}"

    return url


def modify_dict(input_dict: dict, substitution_dict: dict, hook_class=None):
    for k in input_dict:
        if k in substitution_dict:
            input_dict[k] = _get_final_val(substitution_dict[k], hook_class)

    return input_dict


def modify_qs(url, query_dict, param_dict, hook_class):
    query_string = parse.urlencode(
        modify_dict(query_dict, param_dict, hook_class)
    )

    return f'{url.split("?")[0]}?{query_string}'
