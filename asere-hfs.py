#!/usr/bin/python3.9

import asyncio
import inspect
import logging

from datetime import datetime
from pathlib import Path
from urllib.parse import quote as uquote

from aiohttp import web

# https://stackoverflow.com/questions/34565705/asyncio-and-aiohttp-route-all-urls-paths-to-handler
# https://dev.to/vearutop/using-nginx-as-a-proxy-to-multiple-unix-sockets-3c7a

###############################################################################

_date_version="2023-08-23"

_static_data={}

_icon_dir="📂"
_icon_file="📄"

_help="""
Arguments:

--port NUMBER
	The port that the server will listen to

--socket PATH
	The UNIX socket that the server will listen to
	Recommended for setting up behind a proxy

--master PATH
	Master path

--slave PATH
	Slave path
	Any path that resolves outside of he master path should resolve to the slave path
	Optional

--proxy-appname STRING
	Custom virtual host name
	All the links at the frontend will be prefixed using this name
	Optional
	Used for setting up behind a proxy

--proxy-static ABSOL_PATH
	Custom absolute path for static content
	A different service will deliver the requested files to the client instead of AsereHFS
	Optional
	Requires '--proxy-appname' argument
	Used for setting up behind a proxy

Important notes:

→ You can only listen to either a port or a socket, not both
→ The slave directory cannot be relative to the master directory
→ The path to the socket file cannot be relative to the master directory nor the slave directory
→ The path to the socket file cannot exist before running the server, the program will create and delete the file on is own
→ The directory of the program cannot be relative to the master directory nor the slave directory
"""

_html_home="""
<body>
<div class="mainpage">
<h1>Asere HTTP File Server</h1>
</div>
<div class="mainpage">
<h2><a class="menu" href="REPLACE_ME">🔥 Browse files 🔥</a></h2>
<div>
<!--
<div class="mainpage">
<p>Author: <a href="https://github.com/carlos-a-g-h">this guy</a></p>
<p>Repository: <a href="https://github.com/carlos-a-g-h/asere-hfs">here</a></p>
</div>
-->
</body>
"""

_html_css="""
h1 {font-size: calc(1vw + 1vh + .5vmin);}
h2,th {font-size: calc(0.75vw + 1vh + .5vmin);}
p,tr {font-size: calc(0.5vw + 1vh + .5vmin);}
body{background-color:#25292b;color:white;}

div.mainpage {margin-top:64px;text-align:center;}

table {width:100%;text-align:left;}
td,th {padding:8px;}
th {background-color:#25292b;}
th.namecol {min-width:auto}
th.sizecol {min-width:auto;max-width:fit-content}
tr:nth-child(even) {background-color: #33393B;}
tr:nth-child(odd) {background-color: #515658;}

a {padding:8;background-color:transparent;font-weight:bold;}
a:link {color:#00BFFF;text-decoration:none;}
a:hover {text-decoration:underline;}
a:active {color:white;}
a:visited {color:#4682B4;text-decoration:none;}

a.button {background-color:#25292b;color:white;border:2px solid black;padding:2px 10px;margin-right:8px;text-align:center;text-decoration:none;display:inline-block;cursor:pointer;font-size:115%;}
a.button:hover {background-color:#4682B4;}
a.button:active {background-color:#00BFFF;color:black;}

a.menu {display:inline-block;border:2px solid black;color:#00BFFF;padding:8px;margin-left:8px;margin-bottom:4px;text-decoration: none;}
a.menu:hover {background-color:#33393B;}
a.menu:active {color:white;}

a.menuoff {display:inline-block;border:2px solid black;color:#25292B;background-color:#33393B;padding:8px;margin-left:8px;text-decoration: none;}

/*
a.fse {color:#00BFFF;background-color:transparent;border:transparent;text-align:left}
a.fse:hover {color:white}
*/

textarea {margin:8px;background-color:#25292B;color:white;border:2px solid black;min-width:calc(100% - 16px);max-width:100%;min-height:20%;min-height:128px;max-height:128px;font-size:inherit;}

#mediacontent {background-color:black;max-width:100%;display:block;text-align:center;}

audio {margin:8px;max-width:calc(100% - 16px);min-width:calc(100% - 16px);}
video,img {margin:4px;width:calc(auto - 16px);max-width:calc(100% - 16px)}
"""

