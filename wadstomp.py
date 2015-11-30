# -*- coding: utf-8 -*-

# BEWARE
# COMMENTS ARE IN _RUSSIAN_

# wadstomp.py -iwad <wadname> -file <wadname2> <wadname3> <wadname4> -map <mapname> -out <out_wadname> -outmap <out_mapname>
#  (-maponly)

# алгоритм на всякий случай.
#  1) хэш текстуры = md5 на все патчи внутри, плюс данные из ANIMATED/SWITCHES
#  2) хэш патча = md5 ( хэш лампа + xoffs + yoffs )
#  3) хэш флэта = md5 лампа
#
# ключевые моменты
#  - две текстуры, в которых одинаковые патчи с одинаковыми оффсетами, но одна свитч, а вторая нет — это РАЗНЫЕ текстуры, и их надо держать отдельно.
#     - причём учитывая хуёвую организацию анимаций в буме, то анимации в общем-то нужно вообще как-то отдельно обрабатывать, потому что там получается что надо копировать все текстуры участвующие в анимации, и сохраняя порядок.
#  - аналогично с анимациями
#  - при копировании текстур сверяется сначала общий хэш. если он совпадает с существующей текстурой, то в карте все использования этой текстуры меняются на существующую, и ничего не копируется.
#  - если в текстуре совпадают некоторые (или все) патчи, но не их порядок, то патчи заново НЕ КОПИРУЮТСЯ. в текстуре меняются названия патчей на существующие.
#  - с флэтами аналогично, только гораздо проще: тут сверяется один ламп
#  - если оказывается, что в выхлопном ваде уже есть текстура с таким названием (но хэш другой), то новая текстура переименовывается (и в карте тоже)

import hashlib
import sys

NameIWAD = None
NamePWADs = []
NameMap = None
NameOutMap = None
NameOutWAD = None

DefSwAni = 'swan_defswani.dat'

_argv_files_started = False
for i in range(1, len(sys.argv)):
	if sys.argv[i] == '-iwad' and (i+1) < len(sys.argv):
		_argv_files_started = False
		NameIWAD = sys.argv[i+1]
	elif sys.argv[i] == '-file':
		_argv_files_started = True
	elif _argv_files_started and sys.argv[i][0] != '-':
		NamePWADs.append(sys.argv[i])
	elif sys.argv[i] == '-map' and (i+1) < len(sys.argv):
		_argv_files_started = False
		NameMap = sys.argv[i+1].upper()
	elif sys.argv[i] == '-out' and (i+1) < len(sys.argv):
		_argv_files_started = False
		NameOutWAD = sys.argv[i+1]
	elif sys.argv[i] == '-outmap' and (i+1) < len(sys.argv):
		_argv_files_started = False
		NameOutMap = sys.argv[i+1].upper()
	elif sys.argv[i] == '-defswani' and (i+1) < len(sys.argv):
		_argv_files_started = False
		DefSwAni = sys.argv[i+1]

if NameIWAD is None:
	print('IWAD is required.')
	sys.exit(1)
	
# если указана карта, то вытаскиваются только текстуры, использованные в этой карте. и мерджатся в один вад, вместе с этой картой.
# если карта не указана, то вытаскиваются вообще все текстуры из -file и мерджатся в один вад.

if len(NamePWADs) <= 0:
	print('PWADs not specified, nothing to do.')
	sys.exit(1)

print('=================================')
print('IWAD: %s' % (NameIWAD))
print('PWAD(s):\n%s' % ('\n'.join(NamePWADs)))
if NameMap is not None:
	print('Map: %s' % (NameMap))
	if NameOutMap is None:
		NameOutMap = NameMap
	print('Output map: %s' % (NameOutMap))
if NameOutWAD is None:
	NameOutWAD = 'wstomped.wad'
print('Output WAD: %s' % (NameOutWAD))
print('=================================')


# ########################################################## #
#   тут начинаем собственно чото делать                      #
# ########################################################## #

from wad import WADFile, WADLump

try:
	IWAD = WADFile.from_file(NameIWAD)
except:
	print('Couldn\'t load IWAD!')
	raise

PWADs = []
for name in NamePWADs:
	try:
		PWAD = WADFile.from_file(name)
		PWADs.append(PWAD)
	except:
		print('Couldn\'t load PWAD (%s)!' % (name))
		raise


try:
	OutWAD = WADFile.from_file(NameOutWAD)
except:
	OutWAD = WADFile()


from texture import Texture1, Texture1Texture, Texture1Patch
from level import DoomLevel

# собираем текстуры со всех вадов.
TexIWAD = Texture1.from_wad(IWAD, 'TEXTURE1')
TexPWADs = []
for pwad in PWADs:
	try:
		tex = Texture1.from_wad(pwad, 'TEXTURE2')
		TexPWADs.append(tex)
	except:
		TexPWADs.append(None)
	try:
		tex = Texture1.from_wad(pwad, 'TEXTURE1')
		if TexPWADs[-1] is not None:
			TexPWADs[-1] += tex
		else:
			TexPWADs[-1] = tex
	except:
		pass


Map = None

	
# возможно, в выхлопном ваде уже есть текстуры.
# возможно, даже TEXTURE1.
try:
	TexOutWAD = Texture1.from_wad(OutWAD, 'TEXTURE2')
