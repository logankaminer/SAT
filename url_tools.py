import urllib.parse as parse

def _get_final_val(val, hook_class=None):
	if hook_class and type(val) == tuple:
		func, attr = val
		if callable(func) and func.__name__ == 'get_instance_attr':
			return getattr(hook_class, attr)
	else:
		return (val if not callable(val) else val())

def modify_path(url: str, url_dict: dict):
	parse_result = parse.urlparse(url) #TODO: what if url path has "/" in it?
	path = parse_result.path.split('/')

	for loc in path:
		if loc != str() and loc in url_dict:
			new_loc = _get_final_val(url_dict[loc])
			loc_i = path.index(loc)

			path.pop(loc_i)
			path.insert(loc_i, new_loc)

	path = '/'.join(path)
	url = f'{parse_result.scheme}://{parse_result.netloc}{path}'

	return url

def modify_dict(input_dict: dict, substitution_dict: dict, hook_class=None):
	for k in input_dict:
		if k in substitution_dict:
			input_dict[k] = _get_final_val(substitution_dict[k], hook_class)

	return input_dict

# def modify_qs(url: str, param_dict: dict):
# 	qs_dict = parse.parse_qs(url)
# 	first_k, v = list(qs_dict.items())[0]

# 	param_index = first_k.index('?') + 1
# 	first_param = first_k[param_index:len(first_k)]

# 	qs_dict.pop(first_k)
# 	qs_dict[first_param] = v

# 	for param in qs_dict:
# 		if param in param_dict:
# 			query_val = ','.join(qs_dict[param]) #TODO: hardcoding comma-separated vals
# 			new_val = _get_final_val(param_dict[param])

# 			url = url.replace(query_val, new_val)

# 	return url
