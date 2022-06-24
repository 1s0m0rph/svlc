"""
file_handler -- handles all of the local file manipulation (incl. compression, encryption, permanent backup [in the event of an upload ver fail])
"""

from util import *

from os.path import isdir, getsize
from os import mkdir, remove
from shutil import move
import logging
from filecmp import cmp as compare_files
from gnupg import GPG
import zipfile

log = get_logger('file_handler')

def local_backup(files_to_perm_backup):
	"""
	Perform a local backup of the given files
	"""

	log.warning("Performing local backup of the following files due to upload verification failure: ")
	for file in files_to_perm_backup:
		log.warning(file)

	# create local backup dir if it does not exist already
	if not isdir(LOCAL_BACKUP_LOC):
		log.info("Local backup directory does not already exist, creating.")
		mkdir(LOCAL_BACKUP_LOC)

	# move all files from their current location into the backup dir
	for file in files_to_perm_backup:
		move(file,"{}/{}".format(LOCAL_BACKUP_LOC,file))

	log.warning("Local backup complete")

def compress_files(filenames,dest_filename):
	zf = zipfile.ZipFile(dest_filename, mode='w')
	try:
		for filename in filenames:
			zf.write(filename, filename, compress_type=zipfile.ZIP_DEFLATED)
	except FileNotFoundError as e:
		log.error("Caught FileNotFoundError while attempting to create zip file: {}".format(e))
	finally:
		zf.close()

def encrypt_file(filename,enc_filename):
	log.info("Encrypting {} using passphrase".format(filename))
	# disable logging for all GPG related things because it is way too damned noisy -_-
	log.setLevel(logging.CRITICAL)
	gpg = GPG()
	log.setLevel(logging.DEBUG)
	key = ""

	# read key from file
	with open(ENC_PASSPHRASE_LOC,'r') as keyfile:
		key = keyfile.readline()
		# remove characters that will cause GPG to think this is an "incorrect passphrase" smdh
		key = key.replace('\n','').replace('\r','')

	if "" == key:
		log.error("Error reading key from keyfile: empty string")

	# do the encryption
	with open(filename,'rb') as raw_file:
		log.setLevel(logging.CRITICAL)
		gpg.encrypt_file(raw_file,[],passphrase=key,output=enc_filename,symmetric=True)
		log.setLevel(logging.DEBUG)


def check_if_files_match(local_file_path, downloaded_file_path):
	return compare_files(local_file_path, downloaded_file_path)

class FileHandler:

	def __init__(self):
		# this is a purely empirical thing to get a decent starting point for batch size -- it will be updated as we go
		self.approx_final_bytes_per_img = 575000
		self.num_images_approx_based_on = 8
		self.log = get_logger('file_handler.FileHandler')

	def compress_and_encrypt_batch(self,filelist:list):
		"""
		given a list of files that need to be compressed/encrypted, generate and size the batches properly so that all of the final products are less than <max upload size>
		"""
		self.log.info("Performing batch compression and encryption.")

		# first we have to generate the batch assignments
		left_to_assign = filelist.copy()
		assignments = {file:None for file in filelist} # this will map file names onto batch number
		final_filenames = []
		all_assigned_and_verified = False
		batch_num = 0

		# info that is useful for debugging (probably)
		num_downward_adjustments = 0
		num_upward_adjustments = 0

		while not all_assigned_and_verified:
			# get the file name for this batch
			batch_zip_filename = gen_file_name() + "_B{}.zip".format(batch_num)
			batch_filename = batch_zip_filename + '.gpg'

			# start with the best initial guess for the next batch
			num_in_this_batch = min(len(left_to_assign),max(1,int(MAX_FILE_SIZE_PER_UPLOAD / self.approx_final_bytes_per_img)))
			prev_was_too_big = False
			good_num_found = False
			while not good_num_found:
				# try the current value
				this_batch_files = left_to_assign[:num_in_this_batch]
				compress_files(this_batch_files,batch_zip_filename)
				encrypt_file(batch_zip_filename,batch_filename)
				# check size
				size = getsize(batch_filename)
				if num_in_this_batch == 1:
					# we're just gonna have to live with an overly large file unfortunately. luckily this should be pretty unlikely
					self.log.warning("File {} produces a compressed/encrypted archive larger than the upload limit ({} bytes > {} bytes)".format(this_batch_files[0], size, MAX_FILE_SIZE_PER_UPLOAD))
					good_num_found = True
				elif size > MAX_FILE_SIZE_PER_UPLOAD:
					# too big, have to decrease
					num_in_this_batch -= 1
					num_downward_adjustments += 1
					# set this so we know when to stop shrinking
					prev_was_too_big = True
				else:
					if prev_was_too_big:
						# we know for a fact we can't add on -- just stick with what we've got
						good_num_found = True
					elif size > MAX_FILE_SIZE_PER_UPLOAD - (self.approx_final_bytes_per_img*0.9):
						# deadband case -- assume that our estimate is good
						good_num_found = True
					elif num_in_this_batch == len(left_to_assign):
						# no more left to assign -- this'll do
						good_num_found = True
					else:
						# could probably fit more in -- increase
						num_in_this_batch += 1
						num_upward_adjustments += 1

				if not good_num_found:
					# clear out this iteration's files
					remove(batch_zip_filename)
					remove(batch_filename)
				else:
					# when done get rid of the zip file and image files
					self.log.info("Good size found: {} files. Removing zip and packaged files.".format(num_in_this_batch))
					remove(batch_zip_filename)
					for file in this_batch_files:
						self.log.debug("Removing {}".format(file))
						remove(file)

			# update our estimates
			self.approx_final_bytes_per_img = ((self.approx_final_bytes_per_img*self.num_images_approx_based_on) + getsize(batch_filename)) / (self.num_images_approx_based_on + num_in_this_batch)
			self.num_images_approx_based_on += num_in_this_batch
			self.log.info("New estimated final bytes per image: {}, based on {} total images screened.".format(self.approx_final_bytes_per_img, self.num_images_approx_based_on))

			# assign the files
			this_batch_files = left_to_assign[:num_in_this_batch]
			for file in this_batch_files:
				assignments[file] = batch_num
			left_to_assign = left_to_assign[num_in_this_batch:]
			final_filenames.append(batch_filename)
			batch_num += 1

		# log adjustment info
		self.log.debug("Number of times batch size increased: {}".format(num_upward_adjustments))
		self.log.debug("Number of times batch size decreased: {}".format(num_downward_adjustments))

		# finally, return the file names we ended up with
		return final_filenames
