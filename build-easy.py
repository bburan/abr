import os
from distutils.core import setup
import py2exe
import glob

import matplotlib

setup(  version='0.8.0-rc1',
        windows=['notebook.py'],
        data_files=[matplotlib.get_py2exe_datafiles()],
        options={"py2exe":{"optimize":2}},
    )
