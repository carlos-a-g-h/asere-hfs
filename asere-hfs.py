#!/usr/bin/python3.9

import logging

from datetime import datetime
from pathlib import Path
from urllib.parse import quote as uquote

from aiohttp import web

###############################################################################

_date_version="2023-08-20"

_static_data={}

_icon_dir="📂"
_icon_file="📄"

_html_home="""
<body>
<div class="mainpage">
<h1>Asere HTTP File Server</h1>
</div>
<div class="mainpage">
<h2><a href="/info/">Browse files</a></h2>
<div>
<!--
<div class="mainpage">
<p>Author: <a href="https://github.com/carlos-a-g-h">this guy</a></p>
<p>Repository: <a href="https://github.com/carlos-a-g-h/asere-hfs">here</a></p>
</div>
-->
</body>
"""

#_head_script="""
#<script>
#/*
#function copylink(aid)
#{
#	let tag_a=document.getElementById(aid);
#	let text=tag_a.href;
#	navigator.clipboard.writeText(text);
#	alert("Link copied:\n\n"+text);
#};
#*/
#async function do_copy(text)
#{
#	let msg="";
#	try
#	{
#		await navigator.clipboard.writeText(text);
#		msg="Link copied:\n\n"+text;
#	}
#	catch (error)
#	{
#		msg="ERROR:\n\n"+String(error);
#	};
#	alert(msg);
#};
#window.onload=function init()
#{
#	let copy_buttons=document.getElementsByClassName("copy-link");
#	let idx=0;
#	while (idx<copy_buttons.length)
#	{
#		let elem=copy_buttons[idx];
#		let copyfun=function ()
#		{
#			let elem_link=elem.parentNode.getElementsByClassName("fse-link")[0];
#			if (elem_link===undefined){return};
#			let text=elem_link.href;
#			if (text===undefined){return};
#			do_copy(text);
#		};
#		elem.addEventListener("click",copyfun);
#		idx++;
#	};
#};
#</script>
#"""

