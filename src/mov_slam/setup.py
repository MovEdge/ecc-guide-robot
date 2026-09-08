from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'mov_slam'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'maps'), glob('maps/*')),
        (os.path.join('share', package_name, 'landmarks'), glob('landmarks/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='movedge',
    maintainer_email='movedge@todo.todo',
    description='ECC 실측 맵과 랜드마크 좌표DB를 share 리소스로 제공',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
        ],
    },
)
