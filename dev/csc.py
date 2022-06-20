#!/usr/bin/env python3
# author: Gabriel Auger
# version: 0.1.0
# name: release
# license: MIT

from pprint import pprint
import os
import re
import sys
import urllib.parse
import subprocess
import shlex

from .csproj_update import csproj_update_files, is_project_need_build, build_project
from .csproj import get_all_build_paths

def csc(
	csproj_xml_tree,
	debug,
	direpa_framework,
	direpa_root,
	filenpa_assembly,
	filenpa_csproj,
	filenpa_msbuild,
	link_keywords,
	mode,
	params,
	project_name,
):
	dy_files=dict(
		assemblies=[],
		concat_assemblies=" ",
		concat_cs=" ",
		concat_packages=" ",
		cs=[],
		packages=[],
		lib="",
	)

	if params is None:
		params=[]
	else:
		params=shlex.split(params)

	direpa_runtime=os.path.join(direpa_root, "_runtime")
	direpa_main=os.path.join(direpa_runtime, project_name)
	os.makedirs(direpa_main, exist_ok=True)
	filenpa_main=os.path.join(direpa_main, "main.cs")

	if not os.path.exists(filenpa_main):
		print("'{}' not found".format(filenpa_main))
		# user_choice="Y"
		user_choice=input("Do you want to create it? (Y/n) ")
		if user_choice.lower() == "n":
			sys.exit(1)
		else:
			file_content="""
				using System;
				namespace Runtime
				{{
					class {}
					{{
						static void Main(string[] args)
						{{
							Console.WriteLine("Hello Program!");
						}}
					}}
				}}
			""".format(project_name.capitalize())

			with open(filenpa_main, "w") as f:
				count=0
				indent=None
				for line in file_content.splitlines():
					if count > 0:
						# print(line)
						if indent is None:
							reg_indent = re.match(r"^(\s+).+$", line)
							indent=reg_indent.group(1)
						f.write("{}\n".format(line[len(indent):]))
					count+=1

			print("'{}' created".format(filenpa_main))
	
	direpa_bin=os.path.join(direpa_root, "bin")
	filenpa_csc=os.path.join(direpa_bin, "roslyn", "csc.exe")
	filenpa_exe=os.path.join(direpa_bin, project_name+".exe")

	return_code=None;
	if mode == "run":
		return_code=0
		if not os.path.exists(filenpa_exe):
			print("Not found '{}'".format(filenpa_exe))
			sys.exit(1)
	elif mode == "fat" or mode == "slim":
		excluded_bin_folders=[
			"bin",
			# "conf",
			# "_runtime",
		]
		excluded_bin_files=[
		]
		included_bin_extensions=[
			".cs",
			".conf",
		]
		# print(ex)
		filenpas_run=list(get_all_build_paths(
			direpa_root=direpa_main,
			excluded_bin_extensions=[],
			excluded_bin_files=excluded_bin_files,
			excluded_bin_folders=excluded_bin_folders,
			included_bin_extensions=included_bin_extensions,
		))


		add_cmd=[]
		extra_filenpa_runs=[]
		if mode == "fat":
			build_project(
				debug,
				direpa_root,
				csproj_xml_tree,
				filenpa_assembly,
				filenpa_csproj,
				filenpa_msbuild,
			)
			add_cmd.append("-r:{} ".format(os.path.basename(filenpa_assembly)))
		elif mode == "slim":
			csproj_update_files(
				csproj_xml_tree,
				debug,
				direpa_root,
				filenpa_csproj,
			)
			set_files_csproj(
				csproj_xml_tree,
				direpa_framework,
				dy_files,
				filenpa_csproj, 
			)

			direpa_conf=os.path.join(direpa_main, "conf")
			os.makedirs(direpa_conf, exist_ok=True)
			filenpa_conf=os.path.join(direpa_conf, project_name+".conf")

			if not os.path.exists(filenpa_conf):
				open(filenpa_conf, "w").close()
			
			existingReferences=[]
			file_conf_old=""
			with open(filenpa_conf, "r") as f:
				file_conf_old=f.read()
				lines=file_conf_old.splitlines()
				for line in lines:
					line=line.strip()
					if line:
						if line[0] != "#":
							existingReferences.append(line)
		
			paths=[]
			paths.extend(dy_files["cs"])
			paths.extend(dy_files["packages"])
			paths.extend(dy_files["assemblies"])
			paths.sort()

			searched_references=set()

			for keyword in link_keywords:
				tmp_references=[]
				for elem in paths:
					if keyword.lower() in elem.lower():
						tmp_references.append(elem)

				if len(tmp_references) == 1:
					tmp_reference=tmp_references[0]
					if tmp_reference not in existingReferences:
						user_choice=input("Do you want to add reference:\n{} (Y/n)? ".format(tmp_reference))
						if user_choice.lower() != "n":
							searched_references.add(tmp_reference)
				elif len(tmp_references) > 1:
					for tmp_reference in tmp_references:
						print(tmp_reference)
					print("\nUncomment the above needed references if any from file '{}'".format(filenpa_conf))
					sys.exit(1)

			file_conf_new=""

			for elem in paths:
				prefix="# "
				if elem in searched_references or elem in existingReferences:
						prefix=""
				file_conf_new+="{}{}\n".format(prefix, elem)

			if file_conf_old != file_conf_new:
				with open(filenpa_conf, 'w') as f:
					f.write(file_conf_new)

			with open(filenpa_conf, 'r') as f:
				for line in f.read().splitlines():
					line=line.strip()
					if line != "" and line[0] != "#":
						if line[:len("-reference:")] == "-reference:":
							add_cmd.append("{}".format(line))
						else:
							filenpa_tmp=os.path.join(direpa_root, line)
							add_cmd.append("{}".format(filenpa_tmp))
							extra_filenpa_runs.append(filenpa_tmp)


		for filenpa_run in filenpas_run:
			if filenpa_run != filenpa_main and filenpa_run != filenpa_conf:
				add_cmd.append(filenpa_run)

		filenpas_run.extend(extra_filenpa_runs)

		cmd=r'{} {} -lib:{} {}-nologo -out:{} -nowarn:219'.format(
			filenpa_csc,
			filenpa_main,
			direpa_bin,			
			add_cmd,
			filenpa_exe
		)

		cmd=[
			filenpa_csc,
			filenpa_main,
			"-lib:{}".format(direpa_bin),
			*add_cmd,
			"-nologo",
			"-out:{}".format(filenpa_exe),
			"-nowarn:219",
		]
		if debug is True:
			print(" ".join(cmd))

		if is_project_need_build(
			debug,
			direpa_root,
			csproj_xml_tree,
			filenpa_assembly,
			filenpa_csproj,
			filenpas=filenpas_run,
			filenpa_main=filenpa_exe,
			return_filenpas=False,
		):
			if debug is True:
				print("build")
			return_code= subprocess.call(cmd)
		else:
			if debug is True:
				print("No build needed.")
			return_code=0;
	else:
		print("Please provide at least one parameter from [\"--fat\", \"--slim\", \"--exe\"]")
		sys.exit(1)

	# print (return_code)
	if return_code == 0:
		cmd=[
			filenpa_exe
		]
		cmd.extend(params)

		sys.exit(subprocess.call(cmd))
	else:
		sys.exit(return_code)

