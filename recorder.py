"""
recorder -- handles all functionalities for svlc related to the capturing of images
"""

from util import *
from os.path import isdir
from os import mkdir
from picamera import PiCamera # unrunnable except on the pis themselves

class Recorder:

	def __init__(self):
		self.cam = PiCamera()
		self.cam.resolution = (1024,768) # TODO check if there are other options
		self.warmup_timer = Timer(2) # 2 second warmup
		self.log = get_logger('recorder.Recorder')

	def begin_warmup(self):
		self.cam.start_preview()
		self.warmup_timer.start()

	def capture(self):
		if not self.warmup_timer.check_expired():
			# not warmed up yet, do not attempt to capture
			self.log.info("Ignoring capture request due to incomplete warmup.")
			return

		# make sure the image working dir exists
		if not isdir(PATH_TO_IMAGES):
			self.log.info("Images working directory does not exist. Creating under {}".format(PATH_TO_IMAGES))
			mkdir(PATH_TO_IMAGES)

		# generate image name
		imgname = PATH_TO_IMAGES + gen_file_name('jpg')

		self.cam.capture(imgname)