###############################################################################

def util_test():
	print("THIS IS A TEST")

def util_dtnow():
	dtobj=datetime.now()
	return f"{dtobj.year}-{str(dtobj.month).zfill(2)}-{str(dtobj.day).zfill(2)}-{str(dtobj.hour).zfill(2)}-{str(dtobj.minute).zfill(2)}-{str(dtobj.second).zfill(2)}"

def util_ispair(num):
	idx=0
	ispair=True
	while idx<num:
		ispair=(not ispair)
		idx=idx+1
	return ispair

def util_datafix(data_raw):
	data_ok=[]
	data_check=[]
	if type(data_raw)==str:
		data_check.extend(data_raw.split())

	if type(data_raw)==list or type(data_raw)==tuple:
		istuple=type(data_raw)==tuple
		if not istuple:
			data_check.extend(data_raw)
		if istuple:
			data_check.extend(list(data_raw))

	if len(data_check)>0:
		for part in data_check:
			part_ok=part.strip()
			if len(part_ok)==0:
				continue
			data_ok.append(part_ok)

		data_check.clear()

	return data_ok

def util_humanbytes(b):
	u_kb=1024
	u_mb=u_kb*u_kb
	u_gb=u_kb*u_mb

	if b>u_gb:
		return f"{round(b/u_gb,2)} G"
	if b>u_mb:
		return f"{round(b/u_mb,2)} M"
	if b>u_kb:
		return f"{round(b/u_kb,2)} K"
	return f"{b} B"

async def util_subprocess(cmd_line,ret_stcode=True,ret_stdout=True,ret_stderr=True):

	proc=await asyncio.create_subprocess_exec(
			*cmd_line,
			stdout={True:asyncio.subprocess.PIPE,False:None}[ret_stdout],
			stderr={True:asyncio.subprocess.PIPE,False:None}[ret_stderr],
		)

	print(f"\n- RUN: {cmd_line}\n  PID: {proc.pid}")
	stdout_raw,stderr_raw=await proc.communicate()

	payload=[]
	if ret_stcode:
		payload.append(proc.returncode)
	if ret_stdout:
		if stdout_raw:
			payload.append(stdout_raw.decode())
		if not stdout_raw:
			payload.append(None)
	if ret_stderr:
		if stderr_raw:
			payload.append(stderr_raw.decode())
		if not stderr_raw:
			payload.append(None)

	if len(payload)==0:
		return
	if len(payload)==1:
		return payload[0]
	return payload

################################################################################

async def fse_watcher(filepath):
	print(f"Watching: {filepath}")
	try:
		while True:
			await asyncio.sleep(1)

	except asyncio.CancelledError:
		print("Stopping...")

	finally:
		print(f"Stopped watching: {filepath}")

def fse_translate(fse,path_frontend):
	return _static_data["path_masterdir"].joinpath(fse.relative_to(Path(path_frontend)))

def fse_validate(fse):

	if not fse.exists():
		return None

	fse_resolved=fse.resolve()

	if not fse_resolved.exists():
		return None

	the_masterdir=_static_data["path_masterdir"]
	the_slavedir=_static_data.get("path_slavedir")

	valid=fse_resolved.is_relative_to(the_masterdir)
	if (not valid) and (not the_slavedir==None):
		valid=fse_resolved.is_relative_to(the_slavedir)

	if not valid:
		return None

	return fse_resolved

def fse_isav(fse):
	return (fse.suffix[1:] in ("ac3","aac","av1","avi","flac","m4a","mkv","mp4","mpg","ogg","rm","rmvb","wav","webm","wma","wmv"))

def fse_position(fse_given):
	names_list=[]
	for fse in fse_given.parent.iterdir():
		if not fse.is_file():
			continue
		names_list.append(fse.name)

	names_total=len(names_list)

	if names_total<2:
		return None,None,1,names_total

	names_list.sort()
	idx=0
	name_prev=None
	name_next=None

	idx_last=len(names_list)-1

	for name in names_list:
		if name==fse_given.name:
			if idx>0:
				name_prev=names_list[idx-1]
			if idx<idx_last:
				name_next=names_list[idx+1]

			break

		idx=idx+1

	return name_prev,name_next,idx+1,names_total

