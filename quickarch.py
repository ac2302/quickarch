#!/usr/bin/python

import os
import subprocess


class Installer:
    def __init__(self):
        self.root = '/mnt'

    def run(self, command):
        """runs command in the terminal"""
        exit_code = os.system(command)

    def run_chroot(self, command):
        """ runns command after chrooting """
        self.run(f"arch-chroot {self.root} {command}")

    def install(self, packages, noconfirm=True):
        """
            installs given packages in chroot envinronment
            eg.
                packages = ['vim', 'gcc']
        """
        # adding packages to a string
        pkg_str = ' '.join(packages)
        #the command which will be executed
        command = f'pacman -Sy {pkg_str}'
        # conditionally adding the --noconfirm flag
        if noconfirm:
            command += ' --noconfirm'
        # running the command
        self.run_chroot(command)

    def enable(self, services):
        """
            enables given services on the work in progress arch install
            eg.
                services = ['sshd', 'lightdm']
        """
        for service in services:
            self.run_chroot(f'systemctl enable {service}')


if __name__ == '__main__':
    ins = Installer()
    ins.enable(['pee', 'pee', 'poo', 'poo'])
    ins.run_chroot('neofetch')