except:
	TexOutWAD = Texture1()
try:
	TexOutWAD += Texture1.from_wad(OutWAD, 'TEXTURE1')
except:
	pass
	
def global_get_last_file(name, iwad=False): # scans all PWADs and returns the lump. returns none if not in PWADs. used for patches.
	global IWAD
	global PWADs
	for i in reversed(range(len(PWADs))):
		wf = PWADs[i]
		lump = wf.get_lump(name)
		if lump is not None:
			return lump
	if iwad:
		return IWAD.get_lump(name)
	return None
	
	
def global_get_last_file_marked(name, start, end, iwad=False): # does the same as _file, but only in F_ and FF_ directories
	global IWAD
	global PWADs
	if iwad:
		wadlist = [IWAD] + PWADs
	else:
		wadlist = PWADs
	for wf in reversed(wadlist):
		nums = wf.get_nums_between(start, end)
		for num in nums:
			if wf[num].name == name.upper():
				return wf[num]
	return None
	

def global_get_last_texture(name, tex=None, iwad=False): # scans all PWADs and returns texture or None
	global IWAD
	global TexPWADs
	if tex is None:
		texlist = TexPWADs
	else:
		texlist = [tex]
	if iwad:
		texlist[0:0] = [TexIWAD]
	for textures in reversed(texlist):
		if textures is None:
			continue
		for tex in textures:
			if tex.name.upper() == name:
				return tex
	return None
	
	
def global_get_last_texture_md5(md5, tex=None, iwad=False): # scans all PWADs and returns texture or None. for animations.
	global IWAD
	global TexPWADs
	if tex is None:
		texlist = TexPWADs
	else:
		texlist = [tex]
	if iwad:
		texlist[0:0] = [TexIWAD]
	for textures in reversed(texlist):
		if textures is None:
			continue
		for tex in textures:
			if not hasattr(tex, 'md5'):
				tex.md5 = calc_texture_hash(tex)
			if tex.md5 == md5:
				return tex
	return None


def global_get_last_map(name): # scans all PWADs for a map file.
	global IWAD
	global PWADs
	for i in reversed(range(len(PWADs))):
		try:
			map = DoomLevel.from_wad(PWADs[i], name)
			return map
		except:
			continue
	try:
		map = DoomLevel.from_wad(IWAD, name)
		return map
	except:
		return None
	
	
def calc_texture_hash(tex, patch_wad=None):
	global IWAD
	hs = []
	hs.append('%s,%s' % (tex.width, tex.height))
	for patch in tex.patches:
		patch_md5 = 'None'
		if patch_wad is None:
			patch_file = global_get_last_file(patch.name, True)
		else:
			patch_file = patch_wad.get_lump(patch.name)
			if patch_file is None:
				patch_file = IWAD.get_lump(patch.name)
		if patch_file is not None:
			patch_md5 = hashlib.md5(patch_file.data).hexdigest()
		hs.append('%d,%d,%s' % (patch.originx, patch.originy, patch_md5))
	return hashlib.md5(';'.join(hs)).hexdigest()


# считаем необходимые чексуммы.
print('Calculating IWAD hashes...')
for tex_iwad in TexIWAD:
	tex_iwad.md5 = calc_texture_hash(tex_iwad, IWAD)
print('IWAD hashes calculated.')
print('Calculating output hashes...')
for tex_out in TexOutWAD:
	tex_out.md5 = calc_texture_hash(tex_out, OutWAD)
print('Output hashes calculated.')
print('Calculating output lump hashes...')
for lump in OutWAD:
	lump.md5 = hashlib.md5(lump.data).hexdigest()
print('Output lump hashes calculated.')

	
print('Loading ANIMATED/SWITCHES definitions...')
from swan import Swan, SwanAnimation, SwanSwitch
SwanInternal = Swan.from_ini(DefSwAni)
if IWAD.get_lump('ANIMATED') is not None or IWAD.get_lump('SWITCHES') is not None:
	SwanInternal.merge_another(Swan.from_wad(IWAD))
SwanPWADs = Swan()
SwanPWADs.switches = SwanInternal.switches
SwanPWADs.textures = SwanInternal.textures
SwanPWADs.flats = SwanInternal.flats
for wf in PWADs:
	has_animated = (wf.get_lump('ANIMATED') is not None)
	has_switches = (wf.get_lump('SWITCHES') is not None)
	if not has_animated and not has_switches:
		continue
	wf_swan = Swan.from_wad(wf)
	if has_animated:
		SwanPWADs.textures = wf_swan.textures
		SwanPWADs.flats = wf_swan.flats
	if has_switches:
		SwanPWADs.switches = wf_swan.switches
