#!/usr/bin/env python3
APP_NAME='Timetable'
APP_VERSION='v10822'

import sys, json, requests, configparser
from sys import exit
from re import match
from pathlib import Path
from tqdm import tqdm
from copy import deepcopy
from bs4 import BeautifulSoup
from socket import gethostbyname
from prettytable import PrettyTable
from colorama import Fore, Back, Style
from base64 import b64encode, b64decode
from os import mkdir, system, name, path
from datetime import datetime, timedelta
from simplejson.errors import JSONDecodeError
from os.path import realpath, dirname, join, basename, abspath

class ExecutionType:
	def __init__(self):
		self.value = None

class ManageCredentials:
	def __init__(self):
		self.username = None
		self.password = None

	def update_username(self, username):
		self.username = username

	def update_password(self, password):
		self.password = password

	def export_json(self):
		json_object = {"1": self.username.decode('utf-8'), "2": self.password.decode('utf-8')}

		with open(env_files.credentials_path, 'w+') as text_file:
			text_file.write(json.dumps(json_object))

	def try_load_json(self):
		try:
			with open(env_files.credentials_path, 'r') as text_file:
				json_object = json.load(text_file)
				self.update_username(json_object['1'])
				self.update_password(json_object['2'])
		except FileNotFoundError:
			raise Unauthorized
		except json.decoder.JSONDecodeError:
			raise Unauthorized

class DeclareTokens:
	def __init__(self):
		self.refresh_token = None
		self.access_token = None

	def update_refresh(self, refresh_token):
		self.refresh_token = refresh_token

	def update_access(self, access_token):
		self.access_token = access_token

	def export_json(self):
		json_object = {"refresh": self.refresh_token.decode('utf-8'), "access": self.access_token.decode('utf-8')}

		with open(env_files.tokens_path, 'w+') as text_file:
			text_file.write(json.dumps(json_object))

	def try_load_json(self):
		try:
			with open(env_files.tokens_path, 'r') as text_file:
				json_object = json.load(text_file)
				self.update_refresh(json_object['refresh'])
				self.update_access(json_object['access'])
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
		"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
		}

	def generate_platform_login(self):
		self.platform_login = deepcopy(self.generic_header)
		self.platform_login["method"] = "POST"
		self.platform_login["path"] = "/api/token-auth/"
		self.platform_login["referer"] = "https://{}/auth/login".format(platform_hostname)
		self.platform_login.pop("connection")

	def generate_refresh_token(self):
		self.refresh_token = deepcopy(self.generic_header)
		self.refresh_token["path"] = "/api/token-refresh/"
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
	BLINK_WHITE = '\33[5m'
	WHITE = '\033[97m'
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

class WeekendsClass:
	def __init__(self):
		self.value = False

class EnvClass:
	def __init__(self):
		self.tokens_path = None
		self.credentials_path = None

def debug_print(varname, data):
	if execution_type.value == 'Script':
		ic('{}: {}'.format(varname, data))
	else:
		#print('{}: {}'.format(varname, data))
		color_print('YELLOW', 'CYAN', 'NOBRIGHT', varname, data)


def color_print(COLORNAME, text, *var):
	def _color_print(arg):
		if type(COLORNAME) == tuple:
			if len(COLORNAME) == 3:
				print(arg)
		else:
			print()
			print(arg)

	if type(COLORNAME) == tuple: # With variable and different colors
		if len(COLORNAME) == 2:
			_color_print(f'{Style.BRIGHT}{getattr(Fore, COLORNAME[0])}{text}{getattr(Fore, COLORNAME[1])}{var[0]}{Style.RESET_ALL}')
		elif len(COLORNAME) == 3:
			if COLORNAME[2] == 'NOBRIGHT':
				_color_print(f'{Style.BRIGHT}{getattr(Fore, COLORNAME[0])}{text}{Style.NORMAL}{getattr(Fore, COLORNAME[1])}{var[0]}{Style.RESET_ALL}')
			else: _color_print('Unrecognized 3rd color arguments!')
	elif var: # With variable and same color
		_color_print(f'{Style.BRIGHT}{getattr(Fore, COLORNAME)}{text}{var[0]}{Style.RESET_ALL}')
	else: # Just text
		_color_print(f'{Style.BRIGHT}{getattr(Fore, COLORNAME)}{text}{Style.RESET_ALL}')

confFileContent = '''# Timetable configuration file

[Platform]
Platform Url = example.com

[Worker Credentials]
Worker Username = USERNAME
Worker Password = PASSWORD

[Worker Details]
Worker Name = FULL NAME
Worker ID = ID

[Settings]
Clear screen before printing = True
'''

execution_type = ExecutionType()
env_files = EnvClass()
credentials = ManageCredentials()
shows_weekends = WeekendsClass()

sys_path = abspath(dirname(sys.executable))

# Verify execution type
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'): # Exe bundle
	configFilePath = join(sys_path, 'timetable.conf')
	execution_type.value = 'Executable'

