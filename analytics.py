import os
import re
import json

class Analyzer():
	def __init__(self, fingerprint_threshold=2) -> None:
		self.fingerprint_threshold = fingerprint_threshold
		self.dict = self.get_json()

	def get_curdir(self):
		path = __file__.split(os.sep)
		return os.sep.join(path[0:len(path)-1])

	def get_json(self):
		_file = open(f'{self.get_curdir()}/analytics.json')
		return json.load(_file)

	def omit_domains(self, _json):
		tracker_count = 0

		for i in range(0, len(_json)):
			modified_json = _json.copy()

			data = _json[i]
			url = data['url']

			for domain in self.dict:
				fingerprint = self.dict[domain]['fingerprint']

				pattern = self.dict[domain]['pattern'] if 'pattern' in self.dict[domain] else None
				if pattern:
					pattern = re.match(pattern, url)
				else:
					continue

				if domain in url and fingerprint >= self.fingerprint_threshold:
					modified_json.pop(i)
					tracker_count += 1

		return modified_json, tracker_count
