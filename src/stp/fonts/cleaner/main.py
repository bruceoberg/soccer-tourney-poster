import subprocess
from pathlib import Path
from fontTools import ttLib

pathThis = Path(__file__)
pathDirThis = pathThis.parent
pathDirParent = pathDirThis.parent

def UsePyft(pathTtf: Path, pathTtfOut: Path):
	lStrCmd = [
		'pyftsubset',
			str(pathTtf),
			'--output-file=' + str(pathTtfOut),
			'--drop-tables=EBLC,EBDT'
	]
	strCmd = ' '.join(lStrCmd)
	#print(f"running {strCmd}")
	subprocess.call(lStrCmd)

def UseTTLib(pathTtf: Path, pathTtfOut: Path):
	font = ttLib.TTFont(pathTtf)
	if 'EBLC' in font:
		del font['EBLC']
	if 'EBDT' in font:
		del font['EBDT']
	font.save(pathTtfOut)

for pathTtf in pathDirParent.glob('*calibri*.ttf'):
	print(f"processing {pathTtf}")
	pathTtfOut = pathDirThis / pathTtf.name
	#UsePyft(pathTtf, pathTtfOut)
	UseTTLib(pathTtf, pathTtfOut)