else: # Python script
	configFilePath = join(dirname(__file__), 'timetable.conf')
	from icecream import ic
	execution_type.value = 'Script'

if not Path(configFilePath).is_file():
	with open(configFilePath, 'w') as text_file:
		text_file.write(confFileContent)
	color_print('WHITE', 'Missing configuration file, a template one was created on: ', configFilePath)
	color_print('YELLOW', 'You need to customize it!')
	exit(1)

configParser = configparser.RawConfigParser(interpolation=None, allow_no_value=True)
configParser.optionxform = str
configParser.read(configFilePath)

if execution_type.value == 'Script':
	env_files.tokens_path = join(dirname(__file__), '.timetable-tks.json')
	env_files.credentials_path = join(dirname(__file__), '.timetable-crd.json')
else:
	env_files.tokens_path = '{}\{}'.format(sys_path, '.timetable-tks.json')
	env_files.credentials_path = '{}\{}'.format(sys_path, '.timetable-crd.json')

platform_hostname = configParser.get('Platform', 'Platform Url')
worker_id = configParser.get('Worker Details', 'Worker ID')
worker_name = configParser.get('Worker Details', 'Worker Name')
clear_screen = configParser.getboolean('Settings', 'Clear screen before printing')

CURRENT_MONTH = datetime.now().month
CURRENT_YEAR = datetime.now().year

def empty_configparser_value(section, item, value):
	configParser.set(section, item, value)
	with open(configFilePath, 'w') as configfile:
		configParser.write(configfile)

if platform_hostname == 'example.com':
	color_print('YELLOW', 'You still need to customize the template configuration!: ', configFilePath)
	exit(1)

if configParser.get('Worker Credentials', 'Worker Username') and configParser.get('Worker Credentials', 'Worker Password'): # Get credentials from conf file
	credentials.update_username(b64encode(configParser.get('Worker Credentials', 'Worker Username').encode('utf-8')))
	credentials.update_password(b64encode(configParser.get('Worker Credentials', 'Worker Password').encode('utf-8')))
	credentials.export_json()
	empty_configparser_value('Worker Credentials', 'Worker Username', None)
	empty_configparser_value('Worker Credentials', 'Worker Password', None)
	with open(configFilePath, 'w') as configfile:
		configParser.write(configfile)
else: # Get credentials from JSON file
	credentials.try_load_json()


def x_print_help():
	print()
	print(f"## {Style.BRIGHT}Timetable's Legend{Style.RESET_ALL} ##")
	print()
	print(f'# {Style.BRIGHT}{Fore.GREEN}1° parameter{Style.RESET_ALL} = Year (4 digits)' )
	print(f'# {Style.BRIGHT}{Fore.GREEN}2° parameter{Style.RESET_ALL} = Month (Without "0" prefix)')
	print(f'# {Style.BRIGHT}{Fore.YELLOW}Optional "weekends" parameter"{Style.RESET_ALL} = Show weekends in table')
	print(f'# {Style.BRIGHT}{Fore.CYAN}You can call Timetable without parameters to see current month hours{Style.RESET_ALL}')
	print()
	print(f"{Style.BRIGHT}# Example A:{Style.RESET_ALL} timetable.[py/exe] {Style.BRIGHT}{Fore.YELLOW}(use current month){Style.RESET_ALL}")
	print(f"{Style.BRIGHT}# Example B:{Style.RESET_ALL} timetable.[py/exe] weekends {Style.BRIGHT}{Fore.YELLOW}(use current month plus weekends){Style.RESET_ALL}")
	print(f"{Style.BRIGHT}# Example C:{Style.RESET_ALL} timetable.[py/exe] 2022 6 {Style.BRIGHT}{Fore.YELLOW}(specifies year and month){Style.RESET_ALL}")
	print(f"{Style.BRIGHT}# Example D:{Style.RESET_ALL} timetable.[py/exe] 2022 11 weekends {Style.BRIGHT}{Fore.YELLOW}(specifies year and month plus weekends){Style.RESET_ALL}")
	exit(0)

def request_validator(status_code, *request_json): # Checking status_code for requests
	if status_code == 401:
		raise Unauthorized
	elif match(r"4[0-9][0-9]", str(status_code)):
		color_print('RED', 'Page thrown an error! --> https.status_code: ', status_code)
		debug_print('status_code', status_code)
		if request_json: debug_print('request_json', request_json)
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
			color_print('YELLOW', 'Platform unavailable!, check your network settings')
			exit(1)
		except Unauthorized:
			color_print('YELLOW', 'Requesting new tokens')
			platform_login()
			return
		except PageError:
			color_print('RED', 'Error while validating tokens')
			exit(1)

	color_print('GREEN', 'Tokens OK')

