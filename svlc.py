#!/bin/python

"""
svlc aka surveillance s/w prototype (svlc is just a shortened version of the word)

this file contains the main loop and defers all (other) functionalities elsewhere

primary functionalities:
	- surveillance:
		+ recording of static images on a fixed interval, output to files with timestamp and hostname
	- uploading:
		+ compression of surveillance files for bulk upload
		+ encryption of compressed bulk upload
		+ upload encrypted files to google drive
		+ verify integrity of upload
			# backup of unverifiable files
	- cleaning:
		+ purging of old files
			# ignores files moved out of the working dir (i.e. don't just kill everything all the time)

"""

#TODO log activity

# from recorder import *
from gdrive_handler import *
from file_handler import *
from constants import *

from os import listdir, remove
from time import time, sleep
from shutil import copy
import logging as log

LOGFILE_NAME = "{}_STARTAT_{}.log".format(get_hostname(),float_to_filename_compatible_str(time()))

# set up objects
# recorder = Recorder()
drive_handler = GDriveHandler()
file_handler = FileHandler()

# set up timers
capture_timer = Timer(SECS_PER_STILL_CAP)
purge_timer = Timer(SECS_PER_PURGE)
upload_timer = Timer(SECS_PER_UPLOAD)
log_upload_timer = Timer(SECS_PER_LOG_UPLOAD)

# set up misc data
num_times_logs_uploaded = 0

# TODO (high priority)
## get fucking gpg out of the logs
## clean up the gpg files that are hanging around in the working dir
## figure out why things aren't showing up on gdrive?

def main_loop():
	# check for timer expiration
	if capture_timer.check_expired():
		print('capture')
		# perform capture
		# recorder.capture()
		# restart timer for next cycle
		capture_timer.restart()

	if purge_timer.check_expired():
		print('purge')
		# perform purge
		drive_handler.purge_olds()
		# restart timer for next cycle
		purge_timer.restart()

	if upload_timer.check_expired():
		print('upload')
		# get file list
		files_to_package = listdir(PATH_TO_IMAGES)
		files_to_package = [PATH_TO_IMAGES + x for x in files_to_package]
		# perform compress/encrypt
		files_to_upload = file_handler.compress_and_encrypt_batch(files_to_package)
		# most likely, we'll get all or none, but track them separately (and only backup failures) just in case
		ver_failed_files = []
		# upload and verify the files
		for file in files_to_upload:
			# upload this file
			drive_file_id = drive_handler.upload_file(file)
			# verify this file (or backup if ver fails)
			ver = drive_handler.verify_upload(file, drive_file_id)
			if not ver:
				# verification failed, we need to back these files up
				ver_failed_files.append(file)
			# otherwise the file will have been deleted

		# backup all failures
		if 0 != len(ver_failed_files):
			local_backup(ver_failed_files)

		# restart timer for next cycle
		upload_timer.restart()

	if log_upload_timer.check_expired():
		# copy to temp for uploading with new name to avoid rename issues on the drive side
		upload_file_name = LOGFILE_NAME[:-4] + "_{}.log".format(num_times_logs_uploaded)
		copy(LOGFILE_NAME,upload_file_name)
		# perform compress/encrypt
		files_to_upload = file_handler.compress_and_encrypt_batch([upload_file_name])
		# upload the file
		drive_handler.upload_file(files_to_upload[0])
		# do not verify, just delete the temp copy of the file
		remove(upload_file_name)

		# restart timer for next cycle
		log_upload_timer.restart()


if __name__ == "__main__":

	# set up logging
	log.basicConfig(filename=LOGFILE_NAME,
					encoding='utf-8',
					level=log.DEBUG,
					format="%(asctime)s:\t %(levelname)s: %(message)s",#TODO figure out how to use Ztime
					datefmt="%Y-%m-%d %H:%M:%S %Z"
					)
	log.info("File logger created, logging to {}".format(LOGFILE_NAME))

	# initialize objects
	# recorder.begin_warmup()

	# start timers
	capture_timer.start()
	purge_timer.start()
	upload_timer.start()
	log_upload_timer.start()

	# perform the main loop
	while True:
		# record cycle start time 
		start_time = time() # epoch in seconds
		
		main_loop()
		
		end_time = time()
		remain_cycle_time = SECS_PER_CYCLE - (end_time - start_time)
		if remain_cycle_time < 0:
			log.debug("Cycle overrun by {} sec".format(-remain_cycle_time))
			remain_cycle_time = 0
		# delay remaining cycle time
		sleep(remain_cycle_time)