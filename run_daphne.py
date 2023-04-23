import os
import sys
from daphne.cli import CommandLineInterface

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fishyandex.settings')

if __name__ == '__main__':
    sys.argv.extend(['-b', '192.168.0.102', '-p', '80', 'fishyandex.asgi:application'])
    CommandLineInterface().run(sys.argv)