#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding: utf-8

import os
import contextlib
import tempfile
import fcntl

class LockError(Exception):
	def __init__(self,message):
		super().__init__(message)

class RWFileLock(object):
	def __init__(self,filename=None):
		self.lock_fd = os.open(filename,(os.O_RDWR | os.O_CREAT),mode=0o700)
		self.isLocked = False
	
	def r_lock(self):
		if self.isLocked:
			raise LockError('Already locked by ourselves')
		
		try:
			fcntl.lockf(self.lock_fd,(fcntl.LOCK_SH|fcntl.LOCK_NB))
			self.isLocked = True
		except IOError:
			raise LockError('Already locked by others')
	
	def r_blocking_lock(self):
		if self.isLocked:
			raise LockError('Already locked by ourselves')
		
		fcntl.lockf(self.lock_fd,fcntl.LOCK_SH)
		self.isLocked = True
	
	def w_lock(self):
		if self.isLocked:
			raise LockError('Already locked by ourselves')
		
		try:
			fcntl.lockf(self.lock_fd,(fcntl.LOCK_EX|fcntl.LOCK_NB))
			self.isLocked = True
		except IOError:
			raise LockError('Already locked by others')
	
	def w_blocking_lock(self):
		if self.isLocked:
			raise LockError('Already locked by ourselves')
		
		fcntl.lockf(self.lock_fd,fcntl.LOCK_EX)
		self.isLocked = True
	
	def unlock(self):
		if self.isLocked:
			try:
				fcntl.lockf(self.lock_fd,fcntl.LOCK_UN)
			except IOError:
				raise LockError('Already locked by others')
			finally:
				self.isLocked = False
		else:
			raise LockError('No lock was held')
	
	@contextlib.contextmanager
	def shared_lock(self):
		self.r_lock()
		try:
			yield
		finally:
			self.unlock()
	
	@contextlib.contextmanager
	def shared_blocking_lock(self):
		try:
			self.r_lock()
			yield
		finally:
			self.unlock()
	
	@contextlib.contextmanager
	def exclusive_lock(self):
		self.w_lock()
		try:
			yield
		finally:
			self.unlock()
	
	@contextlib.contextmanager
	def exclusive_blocking_lock(self):
		try:
			self.w_blocking_lock()
			yield
		finally:
			self.unlock()
	
	def __del__(self):
		os.close(self.lock_fd)

if __name__ == '__main__':
	lock = RWFileLock('/tmp/rwfilelock.lock')
	
	print("Trying getting lock")
	import sys
	sys.stdout.flush()
	try:
		if len(sys.argv) > 1:
			with lock.exclusive_lock():
				import time
				time.sleep(10)
		else:
			with lock.shared_lock():
				import time
				time.sleep(10)
	except LockError:
		print("Unable to get lock")