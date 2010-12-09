from distutils.core import setup
from distutils.core import Distribution
import py2exe
import sys
import glob
import os
import shutil
import matplotlib

# Subclass py2exe to ensure upx compression of binaries
from py2exe.build_exe import py2exe as build_exe
class py2exe_upx(build_exe):

    def initialize_options(self):
        # Add a new "upx" option for compression with upx
        build_exe.initialize_options(self)
        self.upx = 0

    def copy_file(self, *args, **kwargs):
        # Override to UPX copied binaries.
        (fname, copied) = result = build_exe.copy_file(self, *args, **kwargs)

        basename = os.path.basename(fname)
        if (copied and self.upx and
            (basename[:6]+basename[-4:]).lower() != 'python.dll' and
            fname[-4:].lower() in ('.pyd', '.dll')):
            os.system('upx --best "%s"' % os.path.normpath(fname))
        return result

    def patch_python_dll_winver(self, dll_name, new_winver=None):
        # Override this to first check if the file is upx'd and skip if so
        if not self.dry_run:
            if not os.system('upx -qt "%s" >nul' % dll_name):
                if self.verbose:
                    print "Skipping setting sys.winver for '%s' (UPX'd)" % \
                          dll_name
            else:
                build_exe.patch_python_dll_winver(self, dll_name, new_winver)
                # We UPX this one file here rather than in copy_file so
                # the version adjustment can be successful
                if self.upx:
                    os.system('upx --best "%s"' % os.path.normpath(dll_name))

# Run py2exe
if len(sys.argv) == 1:
    sys.argv.append("py2exe")
    sys.argv.append("-q")

# Ensure clean build
if os.path.exists("dist"):
    shutil.rmtree("dist")

if os.path.exists("build"):
    shutil.rmtree("build")

manifest_template = '''
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<assemblyIdentity
    version="5.0.0.0"
    processorArchitecture="x86"
    name="%(prog)s"
    type="win32"
/>
<description>%(prog)s Program</description>
<dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="X86"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
</dependency>
</assembly>
'''

class Target:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        self.company_name = "Speech and Hearing Bioscience and Technology"
        self.copyright = "2007 by Brad Buran"
        self.name = "ABR Peak Analysis"

excludes = ["pywin", "pywin.debugger", "pywin.debugger.dbgcon",
            "pywin.dialogs", "pywin.dialogs.list", 'MySQLdb',
            "Tkconstants", "Tkinter", "tcl", "_imagingtk", 
            "PIL._imagingtk", "ImageTk", "PIL.ImageTk", "FixTk"]

includes = ['matplotlib.numerix', 'pytz']

RT_MANIFEST = 24
manifest = manifest_template % dict(prog="notebook")

notebook = Target(
    version = '0.8.0-rc1',
    description = "ABR Notebook",
    script = "notebook.py",
    other_resources = [(RT_MANIFEST, 1, manifest)],
    dest_base = "notebook"
    )

setup(
    #cmdclass = {'py2exe': py2exe},
    windows = [notebook],
	 console = [notebook],
    zipfile = 'library.zip',
    data_files = matplotlib.get_py2exe_datafiles(),
    options = {
        'py2exe': {
            'compressed': 2,
            'optimize': 2,
            'packages': includes,
            'excludes': excludes,
        }
    })