def set_files_csproj(
	csproj_xml_tree,
	direpa_framework,
	dy_files,
	filenpa_csproj, 
):
	previous_assembly=False

	root=csproj_xml_tree.getroot()
	dy_files["cs"]=[ urllib.parse.unquote(item.attrib["Include"]) for item in root.findall('.//Compile[@Include]', namespaces=root.nsmap)]

	assemblies=[ item for item in root.findall('.//Reference[@Include]', namespaces=root.nsmap) ]
	for assembly in assemblies:
		tmp_assembly=assembly.attrib["Include"].split(",")[0]
		dy_files["assemblies"].append("-reference:{}.dll".format(tmp_assembly))
		# if len(assembly) == 0:
		# 	dy_files["assemblies"].append("-reference:{}.dll".format(tmp_assembly))
		# else:
		# 	hint_path=assembly.findall('HintPath', namespaces=root.nsmap)
		# 	if hint_path:
		# 		iPath=urllib.parse.unquote(hint_path[0].text)
		# 		if iPath[:3] == "..\\":
		# 			iPath=iPath[3:]

		# 		# print(iPath)
		# 		# print(direpa_root)
		# 		# print(os.path.normpath(os.path.join(direpa_root, iPath)))
		# 		# sys.exit()
		# 		# os.path.normpath(os.path.join(direpa_root, iPath)))
		# 		dy_files["packages"].append("-reference:{}".format(iPath))
		# 	else:
		# 		private=assembly.findall('Private', namespaces=root.nsmap)
		# 		if private:
		# 			tmp_assembly=None
		# 		else:
		# 			dy_files["assemblies"].append("-reference:{}.dll".format(tmp_assembly))

	version=[ item.text for item in root.findall('.//TargetFrameworkVersion', namespaces=root.nsmap)]
	if not version:
		print("Error TargetFrameworkVersion not Found in '{}'".format(filenpa_csproj))
		sys.exit(1)

	version=version[0]

	direpa_version=os.path.normpath(os.path.join(direpa_framework, version))
	if not os.path.exists(direpa_version):
		print("For NET Framework version '{}'".format(version))
		print("'{}' not found".format(direpa_version))
		sys.exit(1)

	dy_files["lib"]=" -lib:\"{}\" ".format(direpa_version)
	dy_files["concat_assemblies"]=" ".join(dy_files["assemblies"])
	dy_files["concat_packages"]=" ".join(dy_files["packages"])
	dy_files["concat_cs"]=" ".join(dy_files["cs"])


