#!/usr/bin/env python3
# Timetable [v19522]
from re import match
from os import mkdir
from tqdm import tqdm
from icecream import ic
from copy import deepcopy
from os.path import basename
from bs4 import BeautifulSoup
from socket import gethostbyname
from prettytable import PrettyTable
from colorama import Fore, Back, Style
from base64 import b64encode, b64decode
from datetime import datetime, timedelta
from os.path import realpath, dirname, join
from simplejson.errors import JSONDecodeError
import sys, json, requests, configparser

class DeclareTokens:
	def __init__(self):
		self.refresh_token = None
		self.access_token = None

	def update_refresh(self, refresh_token):
		self.refresh_token = refresh_token

	def update_access(self, access_token):
		self.access_token = access_token

	def export_json(self):
		json_object = {"refresh": tokens.refresh_token.decode('utf-8'), "access": tokens.access_token.decode('utf-8')}

		with open(envfile, 'w+') as text_file:
			text_file.write(json.dumps(json_object))

	def try_load_json(self):
		try:
			with open(envfile, 'r') as text_file:
				global json_object
				json_object = json.load(text_file)
				tokens.update_refresh(json_object['refresh'])
				tokens.update_access(json_object['access'])
		except FileNotFoundError:
			raise Unauthorized
		except json.decoder.JSONDecodeError:
			raise Unauthorized

class DeclareHeaders:
	def __init__(self):
		self.generic_header = {
		"authority": platform_hostname,
		"scheme": "https",
		"accept": "application/json, text/plain, */*",
		"accept-encoding": "gzip, deflate, br",
		"accept-language": "it",
		"dnt": "1",
		"connection": 'keep-alive',
		"origin": "https://{}".format(platform_hostname),
		"referer": "https://{}/ticket-dashboard".format(platform_hostname),
		"sec-fetch-dest": "empty",
		"sec-fetch-mode": "cors",
		"sec-fetch-site": "same-origin",
		"user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"
		}

	def generate_platform_login(self):
		self.platform_login = deepcopy(self.generic_header)
		self.platform_login["method"] = "POST"
		self.platform_login["path"] = "/api/token-auth/"
		self.platform_login["referer"] = "https://{}/auth/login".format(platform_hostname)
		self.platform_login.pop("connection")

	def generate_refresh_token(self):
		self.refresh_token = deepcopy(self.generic_header)
		self.refresh_token["path"] = "/api/token-auth/"
		self.refresh_token["referer"] = "https://{}/auth/login".format(platform_hostname)
		self.refresh_token.pop("authority")
		self.refresh_token.pop("scheme")
		self.refresh_token.pop("sec-fetch-dest")
		self.refresh_token.pop("sec-fetch-mode")
		self.refresh_token.pop("sec-fetch-site")

	def generate_get_counters(self):
		self.get_counters = deepcopy(self.generic_header)
		self.get_counters["authorization"] = "JWT {}".format(b64decode(tokens.access_token).decode('utf-8'))
		self.get_counters["host"] = platform_hostname

	def generate_search_assistances(self, worker_id, date):
		self._search_assistances = deepcopy(self.generic_header)
		self._search_assistances["method"] = "GET"
		self._search_assistances["authorization"] = "JWT {}".format(b64decode(tokens.access_token).decode('utf-8'))
		self._search_assistances["path"] = "/api/v1/ticket/manager/assistance/?per_page=100&page=1&filter__worker__in={}&order_by__=date_begin&filter__date_begin__date={}".format(worker_id, date)

class LoginError(Exception):
	"""Raised when providing wrong credentials at login"""
	pass

class PageError(Exception):
	"""Raised when the request status code is not 2xx"""
	pass

class Unauthorized(Exception):
	"""Raised when the access token is expired"""
	pass

