#!/usr/bin/env python3
# author: Gabriel Auger
# version: 0.1.0
# name: release
# license: MIT

from pprint import pprint
import os
import sys

from ..gpkgs import message as msg

def examples():
    print()
    msg.info(r"""
        mstools --publish -p proxy --any

        mstools --deploy -p proxy --push '"web.config"'
        mstools -p mydev --deploy --exclude app scripts
        mstools --publish -p mydev -r any --deploy --exclude app scripts App_Data Content EmailTemplates bin\roslyn fonts Properties Views

        mstools --run --main mydebug --params thisisparam --slim
        mstools --run --main mydebug --params thisisparam --exe
        mstools --run --main mydebug --params thisisparam --fat

        mstools --run --main mydebug --slim --quiet

        # csc create a project in _runtime folder
        # it is for quick test on files that don't need to compile the whole solution.
        # fat use all the assemblies to compile you project
        mstools --csc mydebug --fat
        # run allow to run your compiled file once build
        mstools --csc mydebug --run
        # slim use only the assemblies selected with the keywords from link argument
        mstools --csc mydebug --slim --link mimetypes mydebug.cs system.net.http.dll datahelpers newtonsoft web.http.dll
    """, heredoc=True, bullet="")
