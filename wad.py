# -*- coding: utf-8 -*-

import struct
import StringIO
import cStringIO


def stomp_c_string(s):
	i0 = s.find('\0')
	if i0 < 0:
		return s
	return s[:i0]


class WADError(Exception):
	pass
	
	
class WADLump:
	def __init__(self):
		self.data = ''
		self.name = ''
		
	def get_stream(self):
		return cStringIO.StringIO(self.data)
		
	def get_stream_write(self):
		stream = StringIO.StringIO(self.data)
		def stream_save(s):
			self.data = s.getvalue()
			s.close()
		stream.save = stream_save.__get__(stream, StringIO.StringIO)
		return stream
		
	def __repr__(self):
		return repr((self.name, len(self.data)))

class WADFile(list):
	@classmethod
	def from_file(self, filename):
		with open(filename, 'rb') as f:
			return self.from_stream(f)
			
	@classmethod
	def from_stream(self, stream):
		FileBase = stream.tell()
		# read signature
		sig = stream.read(4)
		if sig != 'IWAD' and sig != 'PWAD':
			raise WADError('Bad file signature')
			
		numlumps, infotableofs = struct.unpack('<II', stream.read(8))
		wad = self()
		
		stream.seek(FileBase + infotableofs)
		for i in range(numlumps):
			stream.seek(FileBase + infotableofs + i * 16)
			filepos, size = struct.unpack('<II', stream.read(8))
			name = stomp_c_string(stream.read(8)).upper()
			lump = WADLump()
			lump.name = name
			stream.seek(FileBase + filepos)
			lump.data = stream.read(size)
			wad.append(lump)
		
		return wad

	def to_file(self, filename, iwad=False):
		with open(filename, 'wb') as f:
			self.to_stream(f, iwad)
			
	def to_stream(self, stream, iwad=False):
		FileBase = stream.tell()
		sig = 'IWAD' if iwad else 'PWAD'
		stream.write(sig)
		
		filepos = []
		infotableofs = 12
		
		for lump in self:
			filepos.append(infotableofs)
			infotableofs += len(lump.data)

		stream.write(struct.pack('<II', len(self), infotableofs))
		
		for lump in self:
			stream.write(lump.data)
			
		assert stream.tell() == infotableofs
		
		for i in range(len(self)):
			stream.write(struct.pack('<II', filepos[i], len(self[i].data)))
			stream.write(struct.pack('<8s', self[i].name))
			
	def get_num_for_name(self, name, start=-1):
		if start >= len(self) or start < -1:
			return -1
		name = name.upper()
		for i in range(start+1, len(self)):
			if self[i].name.upper() == name:
				return i
		return -1

	def get_lump_or_new(self, name):
		for lump in self:
			if lump.name.upper() == name:
				return lump
		lump = WADLump()
		lump.name = name
		self.append(lump)
		return lump

	def get_lump(self, name):
		for lump in self:
			if lump.name.upper() == name:
				return lump
		return None

	def get_lump_between(self, name, start, end):
		name = name.upper()
		nums = self.get_nums_between(start, end)
		for num in nums:
			if self[num].name == name:
				return self[num]
		return None
		
	def get_num_between(self, name, start, end):
		name = name.upper()
		nums = self.get_nums_between(start, end)
		for num in nums:
			if self[num].name == name:
				return num
		return -1
		
	def get_nums_between(self, start, end):
		nums = []
		offset = -1
		while True:
			num_start = self.get_num_for_name(start, offset)
			num_end = self.get_num_for_name(end, num_start)
			if num_start < 0:
				break
			if num_end < 0:
				num_end = len(self)
			offset = num_end+1
			for i in range(num_start+1, num_end):
				nums.append(i)
		return nums
