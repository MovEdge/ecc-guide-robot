from setuptools import find_packages, setup

package_name = 'mov_tts'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='movedge',
    maintainer_email='movedge@todo.todo',
    description='Gemini TTS 기반 음성 출력 — 텍스트를 받아 합성 음성으로 재생',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'tts_node = mov_tts.tts_node:main',
        ],
    },
)
