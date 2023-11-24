#!/usr/bin/python3.9

from hashlib import md5
from pathlib import Path

import fitz

_help="""
AsereHFS e-book toolkit

Usage:
$ PROGRAM_NAME [FILEPATH] [ACTION] (ACTION ARGs)

Available actions:

--get-total-pages
	Returns: The ammount of pages

--render-page [IDX] [OUTDIR]
	Returns: Image filename
	→ IDX: Page number
	→ OUTDIR: Output directory
"""

def util_path_to_hash(fpath):
	fpath_str=str(fpath.resolve())
	fpath_str_ready=fpath_str.encode()
	return md5(fpath_str_ready).hexdigest()

def action_get_total_pages(fpath):
	pages=0
	with fitz.open(fpath) as doc:
		pages=doc.page_count

	return pages

def action_render_page(fpath,index,odir):
	fse_page_name=f"{util_path_to_hash(fpath)}_{index}.png"
	opath=odir.joinpath(fse_page_name)
	if opath.exists():
		print(fse_page_name)
		return 0

	odir.mkdir(exist_ok=True,parents=True)
	with fitz.open(fpath) as doc:
		pix=doc[index].get_pixmap()
		pix.writeImage(opath)

	print(fse_page_name)
	return 0

if __name__=="__main__":

	from sys import argv as sys_argv
	from sys import exit as sys_exit

	program_name=Path(sys_argv[0]).name
	if not (len(sys_argv)>2):
		print(_help.replace("PROGRAM_NAME",program_name))
		sys_exit(1)

	ipath_raw=sys_argv[1].strip()
	action=sys_argv[2].strip().lower()

	if action not in ["--get-total-pages","--render-page"]:
		print("Unknown action")
		sys_exit(1)

	if action=="--get-total-pages":
		if not len(sys_argv)==3:
			print(f"Incorrect number of arguments\nUsage:\n{program_name} {action}")
			sys_exit(1)

		pages=action_get_total_pages(ipath_raw)
		print(pages)
		if pages<1:
			sys_exit(1)

		sys_exit(0)

	if action=="--render-page":
		if not len(sys_argv)==5:
			print(f"Incorrect number of arguments\nUsage:\n{program_name} {action} [IDX] [ODIR]")
			sys_exit(1)

		index=int(sys_argv[3].strip())
		odir_raw=sys_argv[4].strip()

		sc=action_render_page(Path(ipath_raw),index,Path(odir_raw))
		sys_exit(sc)