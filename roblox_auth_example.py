import SAT
from bs4 import BeautifulSoup
from datetime import datetime

class RobloxAuth():
	def __init__(self):
		self.gid = None
		self.x_csrf_token = None

	@SAT.hook(url='https://www.roblox.com/')
	def set_gid(self, response):
		soup = BeautifulSoup(response.text, 'html.parser')

		self.x_csrf_token = soup.find('meta', attrs={'name': 'csrf-token'}).get('data-token')
		self.gid = response.cookies['GuestData'].split('UserID=')[1]

	@SAT.hook(url='https://auth.roblox.com/v2/login')
	def get_text(self, response):
		if response.request.method != 'POST':
			return

		auth_data = response.json()
		if 'isBanned' in auth_data:
			print('[*]Authentication Successful ...')
		else:
			print('[*]Authentication FAILED ...')

config = SAT.Config(
	har_file=None,
	hook_class=RobloxAuth,
	payload_dict={
		'cvalue': 'USERNAME',
		'password': 'PASSWORD'
	},
	param_dict={
		'lt': datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + 'Z',
		'gid': SAT.get_instance_attr('gid'),
	},
	headers_dict={
		'x-csrf-token': SAT.get_instance_attr('x_csrf_token')
	}
)

instance = SAT.SATFramework(config)
instance.main()

print(instance.session.cookies)
