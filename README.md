# wadstomp
An utility to compile multiple BOOM maps with arbitrary texture packs into single PWAD

The only thing required to run the script is Python 2.7. No additional modules are used.
The main file is wadstomp.py.

The command-line switches are:
 *  -iwad             Specifies main WAD resource (typically doom2.wad)
 *  -file             Specifies additional WAD resource(s)
 *  -map              Specifies input map name. The last occurrence in all resources will be used.
 *  -out              Specifies output WAD filename. Default is wstomped.wad
 *  -outmap           Specifies output map name (will be replaced if already present in output WAD)
 *  -defswani         Specifies custom DEFSWANI.DAT file. It is used by the script to enumerate vanilla animations and switches (those present in IWAD).

Features:
 * Does not copy unused textures.
 * Does not replace IWAD images. Instead, flats/textures/patches are renamed (along with the values used in the currently-added map).
 * In case of different overlapping texture packs, does not duplicate patches, flats and textures.
 * Supports merging of ANIMATED and SWITCHES lumps.
 * Reads TEXTURE1, TEXTURE2, F_* and FF_*. Writes only TEXTURE2 and FF_* (although dummy IWAD TEXTURE1 is present).
