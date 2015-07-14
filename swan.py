# -*- coding: utf-8 -*-

# этот класс обеспечивает работу с ANIMATED и SWITCHES лампами, а также с их текстовым представлением (чтобы читать DEFSWANI.dat, в основном, но мало ли)

import wad
import re
import struct

class SwanAnimation:
	def __init__(self):
		self.speed = 1
		self.first = 'AASHITTY'
		self.last = 'AASHITTY'
		self.decals = False
		
		
class SwanSwitch:
	def __init__(self):
		self.version = 3 # 1 = shareware, 2 = doom1, 3 = doom2
		self.off = 'AASHITTY'
		self.on = 'AASHITTY'


class Swan:
	def __init__(self):
		self.switches = []
		self.textures = []
		self.flats = []
		
	@classmethod
	def from_ini(self, filename):
		with open(filename, 'r') as f:
			swan = self()
			raw_text = f.read()
			lines = raw_text.split('\n')
			section = ''
			for line in lines:
				comment_sep = line.find('#')
				if comment_sep >= 0:
					line = line[:comment_sep].strip()
				if not line:
					continue
				if line[0] == '[' and line[-1] == ']':
					section = line[1:-1].lower()
				else:
					line_split = re.split(r'[\s\t]+', line)
					if len(line_split) < 3:
						continue
					if section == 'textures' or section == 'flats':
						anim = SwanAnimation()
						anim.speed = int(line_split[0])
						anim.last = line_split[1].upper()
						anim.first = line_split[2].upper()
						if section == 'textures':
							swan.textures.append(anim)
						else:
							swan.flats.append(anim)
					else:
						swch = SwanSwitch()
						swch.version = int(line_split[0])
						swch.off = line_split[1].upper()
						swch.on = line_split[2].upper()
						swan.switches.append(swch)
			return swan
			
	@classmethod
	def from_wad(self, wf):
		animated = wf.get_lump('ANIMATED')
		switches = wf.get_lump('SWITCHES')
		
		swan = self()
		if animated is not None:
			animated_stream = animated.get_stream()
			while True:
				type = struct.unpack('<B', animated_stream.read(1))[0]
				if type == 255:
					break
				last = wad.stomp_c_string(animated_stream.read(9)).upper()
				first = wad.stomp_c_string(animated_stream.read(9)).upper()
				speed = struct.unpack('<I', animated_stream.read(4))[0]
				anim = SwanAnimation()
				anim.first = first
				anim.last = last
				anim.speed = speed
				anim.decals = (type == 3)
				if type == 0:
					swan.flats.append(anim)
				else:
					swan.textures.append(anim)
			animated_stream.close()

		if switches is not None:
			switches_stream = switches.get_stream()
			while True:
				off = wad.stomp_c_string(switches_stream.read(9)).upper()
				on = wad.stomp_c_string(switches_stream.read(9)).upper()
				version = struct.unpack('<h', switches_stream.read(2))[0]
				if version == 0:
					break
				swch = SwanSwitch()
				swch.off = off
				swch.on = on
				swch.version = version
				swan.switches.append(swch)
				
		return swan

	def to_ini(self, filename):
		with open(filename, 'w') as f:
			f.write('[TEXTURES]\r\n')
			for texture in self.textures:
				f.write('%-8d %-8s %-8s\r\n' % (texture.speed, texture.last, texture.first))
			f.write('\r\n[FLATS]\r\n')
			for flat in self.flats:
				f.write('%-8d %-8s %-8s\r\n' % (flat.speed, flat.last, flat.first))
			f.write('\r\n[SWITCHES]\r\n')
			for switch in self.switches:
				f.write('%-8d %-8s %-8s\r\n' % (switch.version, switch.off, switch.on))
			f.write('\r\n')

	def to_wad(self, wf):
		if len(self.textures) or len(self.flats):
			animated = wf.get_lump_or_new('ANIMATED')
			animated.data = ''
			animated_stream = animated.get_stream_write()
			for texture in self.textures:
				animated_stream.write(struct.pack('<B9s9sI', 3 if texture.decals else 1, texture.last, texture.first, texture.speed))
			for flat in self.flats:
				animated_stream.write(struct.pack('<B9s9sI', 0, flat.last, flat.first, flat.speed))
			animated_stream.write(struct.pack('<B', 255))
			animated_stream.save()
		
		if len(self.switches):
			switches = wf.get_lump_or_new('SWITCHES')
			switches.data = ''
			switches_stream = switches.get_stream_write()
			for switch in self.switches:
				switches_stream.write(struct.pack('<9s9sh', switch.off, switch.on, switch.version))
			switches_stream.write(struct.pack('<9s9sh', '', '', 0))
			switches_stream.save()

	def merge_another(self, swan):
		for texture in swan.textures:
			found = False
			for texture_own in self.textures:
				if texture_own.first == texture.first and\
				   texture_own.last == texture.last:
					found = True
					texture_own.speed = texture.speed
					texture_own.decals = texture.decals
					break
			if not found:
				self.textures.append(texture)
		for flat in swan.flats:
			found = False
			for flat_own in self.flats:
				if flat_own.first == flat.first and\
				   flat_own.last == flat.last:
					found = True
					flat_own.speed = flat.speed
					break
			if not found:
				self.flats.append(flat)
		for switch in swan.switches:
			found = False
			for switch_own in self.switches:
				if switch_own.off == switch.off and\
				   switch_own.on == switch.on:
					found = True
					switch_own.version = switch.version
					break
			if not found:
				self.switches.append(switch)
