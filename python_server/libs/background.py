#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding: utf-8

import daemon
import datetime
import logging
import os
import shutil
import signal
import socket
import struct
import sys
import _thread
import threading
import time

from RWFileLock import RWFileLock, LockError

from .singleton import SingletonMeta

# Idea taken from https://blog.miguelgrinberg.com/post/how-to-kill-a-python-thread
EXIT_EVENT = threading.Event()

class BackgroundMulticastReceiver(metaclass=SingletonMeta):
	# Inspired by https://gist.github.com/dksmiffs/96ddbfd11ad7349ab4889b2e79dc2b22

	DEFAULT_MCAST_GRP = '224.1.1.1'
	DEFAULT_MCAST_PORT = 5007
	
	DEFAULT_LOGGING_FORMAT = '%(asctime)-15s - [%(process)d][%(levelname)s] %(message)s'
	DEFAULT_LOG_LEVEL = logging.DEBUG
	# DEFAULT_LOG_LEVEL = logging.INFO
	
	@staticmethod
	def commands_mcast_listener(mcast_grp=DEFAULT_MCAST_GRP, mcast_port=DEFAULT_MCAST_PORT, is_all_groups=False):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		if is_all_groups:
			# on this port, receives ALL multicast groups
			sock.bind(('', mcast_port))
		else:
			# on this port, listen ONLY to mcast_grp
			sock.bind((mcast_grp, mcast_port))
		mreq = struct.pack("4sl", socket.inet_aton(mcast_grp), socket.INADDR_ANY)

		sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

		while True:
			mess = sock.recv(10240)
			# print(f'* [{datetime.datetime.now().isoformat()}] Message {mess}')

			if mess == b'shutdown':
				# print("\nThat's all folks, friends!!! Telling my siblings to go away")
				# sys.stdout.flush()
				_thread.interrupt_main()
				break
	
	@staticmethod
	def default_sigint_handler(signum, stack_frame):
		"""
		This is the signal received by main thread when
		when 
		"""
		#print("S'acabó")
		#sys.stdout.flush()
		EXIT_EVENT.set()
		sys.exit(1)

	def __init__(self, local_config={}, sigint_handler=default_sigint_handler.__get__(object)):
		self.logger = logging.getLogger(self.__class__.__name__)
		
		# First, setting the signal handler
		signal.signal(signal.SIGINT, sigint_handler)
		
		# Second, start the listener thread
		back_setup = local_config.get('backchannel', {})
		self.mcast_grp = back_setup.get('multicast-group' , self.DEFAULT_MCAST_GRP)
		self.mcast_port = back_setup.get('multicast-port' , self.DEFAULT_MCAST_PORT)
		self.is_all_groups = back_setup.get('is-all-groups' , False)
		self.mcast_thread = threading.Thread(
			name="background-mcast",
			target=self.commands_mcast_listener,
			args=(),
			kwargs={
				'mcast_grp': self.mcast_grp,
				'mcast_port': self.mcast_port,
				'is_all_groups': self.is_all_groups,
			},
			daemon=True
		)
		self.mcast_thread.start()
	
	def getRebuildLock(self, newCacheDir):
		serverLockFile = os.path.join(newCacheDir, 'rebuild.lock')
		return RWFileLock(serverLockFile)
	
	def background_rebuild_caches(self, new_local_config, oldftv, stdout=None, stderr=None):
		"""
		This method creates a detached background process which
		rebuilds caches in a separate directory
		"""
		
		# Am I the new server process?
		if os.fork() == 0:
			newCacheDir = new_local_config['cacheDir']
			if (stdout is None) or (stderr is None):
				os.makedirs(newCacheDir, mode=0o750, exist_ok=True)
				logstream = open(os.path.join(newCacheDir, 'background-update.log'), mode='w', encoding='utf-8')
				if stdout is None:
					stdout = logstream
				if stderr is None:
					stderr = logstream
			with daemon.DaemonContext(detach_process=True,umask=0o027,stdout=stdout,stderr=stderr) as context:
				# Let's reset the logging setup in order to gather clues
				logging.basicConfig(
					format=self.DEFAULT_LOGGING_FORMAT,
					level=self.DEFAULT_LOG_LEVEL,
					stream=stderr,
					force=True
				)
				
				os.makedirs(newCacheDir, mode=0o750, exist_ok=True)
				slock = self.getRebuildLock(newCacheDir)
				try:
					try:
						slock.w_lock()
					except LockError:
						# Other one controls all
						# Gracefully exit
						if stderr is not None:
							stderr.write(str(time.time())+"\nLOCKED\n")
						sys.exit(1)
					
					try:
						# Rebuild the caches in a new instance
						tftv = oldftv.__class__(new_local_config, isRW=True)
						
						# Acquire the exclusive locks of old directories
						oldftv._init_locks()
						with oldftv.SchemaCacheLock.exclusive_blocking_lock(), \
							oldftv.ExtensionsCacheLock.exclusive_blocking_lock():
							
							# Broadcast the shutdown message
							self.broadcast_shutdown()
							
							# Interchange the directories
							oldCacheDir = oldftv.cacheDir + '_old'
							
							if os.path.exists(oldCacheDir):
								shutil.rmtree(oldCacheDir)
							
							os.rename(oldftv.cacheDir, oldCacheDir)
							os.rename(tftv.cacheDir, oldftv.cacheDir)
							
							# Release the exclusive locks
					except:
						if stderr is not None:
							import traceback
							stderr.write(str(time.time())+"\n")
							traceback.print_exc(None,stderr)
							stderr.flush()
				finally:
					if(slock.isLocked):
						slock.unlock()
					del slock
				
				sys.exit(0)
		
		return True
	
	def broadcast_shutdown(self):
		# for all packets sent, after two hops on the network the packet will not 
		# be re-sent/broadcast (see https://www.tldp.org/HOWTO/Multicast-HOWTO-6.html)
		MULTICAST_TTL = 2

		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)
		sock.sendto('shutdown'.encode('utf-8'), (self.mcast_grp, self.mcast_port))
#
#def otra_hebra():
#    counter = 0
#    while not EXIT_EVENT.wait(7):
#        print(f'\tOtra {datetime.datetime.now().isoformat()}')
#        sys.stdout.flush()
#
#otra_thread = threading.Thread(target=otra_hebra, name="OTRA")
#otra_thread.start()
#
#counter = 0
#while True:
#    time.sleep(10)
#    print(f'Awoke {datetime.datetime.now().isoformat()}')
#    sys.stdout.flush()
#    counter += 1