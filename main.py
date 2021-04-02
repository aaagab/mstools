#!/usr/bin/env python3
# author: Gabriel Auger
# license: MIT

import json
from pprint import pprint
import re
import os
import sys


# pip3 install lxml

def get_dy_conf():
    direpa_conf=os.path.join(os.path.expanduser("~"), "fty", "etc", "mstools")
    os.makedirs(direpa_conf, exist_ok=True)
    filenpa_apps=os.path.join(direpa_conf, "settings.json")
    if not os.path.exists(filenpa_apps):
        pkg.msg.error("Not found '{}'".format(filenpa_apps), exit=1)
    dy_conf=pkg.Json_config(filenpa_apps).data
    conf_profiles=dy_conf["globals"]["confs"]
    return dict(
        conf_apps=dy_conf["apps"],
        conf_profiles=conf_profiles,
        direpa_framework=dy_conf["globals"]["direpa_framework"],
        filenpa_apps=filenpa_apps,
        filenpa_msbuild=dy_conf["globals"]["filenpa_msbuild"],
        filenpa_msdeploy=dy_conf["globals"]["filenpa_msdeploy"],
        profile_names=[cfname for cfname in conf_profiles],
    )

if __name__ == "__main__":
    import sys, os
    import importlib
    direpa_script=os.path.dirname(os.path.realpath(__file__))
    direpa_script_parent=os.path.dirname(direpa_script)
    module_name=os.path.basename(direpa_script)
    sys.path.insert(0, direpa_script_parent)
    pkg=importlib.import_module(module_name)
    del sys.path[0]

    args, dy_app=pkg.Options(filenpa_app="gpm.json", filenpa_args="config/options.json").get_argsns_dy_app()

    if args.build.here:
        dy_csproj=pkg.get_dy_csproj(direpa_root=args.path_csproj.value)

        pkg.build_project(
            debug=args.debug.here,
            direpa_root=dy_csproj["direpa_root"],
            csproj_xml_tree=dy_csproj["csproj_xml_tree"],
            filenpa_assembly=dy_csproj["filenpa_assembly"],
            filenpa_csproj=dy_csproj["filenpa_csproj"],
            filenpa_msbuild=dy_conf["filenpa_msbuild"],
            force=args.force.here,
        )
    elif args.csproj.here:
        dy_csproj=pkg.get_dy_csproj(direpa_root=args.path_csproj.value)
        if args.clean.here:
            pkg.csproj_clean_files(
                csproj_xml_tree=dy_csproj["csproj_xml_tree"],
                debug=args.debug.here,
                direpa_root=dy_csproj["direpa_root"],
                filenpa_csproj=dy_csproj["filenpa_csproj"],
            )
        if args.add.here:
            pkg.csproj_add_files(
                csproj_xml_tree=dy_csproj["csproj_xml_tree"],
                debug=args.debug.here,
                direpa_root=dy_csproj["direpa_root"],
                filenpa_csproj=dy_csproj["filenpa_csproj"],
            )
        else:
            if args.update.here:
                pkg.csproj_update_files(
                    csproj_xml_tree=dy_csproj["csproj_xml_tree"],
                    debug=args.debug.here,
                    direpa_root=dy_csproj["direpa_root"],
                    filenpa_csproj=dy_csproj["filenpa_csproj"],
                )
    elif args.db.here:
        dy_conf=get_dy_conf()
        dy_csproj=pkg.get_dy_csproj(direpa_root=args.path_csproj.value)

        pkg.entity(
            csproj_xml_tree=dy_csproj["csproj_xml_tree"],
            direpa_root=dy_csproj["direpa_root"],
            debug=args.debug.here,
            filenpa_assembly=dy_csproj["filenpa_assembly"],
            filenpa_csproj=dy_csproj["filenpa_csproj"],
            filenpa_msbuild=dy_conf["filenpa_msbuild"],
            params=args.db.value,
            xml_root_namespace=dy_csproj["xml_root_namespace"],
        )
    elif args.examples.here:
        pkg.examples()
    elif args.publish.here or args.deploy.here:
        dy_conf=get_dy_conf()

        dy_csproj=pkg.get_dy_csproj(direpa_root=args.path_csproj.value)

        profile=pkg.get_profile(
            app_name=dy_csproj["app_name"],
            conf_apps=dy_conf["conf_apps"],
            conf_profiles=dy_conf["conf_profiles"],
            direpa_root=dy_csproj["direpa_root"],
            filenpa_apps=dy_conf["filenpa_apps"],
            filen_assembly=os.path.basename(dy_csproj["filenpa_assembly"]),
            profile_name=args.profile.value,
            profile_names=dy_conf["profile_names"],
        )

        is_new_publishing=False
        rebuild_mode=args.rebuild.value
        if args.publish.here:
            rebuild_modes=["any", "frontend", "fullstack"]
            if rebuild_mode not in rebuild_modes:
                pkg.msg.error("--rebuild '{}' not in {}".format(rebuild_mode, rebuild_modes), exit=1)

            is_new_publishing=pkg.publish(
                app_name=dy_csproj["app_name"],
                debug=args.debug.here,
                direpa_publish=profile["direpa_publish"],
                direpa_root=dy_csproj["direpa_root"],
                csproj_xml_tree=dy_csproj["csproj_xml_tree"],
                filenpa_assembly=dy_csproj["filenpa_assembly"],
                filenpa_cache_assembly=profile["filenpa_cache_assembly"],
                filenpa_csproj=dy_csproj["filenpa_csproj"],
                filenpa_log=dy_csproj["filenpa_log"],
                filenpa_msbuild=dy_conf["filenpa_msbuild"],
                profile_name=args.profile.value,
                rebuild_mode=rebuild_mode,
                set_doc=args.set_doc.here,
            )

        is_updated_webconfig=False
        webconfigs=args.webconfig.values
        if args.webconfig.here:
            webconfs_allowed= [
                "bundle-off",
                "bundle-on",
                "custom-off",
                "custom-on",
                "debug-off",
                "debug-on",
            ]
            for wconf in webconfigs:
                if wconf not in webconfs_allowed:
                    pkg.msg.error("--webconfig '{}' not in {}".format(wconf, webconfs_allowed), exit=1)
            is_updated_webconfig=pkg.set_web_config(
                direpa_publish=profile["direpa_publish"],
                webconfigs=webconfigs,
            )

        is_pre_deployed=False
        if args.pre_deploy.here:
            is_pre_deployed=True
            if os.system(args.pre_deploy.value) != 0:
                pkg.msg.error("pre-deploy script failed '{}'".format(arg.pre_deploy.value), exit=1)

        if args.zip_release.here is True:
            direpa_dst=args.zip_release.value
            if direpa_dst is None:
                direpa_dst=profile["deploy_path"]
            pkg.zip_release(
                app_name=dy_csproj["app_name"],
                direpa_dst=direpa_dst,
                direpa_publish=profile["direpa_publish"],
            )

        to_deploy=  (args.deploy.here is True and args.publish.here is False) or \
                    (args.deploy.here is True and args.publish.here is True and (is_new_publishing is True or is_updated_webconfig is True or is_pre_deployed is True))

        if to_deploy is True:
            pkg.deploy(
                deploy_path=profile["deploy_path"],
                direpa_publish=profile["direpa_publish"],
                filenpa_msdeploy=dy_conf["filenpa_msdeploy"],
                exclude_paths=args.exclude.values,
                include_paths=args.include.values,
            )

    elif args.csc.here:
        dy_csproj=pkg.get_dy_csproj(direpa_root=args.path_csproj.value)
        dy_conf=get_dy_conf()

        mode=None
        if args.fat.here:
            mode="fat"
        elif args.slim.here:
            mode="slim"
        elif args.run.here:
            mode="run"
        if mode is None:
            pkg.msg.error("Select either --fat, --slim or --run argument.", exit=1)
        pkg.csc(
            csproj_xml_tree=dy_csproj["csproj_xml_tree"],
            debug=args.debug.here,
            direpa_framework=dy_conf["direpa_framework"],
            direpa_root=dy_csproj["direpa_root"],
            filenpa_assembly=dy_csproj["filenpa_assembly"],
            filenpa_csproj=dy_csproj["filenpa_csproj"],
            filenpa_msbuild=dy_conf["filenpa_msbuild"],
            link_keywords=args.link.values,
            mode=mode,
            params=args.params.value,
            project_name=args.csc.value,
        )
        