SwanOutWAD = Swan.from_wad(OutWAD)

	
def calc_animated_hash(anim, is_flat, wf=None, tex=None):
	global IWAD
	global PWADs
	if wf is None:
		wadlist = [IWAD]+PWADs
	else:
		wadlist = [wf]
	if tex is None:
		texlist = [TexIWAD]+TexPWADs
	else:
		texlist = [tex]
	# anim.lumps = ...
	if not is_flat:
		anim.names = []
		anim.lumps = []
		for textures in reversed(texlist):
			if textures is None:
				continue
			if not textures.check_name_exists(anim.first) or not textures.check_name_exists(anim.last):
				continue
			num_first = -1
			num_last = -1
			for i in range(len(textures)):
				if textures[i].name == anim.first:
					num_first = i
				elif textures[i].name == anim.last:
					num_last = i
			if num_first < 0 or num_last < 0 or num_last < num_first:
				continue
			for i in range(num_first, num_last+1):
				textures[i].anim = anim
				anim.lumps.append(calc_texture_hash(textures[i], wf))
				anim.names.append(textures[i].name)
			break
		hash = ['%d,%d' % (1 if not anim.decals else 3, anim.speed)]
		hash += anim.lumps
		anim.md5 = hashlib.md5(';'.join(hash)).hexdigest()
	else:
		anim.names = []
		anim.lumps = []
		for wf in reversed(wadlist):
			nums = wf.get_nums_between('F_START', 'F_END')
			nums += wf.get_nums_between('FF_START', 'FF_END')
			num_first = -1
			num_last = -1
			for num in nums:
				if wf[num].name == anim.first:
					num_first = num
				elif wf[num].name == anim.last:
					num_last = num
			if num_first < 0 or num_last < 0 or num_last < num_first:
				continue
			for num in range(num_first, num_last+1):
				wf[num].anim = anim
				anim.lumps.append(hashlib.md5(wf[num].data).hexdigest())
				anim.names.append(wf[num].name)
			break
		hash = ['%d' % (anim.speed)]
		hash += anim.lumps
		anim.md5 = hashlib.md5(';'.join(hash)).hexdigest()
		
		
def calc_switch_hash(swch, wf=None, tex=None):
	# у свитча (точнее, у его off и on частей) есть 3 параметра
	#  - анимация или None
	#  - хеш картинки
	#  - номер этого хеша, если одинаковая картинка юзается несколько раз. обычно 0.
	tex_off = global_get_last_texture(swch.off, tex, (wf is None))
	tex_on = global_get_last_texture(swch.on, tex, (wf is None))
	if tex_off is None or tex_on is None:
		swch.md5 = ''
		return
	tex_off.swch = swch
	tex_on.swch = swch
	if not hasattr(tex_off, 'md5'):
		tex_off.md5 = calc_texture_hash(tex_off)
	if not hasattr(tex_on, 'md5'):
		tex_on.md5 = calc_texture_hash(tex_on)
	swch.off_md5 = tex_off.md5
	swch.on_md5 = tex_on.md5
	swch.off_anim = tex_off.anim if hasattr(tex_off, 'anim') else None
	swch.on_anim = tex_on.anim if hasattr(tex_on, 'anim') else None
	swch.off_idx = 0
	swch.on_idx = 0
	if swch.off_anim is not None:
		for i in range(len(swch.off_anim.names)):
			lumpname = swch.off_anim.names[i]
			lump = swch.off_anim.lumps[i]
			if lump == swch.off_md5 and lumpname != swch.off:
				swch.off_idx += 1
			elif lump == swch.off_md5:
				break
	if swch.on_anim is not None:
		for i in range(len(swch.on_anim.names)):
			lumpname = swch.on_anim.names[i]
			lump = swch.on_anim.lumps[i]
			if lump == swch.on_md5 and lumpname != swch.on:
				swch.off_idx += 1
			elif lump == swch.on_md5:
				break
	hash = ['%d' % (swch.version)]
	hash.append('%s,%s,%d' % (swch.off_md5, swch.off_anim.md5 if swch.off_anim is not None else '', swch.off_idx))
	hash.append('%s,%s,%d' % (swch.on_md5, swch.on_anim.md5 if swch.on_anim is not None else '', swch.on_idx))
	swch.md5 = hashlib.md5(';'.join(hash)).hexdigest()


print('Calculating animation hashes...')
for anim in SwanInternal.textures:
	calc_animated_hash(anim, False, IWAD, TexIWAD)
for anim in SwanInternal.flats:
	calc_animated_hash(anim, True, IWAD, TexIWAD)

for anim in SwanOutWAD.textures:
	calc_animated_hash(anim, False, OutWAD, TexOutWAD)
for anim in SwanOutWAD.flats:
	calc_animated_hash(anim, True, OutWAD, TexOutWAD)

for anim in SwanPWADs.textures:
	calc_animated_hash(anim, False, None, None)
for anim in SwanPWADs.flats:
	calc_animated_hash(anim, True, None, None)
print('Animation hashes calculated.')


print('Calculating switch hashes...')
for swch in SwanInternal.switches:
	calc_switch_hash(swch, IWAD, TexIWAD)

for swch in SwanOutWAD.switches:
	calc_switch_hash(swch, OutWAD, TexOutWAD)
	
for swch in SwanPWADs.switches:
	calc_switch_hash(swch, None, None)
print('Switch hashes calculated.')


if NameMap is not None:
	Map = global_get_last_map(NameMap)
	if Map is None:
		print('Error: the specified map (%s) not found.' % (NameMap))
		sys.exit(1)