def from_info_to_download(ypath_info,prefix_path_appname,custom_static):

	the_path={
		True:Path(f"{prefix_path_appname}/download"),
		False:custom_static
	}[custom_static==None]

	return str(the_path.joinpath(ypath_info.relative_to("/info/")))

def from_yurl_to_home(yurl):

	text=f"{yurl.scheme}://{yurl.host}"
	if not (yurl.port==443 or yurl.port==80):
		text=f"{text}:{yurl.port}"
	return text

###############################################################################

def html_info_topctl(ypath,prefix_path_appname):

	text="\n<h3>"+str(Path("/").joinpath(ypath.relative_to("/info/")))+f"</h3>\n<p>"

	if len(ypath.parent.parts)>1:
		text=f"{text}<a class=\"menu\" href=\"{prefix_path_appname}{str(ypath.parent)}\">⬆️ Go to parent directory</a> "

	text=f"{text}<a class=\"menu\" href=\"{prefix_path_appname}/\">🏠 Go home</a> <a class=\"menu\" href=\"{prefix_path_appname}{str(ypath)}\">🔁 Refresh page</a></p>"

	return text

def html_info_file(fse_serverside,yurl,prefix_path_appname):

	yurl_path=Path(yurl.path)

	fse_size=fse_serverside.stat().st_size

	fse_suffix=fse_serverside.suffix.lower()[1:]
	is_audio=(fse_size>1024 and fse_suffix in ("aac","m4a","mp3","ogg","wav"))
	is_picture=(fse_size>1024 and fse_suffix in ("bmp","gif","jpg","jpeg","png","webp"))
	is_video=(fse_size>1024 and fse_suffix in ("mp4","webm"))
	is_regular=(is_audio==False and is_picture==False and is_video==False)

	download_link=from_info_to_download(yurl_path,prefix_path_appname,_static_data.get("proxy_static",None))

	# Determine next or prev files in parent dir

	name_prev,name_next,position,total=fse_position(fse_serverside)

	html_text="<body>\n<h1>File viewer</h1>"
	html_text=f"{html_text}{html_info_topctl(yurl_path,prefix_path_appname)}"

	can_nav=((not name_prev==None) or (not name_next==None))
	if can_nav:
		html_text=f"{html_text}\n<div>\n"

		# Prev
		the_class={True:"menuoff",False:"menu"}[name_prev==None]
		the_href=""
		if not name_prev==None:
			the_href=f" href=\"{prefix_path_appname}{str(yurl_path.parent.joinpath(name_prev))}"
		html_text=f"{html_text}<a class=\"{the_class}\"{the_href}\">Prev file</a> "

		# Next
		the_class={True:"menuoff",False:"menu"}[name_next==None]
		the_href=""
		if not name_next==None:
			the_href=f" href=\"{prefix_path_appname}{str(yurl_path.parent.joinpath(name_next))}"
		html_text=f"{html_text}<a class=\"{the_class}\"{the_href}\">Next file</a>"

		html_text=f"{html_text}\n</div>"

	html_text=f"{html_text}\n<h2>"
	if is_audio:
		html_text=f"{html_text}Audio"
	if is_picture:
		html_text=f"{html_text}Picture"
	if is_video:
		html_text=f"{html_text}Video"
	if is_regular:
		html_text=f"{html_text}File"
	html_text=f"{html_text}</h2>"

	html_text=f"{html_text}\n<p>"

	if can_nav:
		html_text=f"{html_text}No.: {position} / {total} ; "

	html_text=f"{html_text}Size: {util_humanbytes(fse_size)}"
	if fse_size>1024:
		html_text=f"{html_text} ( {fse_size} bytes )"
	html_text=f"{html_text}</p>"

	if not is_regular:
		html_text=f"{html_text}\n<div id=\"mediacontent\">"

	if is_audio:
		mimetype={
			"mp3":"audio/mpeg",
			"m4a":"audio/mp4",
			"aac":f"audio/{fse_suffix}",
			"ogg":f"audio/{fse_suffix}",
			"wav":f"audio/{fse_suffix}",
		}[fse_suffix]
		html_text=f"{html_text}\n<audio controls><source src=\"{download_link}\" type=\"{mimetype}\"></audio>"

	if is_picture:
		html_text=f"{html_text}\n<img src=\"{download_link}\">"

	if is_video:
		type_found=True
		mimetype={
			"mp4":f"video/{fse_suffix}",
			"webm":f"video/{fse_suffix}",
		}[fse_suffix]

		html_text=f"{html_text}\n<video controls><source src=\"{download_link}\" type=\"{mimetype}\"></video>"

	if not is_regular:
		html_text=f"{html_text}\n</div>"

	html_text=f"{html_text}\n<p><a class=\"menu\" href=\"{download_link}\">Download file</a></p>\n<p><textarea readonly=true>{from_yurl_to_home(yurl)}{download_link}</textarea></p>"

	return f"{html_text}\n</body>"

