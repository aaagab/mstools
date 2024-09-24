#!/usr/bin/env python3
from enum import Enum
from pprint import pprint
import os
import re
import sys
import urllib.parse
import subprocess
import shlex

from lxml.etree import _ElementTree

from .csproj_update import csproj_update_files, is_project_need_build, build_project
from .csproj import get_all_build_paths, Csproj

class CscMode(str, Enum):
	__order__ = "FAT RUN SLIM"
	FAT="fat"
	RUN="run"
	SLIM="slim"

def csc(
	csproj:Csproj,
	direpa_framework:str,
	filenpa_msbuild:str,
	link_keywords:list[str],
	mode:CscMode,
	params:str|None,
	project_name:str,
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

	tmp_params:list[str]
	if params is None:
		tmp_params=[]
	else:
		tmp_params=shlex.split(params)

	direpa_runtime=os.path.join(csproj.direpa_root, "_runtime")
	direpa_main=os.path.join(direpa_runtime, project_name)
	os.makedirs(direpa_main, exist_ok=True)
	filenpa_main=os.path.join(direpa_main, "main.cs")

	if not os.path.exists(filenpa_main):
		print("'{}' not found".format(filenpa_main))
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
						if indent is None:
							reg_indent = re.match(r"^(\s+).+$", line)
							if reg_indent is None:
								raise Exception("regex should match any line")
							indent=reg_indent.group(1)
						f.write("{}\n".format(line[len(indent):]))
					count+=1

			print("'{}' created".format(filenpa_main))
	
	direpa_bin=os.path.join(csproj.direpa_root, "bin")
	filenpa_csc=os.path.join(direpa_bin, "roslyn", "csc.exe")
	filenpa_exe=os.path.join(direpa_bin, project_name+".exe")

	return_code=None
	if mode == CscMode.RUN:
		return_code=0
		if not os.path.exists(filenpa_exe):
			print("Not found '{}'".format(filenpa_exe))
			sys.exit(1)
	elif mode == CscMode.FAT or mode == CscMode.SLIM:
		excluded_bin_folders:list[str]=[
			"bin",
		]
		excluded_bin_files:list[str]=[
		]
		included_bin_extensions:list[str]=[
			".cs",
			".conf",
		]
		filenpas_run=list(get_all_build_paths(
			direpa_root=direpa_main,
			excluded_bin_extensions=[],
			excluded_bin_files=excluded_bin_files,
			excluded_bin_folders=excluded_bin_folders,
			included_bin_extensions=included_bin_extensions,
		))

		add_cmd:list[str]=[]
		extra_filenpa_runs:list[str]=[]
		if mode == CscMode.FAT:
			build_project(
				csproj=csproj,
				filenpa_msbuild=filenpa_msbuild,
			)
			add_cmd.append("-r:{} ".format(os.path.basename(csproj.filenpa_assembly)))
		elif mode == CscMode.SLIM:
			csproj_update_files(csproj=csproj)
			set_files_csproj(
				csproj.xml_tree,
				direpa_framework,
				dy_files,
				csproj.filenpa_csproj, 
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
							filenpa_tmp=os.path.join(csproj.direpa_root, line)
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
		if csproj.debug is True:
			print(" ".join(cmd))

		if is_project_need_build(
			csproj=csproj,
			filenpas=filenpas_run,
		):
			if csproj.debug is True:
				print("build")
			return_code= subprocess.call(cmd)
		else:
			if csproj.debug is True:
				print("No build needed.")
			return_code=0

	if return_code == 0:
		cmd=[
			filenpa_exe
		]
		cmd.extend(tmp_params)

		sys.exit(subprocess.call(cmd))
	else:
		sys.exit(return_code)

def set_files_csproj(
	csproj_xml_tree,
	direpa_framework,
	dy_files,
	filenpa_csproj, 
):
	root=csproj_xml_tree.getroot()
	dy_files["cs"]=[ urllib.parse.unquote(item.attrib["Include"]) for item in root.findall('.//Compile[@Include]', namespaces=root.nsmap)]

	assemblies=[ item for item in root.findall('.//Reference[@Include]', namespaces=root.nsmap) ]
	for assembly in assemblies:
		tmp_assembly=assembly.attrib["Include"].split(",")[0]
		dy_files["assemblies"].append("-reference:{}.dll".format(tmp_assembly))

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

