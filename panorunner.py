import sys
import os
import argparse
import fnmatch
import re
from subprocess import call
from distutils.spawn import find_executable
import logging

class Runner(object):
    ori_files = []
    def __init__(self, **args):
        paths = os.environ['PATH'].split(':')
        paths.append(args['hugin'])
        self.path = ':'.join(paths)
        for k in ('directory', 'orient', 'verbose'):
            setattr(self, k, args.get(k))

        FORMAT = '%(asctime)-15s %(message)s'
        logging.basicConfig(format=FORMAT, filename='runner.log', 
                            level=getattr(logging, self.verbose.upper()))
        self.logger = logging.getLogger(__name__)
        if self.directory == '.':
            self.directory = os.getcwd()

        self.includes = ['*.JPG', '*.jpg']
        self.includes = r'|'.join([fnmatch.translate(x) for x in self.includes])
        files = [f for f in os.listdir(self.directory) if os.path.isfile(f)]
        self.ori_files = [os.path.join(self.directory, f) for f in files if re.match(self.includes, f)]
        self.tools = {}
        self.register_tools()

    def reset_orient(self):
        self.logger.info('resetting orientation...')
        kwargs = {'executable': self.tools['convert'],
                  'orient': self.orient}
        for f in self.ori_files:
            kwargs.update({'file': f})
            cmd = '{executable} {file} -orient {orient} {file}'
            # convert -list orientation to get a complete list of orientations
            try:
                _cmd = cmd.format(**kwargs)
                self.logger.debug(_cmd)
                call(_cmd.split())
            except Exception as e:
                print repr(e)
                break

    def register_tools(self):
        executable_list = ['convert', 'pto_gen']

        for e in executable_list:
            self.tools.update({e: find_executable(e, path=self.path)})

    def gen_project(self):
        print self.tools
        pass

parser = argparse.ArgumentParser()
parser.add_argument('--directory', default='.', help='image directory')
parser.add_argument('--orient', default='RightBottom', help='image orientation')
parser.add_argument('--verbose', default='INFO', help='INFO, DEBUG')
parser.add_argument('--hugin', default='/Applications/HuginTools')
args = parser.parse_args()

runner = Runner(**(args.__dict__))
#runner.reset_orient()
runner.gen_project()
    