def html_info_dir(fse_serverside,yurl_path,prefix_path_appname):

	path_neutral=yurl_path.relative_to("/info/")

	html_text=f"<body>\n<h1>Directory contents</h1>"
	html_text=f"{html_text}{html_info_topctl(yurl_path,prefix_path_appname)}"

	fse_list=list(fse_serverside.iterdir())

	if len(fse_list)==0:
		return f"{html_text}\n<h2 style=\"margin-left:8px\">Empty...</h2></body>"

	html_text_dirs=""
	html_text_files=""

	fse_list.sort()

	qtty_files=0
	qtty_files_av=0
	qtty_dirs=0

	files_tsize=0

	custom_static=_static_data.get("proxy_static",None)

	while True:
		fse_curr=fse_list.pop(0)

		is_file=(fse_curr.is_file())

		if not is_file:
			qtty_dirs=qtty_dirs+1

		if is_file:
			qtty_files=qtty_files+1
			if fse_isav(fse_curr):
				qtty_files_av=qtty_files_av+1

		yurl_path_info=yurl_path.joinpath(fse_curr.name)

		text=f"<tr><td><code>"

		if is_file:
			text=f"{text} <a class=\"button\" href=\"{from_info_to_download(yurl_path_info,prefix_path_appname,custom_static)}\">⬇️</a> "

		text=f"{text}<a href=\"{prefix_path_appname}{str(yurl_path_info)}\">"+{True:_icon_file,False:_icon_dir}[is_file]+f" {yurl_path_info.name}</a></code></td>"

		if is_file:
			fse_size=fse_curr.stat().st_size
			files_tsize=files_tsize+fse_size
			text=f"{text}<td>{util_humanbytes(fse_size)}</td>"

		text=f"{text}</tr>"

		if not is_file:
			html_text_dirs=f"{html_text_dirs}\n{text}"

			if len(fse_list)==0:
				break
			continue

		if is_file:
			html_text_files=f"{html_text_files}\n{text}"

			if len(fse_list)==0:
				break
			continue

		if len(fse_list)==0:
			break

	if len(html_text_dirs)>0:
		html_text=f"{html_text}\n<p>\n<table><th>"+{
			True:"Directory",
			False:"Directories"
		}[qtty_dirs==1]+f"</th>{html_text_dirs}</table></p>"

	if len(html_text_files)>0:
		# html_text=f"{html_text}\n<h2>Files</h2>"

		html_text=f"{html_text}\n<p>\n<table>"

		if qtty_files==1:
			html_text=f"{html_text}<th colspan=2>File</th>"
		if qtty_files>1:
			html_text=f"{html_text}<th class=\"namecol\">Files</th><th class=\"sizecol\">Total Size: {util_humanbytes(files_tsize)}</th>"

		html_text=f"{html_text}\n{html_text_files}</table></p>"

	if qtty_files>0 or qtty_dirs>0:

		html_text=f"{html_text}\n<h2>Available action(s)</h2>\n<p>"

		if qtty_files>1:

			# Normal TXT

			link_action=str(Path("/action/make-txt/").joinpath(path_neutral))
			if not link_action.endswith("/"):
				link_action=f"{link_action}/"

			html_text=f"{html_text}\n<a class=\"menu\" href=\"{prefix_path_appname}{link_action}\">Generate TXT file</a> "

			# IDM compatible TXT

			link_action=str(Path("/action/make-txt-idm/").joinpath(path_neutral))
			if not link_action.endswith("/"):
				link_action=f"{link_action}/"

			html_text=f"{html_text}\n<a class=\"menu\" href=\"{prefix_path_appname}{link_action}\">Generate TXT file for IDM</a> "

			# M3U Playlist

			if qtty_files_av>1:
				link_action=str(Path("/action/make-m3u/").joinpath(path_neutral))
				if not link_action.endswith("/"):
					link_action=f"{link_action}/"

				html_text=f"{html_text}\n<a class=\"menu\" href=\"{prefix_path_appname}{link_action}\">Generate M3U Playlist</a> "

		# TAR archiver

		link_action=str(Path("/action/tardir/").joinpath(path_neutral))
		if not link_action.endswith("/"):
			link_action=f"{link_action}/"

		html_text=f"{html_text}\n<a class=\"menu\" href=\"{prefix_path_appname}{link_action}\">Download as a TAR file</a> "

		html_text=f"{html_text.strip()}</p>"

	return f"{html_text}\n</body>"

