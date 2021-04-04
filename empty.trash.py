#!/usr/bin/python3
# Usage: ./empty.trash.py
# To actually delete run: ./empty.trash.py --destroy

import argparse
import os
import time
import sys
import re

DESTROY = False
VERBOSE = False


################################################################################
# This is a generated section. Do not edit.
# Written by SurpriseDog at: https://github.com/SurpriseDog


class Eprinter:
	#Drop in replace to print errors if verbose level higher than setup level
	#To replace every print statement type: from common import eprint as print

	#Setup: eprint = Eprinter(<verbosity level>).eprint
	#Simple setup: from common import eprint
	#Usage: eprint(messages, v=1)

	#Source for colors: https://svn.blender.org/svnroot/bf-blender/trunk/blender/build_files/scons/tools/bcolors.py
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKCYAN = '\033[96m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	ENDC = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'

	def __init__(self, verbose=1):
		self.level = verbose

	def eprint(self, *args, v=1, color=None, header=None, **kargs):
		#Print to stderr
		verbose = kargs.get('verbose', v)
		#Will print if verbose >= level
		if v == 2 and not color:
			color=f"{self.WARNING}"
		if v >= 3 and not color:
			color=f"{self.FAIL}"+f"{self.BOLD}"

		if verbose >= self.level:
			msg = ' '.join(map(str, args))
			if color:
				print(color+msg+f"{self.ENDC}", file=sys.stderr, **kargs)
			else:
				print(msg, file=sys.stderr, **kargs)
			return len(msg)
		return 0


def walk(path, match=None, **kargs):
	#Walk through directory looking for full filenames
	#match applies a re.match expression

	for (dirpath, dirnames, filenames) in os.walk(path, **kargs):
		#print(filenames, dirpath, dirnames)
		for filename in filenames:
			if match and re.match(match, filename) or not match:
				yield os.path.join(dirpath, filename)


def warn(*args, header="\n\nWarning:", delay=1/64):
	time.sleep(eprint(*args, header=header, v=2) * delay)


eprint = Eprinter(verbose=1).eprint


def rfs(num, mult=1000, digits=3):
	# A "readable" file size	 
	# mult is the value of a kilobyte in the filesystem. (1000 or 1024)
	if abs(num) <  mult:
		return str(num)+' B'
	suffix = ' KMGTPEZY'
	#Faster than using math.log:
	for x in range(8,-1,-1):
		magnitude = mult**x
		if abs(num) >= magnitude:
			return sig(num / magnitude, digits) + ' ' + suffix[x] + 'B'


def sig(num, digits=3):
	#Return number formatted for significant digits	(formerly get_significant)
	ret = ("{0:."+str(digits)+"g}").format(num)
	if 'e' in ret:
		if abs(num) >= 1:
			return str(int(num))
		else:
			return str(num)
	else:
		return ret


################################################################################


def argfixer():
	'''Fix up args for argparse. Lowers case and turns -args into --args'''
	out = []
	sys.argv = [word.lower() for word in sys.argv]
	for word in sys.argv:
		word = word.lower()
		if re.match('^-[^-]', word):
			out.append('-' + word)
		else:
			out.append(word)
	return out[1:]


def parse_args():
	'''Parse arguments'''
	global DESTROY, VERBOSE

	parser = argparse.ArgumentParser(
		description='Delete older files from trash folders system wide.', allow_abbrev=True)

	parser.add_argument('--age', dest='min_age',
						nargs='?', type=float, default=365,
						help="File age in days")
	parser.add_argument('--largesize', dest='large_min_size',
						nargs='?', type=float, default=100,
						help="Min file size in MB to be considered 'large'")
	parser.add_argument('--largeage', dest='large_min_age',
						nargs='?', type=float, default=64,
						help="Large file age in days")
	parser.add_argument('--destroy', action='store_true', default=False,
						help="Actually delete files")
	parser.add_argument('--verbose', '-v', action='store_true',
						help="List each file deleted")

	args = parser.parse_args(argfixer())
	DESTROY = args.destroy
	VERBOSE = args.verbose

	return args


def warn(*args, header="\n\nWarning:"):
	eprint(*args, header=header, v=2)


