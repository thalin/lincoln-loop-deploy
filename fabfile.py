import os
import sys
from types import ListType
        
class VersionControl(object):
    """Generates command strings for VCS tasks"""
    def __init__(self, *args, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)
        self.cmd = '%s ' % self.dist
        
class Subversion(VersionControl):
    def checkout(self):
        cmd = self.cmd
        if hasattr(self, 'rev'):
            cmd += '-r %s ' % self.rev
        cmd += 'co %s ./src/%s' % (self.url, self.name)
        return cmd

class Git(VersionControl):
    def clone(self):
        cmd = '%s clone %s ./src/%s' % (self.cmd, self.url, self.name)
        if hasattr(self, 'branch'):
            cmd += '\\\n&& (cd ./src/%s; git checkout --track -b %s origin/%s)' % (self.name, self.branch, self.branch) 
        return cmd

class Mercurial(VersionControl):
     def clone(self):
        cmd = '%s clone %s ./src/%s' % (self.cmd, self.url, self.name)
        if hasattr(self, 'branch'):
            cmd += '\\\n&& (cd ./src/%s; hg update -C %s )' % (self.name, self.branch) 
        return cmd

class Bazaar(VersionControl):
    def branch(self):
        cmd = '%s branch %s ./src/%s' % (self.cmd, self.url, self.name)
        return cmd


def install_module(src_dir, module_name='', dist_utils=False, media_type=None):
    """
    Installs a Python module from the ./src directory either using
    distutils or by symlinking the package to site-packages
    """
    #setup using distutils
    if dist_utils:
        cmd = '(cd src/%s;\\\n../../ve/bin/python setup.py install)' % src_dir
    #symlink to site-packages
    else:
        src = os.path.join(src_dir,module_name).rstrip('/')
        if media_type:
            dest_path = 'media/%s/' % media_type
            src_path = '../../src/%s' % src
        else:
            dest_path = 've/lib/python2.5/site-packages'
            src_path = '../../../../src/%s' % src
        cmd = 'ln -sf %s %s' % (src_path, dest_path)
    return cmd
    
def pkg_install(pkg):
    """
    Installs packages based on package arguments.  If a package name isn't
    specified, assume dist_utils.
    """
    if pkg.has_key('media'):
        media = pkg['media']
        local('mkdir media/%s' % media, fail='warn')
    else:
        media = None
    if pkg.has_key('package'):
        if isinstance(pkg['package'], ListType):
            for package in pkg['package']:
                local(install_module(pkg['name'], package, media_type=media))
        else:
            local(install_module(pkg['name'], pkg['package'], media_type=media))
    else:
        local(install_module(pkg['name'], dist_utils=True, media_type=media))

def bootstrap():
    """
    1. Creates a new virtualenv
    2. Downloads all sources from fabreqs.py, adding them 
       to the PYTHONPATH along the way
    
    """
    #put the cwd on the python path so we can use fabreqs.py
    sys.path.append('.') 
    from fabreqs import requirements
    local('rm -rf ve src')
    local('virtualenv ve')
    #hack activate so it uses project directory instead of ve in prompt
    local('sed \'s/(`basename \\\\"\\$VIRTUAL_ENV\\\\\"`)/(`basename \\\\`dirname \\\\"$VIRTUAL_ENV\\\\"\\\\``)/g\' ve/bin/activate > ve/bin/activate.tmp')
    #sed 's/(`basename \\"\$VIRTUAL_ENV\\\"`)/(`basename \\`dirname \\"$VIRTUAL_ENV\\"\\``)/g'
    local('mv ve/bin/activate.tmp ve/bin/activate')
    local('mkdir src', fail='warn')
    local('mkdir media', fail='warn')
    for pkg in requirements:
        #easy_install package from PyPi
        if pkg['dist'] == 'pypi':
            cmd = './ve/bin/easy_install -a %s' % pkg['name']
            if pkg.has_key('rev'):
                cmd += '==%s' % pkg['rev']
            local(cmd)
            
        #download single file
        elif pkg['dist'] == 'wget':
            local('cd src && wget %s' % pkg['url'])
            local(install_module(pkg['name']))

        elif pkg['dist'] == 'zipfile':
            filename = pkg['url'].split('/')[-1]
            local('cd src && wget %s && unzip %s' % (pkg['url'], filename))
            pkg_install(pkg)
        
        else: #it's a vcs
            if pkg['dist'] == 'svn':
                local(Subversion(**pkg).checkout())
            elif pkg['dist'] == 'git':
                local(Git(**pkg).clone())
            elif pkg['dist'] == 'hg':
                local(Mercurial(**pkg).clone())
            elif pkg['dist'] == 'bzr':
                local(Bazaar(**pkg).branch())
            else:
                raise Exception, '%s is not a recognized distribution method' % pkg['dist']
            pkg_install(pkg)