TexturesToCopy = list()
TexturesToCopyAnimated = list() # [animation, hash1, hash2, hash3, ...]
FlatsToCopy = list()
FlatsToCopyAnimated = list() # same as textures
TexturesToRename = dict() # for example, if two different textures are called HI, the other one will be renamed to HI001.
FlatsToRename = dict()


if Map is not None:
	# и делаем список текстур на этой карте.
	for sidedef in Map.sidedefs:
		if sidedef.tex_upper != '-' and sidedef.tex_upper not in TexturesToCopy:
			TexturesToCopy.append(sidedef.tex_upper)
		if sidedef.tex_middle != '-' and sidedef.tex_middle not in TexturesToCopy:
			TexturesToCopy.append(sidedef.tex_middle)
		if sidedef.tex_lower != '-' and sidedef.tex_lower not in TexturesToCopy:
			TexturesToCopy.append(sidedef.tex_lower)
	for sector in Map.sectors:
		if sector.tex_floor not in FlatsToCopy:
			FlatsToCopy.append(sector.tex_floor)
		if sector.tex_ceiling not in FlatsToCopy:
			FlatsToCopy.append(sector.tex_ceiling)
else:
	for i in reversed(range(len(PWADs))):
		wf = PWADs[i]
		# outer loop
		offset = 0
		markers = ['F_START', 'F_END', 'FF_START', 'FF_END']
		for j in range(2):
			nums = wf.get_nums_between(markers[j*2], markers[j*2+1])
			for num in nums:
				FlatsToCopy.append(wf[num].name)
		# now do the same to textures
		if TexPWADs[i] is not None:
			for tex in TexPWADs[i]:
				if tex.name not in TexturesToCopy:
					TexturesToCopy.append(tex.name)


print('%d flats and %d textures prepared to copy.' % (len(FlatsToCopy), len(TexturesToCopy)))


# enumerate flats in the out wad (if any). we'll need hashes.
FlatsOutWAD = []
markers = ['F_START', 'F_END', 'FF_START', 'FF_END']
for j in range(2):
	nums = OutWAD.get_nums_between(markers[j*2], markers[j*2+1])
	for num in nums:
		FlatsOutWAD.append(OutWAD[num])					
print('%d flats already present in output WAD.' % (len(FlatsOutWAD)))


# check if we even have a flat directory yet
ff_num = OutWAD.get_num_for_name('FF_START')
if ff_num < 0:
	ff_start = WADLump()
	ff_start.name = 'FF_START'
	ff_start.md5 = ''
	ff_end = WADLump()
	ff_end.name = 'FF_END'
	ff_end.md5 = ''
	OutWAD.append(ff_start)
	ff_num = len(OutWAD)
	OutWAD.append(ff_end)
else:
	ff_num += 1

	
# проверяем, чтобы здесь не пытались копировать анимированные флэты.
# если попытались, то выпиливаем флэты из общего списка и впиливаем в отдельный.
i = -1
while i+1 < len(FlatsToCopy):
	i += 1
	flat_src = FlatsToCopy[i]
	file_src = global_get_last_file_marked(flat_src, 'F_START', 'F_END', True)
	if file_src is None:
		file_src = global_get_last_file_marked(flat_src, 'FF_START', 'FF_END', True)
	if file_src is None: # not in PWADs, hence can't be copied
		continue
	if hasattr(file_src, 'anim'):
		print(' * flat %s is animated (%s)' % (flat_src, ','.join(file_src.anim.names)))
		del FlatsToCopy[i]
		i -= 1
		if file_src.anim not in FlatsToCopyAnimated:
			FlatsToCopyAnimated.append(file_src.anim)
	
	
# ######################################################## #
#   копируем флэты, в данный момент не учитывая ANIMATED   #
#    в будущем нужно будет форсированно копировать все     #
#    флэты для анимации, если анимация в OutWAD            #
#    не совпадает (или её нет)                             # 
# ######################################################## #
for flat_src in FlatsToCopy:
	file_src = global_get_last_file_marked(flat_src, 'F_START', 'F_END')
	if file_src is None:
		file_src = global_get_last_file_marked(flat_src, 'FF_START', 'FF_END')
	if file_src is None: # not in PWADs, hence can't be copied
		print(' * skipped flat %s (not in PWADs)' % (flat_src))
		continue
	md5_src = hashlib.md5(file_src.data).hexdigest()
	# now check if we already have a flat with this hash in the output PWAD
	found = False
	for file_dst in FlatsOutWAD:
		md5_dst = hashlib.md5(file_dst.data).hexdigest()
		if md5_dst == md5_src and not hasattr(file_dst, 'anim'): # мы не копируем анимации здесь. если в выхлопном файле есть совпадение, но оно включено в анимацию, то мы его игнорируем.
			print(' * skipped flat %s (duplicate %s in output WAD)' % (flat_src, file_dst.name))
			FlatsToRename[flat_src] = file_dst.name
			found = True
			break
	if not found:
		file_dst = WADLump()
		file_dst.name = file_src.name
		file_dst.data = file_src.data
		# check if there's a flat with the same name. rename if so.
		n2_tpl = file_dst.name
		for i in range(1000): # 0 to 999
			file_dst2 = OutWAD.get_lump_between(n2_tpl, 'F_START', 'F_END')
			if file_dst2 is None:
				file_dst2 = OutWAD.get_lump_between(n2_tpl, 'FF_START', 'FF_END')
			# и за компанию нужно убедиться что мы не заменяем полностью флэт из ивада. потому что мы можем в итоге мержить несколько уровней, один из которых заменяет флэты, а другой нет.
			if file_dst2 is None:
				file_dst2 = IWAD.get_lump_between(n2_tpl, 'F_START', 'F_END')
			if file_dst2 is not None:
				n2_tpl = file_dst.name[0:5]+('%03d'%i)
				continue
			break
		if n2_tpl != file_dst.name:
			print(' * flat name conflict, renamed %s -> %s' % (file_dst.name, n2_tpl))
			FlatsToRename[file_dst.name] = n2_tpl
			file_dst.name = n2_tpl
		file_dst.md5 = md5_src
		OutWAD[ff_num:ff_num] = [file_dst]
		ff_num += 1
		