class ConsoleColor:
	# Color
	BLACK = '\033[90m'
	RED = '\033[91m'
	GREEN = '\033[92m'
	YELLOW = '\033[93m'
	BLUE = '\033[94m'
	PURPLE = '\033[95m'
	CYAN = '\033[96m'
	GRAY = '\033[97m'

	# Style
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'

	# BackgroundColor
	BgBLACK = '\033[40m'
	BgRED = '\033[41m'
	BgGREEN = '\033[42m'
	BgORANGE = '\033[43m'
	BgBLUE = '\033[44m'
	BgPURPLE = '\033[45m'
	BgCYAN = '\033[46m'
	BgGRAY = '\033[47m'

	# End
	END = '\033[0m'

filename = basename(sys.argv[0])
sys_path = __file__.replace(filename, '')

configParser = configparser.RawConfigParser()
configFilePath = '{}{}'.format(sys_path, 'timetable.conf')
configParser.read(configFilePath)

platform_hostname = configParser.get('Platform', 'platformUrl')

worker_id = configParser.get('Worker Details', 'workerID')
worker_name = configParser.get('Worker Details', 'workerName')
worker_area = configParser.get('Worker Details', 'workerArea')
worker_username = b64encode(configParser.get('Worker Credentials', 'workerUsername').encode('utf-8'))
worker_password = b64encode(configParser.get('Worker Credentials', 'workerPassword').encode('utf-8'))

manager_id = configParser.get('Manager Details', 'managerID')
manager_name = configParser.get('Manager Details', 'managerName')

envfile = join(dirname(__file__), '.timetable-env.json')

def x_print_help():
	print()
	print(f"## {Style.BRIGHT}Timetable's Legend{Style.RESET_ALL} ##")
	print()
	print(f'# {Style.BRIGHT}{Fore.GREEN}1st argument{Style.RESET_ALL} = Year (4 digits)' )
	print(f'# {Style.BRIGHT}{Fore.GREEN}2nd argument{Style.RESET_ALL} = Month (Without "0" prefix)')
	print(f'# {Style.BRIGHT}{Fore.YELLOW}Optional "weekends" argument"{Style.RESET_ALL} = Show weekends in table')
	print()
	print(f"{Style.BRIGHT}# Example A:{Style.RESET_ALL} ./timemap.py 2022 6")
	print(f"{Style.BRIGHT}# Example B:{Style.RESET_ALL} ./timemap.py 2022 11 weekends")
	exit(0)

def request_validator(status_code, *request_json):
	if status_code == 401:
		raise Unauthorized
	elif match(r"4[0-9][0-9]", str(status_code)):
		print_something('RED', 'Page thrown an error! --> https.status_code: ', status_code)
		ic(status_code)
		if request_json: ic(request_json)
		raise PageError

def _init_validate_tokens():
	while True:
		try:
			print('Connecting to: {} ({})...'.format(platform_hostname, gethostbyname(platform_hostname)))
			tokens.try_load_json()
			status_code = get_counters('validate')
			request_validator(status_code)
			break
		except requests.exceptions.ConnectionError:
			print_something('YELLOW', 'Platform unavailable!, check your network settings')
			exit(1)
		except Unauthorized:
			print_something('YELLOW', 'Requesting new tokens')
			platform_login()
			return
		except PageError:
			print_something('RED', 'Error while validating tokens')
			exit(1)

	print_something('GREEN', 'Tokens OK')

def do_refresh_token():
	def launch_request():
		headers.generate_refresh_token()
		url = "https://{}/api/token-refresh/".format(platform_hostname)

		data = {
		"refresh": tokens.refresh_token
		}

		req = s.post(url, headers=headers.refresh_token, data=data)
		return req.status_code, req.json()

	print_something('YELLOW', 'Access token expired')

	while True:
		try:
			status_code, request_json = launch_request()
			request_validator(status_code, request_json)
			break
		except Unauthorized: # Must launch platform_login() again
			print_something('YELLOW', 'Re-authenticating')
			platform_login()
			return
		except PageError:
			ic(status_code)
			ic(request_json)
			if not tokens.refresh_token:
				print_something('RED', 'Valid token missing!, performing initial login')
				_init_validate_tokens()
			return

	tokens.update_refresh(request_json['refresh'])
	tokens.update_access(request_json['access'])

	print_something('GREEN', 'Token refreshed')