def html_complete(html_body,html_title):
	html_complete=f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"

	html_complete=f"{html_complete}\n<style>{_html_css}"

	#if css_extra:
	#	html_complete=f"{html_complete}{_head_css_extra}"
	html_complete=f"{html_complete}</style>"

	#if tag_script:
	#	html_complete=f"{html_complete}\n{_head_script}"

	return f"{html_complete}\n\n<title>{html_title}</title>\n{html_body}\n<html>"

def html_error(message):
	return f"<body>\n<h1>ERROR</h1>\n<p>{message}</p>\n<p><a class=\"menu\" href=\"/\">🏠 Go home</a></p></body>"

###############################################################################

def action_txtmaker(yurl,fse_neutral,fse_given,atype=0):
	fse_list=[]
	for fse in fse_given.iterdir():
		if not fse.is_file():
			continue
		if atype==2:
			if not fse_isav(fse):
				continue

		fse_list.append(fse)

	if len(fse_list)<2:
		return None

	fse_list.sort()
	txt=""

	url_home=from_yurl_to_home(yurl)

	proxy_appname=_static_data.get("proxy_appname",None)
	proxy_static=_static_data.get("proxy_static",None)
	prefix_path_appname={True:"",False:f"/{proxy_appname}"}[proxy_appname==None]

	base_route={
		True:Path(f"{prefix_path_appname}/download/"),
		False:proxy_static,
	}[proxy_static==None]

	url_path_base=str(base_route.joinpath(fse_neutral))
	if not url_path_base.endswith("/"):
		url_path_base=f"{url_path_base}/"

	for fse in fse_list:
		url_path=uquote(f"{url_path_base}{fse.name}")
		url=f"{url_home}{url_path}"
		txt=f"{txt}\n{url}"
		if atype==1:
			txt=f"{txt}\t{fse.name}"

	return txt.strip()

async def action_tardir(fse):

	# tar -cf "/absolute/path/the.tar" -C "/parent/directory/" "DirectoryName"

	fse_tar_dir=_static_data["path_appdir"]
	fse_tar=fse_tar_dir.joinpath(f"{util_dtnow()}.tar")

	line=[
		"tar","-cf",
		str(fse_tar),
		"-C",str(fse.parent),
		fse.name,
	]

	results=await util_subprocess(line,ret_stdout=False)
	print(results)
	if not results[0]==0:
		return None,results[1]

	return fse_tar,None

###############################################################################

async def route_home(request):

	proxy_appname=_static_data.get("proxy_appname",None)
	path_root="/info/"
	if not proxy_appname==None:
		path_root=f"/{proxy_appname}/info/"

	text=_html_home.replace("REPLACE_ME",path_root)

	return web.Response(body=html_complete(text,"Home Page"),content_type="text/html",charset="utf-8",status=200)

async def route_info(request):

	yurl=request.url
	yurl_path=Path(yurl.path)

	proxy_appname=_static_data.get("proxy_appname",None)
	prefix_path_appname={True:"",False:f"/{proxy_appname}"}[proxy_appname==None]

	fse_serverside=fse_validate(fse_translate(yurl_path,"/info/"))

	html_text=None
	sc=-1

	if not fse_serverside:
		sc=404
		html_text=html_error("Path not found")

	if sc<0:
		if fse_serverside.is_file():
			sc=200
			html_text=html_info_file(fse_serverside,yurl,prefix_path_appname)

	if sc<0:
		if fse_serverside.is_dir():
			sc=200
			html_text=html_info_dir(fse_serverside,yurl_path,prefix_path_appname)

	if sc<0:
		if html_text==None:
			sc=500
			html_text=html_error("Unknown error")

	path_show=yurl_path.relative_to(f"/info/").name
	if len(path_show)>0:
		path_show=f" {path_show}"

	return web.Response(body=html_complete(html_text,f"Info // {path_show}"),content_type="text/html",charset="utf-8",status=sc)

