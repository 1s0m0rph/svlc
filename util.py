"""
basic util functionality
"""

import re
from constants import *
from time import time
import logging
import logging.config
logging.config.fileConfig('logging.conf',disable_existing_loggers=False)

def get_hostname():
	"""
	function to get the current system hostname
	
	mostly this is separate so we can avoid importing hostname related stuff everywhere

	NOTE: no unit tests for this function, as it is essentially untestable
	"""

	import platform
	return platform.node()

def filename_compat_float_to_float(filename:str) -> float:
	"""
	given a string with a filename compatible float, convert to an actual float
	"""

	re_match = re.match(r"(-?\d+)" + FILE_DEC_SEPARATOR + r"?(\d*)", filename)
	integer_part = re_match.group(1)
	decimal_part = re_match.group(2)
	return float("{}.{}".format(integer_part,decimal_part))


def parse_file_name(filename):
	"""
	given the string that is the name of a file (regardless of type), get its source and creation time (s since epoch)
	"""

	re_match = re.match(r"(\w+)_(-?\d+" + FILE_DEC_SEPARATOR + r"?\d*)\..*",filename)
	if re_match is None:
		return None,None
	else:
		return re_match.group(1),filename_compat_float_to_float(re_match.group(2))

def gen_file_name(ext=None):
	"""
	generic file name generator in the standard format (inverse of parse_file_name)
	"""

	if ext is None:
		return "{}_{}".format(get_hostname(),float_to_filename_compatible_str(time()))
	elif "." == ext[0]:
		return "{}_{}{}".format(get_hostname(),float_to_filename_compatible_str(time()),ext)
	else:
		return "{}_{}.{}".format(get_hostname(),float_to_filename_compatible_str(time()),ext)

def float_to_filename_compatible_str(f:float):
	"""
	convert a float to a string that plays nice with file names
	"""

	integer_part = int(f)
	decimal_part = str((f - int(f)))
	if "0." == decimal_part[:2]:
		decimal_part = decimal_part[2:]
	elif "-0." == decimal_part[:3]:
		decimal_part = decimal_part[3:]
		
	return "{}{}{}".format(integer_part,FILE_DEC_SEPARATOR,decimal_part)

# create the logfile name once at program start
LOGFILE_NAME = "{}_STARTAT_{}.log".format(get_hostname(),float_to_filename_compatible_str(time()))

def get_logger(loc):
	"""
	get a logger object pointing to the latched logfile name with proper formatting
	"""

	# create the logger object
	logger = logging.getLogger(loc) # TODO include file/class name here?
	# create file handler to put all stuff into the file
	fh = logging.FileHandler(LOGFILE_NAME)
	fh.setLevel(logging.DEBUG)
	fmtr = logging.Formatter("%(asctime)s:\t%(name)s - %(levelname)s:\t%(message)s")
	fmtr.datefmt = "%Y-%m-%d %H:%M:%S %Z"
	fh.setFormatter(fmtr)
	logger.addHandler(fh)
	return logger

log = get_logger('util')
log.info("Starting log in {}".format(LOGFILE_NAME))

class Timer:

	def __init__(self,timeout):
		self.start_time = None
		self.running = False
		self.timeout = timeout
		self.log = get_logger('util.Timer')

	def reset(self):
		self.start_time = None
		self.running = False

	def start(self):
		if self.start_time is not None:
			self.log.error("Attempting to start an already running timer (did you mean to call restart?)")
		else:
			self.running = True
			self.start_time = time()

	def restart(self):
		self.running = True
		self.start_time = time()

	def stop(self):
		self.running = True

	def is_complete(self):
		return (not self.running) and (self.start_time is not None)

	def is_running(self):
		return self.running

	def elapsed_time(self):
		if self.start_time is None:
			return 0
		return time() - self.start_time

	def check_expired(self):
		if self.start_time is None:
			return False
		if not self.running:
			return False

		if self.elapsed_time() >= self.timeout:
			# autostop
			self.stop()
			return True
		return False
