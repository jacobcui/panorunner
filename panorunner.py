import os
import argparse
import fnmatch
import re
from subprocess import call

class Runner(object):
    ori_files = []
    def __init__(self, **args):
        for k in ('directory', 'orient'):
            setattr(self, k, args.get(k))
        self.includes = ['*.JPG', '*.jpg']
        self.includes = r'|'.join([fnmatch.translate(x) for x in self.includes])
        files = [f for f in os.listdir(self.directory) if os.path.isfile(f)]
        self.ori_files = [f for f in files if re.match(self.includes, f)]

    def reset_orient(self):
        for f in self.ori_files:
            kwargs = {'file': f, 'orient': self.orient}
            cmd = 'convert {file} -orients {orient} {file}'
            # convert -list orientation to get a complete list of orientations
            try:
                call(cmd.format(**kwargs))
            except Exception as e:
                print repr(e)
                break

parser = argparse.ArgumentParser()
parser.add_argument('--directory', default='.', help='image directory')
parser.add_argument('--orient', default='RightBottom', help='image orientation')
args = parser.parse_args()

runner = Runner(**(args.__dict__))
runner.reset_orient()

    
