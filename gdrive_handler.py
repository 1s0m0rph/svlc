"""
gdrive_handler -- handles all of the google drive related functionalities for svlc
"""
import io

from file_handler import *
from constants import *
from util import *

from time import time
import os
from os.path import getsize
from shutil import copyfileobj

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

def init_service():
	# shamelessly stolen from the quickstart file
	creds = None
	# The file token.json stores the user's access and refresh tokens, and is
	# created automatically when the authorization flow completes for the first
	# time.
	if os.path.exists('token.json'):
		creds = Credentials.from_authorized_user_file('token.json', GDRIVE_SCOPES)
	# If there are no (valid) credentials available, let the user log in.
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				'credentials.json', GDRIVE_SCOPES)
			creds = flow.run_local_server(port=8080) # port here is important -- make sure key is configured for http://localhost:8080/ [the trailing slash is important!!!]
		# Save the credentials for the next run
		with open('token.json', 'w') as token:
			token.write(creds.to_json())
			
	
	# NOTE: this can return an HttpError (I think)
	return build('drive', 'v3', credentials=creds)
	

class GDriveHandler:
	"""
	actual handler class
	"""
	
	def __init__(self):
		self.log = get_logger('gdrive_handler.GDriveHandler')
		try:
			self.service = init_service()
		except HttpError as e:
			self.log.error("Caught HTTP error while initializing google drive handler: {}".format(e))

		self.working_dir_id = None # hold onto this so we don't have to get it every time

	def get_working_dir_id(self):
		"""
		Get the ID of the working directory on google drive
		"""

		# return the cached value if one exists
		if self.working_dir_id is not None:
			return self.working_dir_id
		# otherwise figure it out

		# get the contents of the 'my drive'/top level dir
		try:
			top_lv_contents = self.service.files().list(fields="nextPageToken, files(id, name)").execute().get('files',[])
		except HttpError as e:
			self.log.error("Caught HTTP error while getting the contents of the top level dir: {}".format(e))
			return []

		if not top_lv_contents:
			self.log.error("Initial query to google drive to get ID of working directory failed.")
			return []

		# find the working dir ID in the returned list
		top_lv_qry = [x for x in top_lv_contents if ACTIVE_GDRIVE_DIR_NAME == x['name']]
		# make sure we actually found it
		if 0 == len(top_lv_qry):
			self.log.error("unable to find {} directory (active/working dir) on google drive".format(ACTIVE_GDRIVE_DIR_NAME))
			return []
		working_dir_id = top_lv_qry[0]['id']
		return working_dir_id
		
	def upload_file(self, path_to_file):
		"""
		upload the file located at the specified path to google drive within the working directory

		returns: ID of uploaded file, or "" if failure to upload
		"""

		self.log.info("Uploading: {} to google drive".format(path_to_file))

		# do some basic verifications
		# make sure the file exists
		if not os.path.isfile(path_to_file):
			self.log.error("Error uploading file: file {} not found".format(path_to_file))
			return ""
		# make sure the file is small enough
		#TODO figure out how to remove this req by doing bigger uploads
		filesize = getsize(path_to_file)
		if filesize > MAX_FILE_SIZE_PER_UPLOAD:
			self.log.warning("File {} is too large ({} bytes > max limit of {} bytes) to upload using simple (i.e. non interruptable) upload type. Will attempt to upload regardless, but integrity may be compromised.".format(path_to_file,filesize,MAX_FILE_SIZE_PER_UPLOAD))
		# basic verifications complete -- proceed to upload

		working_dir_id = self.get_working_dir_id()
		meta_info = {'name':path_to_file,'parents':[working_dir_id]}
		media = MediaFileUpload(path_to_file)
		try:
			upload_result = self.service.files().create(body=meta_info,media_body=media,fields='id').execute()
		except HttpError as e:
			self.log.error("Caught HTTP error while uploading file {}: {}".format(path_to_file,e))

		# return the ID given by the service
		return upload_result.get('id')

	def remove_file(self, file_id, file_name):
		"""
		remove the file with given name and ID from google drive
		"""

		self.log.info("Deleting file {} with ID {} from google drive".format(file_name,file_id))
		try:
			self.service.files().delete(fileId=file_id)
		except HttpError as e:
			self.log.error("Caught HTTP error while removing file {} with ID {}: {}".format(file_name, file_id, e))
	
	def purge_olds(self):
		"""
		Purge the old (see constants for how old is 'old') files from the working dir on google drive
		"""

		# first get the list of files currently in the working directory
		working_dir_contents = self.find_existing_files()
		min_timestamp_to_not_delete = time() - MAX_AGE_BEFORE_PURGE
		
		# check each of these to see if their timestamp is older than current time - max time before delete
		for file in working_dir_contents:
			name = file['name']
			file_id = file['id']
			
			hostname,timestamp = parse_file_name(name)
			if (hostname is None) or (timestamp is None):
				self.log.error("Found file in working directory with improperly formatted name: {}".format(name))
				# ignore this file
			else:
				# check if old enough to delete
				if timestamp < min_timestamp_to_not_delete:
					# this file is too old -- delete it
					self.remove_file(file_id,name)

	def find_existing_files(self):
		"""
		helper function for purging old files: list the current contents of the working directory
		"""
	
		# find the working directory ID
		working_dir_id = self.get_working_dir_id()
		
		# now that we have the ID of the directory, we can list its contents
		try:
			working_dir_contents = self.service.files().list(q='"{}" in parents'.format(working_dir_id), fields="nextPageToken, files(id, name)").execute().get('files',[])
		except HttpError as e:
			self.log.error("Caught HTTP error while getting contents of working directory: {}".format(e))
			return []

		if not working_dir_contents:
			# this is not an error -- we'll get this if the directory is cleared completely
			self.log.warning("No files found in working directory: {} (id: {})".format(ACTIVE_GDRIVE_DIR_NAME,working_dir_id))
			return []
		
		# we have the contents of the directory (names and file IDs) -- just return that as-is
		return working_dir_contents


	def verify_upload(self, path_to_file, uploaded_file_id):
		"""
		verify that the file at the specified path matches the one on google drive at the given id. delete downloaded and verified file when complete in the event of a verification success
		"""

		# download the file to a temp file
		ver_file_name = path_to_file + "_TMP_VER.raw"
		try:
			req = self.service.files().get_media(fileId=uploaded_file_id)
			fh = io.BytesIO()
			dler = MediaIoBaseDownload(fh, req)
			done = False
			while not done:
				stat, done = dler.next_chunk()

			fh.seek(0)
			with open(ver_file_name,'wb') as verfile:
				copyfileobj(fh, verfile)

		except HttpError:
			self.log.error("Caught HTTP error while downloading file with ID {} (local path: {})".format(uploaded_file_id,path_to_file))
			return False

		# download finished, now check that files match
		if check_if_files_match(path_to_file,ver_file_name):
			# verification success! Delete both files
			remove(path_to_file)
			remove(ver_file_name)
			return True
		else:
			self.log.error("Downloaded file from drive does NOT match local file. Deleting downloaded file and marking local file for local backup.")
			# verification not successful! tell the controller to perform a backup!
			remove(ver_file_name)
			return False
