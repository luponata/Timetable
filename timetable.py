#!/usr/bin/env python3
APP_NAME='Timetable'
APP_VERSION='v4822'

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
import sys, json, requests, configparser

class ExecutionType:
	def __init__(self):
		self.value = None

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

		with open(envFile.path, 'w+') as text_file:
			text_file.write(json.dumps(json_object))

	def try_load_json(self):
		try:
			with open(envFile.path, 'r') as text_file:
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
		self.path = False

def print_debug(data):
	if execution_type == 'Script':
		ic(data)
	else: print(data)


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

confFileContent = '''# Timetable configuration file

[Platform]
Platform Url = example.com

[Worker Credentials]
Worker Username = username
Worker Password = password

[Worker Details]
Worker Name = FULL NAME
Worker ID = ID

[Settings]
Clear screen before printing = True
'''

execution_type = ExecutionType()
envFile = EnvClass()
shows_weekends = WeekendsClass()

# test
sys_path = abspath(dirname(sys.executable))

# Verify execution type
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'): # Exe bundle
	configFilePath = join(sys_path, 'timetable.conf')
	#print_debug('Executable')
	execution_type.value = 'Executable'

else: # Python script
	configFilePath = join(dirname(__file__), 'timetable.conf')
	from icecream import ic
	execution_type.value = 'Script'
	#print_debug('Script')

#print('configFilePath', configFilePath)

if not Path(configFilePath).is_file():
	with open(configFilePath, 'w') as text_file:
		text_file.write(confFileContent)
	print_something('WHITE', 'Missing configuration file, a template one was created on: ', configFilePath)
	print_something('YELLOW', 'You need to customize it!')
	exit(1)

#
#filename = basename(sys.argv[0])
#sys_path = __file__.replace(filename, '')

configParser = configparser.RawConfigParser()
#configFilePath = '{}{}'.format(sys_path, 'timetable.conf')
configParser.read(configFilePath),

if execution_type.value == 'Script':
	envFile.path = join(dirname(__file__), '.timetable-env.json')
else:
	envFile.path = '{}\{}'.format(sys_path, '.timetable-env.json')

platform_hostname = configParser.get('Platform', 'Platform Url')
worker_id = configParser.get('Worker Details', 'Worker ID')
worker_name = configParser.get('Worker Details', 'Worker Name')
worker_username = b64encode(configParser.get('Worker Credentials', 'Worker Username').encode('utf-8'))
worker_password = b64encode(configParser.get('Worker Credentials', 'Worker Password').encode('utf-8'))
clear_screen = configParser.getboolean('Settings', 'Clear screen before printing')

CURRENT_MONTH = datetime.now().month
CURRENT_YEAR = datetime.now().year

if platform_hostname == 'example.com':
	print_something('YELLOW', 'You still need to customize the template configuration!: ', configFilePath)
	exit(1)

def x_print_help():
	print()
	print(f"## {Style.BRIGHT}Timetable's Legend{Style.RESET_ALL} ##")
	print()
	print(f'# {Style.BRIGHT}{Fore.GREEN}1st argument{Style.RESET_ALL} = Year (4 digits)' )
	print(f'# {Style.BRIGHT}{Fore.GREEN}2nd argument{Style.RESET_ALL} = Month (Without "0" prefix)')
	print(f'# {Style.BRIGHT}{Fore.YELLOW}Optional "weekends" argument"{Style.RESET_ALL} = Show weekends in table')
	print(f'# {Style.BRIGHT}{Fore.CYAN}You can call Timetable without arguments to use current month{Style.RESET_ALL}')
	print()
	print(f"{Style.BRIGHT}# Example A:{Style.RESET_ALL} ./timemap.py {Style.BRIGHT}{Fore.YELLOW}(use current month){Style.RESET_ALL}")
	print(f"{Style.BRIGHT}# Example B:{Style.RESET_ALL} ./timemap.py weekends {Style.BRIGHT}{Fore.YELLOW}(use current month plus weekends){Style.RESET_ALL}")
	print(f"{Style.BRIGHT}# Example C:{Style.RESET_ALL} ./timemap.py 2022 6 {Style.BRIGHT}{Fore.YELLOW}(specify a year and month){Style.RESET_ALL}")
	print(f"{Style.BRIGHT}# Example D:{Style.RESET_ALL} ./timemap.py 2022 11 weekends {Style.BRIGHT}{Fore.YELLOW}(specify a year and month plus weekends){Style.RESET_ALL}")
	exit(0)

def request_validator(status_code, *request_json):
	if status_code == 401:
		raise Unauthorized
	elif match(r"4[0-9][0-9]", str(status_code)):
		print_something('RED', 'Page thrown an error! --> https.status_code: ', status_code)
		debug_print(status_code)
		if request_json: debug_print(request_json)
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
			print_something('YELLOW', 'Reauthenticating...')
			platform_login()
			return
		except PageError:
			debug_print(status_code)
			debug_print(request_json)
			if not tokens.refresh_token:
				print_something('RED', 'Valid token missing!, performing authentication')
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
			debug_print(status_code)
			debug_print(request_json)
			do_refresh_token()
		except PageError:
			print_something('RED', 'Error while getting counters')
			exit(1)

	debug_print(status_code)
	debug_print(request_json)

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
		date_begin = datetime.strptime(item['date_begin'][:19], '%Y-%m-%dT%H:%M:%S').strftime('%d/%m/%Y %H:%M:%S')
		date_end = datetime.strptime(item['date_end'][:19], '%Y-%m-%dT%H:%M:%S').strftime('%d/%m/%Y %H:%M:%S')
		assistance_lenght = datetime.strptime(item['date_end'][:19], '%Y-%m-%dT%H:%M:%S') - datetime.strptime(item['date_begin'][:19], '%Y-%m-%dT%H:%M:%S')

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

def launch_table():

	def _launch_table(year, month):
		timetable(year, month)

	def check_weekends(arg_number):
		if sys.argv[arg_number] == 'weekends': shows_weekends.value = True
		else:
			if not sys.argv[arg_number].isnumeric():
				print_something('RED', 'Unrecognized optional argument, you can use "weekends" only')
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
