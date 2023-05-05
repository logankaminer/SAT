import sat
from bs4 import BeautifulSoup
from datetime import datetime

'''
# README
the following code uses a HAR archive that recorded the network activity occuring when authenticating with roblox.com
the archive begins with the first request to roblox.com. no request was manipuated before automating a new session using
the SAT framework. request-wise, this code looks like a typical user behaving normally, because it is modeled after such.

given that i used roblox as an example, a copy of my solver for the ArkoseLabs "crowd-sound" FunCaptcha is available on this github.
implementing this solver using the SAT framework is possible, though there are no guarentees my solver works anymore.
'''

class RobloxAuth():
	def __init__(self):
		self.gid = None
		self.x_csrf_token = None

	@sat.hook('https://www.roblox.com/')
	def set_gid(self, response):
		soup = BeautifulSoup(response.text, 'html.parser')

		self.x_csrf_token = soup.find('meta', attrs={'name': 'csrf-token'}).get('data-token')
		self.gid = response.cookies['GuestData'].split('UserID=')[1]

	@sat.hook(url='https://auth.roblox.com/v2/login')
	def get_text(self, response):
		if response.request.method != 'POST':
			return

		is_authorized =  True if ('user' in (auth_data := response.json()) and 'id' in auth_data['user']) else False
		if is_authorized:
			print('[*]Authentication Successful ...')
		else:
			print('[*]Authentication FAILED ...')

config = sat.Config(
	har_file=r'path/to/roblox_auth.har',
	hook_class=RobloxAuth,
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
