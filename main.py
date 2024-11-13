#!/usr/bin/env python3
from typing import Callable
import json
from pprint import pprint
import re
import os
import sys

# pip3 install lxml
# pip install lxml-stubs

if __name__ == "__main__":
    import sys, os
    import importlib
    import typing
    direpa_script=os.path.dirname(os.path.realpath(__file__))
    direpa_script_parent=os.path.dirname(direpa_script)
    module_name=os.path.basename(direpa_script)
    sys.path.insert(0, direpa_script_parent)
    if typing.TYPE_CHECKING:
        import __init__ as package #type:ignore
        from __init__ import WebconfigOption, RebuildMode, CscMode, Csproj
    pkg:"package" = importlib.import_module(module_name) #type:ignore
    del sys.path[0]

    def get_filenpa_hostname(csproj:"Csproj"):
        return os.path.join(csproj.direpa_root, "hostname_url.txt")


    def seed(pkg_major, direpas_configuration:dict, fun_auto_migrate:Callable):
        fun_auto_migrate()
    etconf=pkg.Etconf(enable_dev_conf=False, tree=dict( files=dict({ "settings.json": dict() })), seed=seed)

    nargs=pkg.Nargs(
        metadata=dict(executable="mstools"), 
        options_file="config/options.yaml",
        path_etc=etconf.direpa_configuration,
        raise_exc=True,
    )
    args=nargs.get_args()

    filenpa_settings=os.path.join(etconf.direpa_configuration, "settings.json")

    debug=args.debug._here

    if args.build._here:

        direpa_sources=os.getcwd()
        if args.build._value is not None:
            direpa_sources=args.build._value

            if os.getcwd() != direpa_sources:
                os.chdir(direpa_sources)

        csproj=pkg.get_csproj(debug=debug, direpa_root=args.path_csproj._value)
        settings=pkg.get_settings(filenpa_settings=filenpa_settings)
      
        pkg.build_project(
            csproj=csproj,
            filenpa_msbuild=settings.filenpa_msbuild,
            force_build=args.build.force_build._here,
            force_csproj=args.build.force_csproj._here,
        )

        if args.build.iis._here:
            pkg.iis(
                http_port=args.build.iis.http._value,
                https_port=args.build.iis.https._value,
                bind=args.build.iis.bind._value,
                reset=args.build.iis.reset._here,
                project_name=csproj.assembly_name,
                direpa_sources=direpa_sources,
                filenpa_hostname=get_filenpa_hostname(csproj),
            )
    elif args.csproj._here:
        csproj=pkg.get_csproj(debug=debug, direpa_root=args.path_csproj._value)
        if args.csproj.clean._here:
            pkg.csproj_clean_files(
                csproj=csproj,
            )
        if args.csproj.add._here:
            pkg.csproj_add_files(csproj=csproj)
        else:
            if args.csproj.update._here:
                pkg.csproj_update_files(
                    csproj=csproj,
                    force=args.csproj.update.force._here,
                )
    elif args.db._here:
        csproj=pkg.get_csproj(debug=debug, direpa_root=args.path_csproj._value)
        settings=pkg.get_settings(filenpa_settings=filenpa_settings)

        pkg.entity(
            csproj=csproj,
            filenpa_msbuild=settings.filenpa_msbuild,
            force_build=args.db.force_build._here,
            ignore_build=args.db.ignore_build._here,
            force_csproj=args.db.force_csproj._here,
            params=args.db._value,
            xml_root_namespace=csproj.xml_root_namespace,
        )
    elif args.profile._here:
        if args.profile.publish._here or args.profile.deploy._here:
            csproj=pkg.get_csproj(debug=debug, direpa_root=args.path_csproj._value)
            settings=pkg.get_settings(filenpa_settings=filenpa_settings)

            profile=pkg.get_profile(
                app_name=csproj.app_name,
                apps=settings.apps,
                profiles=settings.profiles,
                direpa_root=csproj.direpa_root,
                filenpa_settings=filenpa_settings,
                filen_assembly=os.path.basename(csproj.filenpa_assembly),
                profile_name=args.profile._value,
                to_deploy=args.profile.deploy._here,
                direpa_deploy=args.profile.deploy._value,
                no_pubxml=args.profile.no_pubxml._here,
                filenpa_hostname=get_filenpa_hostname(csproj),
            )

            is_new_publishing=False
            if args.profile.publish._here:
                try:
                    rebuild_mode=pkg.RebuildMode(args.profile.publish.rebuild._value)
                except ValueError:
                    pkg.msg.error(f"rebuild option '{args.profile.publish.rebuild._value}' not found in {sorted([r.value for r in pkg.RebuildMode])}")
                    sys.exit(1)
                is_new_publishing=pkg.publish(
                    csproj=csproj,
                    profile=profile,
                    filenpa_msbuild=settings.filenpa_msbuild,
                    rebuild_mode=rebuild_mode,
                    set_doc=args.profile.publish.set_doc._here,
                )

            is_updated_webconfig=False
            if args.profile.webconfig._here:
                webconfigs:list["WebconfigOption"]=[]
                for wconf in args.profile.webconfig._values:
                    try:
                        webconfigs.append(WebconfigOption(wconf))
                    except ValueError:
                        pkg.msg.error(f"webconfig option '{wconf}' not found in {sorted([r.value for r in pkg.WebconfigOption])}")
                        sys.exit(1)

                is_updated_webconfig=pkg.set_web_config(
                    direpa_publish=profile.direpa_publish,
                    webconfigs=webconfigs,
                )

            is_pre_deployed=False
            if args.profile.pre_deploy._here:
                is_pre_deployed=True
                for filenpa_script in args.profile.pre_deploy._values:
                    if os.system(filenpa_script) != 0:
                        pkg.msg.error("pre-deploy script failed '{}'".format(filenpa_script), exit=1)

            if args.profile.publish.zip_release._here is True:
                direpa_dst=args.profile.publish.zip_release._value
                if direpa_dst is None:
                    direpa_dst=profile.direpa_deploy
                
                if direpa_dst is None:
                    raise Exception(f"--zip-release path must be provided because direpa_deploy is not available in profile '{profile.name}'")
                pkg.zip_release(
                    app_name=csproj.app_name,
                    direpa_dst=direpa_dst,
                    direpa_publish=profile.direpa_publish,
                )

            to_deploy=  (args.profile.deploy._here is True and args.profile.publish._here is False) or \
                        (args.profile.deploy._here is True and args.profile.publish._here is True and (is_new_publishing is True or is_updated_webconfig is True or is_pre_deployed is True))

            if to_deploy is True:
                pkg.deploy(
                    direpa_deploy=profile.direpa_deploy,
                    direpa_publish=profile.direpa_publish,
                    filenpa_msdeploy=settings.filenpa_msdeploy,
                    exclude_paths=args.profile.deploy.exclude._values,
                    include_paths=args.profile.deploy.include._values,
                )
        else:
            pkg.msg.error("--publish or --deploy is required.")
            sys.exit(1)

    elif args.csc._here:
        csproj=pkg.get_csproj(debug=debug, direpa_root=args.path_csproj._value)
        settings=pkg.get_settings(filenpa_settings=filenpa_settings)

        mode:"CscMode|None"=None
        if args.csc.fat._here:
            mode=pkg.CscMode.FAT
        elif args.csc.slim._here:
            mode=pkg.CscMode.SLIM
        elif args.csc.run._here:
            mode=pkg.CscMode.RUN
        if mode is None:
            pkg.msg.error("Select either --fat, --slim or --run argument.")
            sys.exit(1)
        pkg.csc(
            csproj=csproj,
            direpa_framework=settings.direpa_framework,
            filenpa_msbuild=settings.filenpa_msbuild,
            link_keywords=args.csc.slim.link._values,
            mode=mode,
            params=args.csc.params._value,
            project_name=args.csc._value,
        )
        