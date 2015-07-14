# -*- coding: utf-8 -*-

import wad
import struct


# level consists of the following lumps in the following order:
#  THINGS
#  LINEDEFS
#  SIDEDEFS
#  VERTEXES
#  [SEGS]
#  [SSECTORS]
#  [NODES]
#  SECTORS
#  [REJECT]
#  [BLOCKMAP]
# lumps in [] aren't required by zdoom, but probably are required by boom, so running nodebuilder is advised


class DoomLevelError(Exception):
	pass
	
	
class DoomLevelSidedef:
	def __init__(self):
		self.xoffs = 0
		self.yoffs = 0
		self.tex_upper = ''
		self.tex_middle = ''
		self.tex_lower = ''
		self.sector = 0
		
		
class DoomLevelSector:
	def __init__(self):
		self.height_floor = 0
		self.height_ceiling = 0
		self.tex_floor = ''
		self.tex_ceiling = ''
		self.light = 0
		self.special = 0
		self.tag = 0


class DoomLevel:
	def __init__(self):
		self.sectors = None
		self.sidedefs = None
		self.lumps = []

	@classmethod
	def map_len_in_wad(self, wf, name):
		map_lump_names = [['THINGS', True],
						  ['LINEDEFS', True],
						  ['SIDEDEFS', True],
						  ['VERTEXES', True],
						  ['SEGS', False],
						  ['SSECTORS', False],
						  ['NODES', False],
						  ['SECTORS', True],
						  ['REJECT', False],
						  ['BLOCKMAP', False]]
		lump0 = wf.get_num_for_name(name)
		if lump0 < 0:
			raise DoomLevelError('Map %s not found' % (name))
		cnt = 0
		for i in range(len(map_lump_names)):
			lumpname_ex = map_lump_names[i][0]
			lumpname = wf[1+lump0+cnt].name.upper()
			if lumpname != lumpname_ex:
				if map_lump_names[i][1]:
					raise DoomLevelError('Not all required lumps are present')
			else:
				cnt += 1
		return cnt
		
	@classmethod
	def from_wad(self, wf, name):
		num = wf.get_num_for_name(name)
		if num < 0:
			raise DoomLevelError('Map %s not found' % (name))
		numlumps = self.map_len_in_wad(wf, name)
		level = DoomLevel()
		for i in range(num+1, num+1+numlumps):
			lump = wf[i]
			level.add_lump(lump)
		return level
		
	def add_lump(self, lump):
		if lump.name.upper() == 'SIDEDEFS':
			self.add_sidedefs(lump)
		elif lump.name.upper() == 'SECTORS':
			self.add_sectors(lump)
		else:
			self.lumps.append(lump)
			
	def add_sidedefs(self, lump):
		self.sidedefs = []
		stream = lump.get_stream()
		try:
			cnt = int(len(lump.data) / 30)
			for i in range(cnt):
				sidedef = DoomLevelSidedef()
				sidedef.xoffs, sidedef.yoffs = struct.unpack('<hh', stream.read(4))
				sidedef.tex_upper = wad.stomp_c_string(stream.read(8)).upper()
				sidedef.tex_lower = wad.stomp_c_string(stream.read(8)).upper()
				sidedef.tex_middle = wad.stomp_c_string(stream.read(8)).upper()
				sidedef.sector = struct.unpack('<H', stream.read(2))[0]
				self.sidedefs.append(sidedef)
		finally:
			stream.close()
			
	def add_sectors(self, lump):
		self.sectors = []
		stream = lump.get_stream()
		try:
			cnt = int(len(lump.data) / 26)
			for i in range(cnt):
				sector = DoomLevelSector()
				sector.height_floor, sector.height_ceiling = struct.unpack('<hh', stream.read(4))
				sector.tex_floor = wad.stomp_c_string(stream.read(8)).upper()
				sector.tex_ceiling = wad.stomp_c_string(stream.read(8)).upper()
				sector.light, sector.special, sector.tag = struct.unpack('<HHH', stream.read(6))
				self.sectors.append(sector)
		finally:
			stream.close()

	def to_wad(self, wf, name):
		map_lump_names = ['THINGS', 'LINEDEFS', 'SIDEDEFS', 'VERTEXES', 'SEGS', 'SSECTORS', 'NODES', 'SECTORS', 'REJECT', 'BLOCKMAP']
		# remove old map from the wad if any
		try:
			num = wf.get_num_for_name(name)
			if num < 0:
				raise DoomLevelError('Map %s not found' % (name))
			numlumps = self.map_len_in_wad(wf, name)
			wf[num+1:num+1+numlumps] = []
			start = num+1
		except:
			ent = wad.WADLump()
			ent.name = name
			wf.append(ent)
			start = len(wf)
		newlumps = []
		for lump_name in map_lump_names:
			if lump_name == 'SIDEDEFS':
				newlumps.append(self.make_sidedefs())
			elif lump_name == 'SECTORS':
				newlumps.append(self.make_sectors())
			else:
				for lump in self.lumps:
					if lump.name.upper() == lump_name:
						newlumps.append(lump)
		wf[start:start] = newlumps

	def make_sidedefs(self):
		lump = wad.WADLump()
		lump.name = 'SIDEDEFS'
		stream = lump.get_stream_write()
		for sidedef in self.sidedefs:
			stream.write(struct.pack('<hh8s8s8sH', sidedef.xoffs, sidedef.yoffs, sidedef.tex_upper, sidedef.tex_lower, sidedef.tex_middle, sidedef.sector))
		stream.save()
		return lump
		
	def make_sectors(self):
		lump = wad.WADLump()
		lump.name = 'SECTORS'
		stream = lump.get_stream_write()
		for sector in self.sectors:
			stream.write(struct.pack('<hh8s8sHHH', sector.height_floor, sector.height_ceiling, sector.tex_floor, sector.tex_ceiling, sector.light, sector.special, sector.tag))
		stream.save()
		return lump
