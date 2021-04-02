#!/usr/bin/env python3
# authors: Gabriel Auger
# name: mstools
# licenses: MIT 
__version__ = "2.5.0"

# from .dev.mstools import mstools
# from .gpkgs import message as msg
# from .gpkgs.options import Options

from .dev.examples import examples
from .dev.publish import publish, zip_release
from .dev.deploy import deploy, set_web_config
from .dev.get_profile import get_profile
from .dev.csc import csc
from .dev.csproj import get_dy_csproj
from .dev.entity import entity
from .dev.csproj_clean_files import csproj_clean_files
from .dev.csproj_add_files import csproj_add_files
from .dev.csproj_update import csproj_update_files, build_project

from .gpkgs.options import Options
from .gpkgs import message as msg
from .gpkgs.json_config import Json_config