async def route_download(request):
	yurl=request.url
	yurl_path=Path(yurl.path)

	proxy_appname=_static_data.get("proxy_appname",None)
	prefix_path_appname={True:"",False:f"/{proxy_appname}"}[proxy_appname==None]

	fse_serverside=fse_validate(fse_translate(yurl_path,"/download/"))

	html_text=None
	sc=-1

	if fse_serverside==None:
		sc=404
		html_text=html_error("This path does not exist")

	if sc<0:
		is_file=fse_serverside.is_file()

		if not is_file:
			sc=403
			html_text=html_error("This path does not lead o a file")

		if is_file:
			size=fse_serverside.stat().st_size
			if size==0:
				sc=403
				html_text=html_error("The file has zero bytes of length")

			if size>0:

				content_disposition=f"attachment; filename=\"{fse_serverside.name}\""
				content_length=f"{size}"

				return web.FileResponse(
						path=fse_serverside,
						headers={"content-disposition":content_disposition,"content-length":content_length},
						chunk_size=1048576,
					)

	if sc<0:
		if html_text==None:
			sc=500
			html_text=html_error("Unknown error")

	return web.Response(body=html_complete(html_text,yurl_path.name),content_type="text/html",charset="utf-8",status=sc)

async def route_action(request):
	yurl=request.url
	yurl_path=Path(yurl.path)

	fse_serverside=None

	pattern=""
	for pattern in ("/action/make-txt/","/action/make-txt-idm/","/action/make-m3u/","/action/tardir/"):
		if not yurl.path.startswith(pattern):
			continue

		fse_serverside=fse_validate(fse_translate(yurl_path,pattern))
		if not fse_serverside==None:
			break

	#pattern="/action/make-txt/"
	#if yurl.path.startswith(pattern):
	#	fse_serverside=fse_validate(fse_translate(yurl_path,pattern))

	#if not fse_serverside:
	#	pattern="/action/make-txt-idm/"
	#	if yurl.path.startswith(pattern):
	#		fse_serverside=fse_validate(fse_translate(yurl_path,pattern))

	#if not fse_serverside:
	#	pattern="/action/make-m3u/"
	#	if yurl.path.startswith(pattern):
	#		fse_serverside=fse_validate(fse_translate(yurl_path,pattern))

	#if not fse_serverside:
	#	pattern="/action/make-m3u/"
	#	if yurl.path.startswith(pattern):
	#		fse_serverside=fse_validate(fse_translate(yurl_path,pattern))

	if not fse_serverside:
		return web.Response(body=html_error("Path or action not valid","???"),content_type="text/html",charset="utf-8",status=404)

	if pattern in ("/action/make-txt/","/action/make-txt-idm/","/action/make-m3u/","/action/tardir/"):
		if not fse_serverside.is_dir():
			return web.Response(body=html_error("The path is not a directory","???"),content_type="text/html",charset="utf-8",status=403)

	if pattern=="/action/tardir/":
		fse_tmp,msg_err=await action_tardir(fse_serverside)
		if fse_tmp==None:
			msg={True:"Unknown error",False:msg_err}[msg_err==None]
			return web.Response(body=html_error(msg,"TAR archiver"),content_type="text/html",charset="utf-8",status=403)

		content_disposition=f"attachment; filename=\"{fse_serverside.name}.tar\""
		content_length=f"{fse_tmp.stat().st_size}"

		return web.FileResponse(
				path=fse_tmp,
				headers={"content-disposition":content_disposition,"content-length":content_length},
				chunk_size=1048576,
				delete_file_after_sending=True,
			)

	if pattern in ("/action/make-txt/","/action/make-txt-idm/","/action/make-m3u/"):

		action_type={
			"/action/make-txt/":0,
			"/action/make-txt-idm/":1,
			"/action/make-m3u/":2,
		}[pattern]

		fse_neutral=yurl_path.relative_to(pattern)
		txt=action_txtmaker(yurl,fse_neutral,fse_serverside,action_type)
		if not txt:
			return web.Response(body=html_error("Unable to create the TXT","???"),content_type="text/html",charset="utf-8",status=404)

		file_stem=str(fse_neutral.name)
		if len(file_stem)==0:
			file_stem=f"{yurl.host} {util_dtnow()}"

		file_sfx={True:"m3u",False:"txt"}[action_type==2]

		content_disposition=f"attachment; filename=\"{file_stem}.{file_sfx}\""

		return web.Response(
				text=txt,headers={"content-disposition":content_disposition},
				content_type="text/plain",status=200
			)