def do_refresh_token():
	def launch_request():
		headers.generate_refresh_token()
		url = "https://{}/api/token-refresh/".format(platform_hostname)

		data = {
		"refresh": tokens.refresh_token
		}

		req = s.post(url, headers=headers.refresh_token, data=data)
		return req.status_code, req.json()

	color_print('YELLOW', 'Access token expired')

	while True:
		try:
			status_code, request_json = launch_request()
			request_validator(status_code, request_json)
			break
		except Unauthorized: # Must launch platform_login() again
			color_print('YELLOW', 'Reauthenticating...')
			platform_login()
			return
		except PageError:
			debug_print('status_code', status_code)
			debug_print('request_json', request_json)
			if not tokens.refresh_token:
				color_print('RED', 'Valid token missing!, performing authentication')
				_init_validate_tokens()
			return

	tokens.update_refresh(request_json['refresh'])
	tokens.update_access(request_json['access'])

	color_print('GREEN', 'Token refreshed')

def platform_login():
	def launch_request():
		headers.generate_platform_login()
		url = "https://{}/api/token-auth/".format(platform_hostname)

		data = {
		"email" : b64decode(credentials.username).decode('utf-8'),
		"password" : b64decode(credentials.password).decode('utf-8')
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

	color_print('GREEN', 'Logged')

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
			do_refresh_token()
		except PageError:
			color_print('RED', 'Error while getting counters')
			exit(1)

def timetable(year, month):
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
	row_color[1] = 'RED'
	row_color[2] = 'RED'
	row_color[3] = 'RED'
	row_color[4] = 'RED'
	row_color[5] = 'YELLOW'
	row_color[6] = 'YELLOW'
	row_color[7] = 'GREEN'

	if execution_type.value == 'Script': row_color[0] = 'BLUE'
	else: row_color[0] = 'WHITE'

	worktime_table = PrettyTable()

	if shows_weekends.value:
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

	if clear_screen:
		from click import clear as cclear
		cclear()
		#system('cls' if name == 'nt' else 'clear')

	print(worktime_table)
	color_print('WHITE', "Month Worktime: {}".format(format_timedelta(sum(month_worktime, timedelta()))))

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
			color_print('RED', "Error while searching assistances")
			exit(1)

	lenght_list = []
	for item in request_json['results']:
		date_begin = datetime.strptime(item['date_begin'][:19], '%Y-%m-%dT%H:%M:%S').strftime('%d/%m/%Y %H:%M:%S')
		date_end = datetime.strptime(item['date_end'][:19], '%Y-%m-%dT%H:%M:%S').strftime('%d/%m/%Y %H:%M:%S')
		assistance_lenght = datetime.strptime(item['date_end'][:19], '%Y-%m-%dT%H:%M:%S') - datetime.strptime(item['date_begin'][:19], '%Y-%m-%dT%H:%M:%S')

		lenght_list.append(assistance_lenght)

		def xprint():
			color_print('YELLOW', "Description: {}".format(BeautifulSoup(item['job_description'], 'lxml').text))
			print("Start date : {}".format(date_begin))
			print("End date   : {}".format(date_end))
			print("Ticket ID: {}, Customer: {}, Description: {}".format(item['ticket']['id'], item['ticket']['organization']['name'], item['ticket']['title']))
			print("Assistance ID: {}".format(item['id']))
			color_print('CYAN', "Lenght: {}".format(assistance_lenght))

		if do_print:
			xprint()

	if do_print:
		color_print('RED', "Day Worktime: {}".format(sum(lenght_list, timedelta())))
	else:
		return sum(lenght_list, timedelta())

def launch_table():

	def _launch_table(year, month):
		timetable(year, month)

	def check_weekends(arg_number):
		if sys.argv[arg_number] == 'weekends': shows_weekends.value = True
		else:
			if not sys.argv[arg_number].isnumeric():
				color_print('RED', 'Unrecognized optional argument, you can use "weekends" only')
				exit(1)
			else:
				x_print_help()

	if len(sys.argv) == 1: # Clean call
		year = CURRENT_YEAR
		month = CURRENT_MONTH
		_launch_table(year, month)

	if len(sys.argv) == 2: # Clean call with weekends
		year = CURRENT_YEAR
		month = CURRENT_MONTH
		check_weekends(1)
		_launch_table(year, month)

	if len(sys.argv) == 3: # Defined call
		year = int(sys.argv[1])
		month = int(sys.argv[2])
		_launch_table(year, month)

	if len(sys.argv) == 4: # Defined call with weekends
		year = int(sys.argv[1])
		month = int(sys.argv[2])
		check_weekends(3)
		_launch_table(year, month)

###################
tokens = DeclareTokens()
headers = DeclareHeaders()

s = requests.Session()

def session_begin(action, login, *args):
	if login: _init_validate_tokens()
	action(*args)

#### BEGIN
if not sys.flags.interactive:
	if len(sys.argv) == 2:
		if sys.argv[1] == 'help': # Show help
			x_print_help()

	session_begin(launch_table, 1)