_head_css_basic="""
h1 {font-size: calc(1vw + 1vh + .5vmin);}
h2,th {font-size: calc(0.75vw + 1vh + .5vmin);}
p,tr {font-size: calc(0.5vw + 1vh + .5vmin);}
body{background-color:#25292b;color:white;}

div.mainpage {margin-top:64px;text-align:center;}

table {width:100%;text-align:left;}
td,th {padding:8px;}
th {background-color:#25292b;}
tr:nth-child(even) {background-color: #33393B;}
tr:nth-child(odd) {background-color: #515658;}

/*
button {background-color:#25292b;color:white;border:2px solid black;padding:2px 10px;margin-right:8px;text-align:center;text-decoration:none;display:inline-block;cursor:pointer;font-size:115%;}
button:hover {background-color:#4682B4;}
button:active {background-color:#00BFFF;color:black;}
*/

a {padding:8;background-color:transparent;font-weight:bold;}
a:link {color:#00BFFF;text-decoration:none;}
a:hover {text-decoration:underline;}
a:active {color:white;}
a:visited {color:#4682B4;text-decoration:none;}

a.button {background-color:#25292b;color:white;border:2px solid black;padding:2px 10px;margin-right:8px;text-align:center;text-decoration:none;display:inline-block;cursor:pointer;font-size:115%;}
a.button:hover {background-color:#4682B4;}
a.button:active {background-color:#00BFFF;color:black;}

a.menu {display:inline-block;border:2px solid black;color:#00BFFF;padding:8px;margin-left:8px;text-decoration: none;}
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

def util_getposargs(data_raw):

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
		if not new_key in ("--port","--workspace","--mainroot"):
			continue

		new_value=data_ready[count].strip()
		if new_key in result:
			continue

		result.update({new_key:new_value})

	return result

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

################################################################################

def fse_translate(fse,pname):
	return _static_data["path_mainroot"].joinpath(fse.relative_to(Path(pname)))

def fse_validate(fse):

	if not fse.exists():
		return None

	fse_resolved=fse.resolve()

	if not fse_resolved.exists():
		return None

	the_mainroot=_static_data.get("path_mainroot")
	the_workspace=_static_data.get("path_workspace")

	valid=fse_resolved.is_relative_to(the_mainroot)
	if (not valid) and (not the_workspace==None):
		valid=fse_resolved.is_relative_to(the_workspace)

	if not valid:
		return None

	return fse_resolved

def fse_isav(fse):
	return (fse.suffix[1:] in ("ac3","aac","av1","avi","flac","m4a","mkv","mp4","mpg","ogg","rm","rmvb","wav","webm","wma","wmv"))

def fse_surroundings(fse_given):
	names_list=[]
	for fse in fse_given.parent.iterdir():
		if not fse.is_file():
			continue
		names_list.append(fse.name)

	if len(names_list)<2:
		return None,None

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

		if (not name_prev==None) and (not name_next==None):
			break

		idx=idx+1

	return name_prev,name_next

def convert_link(ypath_info,pname="/download"):
	return str(Path(pname).joinpath(ypath_info.relative_to("/info/")))

def get_homepage(yurl):
	text=f"{yurl.scheme}://{yurl.host}"
	if not (yurl.port==443 or yurl.port==80):
		text=f"{text}:{yurl.port}"
	return text

###############################################################################

def html_info_topctl(ypath):

	text="\n<h3>"+str(Path("/").joinpath(ypath.relative_to("/info/")))+"</h3>\n<p>"

	if len(ypath.parent.parts)>1:
		text=f"{text}<a class=\"menu\" href=\"{str(ypath.parent)}\">⬆️ Go to parent directory</a> "

	text=f"{text}<a class=\"menu\" href=\"/\">🏠 Go home</a></p>"

	return text

def html_info_file(fse_serverside,yurl):

	yurl_path=Path(yurl.path)

	fse_size=fse_serverside.stat().st_size

	fse_suffix=fse_serverside.suffix.lower()[1:]
	is_audio=(fse_size>1024 and fse_suffix in ("aac","m4a","mp3","ogg","wav"))
	is_picture=(fse_size>1024 and fse_suffix in ("bmp","gif","jpg","jpeg","png","webp"))
	is_video=(fse_size>1024 and fse_suffix in ("mp4","webm"))
	is_regular=(is_audio==False and is_picture==False and is_video==False)

	download_link=convert_link(yurl_path)

	# Determine next or prev files in parent dir

	name_prev,name_next=fse_surroundings(fse_serverside)

	html_text="<body>\n<h1>File viewer</h1>"
	html_text=f"{html_text}{html_info_topctl(yurl_path)}"

	can_nav=((not name_prev==None) or (not name_next==None))
	if can_nav:
		html_text=f"{html_text}\n<div>\n"

		# Prev
		the_class={True:"menuoff",False:"menu"}[name_prev==None]
		the_href=""
		if not name_prev==None:
			the_href=f" href=\"{str(yurl_path.parent.joinpath(name_prev))}"
		html_text=f"{html_text}<a class=\"{the_class}\"{the_href}\">Prev file</a> "

		# Next
		the_class={True:"menuoff",False:"menu"}[name_next==None]
		the_href=""
		if not name_next==None:
			the_href=f" href=\"{str(yurl_path.parent.joinpath(name_next))}"
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

	html_text=f"{html_text}\n<p>{util_humanbytes(fse_size)}"
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

	#################################

	#if not type_found:
	#	html_text=f"{html_text}\n<h2>Normal file</h2>"
	#
	#html_text=f"{html_text}\n<p>{util_humanbytes(size)}"
	#if size>1024:
	#	html_text=f"{html_text} ( {size} bytes )"
	#html_text=f"{html_text}</p>"

	html_text=f"{html_text}\n<p><a class=\"menu\" href=\"{download_link}\">Download file</a></p>\n<p><textarea readonly=true>{get_homepage(yurl)}{download_link}</textarea></p>"

	return f"{html_text}\n</body>"

def html_info_dir(fse_serverside,yurl_path):

	path_neutral=yurl_path.relative_to("/info/")

	html_text=f"<body>\n<h1>Directory contents</h1>"
	html_text=f"{html_text}{html_info_topctl(yurl_path)}"

	fse_list=list(fse_serverside.iterdir())

	if len(fse_list)==0:
		return f"{html_text}\n<p>EMPTY</p></body>"

	html_text_dirs=""
	html_text_files=""

	fse_list.sort()

	files_qtty=0
	files_qtty_av=0
	files_tsize=0

	while True:
		fse_curr=fse_list.pop(0)

		is_file=(fse_curr.is_file())

		if is_file:
			files_qtty=files_qtty+1
			if fse_isav(fse_curr):
				files_qtty_av=files_qtty_av+1

		yurl_path_info=yurl_path.joinpath(fse_curr.name)

		text=f"<tr><td><code>"

		if is_file:
			text=f"{text} <a class=\"button\" href=\"{convert_link(yurl_path_info)}\">⬇️</a> "

		text=f"{text}<a href=\"{str(yurl_path_info)}\">"+{True:_icon_file,False:_icon_dir}[is_file]+f" {yurl_path_info.name}</a></code></td>"

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
		html_text=f"{html_text}\n<h2>Directories</h2>\n<p>\n<table><th>Name</th>{html_text_dirs}</table></p>"

	if len(html_text_files)>0:
		html_text=f"{html_text}\n<h2>Files</h2>"
		if files_qtty>1:
			html_text=f"{html_text}\n<p>Total size: {util_humanbytes(files_tsize)}</p>"

		html_text=f"{html_text}\n<p>\n<table><th>Name</th><th>Size</th>{html_text_files}</table></p>"

	if files_qtty>1:

		html_text=f"{html_text}\n<h2>Available actions</h2>"

		# Normal TXT

		link_action_txt=str(Path("/action/make-txt/").joinpath(path_neutral))
		if not link_action_txt.endswith("/"):
			link_action_txt=f"{link_action_txt}/"

		html_text=f"{html_text}\n<p><a class=\"menu\" href=\"{link_action_txt}\">Download TXT file</a></p>"

		# IDM compatible TXT

		link_action_txt_idm=str(Path("/action/make-txt-idm/").joinpath(path_neutral))
		if not link_action_txt_idm.endswith("/"):
			link_action_txt_idm=f"{link_action_txt_idm}/"

		html_text=f"{html_text}\n<p><a class=\"menu\" href=\"{link_action_txt_idm}\">Download TXT for IDM</a></p>"

		# M3U Playlist

		if files_qtty_av>1:
			link_action_m3u=str(Path("/action/make-m3u/").joinpath(path_neutral))
			if not link_action_m3u.endswith("/"):
				link_action_m3u=f"{link_action_m3u}/"

			html_text=f"{html_text}\n<p><a class=\"menu\" href=\"{link_action_m3u}\">Download M3U Playlist</a></p>"

	return f"{html_text}\n</body>"

def html_complete(html_body,html_title):
	html_complete=f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"

	html_complete=f"{html_complete}\n<style>{_head_css_basic}"

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

	url_home=get_homepage(yurl)

	url_path_base=str(Path("/download/").joinpath(fse_neutral))
	if not url_path_base.endswith("/"):
		url_path_base=f"{url_path_base}/"

	for fse in fse_list:
		url_path=uquote(f"{url_path_base}{fse.name}")
		url=f"{url_home}{url_path}"
		txt=f"{txt}\n{url}"
		if atype==1:
			txt=f"{txt}\t{fse.name}"

	return txt.strip()

###############################################################################

async def route_home(request):
	return web.Response(body=html_complete(_html_home,"Home Page"),content_type="text/html",charset="utf-8",status=200)

async def route_info(request):
	yurl=request.url
	yurl_path=Path(yurl.path)
	fse_serverside=fse_validate(fse_translate(yurl_path,"/info/"))

	html_text=None
	sc=-1

	if not fse_serverside:
		sc=404
		html_text=html_error("Path not found")

	if sc<0:
		if fse_serverside.is_file():
			sc=200
			html_text=html_info_file(fse_serverside,yurl)

	if sc<0:
		if fse_serverside.is_dir():
			sc=200
			html_text=html_info_dir(fse_serverside,yurl_path)

	if sc<0:
		if html_text==None:
			sc=500
			html_text=html_error("Unknown error")

	path_show=yurl_path.relative_to("/info/").name
	if len(path_show)>0:
		path_show=f" {path_show}"

	return web.Response(body=html_complete(html_text,f"Info // {path_show}"),content_type="text/html",charset="utf-8",status=sc)

async def route_download(request):
	yurl=request.url
	yurl_path=Path(yurl.path)
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
				return web.FileResponse(path=fse_serverside,headers={"content-disposition":content_disposition,"content-length":content_length},chunk_size=1048576)

	if sc<0:
		if html_text==None:
			sc=500
			html_text=html_error("Unknown error")

	return web.Response(body=html_complete(html_text,yurl_path.name),content_type="text/html",charset="utf-8",status=sc)

async def route_action(request):
	yurl=request.url
	yurl_path=Path(yurl.path)

	fse_serverside=None

	pattern="/action/make-txt/"
	if yurl.path.startswith(pattern):
		fse_serverside=fse_validate(fse_translate(yurl_path,pattern))

	if not fse_serverside:
		pattern="/action/make-txt-idm/"
		if yurl.path.startswith(pattern):
			fse_serverside=fse_validate(fse_translate(yurl_path,pattern))

	if not fse_serverside:
		pattern="/action/make-m3u/"
		if yurl.path.startswith(pattern):
			fse_serverside=fse_validate(fse_translate(yurl_path,pattern))

	if not fse_serverside:
		return web.Response(body=html_error("The path does not exist","???"),content_type="text/html",charset="utf-8",status=404)

	if pattern in ("/action/make-txt/","/action/make-txt-idm/","/action/make-m3u/"):
		if not fse_serverside.is_dir():
			return web.Response(body=html_error("The path is not a directory","???"),content_type="text/html",charset="utf-8",status=403)

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

		return web.Response(text=txt,headers={"content-disposition":content_disposition},content_type="text/plain",status=200)

###############################################################################

# https://stackoverflow.com/questions/34565705/asyncio-and-aiohttp-route-all-urls-paths-to-handler

#async def app_builder(data_mainroot,data_workspace=None):
async def app_builder():
	app=web.Application()

	#data_static={"path_mainroot":data_mainroot}
	#if not data_workspace==None:
	#	data_static.update({"path_workspace":})
	#app.update({"data_static":data_static})

	app.add_routes([
		web.get("/",route_home),
		web.get("/action/make-m3u/{tail:.*}",route_action),
		web.get("/action/make-txt/{tail:.*}",route_action),
		web.get("/action/make-txt-idm/{tail:.*}",route_action),
		web.get("/download/{tail:.*}",route_download),
		web.get("/info",route_info),
		web.get("/info/{tail:.*}",route_info),
	])
	return app

if __name__=="__main__":

	import sys
 
	no_args=len(sys.argv)==1
	if no_args:
		print(f"Usage:\n$ {sys.argv[0]} --port [NUMBER] --mainroot [PATH] --workspace [PATH]\n\nImportant:\nThe port and mainroot arguments are mandatory\nThe workspace argument is optional and in case of being used, it cannot be relative to the mainroot path\n\nCarlos Alberto González Hernández ({_date_version})")
		sys.exit(0)

	the_options=util_getposargs(sys.argv[1:])

	# Arg: Port
	the_port_raw=the_options.get("--port",None)
	if the_port_raw==None:
		print("ERROR: The '--port' argument is missing")
		sys.exit(1)
	the_port_raw=the_port_raw.strip()
	try:
		the_port=int(the_port_raw)
		assert the_port>0 and the_port<65537
	except:
		print("ERROR: The given port is not valid. Make sure it's a number between 1 and 65536")
		sys.exit(1)

	the_appdir=Path(sys.argv[0]).resolve().parent

	# Arg: Main Root
	the_mainroot_raw=the_options.get("--mainroot",None)
	if the_mainroot_raw==None:
		print("ERROR: The '--mainroot' argument is missing")
		sys.exit(1)
	the_mainroot=Path(the_mainroot_raw.strip()).resolve()
	if not str(the_mainroot).startswith("/"):
		print("ERROR: The given path for the mainroot is not valid")
		sys.exit(1)
	if not the_mainroot.exists():
		print("ERROR: The given path for the mainroot does not exist")
		sys.exit(1)
	if not the_mainroot.is_dir():
		print("ERROR: The given path for the mainroot is not a directory")
		sys.exit(1)
	if the_appdir.is_relative_to(the_mainroot):
		print("ERROR: The given path for the mainroot cannot contain the main program")
		sys.exit(1)

	_static_data.update({"path_mainroot":the_mainroot})

	# Arg: Workspace (optional)
	the_workspace=None
	the_workspace_raw=the_options.get("--workspace",None)
	if not the_workspace_raw==None:
		the_workspace=Path(the_workspace_raw.strip()).resolve()
		if not str(the_workspace).startswith("/"):
			print("ERROR: The given path for the workspace is not valid")
			sys.exit(1)
		if not the_workspace.exists():
			print("ERROR: The given path for the workspace does not exist")
			sys.exit(1)
		if not the_workspace.is_dir():
			print("ERROR: The given path for the workspace is not a directory")
			sys.exit(1)
		if the_workspace.is_relative_to(the_mainroot):
			print("ERROR: The given path for the workspace cannot be relative to the main root")
			sys.exit(1)
		if the_appdir.is_relative_to(the_workspace):
			print("ERROR: The given path for the workspace cannot contain the main program")
			sys.exit(1)

		_static_data.update({"path_workspace":the_workspace})

	msg=f"Asere HTTP File Server\n\tMain Root:\n\t\t{the_mainroot}"
	if not the_workspace==None:
		msg=f"{msg}\n\tWorkspace:\n\t\t{the_workspace}"

	print(f"\n{msg}\n")

	# Run app
	web.run_app(app_builder(),port=the_port)