###############################################################################

def init_arguments(data_raw):

	data_ready=util_datafix(data_raw)
	args_qtty=len(data_ready)

	if (not util_ispair(args_qtty)) or args_qtty==0:
		return {}

	result={}
	count=-1
	while True:
		count=count+2
		if count>args_qtty:
			break

		new_key=data_ready[count-1].strip().lower()
		if not new_key in ("--socket","--port","--slave","--master","--proxy-appname","--proxy-static"):
			continue

		new_value=data_ready[count].strip()
		if new_key in result:
			continue

		result.update({new_key:new_value})

	return result

def init_arg_AnyString(arg_raw):
	if arg_raw==None:
		return None

	text=arg_raw.strip()
	if len(text)==0:
		return None

	return text

def init_arg_port(arg_raw):
	if arg_raw==None:
		return None,None

	try:
		value=int(arg_raw)
	except:
		return None,"The given port is not a number"

	if not (value>0 and value<65537):
		return None,"The port number is not valid"

	return value,None

def init_arg_socket(arg_raw,arg_port):
	if arg_raw==None:
		return None,None

	if not arg_port==None:
		return None,"Cannot use '--socket' with --port"

	the_path=Path(arg_raw.strip()).resolve()
	the_path.parent.mkdir(exist_ok=True,parents=True)
	if the_path.exists():
		return None,"Cannot use the specified file as the socket, delete it, move it somewhere else, etc..."

	return the_path,None

def init_arg_master(arg_raw,appdir,arg_socket):
	if arg_raw==None:
		return None,"Missing argument"

	the_path=Path(arg_raw.strip()).resolve()
	if (not str(the_path).startswith("/")) and len(the_path.parts)==0:
		return None,"The given path is not valid"
	if not the_path.exists():
		return None,"The given path does not exist"
	if not the_path.is_dir():
		return None,"The given path is NOT a directory"
	if len(the_path.parts)==1 and the_path.parts[1]=="/":
		return None,"The given path cannot be '/'"
	if appdir.is_relative_to(the_path):
		return None,"The main program cannot be relative to the given path"
	if not arg_socket==None:
		if arg_socket.is_relative_to(the_path):
			return None,"The path to the socket cannot be relative to the given path"

	return the_path,None

def init_arg_slave(arg_raw,appdir,arg_socket,arg_master):
	if arg_raw==None:
		return None,None
	the_path=Path(arg_raw.strip()).resolve()
	if (not str(the_path).startswith("/")) and len(the_path.parts)==0:
		return None,"The given path is not valid"
	if not the_path.exists():
		return None,"The given path does not exist"
	if not the_path.is_dir():
		return None,"The given path is NOT a directory"
	if len(the_path.parts)==1 and the_path.parts[1]=="/":
		return None,"The given path cannot be '/'"
	if appdir.is_relative_to(the_path):
		return None,"The given path cannot be a parent of the path to the main program"
	if the_path.is_relative_to(arg_master):
		return None,"The given path cannot be relative to the master path"
	if not arg_socket==None:
		if arg_socket.is_relative_to(the_path):
			return None,"The path to the socket cannot be relative to the given path"

	return the_path,None

def init_arg_abspath(arg_raw,proxy_appname):
	if arg_raw==None:
		return None,None

	if proxy_appname==None:
		return None,"The '--proxy-appname' argument is required"

	the_path=Path(arg_raw)
	if len(the_path.parts)<2:
		return None,"The given path is not valid"

	if not the_path.parts[0]=="/":
		return None,"The given path is not an absolute path"

	return the_path,None

