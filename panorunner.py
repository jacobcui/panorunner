import sys
import os
from copy import copy
from os import path, listdir, remove
import argparse
import fnmatch
import re
from subprocess import call, Popen, PIPE
from distutils.spawn import find_executable
import logging

def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

class Runner(object):
    ori_files = []
    def __init__(self, **args):
        paths = os.environ['PATH'].split(':')
        paths.append(args['hugin'])
        self.path = ':'.join(paths)
        for k in ('directory', 'orient', 'verbose', 'output', 'template', 'project',
                  'cp_density'):
            setattr(self, k, args.get(k, ''))

        FORMAT = '%(asctime)-15s %(message)s'
        logging.basicConfig(format=FORMAT, filename='runner.log', 
                            level=getattr(logging, self.verbose.upper()))
        self.logger = logging.getLogger(__name__)
        for f in ('directory', 'template'):
            v = getattr(self, f)
            setattr(self, f, path.abspath(v))

        self.project = self.output
        for n, f in [('project', 'pto'), ('output', 'tif')]:
            setattr(self, n,
                    path.join(self.directory, '{}.{}'.format(getattr(self, n), f)))

        self.includes = ['*.JPG', '*.jpg']
        self.includes = r'|'.join([fnmatch.translate(x) for x in self.includes])
        files = [f for f in listdir(self.directory) if path.isfile(path.join(self.directory, f))]
        self.ori_files = [path.join(self.directory, f) for f in files if re.match(self.includes, f)]
        self.project_files = copy(self.ori_files)
        self.tools = {}
        self.register_tools()

    def run_command(self, command, additional, **kwargs):
        for c in ('project', 'output'):
            if not kwargs.get(c):
                kwargs[c] = getattr(self, c)
        _cmd = command.format(**kwargs)
        msg = _cmd + ' '.format(additional)
        print msg
        self.logger.info(msg)
        call(_cmd.split() + additional)

    def reset_orient(self):
        kwargs = {'executable': self.tools['convert'],
                  'orient': self.orient}
        for f in self.project_files:
            kwargs.update({'file': f})
            _cmd = '{executable} {file} -orient {orient} {file}'
            # convert -list orientation to get a complete list of orientations
            self.run_command(_cmd, [], **kwargs)

    def register_tools(self):
        executable_list = ['convert', 'pto_gen', 'nona', 'enblend', 'cpfind',
                           'pto_template', 'cpclean', 'linefind', 'autooptimiser',
                           'pano_modify']

        for e in executable_list:
            self.tools.update({e: find_executable(e, path=self.path)})

    def gen_project(self):
        kwargs = {'executable': self.tools['pto_gen'], 
                  'project': self.project,
                  'template': self.template}

        _cmd = '{executable} -o {project}'
        self.run_command(_cmd, self.project_files, **kwargs)

        kwargs['executable'] = self.tools['pto_template']
        _cmd = '{executable} --output={project} --template={template} {project}' 
        self.run_command(_cmd, [], **kwargs)

    def find_control_points(self):
        kwargs = {'executable': self.tools['cpfind'],
                  'project': self.project,
                  'cp_density': self.cp_density}
        # find control points
        _cmd = '{executable} --celeste --linearmatch --sieve1width {cp_density} --sieve1height {cp_density} --sieve1size {cp_density} -o {project} {project}'
        self.run_command(_cmd, [], **kwargs)

        # control point clean
        kwargs['executable'] = self.tools['cpclean']
        _cmd = '{executable} -o {project} {project}'
        self.run_command(_cmd, [], **kwargs)

    def find_vertical_lines(self):
        kwargs = {'executable': self.tools['linefind']}
        _cmd = '{executable} -o {project} {project}'
        self.run_command(_cmd, [], **kwargs)

    def optimize(self):
        # Optimize position, do photometric optimization, straighten panorama and select suitable output projection
        kwargs = {'executable': self.tools['autooptimiser']}
        _cmd = '{executable} -a -m -l -s -o {project} {project}'
        self.run_command(_cmd, [], **kwargs)

        kwargs['executable'] = 'pano_modify'
        _cmd = '{executable} --canvas=AUTO --crop=AUTO -o {project} {project}'
        self.run_command(_cmd, [], **kwargs)

    def stitch(self):
        kwargs = {'executable': self.tools['nona'],
                  'project': self.project,
                  'output': self.output}
        _cmd = "{executable} -o out -m TIFF_m {project}"
        self.run_command(_cmd, self.project_files, **kwargs)

        kwargs['executable'] = 'enblend'
        _cmd = "{executable} -o {output}"

        inter_files = ['out{:04d}.tif'.format(i) for i in range(len(self.project_files))]
        self.run_command(_cmd, inter_files, **kwargs)

        # clean outxxxx.tif
        for f in inter_files:
            try:
                remove(f)
            except OSError as e:
                print repr(e)

    def hdr_output(self):
        if len(self.ori_files) != 12:
            print 'Please use 4 sets of 3 photos taken in explores brackets'
            sys.exit()

        for i, files in enumerate( chunks(self.ori_files, 3)):
            out_file = path.join(self.directory, '{:04d}'.format(i+1))
            self.project_files.append(out_file)
            kwargs = {'files': [path.join(self.directory, f) for f in files],
                      'out_file': out_file}

            pfsinme = Popen(['pfsinme'] + kwargs['files'], stdout=PIPE)
            pfsinme.wait()
            pfshdrcalibrate = Popen(['pfshdrcalibrate'], stdin=pfsinme.communicate()[0], stdout=PIPE)
            pfshdrcalibrate.wait()
            pfstmo_drago03 = Popen(['pfstmo_drago03'], stdin=pfshdrcalibrate.communicate()[0], stdout=PIPE)
            pfstmo_drago03.wait()
            pfsgamma = Popen(['pfsgamma', '-g', '1.8'], stdin=pfstmo_drago03.communicate()[0], stdout=PIPE)
            pfsgamma.wait()
            pfsout = Popen(['pfsout', '{}.TIF'.format(kwargs['out_file'])], stdin=pfsgamma.communicate()[0])
            pfsout.wait()

parser = argparse.ArgumentParser()
parser.add_argument('output', default='finished', help='output file name')
parser.add_argument('--directory', default='.', help='image directory')
parser.add_argument('--orient', default='LeftBottom', help='image orientation')
parser.add_argument('--verbose', default='INFO', help='INFO, DEBUG')
parser.add_argument('--hugin', default='/Applications/HuginTools')
parser.add_argument('--template', default=path.join(path.dirname(__file__), 'template.pto'))
parser.add_argument('--cp_density', default=120)
args = parser.parse_args()

if __name__ == '__main__':
    runner = Runner(**(args.__dict__))
    runner.hdr_output()
#    runner.reset_orient()
#    runner.gen_project()
#    runner.find_control_points()
#    runner.find_vertical_lines()
#    runner.optimize()
#    runner.stitch()
