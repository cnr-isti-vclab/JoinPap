import platform
import sys
import os
import subprocess
from pathlib import Path

osused = platform.system()
if osused != 'Linux' and osused != 'Windows' and osused != 'Darwin':
    raise Exception("Operative System not supported")

# check python version
if sys.version_info[0] < 3 or (sys.version_info[0] == 3 and sys.version_info[1] < 6):
    raise Exception("Must be using Python >= 3.6\nInstallation aborted.")

# manage thorch
something_wrong_with_nvcc = False
flag_install_pythorch_cpu = False
nvcc_version = ''
torch_package = 'torch==1.11.0'
torchvision_package = 'torchvision==0.12.0'

# if the user wants to install cpu torch
if len(sys.argv)==2 and sys.argv[1]=='cpu':
    flag_install_pythorch_cpu = True

# get nvcc version
if flag_install_pythorch_cpu == False and osused != 'Darwin':
    result = subprocess.getstatusoutput('nvcc --version')
    output = result[1]
    rc = result[0]
    if rc == 0:
        pos = output.find('release')
        cont = True
        if pos >= 0:
            pos += 8
            nvcc_version = output[pos:pos+4]
            print('Found NVCC version: ' + nvcc_version)
        else:
            raise Exception('Could not read NVCC version.\nInstallation aborted.')
    else:
        print('Impossible to run "nvcc --version" command. CUDA seems to be not installed.')
        something_wrong_with_nvcc = True # remember that we had issues on finding nvcc


    # get nvcc version
    if '9.2' in nvcc_version:
        nvcc_version = '9.2'
        print('Torch for CUDA 9.2')
        torch_package += '+cu92'
        torchvision_package += '+cu92'
    elif nvcc_version == '10.1':
        print('Torch for CUDA 10.1')
        torch_package += '+cu101'
        torchvision_package += '+cu101'
    elif nvcc_version == '10.2':
        # 10.2 is default in torch and torchvision
        print('Torch for CUDA 10.2')
    elif '11.3' in nvcc_version:
        print('Torch for CUDA 11.3')
        torch_package += '+cu113'
        torchvision_package += '+cu113'
    elif something_wrong_with_nvcc==False:
        # nvcc is installed, but some version that is not supported by torch
        print('nvcc version installed not supported by pytorch!!')
        something_wrong_with_nvcc = True # remember that we had issues on finding nvcc

    # if the user tried to run the installer but there were issues on finding a supported
    if something_wrong_with_nvcc == True and flag_install_pythorch_cpu == False:
        ans = input('Something is wrong with NVCC. Do you want to install the CPU version of pythorch? [Y/n]')
        if ans == "Y":
            flag_install_pythorch_cpu = True
        else:
            raise Exception('Installation aborted. Install a proper NVCC version or set the pythorch CPU version.')
elif osused == 'Darwin':
    flag_install_pythorch_cpu = True
    print('NVCC not supported on MacOS. Installing cpu version automatically...')


# somewhere before, this flag has been set to True and the user choose to install the cpu torch version
if flag_install_pythorch_cpu==True:
    print('Torch will be installed in its CPU version.')
    if osused != 'Darwin': # for macos, the DEFAULT is cpu, therefore we don't need the '+cpu' flag
        torch_package += '+cpu'
        torchvision_package += '+cpu'

# manage gdal
gdal_version = ''

