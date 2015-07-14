# -*- coding: utf-8 -*-

import wad
import struct


class TextureError(Exception):
	pass

	
class Texture1Patch:
	def __init__(self):
		self.name = ''
		self.originx = 0
		self.originy = 0
		
	def __repr__(self):
		return repr((self.name, self.originx, self.originy))
		
		
class Texture1Texture:
	def __init__(self):
		self.name = ''
		self.width = 0
		self.height = 0
		self.patches = []
		
	def __repr__(self):
		return repr({'name': self.name, 'width': self.width, 'height': self.height, 'patches': self.patches})
	

class Texture1(list):
	@classmethod
	def from_wad(self, wf, name):
		texture1 = wf.get_lump(name)
		pnames = wf.get_lump('PNAMES')
		if texture1 is None:
			raise TextureError('Lump %s not found' % (name.upper()))
		if pnames is None:
			raise TextureError('Lump PNAMES not found')
		texture1_stream = texture1.get_stream()
		pnames_stream = pnames.get_stream()
		
		texlist = self()
		
		try:
			pnames_cnt = struct.unpack('<I', pnames_stream.read(4))[0]
			pnames_entries = []
			for i in range(pnames_cnt):
				pnames_entries.append(wad.stomp_c_string(pnames_stream.read(8)).upper())
		
			numtextures = struct.unpack('<I', texture1_stream.read(4))[0]
			for i in range(numtextures):
				texture1_stream.seek(4 + i * 4)
				offset = struct.unpack('<I', texture1_stream.read(4))[0]
				texture1_stream.seek(offset)
				
				name = wad.stomp_c_string(texture1_stream.read(8)).upper()
				masked = struct.unpack('<I', texture1_stream.read(4))[0]
				width, height = struct.unpack('<HH', texture1_stream.read(4))
				columndirectory = struct.unpack('<I', texture1_stream.read(4))[0]
				patchcount = struct.unpack('<H', texture1_stream.read(2))[0]
				
				tex = Texture1Texture()
				tex.name = name
				tex.width = width
				tex.height = height
				
				for j in range(patchcount):
					originx, originy = struct.unpack('<hh', texture1_stream.read(4))
					patch_idx, stepdir, colormap = struct.unpack('<HHH', texture1_stream.read(6))
					
					patch = Texture1Patch()
					patch.name = pnames_entries[patch_idx].upper()
					patch.originx = originx
					patch.originy = originy
					
					tex.patches.append(patch)
					
				texlist.append(tex)
				
		finally:
			pnames_stream.close()
			texture1_stream.close()
		
		return texlist
		
		
	def to_wad(self, wf, name, combine_pnames=False):
		pnames_idx = 0
		pnames_repl = dict()
		pnames_list = []
		
		pnames = wf.get_lump_or_new('PNAMES')
		if combine_pnames:
			pnames_stream = pnames.get_stream()
			pnames_cnt = struct.unpack('<I', pnames_stream.read(4))[0]
			for i in range(pnames_cnt):
				pnames_list.append(wad.stomp_c_string(pnames_stream.read(8)).upper())
				pnames_repl[pnames_list[-1]] = i
			pnames_stream.close()
			pnames_idx = len(pnames_list)

		for tex in self:
			for patch in tex.patches:
				if patch.name not in pnames_repl:
					pnames_repl[patch.name] = pnames_idx
					pnames_list.append(patch.name)
					pnames_idx += 1
					
		pnames_stream = pnames.get_stream_write()
		pnames_stream.write(struct.pack('<I', len(pnames_list)))
		for pnames_ent in pnames_list:
			pnames_stream.write(struct.pack('<8s', pnames_ent))
		pnames_stream.save()
		
		texture1 = wf.get_lump_or_new(name)
		texture1_stream = texture1.get_stream_write()
		texture1_stream.write(struct.pack('<I', len(self)))
		offset = 4 + 4 * len(self)
		for tex in self:
			texture1_stream.write(struct.pack('<I', offset))
			offset += 22 + 10 * len(tex.patches)
		
		for tex in self:
			texture1_stream.write(struct.pack('<8sIHHIH', tex.name, 0, tex.width, tex.height, 0, len(tex.patches)))
			for patch in tex.patches:
				texture1_stream.write(struct.pack('<hhHHH', patch.originx, patch.originy, pnames_repl[patch.name], 0, 0))
		texture1_stream.save()

	def check_name_exists(self, name):
		name = name.upper()
		for tex in self:
			if tex.name == name:
				return True
		return False