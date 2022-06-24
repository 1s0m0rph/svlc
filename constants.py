"""
define constants for svlc
"""

# general constants
FILE_DEC_SEPARATOR = "d" # what character do we use to separate integer parts from decimal parts in filenames?

# timing constants
SECS_PER_CYCLE = 0.5 # run at 2Hz
#TODO we may just want to upload when the compressed file gets to 5MB [get a rough estimate beforehand of how long/how many images this will take]
SECS_PER_UPLOAD = 60 # upload every minute
SECS_PER_LOG_UPLOAD = 3600 # logs very hour
SECS_PER_PURGE = 300 # purge olds every five minutes
MAX_AGE_BEFORE_PURGE = 86400 # purge files older than 1 day
SECS_PER_STILL_CAP = 1 # capture 1 image every <value> seconds (TODO: needs tuning)

# google drive related constants
# If modifying these scopes, delete the file token.json.
GDRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']
ACTIVE_GDRIVE_DIR_NAME = 'sv_dev'
# TODO: figure out how to do bigger uploads
MAX_FILE_SIZE_PER_UPLOAD = 5000000 # bytes

# file handling constants
LOCAL_BACKUP_LOC = "~/local_bak/"
ENC_PASSPHRASE_LOC = "./enc_pw.txt" # TODO make this file and make sure it has proper perms (640)
PATH_TO_IMAGES = "./working_images/"