#async def init_app(data_masterdir,data_slavedir=None):
async def init_app(independent):

	app=web.Application()

	#app["path_masterdir"]=path_masterdir
	#if not path_slavedir==None:
	#	app["path_slavedir"]=path_slavedir
	#if not proxy_appname==None:
	#	app["proxy_appname"]=proxy_appname
	#if not proxy_static==None:
	#	app["proxy_static"]=proxy_static

	the_routes=[
		web.get("/",route_home),
		web.get("/info",route_info),
		web.get("/info/{tail:.*}",route_info),
		web.get("/action/make-m3u/{tail:.*}",route_action),
		web.get("/action/make-txt/{tail:.*}",route_action),
		web.get("/action/make-txt-idm/{tail:.*}",route_action),
		web.get("/action/tardir/{tail:.*}",route_action),
	]

	if independent:

		the_routes.append(web.get("/download/{tail:.*}",route_download))

	app.add_routes(the_routes)
	return app

if __name__=="__main__":

	import sys
 
	no_args=len(sys.argv)==1
	if no_args:
		print(f"\nAsere HTTP File Server\n{_help}\nWritten by Carlos Alberto González Hernández\nVer: {_date_version}\n")
		sys.exit(0)

	the_arguments=init_arguments(sys.argv[1:])

	# Arg: Port
	the_port,msg_err=init_arg_port(the_arguments.get("--port",None))
	if not msg_err==None:
		print(f"ERROR with --port: {msg_err}")
		sys.exit(1)

	the_appdir=Path(sys.argv[0]).resolve().parent

	# Arg: Socket
	the_socket,msg_err=init_arg_socket(the_arguments.get("--socket",None),the_port)
	if not msg_err==None:
		print(f"ERROR with --socket: {msg_err}")
		sys.exit(1)

	if the_socket==None and the_port==None:
		print("ERROR: The server must listen to a port or a socket")
		sys.exit(1)

	# Arg: Master
	the_master,msg_err=init_arg_master(the_arguments.get("--master",None),the_appdir,the_socket)
	if not msg_err==None:
		print(f"ERROR with --master: {msg_err}")
		sys.exit(1)

	# Arg: Slave
	the_slave,msg_err=init_arg_slave(the_arguments.get("--slave",None),the_appdir,the_socket,the_master)
	if not msg_err==None:
		print(f"ERROR with --slave: {msg_err}")
		sys.exit(1)

	the_proxy_appname=init_arg_AnyString(the_arguments.get("--proxy-appname",None))

	the_proxy_static,msg_err=init_arg_abspath(the_arguments.get("--proxy-static",None),the_proxy_appname)
	if not msg_err==None:
		print(f"ERROR with --proxy-static: {msg_err}")
		sys.exit(1)

	msg=f"Asere HTTP File Server\n\tMaster directory:\n\t\t{the_master}"
	if not the_slave==None:
		msg=f"{msg}\n\tSlave directory:\n\t\t{the_slave}"
	if not the_socket==None:
		msg=f"{msg}\n\tSocket file:\n\t\t{the_socket}"

	print(f"\n{msg}\n")

	# Adding to static data dict
	_static_data.update({"path_appdir":the_appdir,"path_masterdir":the_master})
	if not the_slave==None:
		_static_data.update({"path_slavedir":the_slave})
	if not the_proxy_appname==None:
		_static_data.update({"proxy_appname":the_proxy_appname})
	if not the_proxy_static==None:
		_static_data.update({"proxy_static":the_proxy_static})

	independent=(the_proxy_static==None)

	the_socket_str={True:None,False:str(the_socket)}[the_socket==None]

	# Run app
	es=0
	try:
		web.run_app(init_app(independent),port=the_port,path=the_socket_str)
	except Exception as e:
		print(e)
		es=1

	if the_socket==None:
		sys.exit(es)

	if not the_socket==None:
		if the_socket.exists():
			print("Deleting socket file...")
			try:
				the_socket.unlink()
			except:
				print("Unable to delete socket file for some reason\nDelete it yourself")

	if not es==0:
		print("AsereHFS finished with a non-zero status")

	sys.exit(es)
