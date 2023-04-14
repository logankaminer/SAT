import sat
from bs4 import BeautifulSoup
from datetime import datetime

class RobloxAuthenticator():
	def __init__(self):
		self.gid = None
		self.x_csrf_token = None

	@sat.hook(url='https://www.roblox.com/')
	def set_gid(self, response):
		soup = BeautifulSoup(response.text, 'html.parser')

		self.x_csrf_token = soup.find('meta', attrs={'name': 'csrf-token'}).get('data-token')
		self.gid = response.cookies['GuestData'].split('UserID=')[1]

	@sat.hook(url='https://auth.roblox.com/v2/login')
	def get_auth_data(self, response):
		if response.request.method == 'POST':
			print(response.json())

config = sat.Config(
	har_file='roblox_auth.har',
	hook_class=RobloxAuthenticator,
	payload_dict={
		'cvalue': 'USERNAME',
		'password': 'PASSWORD'
	},
	param_dict={
		'lt': datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + 'Z',
		'gid': sat.get_instance_attr('gid'),
	},
	headers_dict={
		'x-csrf-token': sat.get_instance_attr('x_csrf_token')
	},
)

instance = sat.Framework(config)
instance.main()