if osused == 'Linux':
    result = subprocess.getstatusoutput('gdal-config --version')
    output = result[1]
    rc = result[0]
    if rc != 0:
        print('Trying to install libgdal-dev...')
        from subprocess import STDOUT, check_call
        import os
        try:
            check_call(['sudo', 'apt-get', 'install', '-y', 'libgdal-dev'],
                       stdout=open(os.devnull, 'wb'), stderr=STDOUT)
        except:
            raise Exception('Impossible to install libgdal-dev. Please install manually libgdal-dev before running '
                            'this script.\nInstallation aborted.')
        result = subprocess.getstatusoutput('gdal-config --version')
        output = result[1]
        rc = result[0]
    if rc == 0:
        gdal_version = output
        print('GDAL version installed: ' + output)
    else:
        raise Exception('Impossible to access to gdal-config binary.\nInstallation aborted.')
    print('Trying to install libxcb-xinerama0...')
    from subprocess import STDOUT, check_call
    import os
    try:
        check_call(['sudo', 'apt-get', 'install', '-y', 'libxcb-xinerama0'],
                   stdout=open(os.devnull, 'wb'), stderr=STDOUT)
    except:
        print('Impossible to install libxcb-xinerama0. If TagLab does not start, please install manually libxcb-xinerama0.')

elif osused == 'Darwin':
    result = subprocess.getstatusoutput('gdal-config --version')
    output = result[1]
    rc = result[0]
    if rc != 0:
        print('Trying to install gdal...')
        from subprocess import STDOUT, check_call
        import os
        try:
            check_call(['brew', 'install', 'gdal'],
                       stdout=open(os.devnull, 'wb'), stderr=STDOUT)
        except:
            raise Exception('Impossible to install gdal through homebrew. Please install manually gdal before running '
                            'this script.\nInstallation aborted.')
        result = subprocess.getstatusoutput('gdal-config --version')
        output = result[1]
        rc = result[0]
    if rc == 0:
        gdal_version = output
        print('GDAL version installed: ' + output)
    else:
        raise Exception('Impossible to access to gdal-config binary.\nInstallation aborted.')

gdal_package = 'gdal==' + gdal_version

# build coraline
if False: #osused != 'Windows':
    try:
        out = subprocess.check_output(['cmake', '--version'])
        if out[0] != 0:
            if osused == 'Darwin':
                print('Trying to install cmake...')
                from subprocess import STDOUT, check_call
                import os
                try:
                    check_call(['brew', 'install', 'cmake'],
                               stdout=open(os.devnull, 'wb'), stderr=STDOUT)
                except:
                    raise Exception('Impossible to install cmake through homebrew. Please install manually cmake before running '
                                    'this script.\nInstallation aborted.')
            elif osused == 'Linux':
                print('Trying to install cmake...')
                from subprocess import STDOUT, check_call
                import os
                try:
                    check_call(['sudo', 'apt-get', 'install', '-y', 'cmake'],
                               stdout=open(os.devnull, 'wb'), stderr=STDOUT)
                except:
                    raise Exception('Impossible to install cmake. Please install manually cmake before running '
                                    'this script.\nInstallation aborted.')
        os.chdir('coraline')
        result = subprocess.getstatusoutput('cmake .')
        if result[0] == 0:
            result = subprocess.getstatusoutput('make')
            if result[0] == 0:
                print('Coraline built correctly.')
                os.chdir('..')
            else:
                raise Exception('Error while building Coraline library.\nInstallation aborted.')
        else:
            raise Exception('Error while configuring Coraline library.\nInstallation aborted.')
    except OSError:
        raise Exception('Cmake not found. Coraline library cannot be compiled. Please install cmake '
                        'first.\nInstallation aborted.')

# requirements needed by TagLab
install_requires = [
    'wheel',
    'pyqt5',
    'numpy==1.24.4',
    'scikit-image==0.18',
    'scikit-learn',
    'pandas',
    'opencv-python',
    'matplotlib',
    'albumentations',
    'shapely',
    'rectangle-packer',
    'git+https://github.com/fabiocarrara/papyrus-matching.git'
]

# installing all the packages
subprocess.check_call([sys.executable, "-m", "pip", "install", *install_requires])

# installing torch, gdal and rasterio

# torch
subprocess.check_call([sys.executable, "-m", "pip", "install", torch_package,
                       '-f', 'https://download.pytorch.org/whl/torch_stable.html'])
subprocess.check_call([sys.executable, "-m", "pip", "install", torchvision_package,
                       '-f', 'https://download.pytorch.org/whl/torch_stable.html'])