def platform_login():
	def launch_request():
		headers.generate_platform_login()
		url = "https://{}/api/token-auth/".format(platform_hostname)

		data = {
		"email" : b64decode(worker_username).decode('utf-8'),
		"password" : b64decode(worker_password).decode('utf-8')
		}

		req = s.post(url, headers=headers.platform_login, data=data)
		return req.status_code, req.json()

	while True:
		try:
			global request_json
			status_code, request_json = launch_request()
			request_validator(status_code, request_json)
			break
		except PageError:
			exit(1)


	tokens.update_refresh(b64encode(request_json['refresh'].encode('utf-8')))
	tokens.update_access(b64encode(request_json['access'].encode('utf-8')))
	tokens.export_json()

	print_something('GREEN', 'Logged')

def get_counters(*validate):
	def launch_request():
		headers.generate_get_counters()
		url = "https://{}/api/v1/ticket/manager/ticket/get-counters/?".format(platform_hostname)

		req = s.get(url, headers=headers.get_counters, timeout=5)
		return req.status_code, req.json()

	if validate:
		status_code, _ = launch_request()
		return status_code

	while True:
		try:
			status_code, request_json = launch_request()
			request_validator(status_code, request_json)
			break
		except Unauthorized:
			ic(status_code)
			ic(request_json)
			do_refresh_token()
		except PageError:
			print_something('RED', 'Error while getting counters')
			exit(1)

	ic(status_code)
	ic(request_json)

def print_something(COLORNAME, text, *var):
	def print_func(arg):
		if type(COLORNAME) == tuple:
			if len(COLORNAME) == 3:
				print(arg)
		else:
			print()
			print(arg)

	if type(COLORNAME) == tuple: # With variable and different colors
		if len(COLORNAME) == 2:
			print_func(f'{Style.BRIGHT}{getattr(Fore, COLORNAME[0])}{text}{getattr(Fore, COLORNAME[1])}{var[0]}{Style.RESET_ALL}')
		elif len(COLORNAME) == 3:
			if COLORNAME[2] == 'NOBRIGHT':
				print_func(f'{Style.BRIGHT}{getattr(Fore, COLORNAME[0])}{text}{Style.NORMAL}{getattr(Fore, COLORNAME[1])}{var[0]}{Style.RESET_ALL}')
			else: print_func('Unrecognized 3rd color arguments!')
	elif var: # With variable and same color
		print_func(f'{Style.BRIGHT}{getattr(Fore, COLORNAME)}{text}{var[0]}{Style.RESET_ALL}')
	else: # Just text
		print_func(f'{Style.BRIGHT}{getattr(Fore, COLORNAME)}{text}{Style.RESET_ALL}')