# допиливаем флэты, которые были указаны в ANIMATED. копируем ВСЕГДА ВСЮ СЕРИЮ, даже из ивада, кроме тех случаев, когда полностью совпала анимация (в таком случае переименовываем флэт)
FlatsIn = []
wadlist = [IWAD]+PWADs
markers = ['F_START', 'F_END', 'FF_START', 'FF_END']
for wf in wadlist:
	for j in range(2):
		nums = wf.get_nums_between(markers[j*2], markers[j*2+1])
		for num in nums:
			if not hasattr(wf[num], 'md5'):
				wf[num].md5 = hashlib.md5(wf[num].data).hexdigest()
			FlatsIn.append(wf[num])
			
for anim in FlatsToCopyAnimated:
	found = False
	for anim_iwad in SwanInternal.flats:
		if anim_iwad.md5 == anim.md5:
			anim_iwad_new = SwanAnimation()
			anim_iwad_new.first = anim_iwad.first
			anim_iwad_new.last = anim_iwad.last
			anim_iwad_new.speed = anim_iwad.speed
			calc_animated_hash(anim_iwad_new, True, None, None)
			if anim_iwad_new.md5 == anim.md5:
				found = True
				print(' * skipped flat animation %s..%s (duplicate %s..%s in IWAD)' % (anim.first, anim.last, anim_iwad.first, anim_iwad.last))
				# переименовываем все флэты из одной анимации в флэты из другой.
				for i in range(len(anim_iwad.lumps)):
					FlatsToRename[anim.names[i]] = anim_iwad.names[i]
				break
	if found:
		continue
	for anim_out in SwanOutWAD.flats:
		if anim_out.md5 == anim.md5:
			found = True
			print(' * skipped flat animation %s..%s (duplicate %s..%s in output WAD)' % (anim.first, anim.last, anim_out.first, anim_out.last))
			for i in range(len(anim_out.lumps)):
				FlatsToRename[anim.names[i]] = anim_out.names[i]
			break
	if found:
		continue
	# теперь тупо копируем к флэтам в OutWAD полностью всё, что совпадает по хэшам. да, из ивада тоже.
	# и добавляем в SwanOutWAD анимацию с этими флэтами.
	# названия переименовываем, если совпадают.
	names_new = []
	for i in range(len(anim.lumps)):
		lump = anim.lumps[i]
		lumpname = anim.names[i]
		for flat in FlatsIn:
			if flat.md5 == lump:
				break
		if flat.md5 != lump:
			print(' * warning: hash %s (originally %s) not found.' % (lump, lumpname))
		n2_tpl = flat.name
		for i in range(1000): # 0 to 999
			flat2 = OutWAD.get_lump_between(n2_tpl, 'F_START', 'F_END')
			if flat2 is None:
				flat2 = OutWAD.get_lump_between(n2_tpl, 'FF_START', 'FF_END')
			if flat2 is None:
				flat2 = IWAD.get_lump_between(n2_tpl, 'F_START', 'F_END')
			if flat2 is not None:
				n2_tpl = flat.name[0:5]+('%03d'%i)
				continue
			break
		if n2_tpl != flat.name:
			print(' * flat name conflict, renamed %s -> %s' % (flat.name, n2_tpl))
			FlatsToRename[flat.name] = n2_tpl
		file_dst = WADLump()
		file_dst.name = n2_tpl
		file_dst.data = flat.data
		file_dst.md5 = flat.md5
		OutWAD[ff_num:ff_num] = [file_dst]
		names_new.append(file_dst.name)
		ff_num += 1
	# add animation.
	anim_new = SwanAnimation()
	anim_new.speed = anim.speed
	anim_new.first = names_new[0]
	anim_new.last = names_new[-1]
	SwanOutWAD.flats.append(anim_new)
		

