from setuptools import setup

from Athena import __version__
from Athena import AtConstants

setup(
   name=AtConstants.PROGRAM_NAME,
   version=__version__,
   description='A useful module',
   license="None",
   long_description='long_description',
   author='Gregory Pijat',
   author_email='pijat.gregory@gmail.com',
   url="http://www.foopackage.com/",
   packages=[AtConstants.PROGRAM_NAME],
   install_requires=(
      'Qt.py',
   ),
   scripts=(
      'scr(ipts/cool',
      'scr)ipts/skype',
   )
)