def timetable(year, month, *shows_weekends):
	date_list = []
	holidays_list = []
	month_worktime = []

	def format_timedelta(td):
		minutes, seconds = divmod(td.seconds + td.days * 86400, 60)
		hours, minutes = divmod(minutes, 60)
		return '{:d}:{:02d}:{:02d}'.format(hours, minutes, seconds)

	def business_days(*shows_weekends):
		from calendar import monthrange
		import datetime

		days = monthrange(year, month)[1]
		for day in range(1,days+1):
			fday = datetime.date(year,month,day)
			sday = str(datetime.date(year,month,day))
			if shows_weekends:
				date_list.append(fday)
				if fday.weekday()>4: holidays_list.append(fday)
			else:
				if fday.weekday()<5: date_list.append(fday)

	row_color = {}
	row_color[0] = 'BLUE'
	row_color[1] = 'RED'
	row_color[2] = 'RED'
	row_color[3] = 'RED'
	row_color[4] = 'RED'
	row_color[5] = 'YELLOW'
	row_color[6] = 'YELLOW'
	row_color[7] = 'GREEN'

	worktime_table = PrettyTable()

	if shows_weekends:
		if shows_weekends[0]:
			business_days(shows_weekends)
			worktime_table.field_names = ['Day (Weekends in purple)', 'Total Worktime']
		else:
			business_days()
			worktime_table.field_names = ['Day', 'Total Worktime']

	for day in tqdm(date_list, desc="Loading.."):
		if day in holidays_list: fday = ConsoleColor.PURPLE + str(day) + ConsoleColor.END
		else: fday = day

		value = _search_assistances(day, False)
		month_worktime.append(value)

		if int(str(value)[0]) > 6: color = row_color[7]
		else: color = row_color[int(str(value)[0])]

		worktime_table.add_row([fday, getattr(ConsoleColor, color) + str(value) + ConsoleColor.END])

	print()
	print(worktime_table)
	print_something('WHITE', "Month Worktime: {}".format(format_timedelta(sum(month_worktime, timedelta()))))

def _search_assistances(date, do_print):
	def launch_request(worker_id, date):
		headers.generate_search_assistances(worker_id, date)
		url = "https://{}/api/v1/ticket/manager/assistance/?per_page=100&page=1&filter__worker__in={}&order_by__=date_begin&filter__date_begin__date={}".format(platform_hostname, worker_id, date)

		req = s.get(url, headers=headers._search_assistances)
		return req.status_code, req.json()

	while True:
		try:
			status_code, request_json = launch_request(worker_id, date)
			request_validator(status_code, request_json)
			break
		except Unauthorized:
			do_refresh_token()
		except PageError:
			print_something('RED', "Error while searching assistances")
			exit(1)

	lenght_list = []
	for item in request_json['results']:
		date_begin = datetime.strptime(item['date_begin'][:-6], '%Y-%m-%dT%H:%M:%S').strftime('%d/%m/%Y %H:%M:%S')
		date_end = datetime.strptime(item['date_end'][:-6], '%Y-%m-%dT%H:%M:%S').strftime('%d/%m/%Y %H:%M:%S')
		assistance_lenght = datetime.strptime(item['date_end'][:-6], '%Y-%m-%dT%H:%M:%S') - datetime.strptime(item['date_begin'][:-6], '%Y-%m-%dT%H:%M:%S')

		lenght_list.append(assistance_lenght)

		def xprint():
			print_something('YELLOW', "Description: {}".format(BeautifulSoup(item['job_description'], 'lxml').text))
			print("Start date : {}".format(date_begin))
			print("End date   : {}".format(date_end))
			print("Ticket ID: {}, Customer: {}, Description: {}".format(item['ticket']['id'], item['ticket']['organization']['name'], item['ticket']['title']))
			print("Assistance ID: {}".format(item['id']))
			print_something('CYAN', "Lenght: {}".format(assistance_lenght))

		if do_print:
			xprint()

	if do_print:
		print_something('RED', "Day Worktime: {}".format(sum(lenght_list, timedelta())))
	else:
		return sum(lenght_list, timedelta())

def launchtable():
	year = int(sys.argv[1])
	month = int(sys.argv[2])

	if len(sys.argv) > 3:
		if sys.argv[3] == 'weekends': shows_weekends = True
		else:
			print_something('RED', 'Unrecognized optional argument, you can only use "weekends"')
			exit(1)
	else: shows_weekends = False

	timetable(year, month, shows_weekends)

###################
tokens = DeclareTokens()
headers = DeclareHeaders()

s = requests.Session()

def session_begin(action, login, *args):
	if login: _init_validate_tokens()
	action(*args)

#### BEGIN
if not sys.flags.interactive:
	if len(sys.argv) == 1:
		x_print_help()
	elif sys.argv[1] == 'help': # Show help
		x_print_help()
	else:
		session_begin(launchtable, 1)
