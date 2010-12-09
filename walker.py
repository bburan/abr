"""
Walker encapsulates os.walk's directory traversal as an object with 
the added features of excluded directories and a hook for calling 
an outside function to act on each file.  Walker can easily be 
subclassed for more functionality.

ReWalker filters filenames in traversal by a regular expression.
"""
import os, os.path
import re

class Walker(object):
    def __init__(self, dir, executeHook=None, excludeDirs=[]):
        self.dir = dir
        self.executeHook = executeHook
        self.excludeDirs = excludeDirs
        
    def isValidFile(self, fileName):
        return True
        
    def isValidDir(self, dir):
        head, tail = os.path.split(dir)
        valid = (not tail in self.excludeDirs)
        return valid
                  
    def executeFile(self, path):
        if self.executeHook:
            self.executeHook(path)
        # else subclass Walker and override executeFile
            
    def execute(self):
        for root, dirs, fileNames in os.walk(self.dir):
            for fileName in fileNames:
                if self.isValidDir(root) and self.isValidFile(fileName):
                    path = os.path.join(root, fileName)
                    self.executeFile(path)
        return self 

    def list(self):
        self.fnames = []
        oldhook = self.executeHook
        self.executeHook = self.fnames.append
        self.execute()
        self.executeHook = oldhook
        fnames = self.fnames
        del self.fnames
        return fnames
    
class ReWalker(Walker):
    def __init__(self, dir, regexp, executeHook=None, excludeDirs=[]):
        Walker.__init__(self, dir, executeHook, excludeDirs)
        self.re = re.compile(regexp)

    def isValidFile(self, fileName):
        return self.re.match(fileName)

def Walk( root, recurse=0, pattern='*', return_folders=0 ):
    import fnmatch, os, string
    
    # initialize
    result = []

    # must have at least root folder
    try:
        names = os.listdir(root)
    except os.error:
        return result

    # expand pattern
    pattern = pattern or '*'
    pat_list = string.splitfields( pattern , ';' )
    
    # check each file
    for name in names:
        fullname = os.path.normpath(os.path.join(root, name))

        # grab if it matches our pattern and entry type
        for pat in pat_list:
            if fnmatch.fnmatch(name, pat):
                if os.path.isfile(fullname) or (return_folders and os.path.isdir(fullname)):
                    result.append(fullname)
                continue
                
        # recursively scan other folders, appending results
        if recurse:
            if os.path.isdir(fullname) and not os.path.islink(fullname):
                result = result + Walk( fullname, recurse, pattern, return_folders )
            
    return result

if __name__ == '__main__':
    # test code
    print '\nExample 1:'
    files = Walk('.', 1, '*', 1)
    print 'There are %s files below current location:' % len(files)
    for file in files:
        print file

    print '\nExample 2:'
    files = Walk('.', 1, '*.py;*.html')
    print 'There are %s files below current location:' % len(files)
    for file in files:
        print file
