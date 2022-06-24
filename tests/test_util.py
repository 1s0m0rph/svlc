from unittest import TestCase
from svlc.util import *

class TestParseFileName(TestCase):
	def test_proper_format_int_timestamp(self):
		fname = "svbase0_1513047.tar.gz"
		expected_result = ("svbase0",1513047)
		actual_result = parse_file_name(fname)
		self.assertTupleEqual(expected_result,actual_result)

	def test_proper_format_dec_timestamp(self):
		fname = "svbase0_1513047{}3125.tar.gz".format(FILE_DEC_SEPARATOR)
		expected_result = ("svbase0",1513047.3125)
		actual_result = parse_file_name(fname)
		self.assertTupleEqual(expected_result,actual_result)

	def test_improper_format(self):
		fname = "asdf.txt"
		expected_result = (None,None)
		actual_result = parse_file_name(fname)
		self.assertTupleEqual(expected_result,actual_result)

class TestFilenameCompatFloatToFloat(TestCase):
	def test_zero(self):
		value = "0{}0".format(FILE_DEC_SEPARATOR)
		expected_result = 0
		actual_result = filename_compat_float_to_float(value)
		self.assertEqual(expected_result,actual_result)

	def test_pos_int(self):
		value = "1{}0".format(FILE_DEC_SEPARATOR)
		expected_result = 1
		actual_result = filename_compat_float_to_float(value)
		self.assertEqual(expected_result,actual_result)

	def test_neg_int(self):
		value = "-1{}0".format(FILE_DEC_SEPARATOR)
		expected_result = -1
		actual_result = filename_compat_float_to_float(value)
		self.assertEqual(expected_result,actual_result)

	def test_pos_nonint(self):
		value = "1{}5".format(FILE_DEC_SEPARATOR)
		expected_result = 1.5
		actual_result = filename_compat_float_to_float(value)
		self.assertEqual(expected_result,actual_result)

	def test_neg_nonint(self):
		value = "-1{}5".format(FILE_DEC_SEPARATOR)
		expected_result = -1.5
		actual_result = filename_compat_float_to_float(value)
		self.assertEqual(expected_result,actual_result)

class TestFloatToFilenameCompatibleStr(TestCase):
	def test_zero(self):
		value = 0
		expected_result = "0{}0".format(FILE_DEC_SEPARATOR)
		actual_result = float_to_filename_compatible_str(value)
		self.assertEqual(expected_result,actual_result)

	def test_pos_int(self):
		value = 1
		expected_result = "1{}0".format(FILE_DEC_SEPARATOR)
		actual_result = float_to_filename_compatible_str(value)
		self.assertEqual(expected_result,actual_result)

	def test_neg_int(self):
		value = -1
		expected_result = "-1{}0".format(FILE_DEC_SEPARATOR)
		actual_result = float_to_filename_compatible_str(value)
		self.assertEqual(expected_result,actual_result)

	def test_pos_nonint(self):
		value = 1.5
		expected_result = "1{}5".format(FILE_DEC_SEPARATOR)
		actual_result = float_to_filename_compatible_str(value)
		self.assertEqual(expected_result,actual_result)

	def test_neg_nonint(self):
		value = -1.5
		expected_result = "-1{}5".format(FILE_DEC_SEPARATOR)
		actual_result = float_to_filename_compatible_str(value)
		self.assertEqual(expected_result,actual_result)