SwitchesToCopy = []
# проверяем текстуры со свитчами. каждый свитч подразумевает копирование своей второй части, в том числе в ANIMATED, поэтому это ставим перед анимациями
for i in range(len(TexturesToCopy)): # чтобы чётко до текущего конца доходило, а не бесконечно рекурсировало
	tex_src_name = TexturesToCopy[i]
	for swch in SwanInternal.switches:
		added = False
		if swch.off == tex_src_name and swch.on not in TexturesToCopy:
			TexturesToCopy.append(swch.on)
			print(' * texture %s is a switch (-> %s)' % (swch.off, swch.on))
			added = True
		if swch.on == tex_src_name and swch.off not in TexturesToCopy:
			TexturesToCopy.append(swch.off)
			print(' * texture %s is a switch (-> %s)' % (swch.on, swch.off))
			added = True
		#if added and swch not in SwitchesToCopy:
		#	SwitchesToCopy.append(swch)
		# а вот тут кроется песец, жирный такой.
		# если мы копируем свитч, то нужно пересчитать хэш, с тем рассчётом чтобы если мы заменили свитчу картинку, она нормально добавилась как ещё 1 свитч.
		if added:
			swch_new = SwanSwitch()
			swch_new.version = swch.version
			swch_new.off = swch.off
			swch_new.on = swch.on
			calc_switch_hash(swch_new, None, None)
			SwitchesToCopy.append(swch_new)
	for swch in SwanPWADs.switches:
		added = False
		if swch.off == tex_src_name and swch.on not in TexturesToCopy:
			TexturesToCopy.append(swch.on)
			print(' * texture %s is a switch (-> %s)' % (swch.off, swch.on))
			added = True
		if swch.on == tex_src_name and swch.off not in TexturesToCopy:
			TexturesToCopy.append(swch.off)
			print(' * texture %s is a switch (-> %s)' % (swch.on, swch.off))
			added = True
		if added and swch not in SwitchesToCopy:
			SwitchesToCopy.append(swch)
			
			
# проверяем анимированные текстуры. удаляем такие из TexturesToCopy, добавляем в TexturesToCopyAnimated.
i = -1
while i+1 < len(TexturesToCopy):
	i += 1
	tex_src_name = TexturesToCopy[i]
	tex_src = global_get_last_texture(tex_src_name)
	if tex_src is None:
		continue
	if hasattr(tex_src, 'anim'):
		print(' * texture %s is animated (%s)' % (tex_src_name, ','.join(tex_src.anim.names)))
		del TexturesToCopy[i]
		i -= 1
		if tex_src.anim not in TexturesToCopyAnimated:
			TexturesToCopyAnimated.append(tex_src.anim)


# ###################### #
#   копируем текстуры.   #
# ###################### #		
def copy_texture(tex_src):
	global TexOutWAD
	global IWAD
	global OutWAD
	global TexturesToRename
	global SwitchesToCopy
	tex_src_name = tex_src.name
	tex_dst = Texture1Texture()
	tex_dst.name = tex_src_name
	tex_dst.width = tex_src.width
	tex_dst.height = tex_src.height
	# проверяем, что имя не занято. если занято, переименовываем.
	n2_tpl = tex_dst.name
	for i in range(1000): # 0 to 999
		# и заодно проверяем чтобы в иваде не было такой текстуры
		if TexOutWAD.check_name_exists(n2_tpl) or TexIWAD.check_name_exists(n2_tpl):
			n2_tpl = tex_dst.name[0:5]+('%03d'%i)
			continue
		break
	if n2_tpl != tex_dst.name:
		print(' * texture name conflict, renamed %s -> %s' % (tex_dst.name, n2_tpl))
		TexturesToRename[tex_dst.name] = n2_tpl
		tex_dst.name = n2_tpl
	# теперь смотрим патчи.
	# патчи ищутся по хэшу, если в выхлопном файле есть патч с таким же хэшем, он юзается.
	# подозреваю, что этот момент может и будет приводить к всяким приколам... гыгы. (с)
	# по сути мы повторяем функционал calc_texture_hash, только пошагово.
	for patch in tex_src.patches:
		patch_file = global_get_last_file(patch.name, False)
		# считается, что если patch_file не нашёлся в PWADах, значит он есть в IWAD и тупо надо использовать его имя как есть.
		patch_dst = Texture1Patch()
		patch_dst.originx = patch.originx
		patch_dst.originy = patch.originy
		if patch_file is None:
			patch_dst.name = patch.name
			tex_dst.patches.append(patch_dst)
			continue
		patch_md5 = hashlib.md5(patch_file.data).hexdigest()
		found = False
		for out_lump in OutWAD:
			if out_lump.md5 == patch_md5:
				print(' * reusing patch %s for %s' % (out_lump.name, patch.name))
				patch_dst.name = out_lump.name
				tex_dst.patches.append(patch_dst)
				found = True
				break
		if found:
			continue
		# патч не нашёлся в выхлопном ваде. копируем патч (и переименовываем, если накладывается имя)
		out_lump = WADLump()
		out_lump.md5 = patch_md5
		out_lump.name = patch_file.name
		out_lump.data = patch_file.data
		n2_tpl = out_lump.name
		for i in range(1000): # 0 to 999
			out_file2 = OutWAD.get_lump(n2_tpl)
			if out_file2 is None:
				out_file2 = IWAD.get_lump(n2_tpl)
			if out_file2 is not None:
				n2_tpl = out_lump.name[0:5]+('%03d'%i)
				continue
			break
		if n2_tpl != out_lump.name:
			print(' * patch name conflict, renamed %s -> %s' % (out_lump.name, n2_tpl))
			out_lump.name = n2_tpl
		OutWAD.append(out_lump)
		patch_dst.name = out_lump.name
		tex_dst.patches.append(patch_dst)
	tex_dst.md5 = calc_texture_hash(tex_dst, OutWAD)
	TexOutWAD.append(tex_dst)
	return tex_dst