def get_trash():
	'''Return list trash folders'''
	with open('/etc/mtab', 'r') as f:
		for line in f.readlines():
			_, mount = re.split(' ', line)[0:2]
			if mount.startswith('/sys'):
				continue
			if not os.access(mount, os.R_OK):
				warn("Could not access", mount)
				continue
			for name in os.listdir(mount):
				if re.match('.Trash-', name):
					yield os.path.join(mount, name)


def user_dirs():
	'''Return list of user dirs'''
	with open('/etc/passwd') as f:
		for line in f.readlines():
			# print(line)
			line = re.split(':', line.strip())
			uid = int(line[2])

			if 65534 > uid >= 1000 or uid == 0:
				yield line[-2]


def walk(dirname):
	'''Walk a directory returning scandir objects'''
	for entry in os.scandir(dirname):
		if entry.is_dir() and not entry.is_symlink():
			yield from walk(entry.path)
		yield entry


def delete(entry, size, age):
	if VERBOSE:
		if not DESTROY:
			msg = "\nNot Deleting:"
		else:
			msg = "\nDeleting:"
		print(msg, entry.path)
		if not entry.is_dir():
			print(rfs(size), 'and', int(age // 86400), "days old")
	if DESTROY:
		os.remove(entry.path)


def is_empty(path): 
	return not next(os.scandir(path), None)

################################################################################


def main():
	args = parse_args()
	min_age = args.min_age * 86400
	large_min_size = args.large_min_size * 1e6
	large_min_age = args.large_min_age * 86400

	dirs = []
	for d in user_dirs():
		d = os.path.join(d, '.local/share/Trash/files')
		dirs.append(d)
	dirs += get_trash()

	# Walk through each trash folder looking for old files:
	del_count = 0
	total_count = 0
	del_size = 0
	total_size = 0
	for dirname in dirs:
		if not os.path.exists(dirname):
			warn("Could not find:", dirname)
			continue
		if not os.access(dirname, os.W_OK):
			warn("No permission for:", dirname)
			continue

		print('\n\n\n\nExploring:', dirname)

		for entry in walk(dirname):
			if entry.is_symlink():
				continue
			stat = entry.stat(follow_symlinks=False)
			size = stat.st_size
			age = time.time() - stat.st_mtime
			total_count += 1
			total_size += size
			if entry.is_dir() and age > min_age and is_empty(entry.path):
				delete(entry, size, age)
			elif age > min_age or (size > large_min_size and age > large_min_age):
				delete(entry, size, age)
				del_count += 1
				del_size += size

	print("\n")
	warn(del_count, 'files processed', '= ' + rfs(del_size) if del_size else "")
	warn(total_count - del_count, 'files remaining',
		 '= ' + rfs(total_size - del_size) if total_size - del_size else "")

	if not DESTROY:
		warn("\nNote: dry_run option was enabled. No files were harmed in the making of this text.")
		warn("To actually delete run with the flag: --destroy")


if __name__ == "__main__": main()

'''
&&&&%%%%%&@@@@&&&%%%%##%%%#%%&@@&&&&%%%%%%/%&&%%%%%%%%%%%&&&%%%%%&&&@@@@&%%%%%%%
%%%%%%%%&@&(((((#%%&%%%%%%%%%&@@&&&&&&%%%&&&&&%%%%%%%%%%%&&&&%&%#((((/#@@%%%%%%%
&&%%%%%%&@(*,,,,,,,/%&%%%%%%%&@@&&&&&%%&&&&%%&&%%%%%%%%%%&&&%#*,,,,,,*/&@&%%%%%%
%%%%%%%&@&/*,,,*,*,,*/%&%%%%%&@@&&&&&&%%&&&&&&&%%%%%%&%%%&&%*,,,,,,,,**#@&&%%%%%
&&&&&%%&@#(**********,*(#&%%%&@&&&&%%%%%%%%%&&&%%%%%%&%&&#*****,*******#@&&%%%%%
&&&%%%&&#/***/*****/*,**,*%&%&@@&&&&&&&&&&&&&&&%%%%%%&&#*,,,*/******/***(%&%%%%%
&&&%%%&%/*****///////**,,,,*/%%&&@@@@@@@@@@@@@@@@&&%#*,,,*,*(///////*****#%&%%%%
@@&%%#&#/,,,*/(//((((//**,,*/#&@@@@@&&&&&&&&&&@@@@@%(/*,,**/(/(((/(//*,,*(&&%%%%
&&&%##&#*,,,*////((((/*///(&@&@@&&&#%((//(/###%&@&@@@@#//**//(#(///***,.,/&&%%%%
%%%%%#%#*,,,**////(///((#&&&%@&%%(/*,,......,,/(#%&&&@@@%((/(/#(///**,,,,(&%%%%%
&&%%%#%%/,..***//(#(#%%&@@@&@%(*.,,..       ...,.,/#@&@@@&&%#(((///**,..,#%%%%%%
%&%%%%%#*,****/(##&@@@&@@@@&%*,....           ....,,(&@@@@@@&@&%((//****,(%%%%%%
%&%%%%%#/,**/#&@@@&@@@@@@@&(*,......    .     ..,..,.(&@@@@@@@&@@@&%#**,*(%%%%%%
&&%%%%#&#(#&@@@&@@@@@@@@%((#@@%&&((,,,,,..,,(**(%@@&@%##(&@@@@@@@@&&@@%#(%%%%%%%
&&&%%%%%&&&&&&@@@@@@%###%@(,%&/@@&(%(/*,..,*/%##&&,%@(*&@#((%&@@@@@@&&@&%%%%&&%%
&&%%%%%%&&&@@@@@@@@#((*#@%,#%%&@#%(/**//,****/(#%%%&&%*(@@*/#(&@@@@@@@&&%%%%%%%%
&&&%%%%%&@@@@&%#/,,,,*,(/%&@@&((%(*,*,,*,**,,*,*#%(#@@&%((**,,,,*#(%&@@&&%%%%%%%
&&&%%%%%@@@@%*/*,...,*,,/*#(//#****,***********,**/#/##(/*,*,...,*/*/&@@&%%&%%%%
&&%%%%%%&@@@(//,....,,*/****/,,/**************/***/,,//**/**,....,*//&@@&%%&%%%%
&&&%%%%%&@@%(/*,. ...,****/*/(//*%&@@&%%%%%%&&&&//*/(*/**/**......,/*#&@&%&&&&%%
&&%%%%%%&@@%(**,,....,/**/((/,#&&&&&%#((((((%&&&@&%/*/(/**/*,. ..,,*/((#@&&&&&&%
%&%%%%%%&&#(/**,..,,,***/((,./%&%&&&@&(/#((#@@&&&%&%,,/((*,/*,,..,,,///(%&%&&&&&
&&%%%%%%&#,**,.,..,,*(//(/,,.,&&&@#&@@##%(#&@&%%@&&#.,,/(((//*,,..,,**,*&%&&%&&&
&&%##%%%#/**,,,,..,*/((((*...,,#&##%(#%%&%%###%(%&/,.. **((((/,...,,,,**(%%#%%%&
&&%####(**,,,.,,.,,/(/(//*,,..../%&(##%&&&%%(#%&#, .. .**//(/(*,,..,.,,**/((#%%%
&&&%#///*,........,/(((//**,.   ,,(#%%%%%%&#%##**.   ,,*//((((*,........,*//(%%%
%%%%(/**...       .,/(((///*., .,*(#(%%%%%%%%##/*,..,,*///((/*.      .....**/(%%
%%%%#(,..          .,/((/(//****,/(((###%#%(#///**,,**/((/((*,          .,.,(%%%
&&%%%#/*...          ,*/(/(/((%%&#&#(/%./.*%(#%#%#&&(((/(/*,.          ..,**(&%%
&&%%%%(*.....          ..*((/**(#&&&&&&&%%%&%&&&%(/,*/((*..           .,..*(&&%%
&&%%%%&#*.      .        */(#/*,,*/((%#%%%%%((**,.*/(#(/,       .       ,(%&%%&%
%%%%%%&%#//**,..           .**(((*,...,,**,,..*,/((/*,.          ...,,//(#%%%%%%
%%%&&&%(/*,**,..,,.,..       .,,**//**,*,,,*,////*,,.        .,.,...,,,**//#%&%%
%%%&&%#/*,*,.    ...      ..         ...  ,.. .       .       ...   ..,,*/(#%&%%
&&&&&%(((*.*... . .*,.   .           .*%%#(,.          .    .*,. ..,.,,**/(%#&%%
Generated on: 2021-04-04
Written by SurpriseDog at: https://github.com/SurpriseDog
<<< All rights reserved unless otherwise stated >>>
'''