r""""
#### OLD DOC NEEDS A REFRESH
msbuild --run --main mydebug --main mydebug --params thisisparam --slim
msbuild --run --main mydebug --main mydebug --params thisisparam --exe
msbuild --run --main mydebug --main mydebug --params thisisparam --fat

msbuild --run --main mydebug --slim --quiet

	# how can I link other file and to know where to get them.
	# let's say I just gather everything in one folder in runtime so I just list all the files from this particular folder. maybe I can explain a bin folder and I can do everything on local too so I have a tiny executable that I can use for any other project???

# two modes:
# --fat means compiled the whole src if needed and grab the main src assembly 
msbuild --run --main mydebug --fat
# without --fat, means you need select almost manually the dll you want to add to the code 
# example without --fat
>  msbuild --run --main mydebug
updating 'Example.csproj'
No Paths to clean for 'Example.csproj'
No Paths to add to 'Example.csproj'
"A:\wrk\e\example\1\src\bin\roslyn\csc.exe A:\wrk\e\example\1\src\_runtime\mydebug.cs -lib:A:\wrk\e\example\1\src\bin -nologo -out:A:\wrk\e\example\1\src\bin\mydebug.exe -nowarn:219"
_runtime\mydebug.cs(17,14): error CS0246: The type or namespace name 'Example' could not be found (are you missing a using directive or an assembly reference?)
_runtime\mydebug.cs(18,14): error CS0246: The type or namespace name 'Example' could not be found (are you missing a using directive or an assembly reference?)

# instead of adding the whole example.dll like --fat does just select the file you want to link like:
line 17 and 18 I have:
using static Example.Models.MimeTypes;
using static Example.Dev.Dbg;

# so link them this way
>  msbuild --run --main mydebug --link mimetypes mydebug
updating 'Example.csproj'
No Paths to clean for 'Example.csproj'
No Paths to add to 'Example.csproj'
Do you want to add reference:
Models\MimeTypes.cs (Y/n)? y
Do you want to add reference:
Dev\MyDebug.cs (Y/n)? y
"A:\wrk\e\example\1\src\bin\roslyn\csc.exe A:\wrk\e\example\1\src\_runtime\mydebug.cs -lib:A:\wrk\e\example\1\src\bin Dev\MyDebug.cs Models\MimeTypes.cs -nologo -out:A:\wrk\e\example\1\src\bin\mydebug.exe -nowarn:219"
Dev\MyDebug.cs(3,18): error CS0234: The type or namespace name 'Http' does not exist in the namespace 'System.Net' (are you missing an assembly reference?)
Dev\MyDebug.cs(5,18): error CS0234: The type or namespace name 'Http' does not exist in the namespace 'System.Web' (are you missing an assembly reference?)
Dev\MyDebug.cs(13,7): error CS0246: The type or namespace name 'Newtonsoft' could not be found (are you missing a using directive or an assembly reference?)
Dev\MyDebug.cs(15,29): error CS0234: The type or namespace name 'DataHelpers' does not exist in the namespace 'Example.Dev' (are you missing an assembly reference?)

# link the remaining needed
# you can continue searching them with the --link parameter and keyword or you can go to the file "A:\wrk\e\example\1\src\_runtime\conf\mydebug.conf" and uncomment the dependencies needed

# that is it
>  msbuild --run --main mydebug --link mimetypes mydebug datahelpers
updating 'Example.csproj'
No Paths to clean for 'Example.csproj'
No Paths to add to 'Example.csproj'
Do you want to add reference:
Dev\DataHelpers.cs (Y/n)? Y
"A:\wrk\e\example\1\src\bin\roslyn\csc.exe A:\wrk\e\example\1\src\_runtime\mydebug.cs -lib:A:\wrk\e\example\1\src\bin -reference:Newtonsoft.Json.dll -reference:System.Net.Http.dll -reference:System.Web.Http.dll Dev\DataHelpers.cs Dev\MyDebug.cs Models\MimeTypes.cs -nologo -out:A:\wrk\e\example\1\src\bin\mydebug.exe -nowarn:219"

# Method with --fat
# pros: no manually search of dll
# cons: slower because the main assembly has to be compiled at each change in source.

# Method without --fat
# pros: lightweight build, faster
# cons: You have a little bit of manual uncomment in a reference file or automatic with --link parameter to do in order to create the needed command to build.(however once this command has been setup you don't need to add more dependencies)

# Conclusion: it is better to use the second options has you don't have to recompile the main assembly eachtime.

This section allows to test code with csc.exe instead of compiling the whole asp.net application
It helps for quick coding on some part that doesn't require the webserver to be tested
all existing referencies from application are exported automatically eachtime in _runtime/references.conf
if some lines are uncommented and exist as reference they are going to still be present in the references.conf file uncommented
then to check for missing dependencies you can run command
msbuild --run --link reference_keyword reference_keyword
keyword searches against lines in references.conf are not case sensitive
if only one line is found for the dependency this line is uncommented from references.conf if user accepts
if multiple lines are found then they are printed to the terminal and user is invited to uncomment any of them manually in the references.conf file

example (missing reference):
>  msbuild --run
_runtime\main.cs(16,14): error CS0246: The type or namespace name 'Example' could not be found (are you missing a using directive or an assembly reference?)
fix:


-lib:A:\wrk\e\example\1\src

"C:/Program Files (x86)/Microsoft Visual Studio/2019/Community/MSBuild/Current/Bin/Roslyn/csc.exe" A:\wrk\e\example\1\src\_runtime\main.cs -reference:System.Net.Http.dll -reference:packages\Microsoft.AspNet.WebApi.Core.5.2.3\lib\net45\System.Web.Http.dll -reference:packages\Newtonsoft.Json.9.0.1\lib\net45\Newtonsoft.Json.dll Dev\DataHelpers.cs -lib:A:\wrk\e\example\1\src\packages\Newtonsoft.Json.9.0.1\lib\net45\ -reference:Newtonsoft.Json.dll Dev\MyDebug.cs Models\MimeTypes.cs -nologo -out:A:\wrk\e\example\1\src\_runtime\main.exe -nowarn:219 & A:\wrk\e\example\1\src\_runtime\main.exe

Actually it is even simpler than that, mysrc no _runtime but the whole folder needs to be build all the time.
then the simplest command is this one.
A:\wrk\e\example\1\src\bin\roslyn\csc.exe A:\wrk\e\example\1\src\_runtime\main.cs -lib:bin -r:Example.dll -nologo -out:A:\wrk\e\example\1\src\bin\main.exe -nowarn:219 & A:\wrk\e\example\1\src\bin\main.exe
or even
.\bin\roslyn\csc.exe .\_runtime\main.cs -lib:bin -r:Example.dll -nologo -out:.\bin\main.exe -nowarn:219 & .\bin\main.exe

so In fact I would just need the main dll name with app_name well the assembly name
"""