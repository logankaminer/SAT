import sys
import json

_json = []

#TODO: file support. if files are sent as payload, are they hashed? how are we re-sending the files?

def export(path):
	with open(path, 'rb') as har:
		data = json.load(har)

		if 'log' not in data:
			print('HAR file corrupted or in invalid format - cannot find "log" in data.')
			sys.exit(0)
		else:
			data = data['log']
			if 'entries' not in data:
				print('HAR file corrupted or in invalid format - cannot find "entries" in data.')
				sys.exit(0)
			else:
				data = data['entries']

		for entry in data:
			data_entry = {}

			request = entry['request']
			response = entry['response']

			data_entry['url'] = request['url']
			data_entry['method'] = request['method']
			data_entry['headers'] = request['headers']
			data_entry['cookies'] = request['cookies']
			data_entry['query_string'] = request['queryString']

			data_entry['status_code'] = response['status']
			data_entry['startedDateTime'] = entry['startedDateTime']

			if 'postData' in request:
				data_entry['postData'] = request['postData']

			_json.append(data_entry)

	return _json
