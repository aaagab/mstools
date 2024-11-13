#!/usr/bin/env python3
# authors: Gabriel Auger
# name: mstools
# licenses: MIT 
__version__= "3.4.0"

# from .dev.mstools import mstools
# from .gpkgs import message as msg
# from .gpkgs.options import Options

from .dev.get_settings import get_settings, Settings, App, RawProfile
from .dev.publish import publish, zip_release, RebuildMode
from .dev.deploy import deploy, set_web_config, WebconfigOption
from .dev.get_profile import get_profile
from .dev.csc import csc, CscMode
from .dev.iis import iis
from .dev.csproj import get_csproj, Csproj, get_all_build_paths
from .dev.entity import entity
from .dev.csproj_clean_files import csproj_clean_files
from .dev.csproj_add_files import csproj_add_files
from .dev.csproj_update import csproj_update_files, build_project

from .gpkgs.options import Options
from .gpkgs import message as msg
from .gpkgs.json_config import Json_config
from .gpkgs.etconf import Etconf
from .gpkgs.nargs import Nargs