for tex_src_name in TexturesToCopy:
	# во-первых, для каждой текстуры нужно посчитать патчи хэшами.
	#  из патчей и самой текстуры составить ещё один хэш, отдельный.
	#  если какой-то патч не существует в пвадах, он уничтожается. потому что мы юзаем TEXTURE2.
	tex_src = global_get_last_texture(tex_src_name)
	if tex_src is None:
		print(' * skipped texture %s (not in PWADs)' % (tex_src_name))
		continue
	tex_md5 = calc_texture_hash(tex_src)
	# все текстуры копируемые сейчас — без анимации! поэтому если совпадает с любой текстурой в анимации (с атрибутом anim), то это НЕ ТА ЖЕ САМАЯ ТЕКСТУРА!
	# проверяем, что текстура есть в иваде с таким же хэшем. есть есть, скипаем.
	found = False
	for tex_iwad in TexIWAD:
		if tex_iwad.md5 == tex_md5 and not hasattr(tex_iwad, 'anim'):
			found = True
			break
	if found:
		print(' * skipped texture %s (in IWAD already as %s)' % (tex_src_name, tex_iwad.name))
		TexturesToRename[tex_src_name] = tex_iwad.name
		continue
	# проверяем, что точно такой же текстуры (с точно такими же параметрами) нет в OutWAD.
	found = False
	for tex_out in TexOutWAD:
		if tex_out.md5 == tex_md5 and not hasattr(tex_iwad, 'anim'):
			print(' * skipped texture %s (duplicate %s in output WAD)' % (tex_src.name, tex_out.name))
			TexturesToRename[tex_src.name] = tex_out.name
			found = True
			break
	if found:
		continue
	copy_texture(tex_src)

	
# допиливаем анимированные текстуры.
for anim in TexturesToCopyAnimated:
	# проверяем, что этой анимации нет в иваде или в выхлопном ваде.
	found = False
	for anim_iwad in SwanInternal.textures:
		if anim_iwad.md5 == anim.md5:
			# убеждаемся, что то что мы видим в иваде это действительно именно оно.
			anim_iwad_new = SwanAnimation()
			anim_iwad_new.first = anim_iwad.first
			anim_iwad_new.last = anim_iwad.last
			anim_iwad_new.speed = anim_iwad.speed
			anim_iwad_new.decals = anim_iwad.decals
			calc_animated_hash(anim_iwad_new, False, None, None)
			if anim_iwad_new.md5 == anim.md5:
				found = True
				print(' * skipped texture animation %s..%s (duplicate %s..%s in IWAD)' % (anim.first, anim.last, anim_iwad.first, anim_iwad.last))
				# переименовываем все текстуры из одной анимации в текстуры из другой.
				for i in range(len(anim_iwad.lumps)):
					TexturesToRename[anim.names[i]] = anim_iwad.names[i]
				break
	if found:
		continue
	for anim_out in SwanOutWAD.textures:
		if anim_out.md5 == anim.md5:
			found = True
			print(' * skipped texture animation %s..%s (duplicate %s..%s in output WAD)' % (anim.first, anim.last, anim_out.first, anim_out.last))
			for i in range(len(anim_out.lumps)):
				TexturesToRename[anim.names[i]] = anim_out.names[i]
			break
	if found:
		continue
	names_new = []
	lumps_new = []
	for i in range(len(anim.lumps)):
		lump = anim.lumps[i]
		lumpname = anim.names[i]
		tex = global_get_last_texture_md5(lump)
		if tex is None:
			print(' * warning: hash %s (originally %s) not found.' % (lump, lumpname))
			continue
		tex_new = copy_texture(tex)
		names_new.append(tex_new.name)
		lumps_new.append(lump)
	# add animation.
	anim_new = SwanAnimation()
	anim_new.decals = anim.decals
	anim_new.speed = anim.speed
	anim_new.first = names_new[0]
	anim_new.last = names_new[-1]
	anim_new.names = names_new
	anim_new.lumps = lumps_new
	calc_animated_hash(anim_new, False, OutWAD, TexOutWAD)
	SwanOutWAD.textures.append(anim_new)


# копируем свитчи.
for swch in SwitchesToCopy:
	found = False
	for swch_iwad in SwanInternal.switches:
		if swch_iwad.md5 == swch.md5:
			print(' * skipped switch %s/%s (duplicate %s/%s in IWAD)' % (swch.off, swch.on, swch_iwad.off, swch_iwad.on))
			found = True
			break
	if found:
		continue
	for swch_out in SwanOutWAD.switches:
		if swch_out.md5 == swch.md5:
			print(' * skipped switch %s/%s (duplicate %s/%s in output WAD)' % (swch.off, swch.on, swch_out.off, swch_out.on))
			found = True
			break
	if found:
		continue
	# если анимации нет, тогда всё просто — ищем текстуру по мд5.
	# если анимация есть, тогда ищем в OutWAD анимацию по мд5, и от её содержания отталкиваемся.
	if swch.off_anim is None:
		off = global_get_last_texture_md5(swch.off_md5, TexOutWAD)
	else:
		swanim = None
		for anim in SwanOutWAD.textures:
			if anim.md5 == swch.off_anim.md5:
				swanim = anim
				break
		if swanim is None:
			off = None
		else:
			idx = 0
			for i in range(len(swanim.lumps)):
				if swanim.lumps[i] == swch.off_md5:
					if idx == swch.off_idx:
						off = global_get_last_texture(swanim.names[i], TexOutWAD)
						break
					else:
						idx += 1
	if swch.on_anim is None:
		on = global_get_last_texture_md5(swch.on_md5, TexOutWAD)
	else:
		swanim = None
		for anim in SwanOutWAD.textures:
			if anim.md5 == swch.on_anim.md5:
				swanim = anim
				break
		if swanim is None:
			on = None
		else:
			idx = 0
			for i in range(len(swanim.lumps)):
				if swanim.lumps[i] == swch.on_md5:
					if idx == swch.on_idx:
						on = global_get_last_texture(swanim.names[i], TexOutWAD)
						break
					else:
						idx += 1
	if off is None:
		print(' * warning: OFF image not found for %s' % (swch.off))
	if on is None:
		print(' * warning: ON image not found for %s' % (swch.on))
	if off is None or on is None:
		continue
	swch_new = SwanSwitch()
	swch_new.version = swch.version
	swch_new.off = off.name
	swch_new.on = on.name
	calc_switch_hash(swch_new, OutWAD, TexOutWAD)
	SwanOutWAD.switches.append(swch_new)
	

# ############################################# #
#   переименовываем текстуры и флэты в карте.   #
# ############################################# #
for sidedef in Map.sidedefs:
	if sidedef.tex_upper in TexturesToRename:
		sidedef.tex_upper = TexturesToRename[sidedef.tex_upper]
	if sidedef.tex_middle in TexturesToRename:
		sidedef.tex_middle = TexturesToRename[sidedef.tex_middle]
	if sidedef.tex_lower in TexturesToRename:
		sidedef.tex_lower = TexturesToRename[sidedef.tex_lower]
for sector in Map.sectors:
	if sector.tex_floor in FlatsToRename:
		sector.tex_floor = FlatsToRename[sector.tex_floor]
	if sector.tex_ceiling in FlatsToRename:
		sector.tex_ceiling = FlatsToRename[sector.tex_ceiling]

		
# ############################## #
#   копируем музыку, если есть   #
# ############################## #
if NameMap is not None:
	MusicList_Doom2 = ['D_RUNNIN', 'D_STALKS', 'D_COUNTD', 'D_BETWEE', 'D_DOOM', 'D_THE_DA', 'D_SHAWN', 'D_DDTBLU', 'D_IN_CIT', 'D_DEAD',
					   'D_STLKS2', 'D_THEDA2', 'D_DOOM2', 'D_DDTBL2', 'D_RUNNI2', 'D_DEAD2', 'D_STLKS3', 'D_ROMERO', 'D_SHAWN2', 'D_MESSAG',
					   'D_COUNT2', 'D_DDTBL3', 'D_AMPIE', 'D_THEDA3', 'D_ADRIAN', 'D_MESSG2', 'D_ROMER2', 'D_TENSE', 'D_SHAWN3', 'D_OPENIN',
					   'D_EVIL', 'D_ULTIMA']
	# doom 1 is simply d_e#m#, and we dont handle episode 4
	def get_music_name(mapname):
		if mapname[0:3].upper() == 'MAP' and len(mapname) == 5: # doom 2 format
			try:
				MapIdx = int(mapname[3:5])-1
				if MapIdx >= 0 and MapIdx < 32:
					return MusicList_Doom2[MapIdx]
			except:
				pass
		elif mapname[0].upper() == 'E' and mapname[2].upper() == 'M' and len(mapname) == 4: # doom 1 format
			try:
				MapIdx1 = int(mapname[1])
				MapIdx2 = int(mapname[3])
				if MapIdx1 >= 1 and MapIdx1 <= 3 and MapIdx2 >= 1 and MapIdx2 <= 9:
					return 'D_E%dM%d' % (MapIdx1, MapIdx2)
			except:
				pass
		return None
		
	NameMusicSrc = get_music_name(NameMap)
	NameMusicDst = get_music_name(NameOutMap)
	if NameMusicSrc is not None and NameMusicDst is not None:
		MusicSrc = global_get_last_file(NameMusicSrc)
		if MusicSrc is not None:
			print('Copying custom music from %s to %s.' % (NameMusicSrc, NameMusicDst))
			MusicDst = OutWAD.get_lump_or_new(NameMusicDst)
			MusicDst.data = MusicSrc.data
		
		
# ############################# #
#   запиливаем выхлопной файл   #
# ############################# #
if Map is not None:
	Map.to_wad(OutWAD, NameOutMap)
TexIWAD.to_wad(OutWAD, 'TEXTURE1', False)
TexOutWAD.to_wad(OutWAD, 'TEXTURE2', True) # save old PNAMES lump
SwanInternal.merge_another(SwanOutWAD)
SwanInternal.to_wad(OutWAD)
OutWAD.to_file(NameOutWAD)