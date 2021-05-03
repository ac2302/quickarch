#!/usr/bin/python

import os
import subprocess


class CommandFailedError(Exception):
    """ I'm too lazy to do this properly """
    pass


class Installer:
    def __init__(self):
        self.boot_part = '/dev/sda1'
        self.root_part = '/dev/sda2'
        self.root_fs = 'ext4'
        self.home_part = None
        self.home_fs = 'ext4'
        self.root = '/mnt'
        self.locale = 'en_IN UTF-8'
        self.timezone = 'Asia/Kolkata'
        self.hostname = 'arch'
        self.kernels = ['linux']
        self.custom_packages = ['openssh']
        self.custom_services = ['sshd']
        self.root_password = 'password'

    def start(self):
        # formatting the partitions
        if self.boot_part:
            self.run(f'mkfs.fat -F32 {self.boot_part}')
        if self.root_part:
            self.run(f'mkfs.{self.root_fs} {self.root_part}')
        if self.home_part:
            self.run(f'mkfs.{self.home_fs} {self.home_part}')

        # mounting the partitions
        self.run(f'mount {self.root_part} {self.root}')
        self.run(f'mkdir -p {self.root}/etc {self.root}/home {self.root}/boot/EFI')
        if self.home_part:
            self.run(f'mount {self.home_part} {self.root}/home')
        # generating fstab
        self.run(f'genfstab -U {self.root} >> {self.root}/etc/fstab')

        # pacstrapping
        self.run(f'pacstrap {self.root} base linux-firmware')
        
        # installing the kernels
        for kernel in self.kernels:
            packages = [kernel, kernel + '-headers']
            self.install(packages=packages)
        
        # installing custom packages
        self.install(packages=self.custom_packages)
        # enabling custom services
        self.enable(services=self.custom_services)

        # setting a locale
        with open(f'{self.root}/etc/locale-gen', 'a') as f:
            print(self.locale, file=f)
        self.run_chroot('locale-gen')

        # installing grub
        self.install(['grub', 'efibootmgr', 'dosfstools', 'os-prober', 'mtools'])
        self.run_chroot(f'mount {self.boot_part} /boot/EFI')
        self.run_chroot('grub-install --target=x86_64-efi --bootloader-id=arch_grub --recheck')
        self.run_chroot('grub-mkconfig -o /boot/grub/grub.cfg')

        # adding users

        # setting the passwords
        print('\n\nset password for root user')
        self.run_chroot('passwd')

        # powering off after user input
        print('*'*40)
        input('finished installing. press enter to poweroff')
        self.run('umount -a ; poweroff')

    def run(self, command):
        """runs command in the terminal"""
        print(f'\n\n# {command}\n\n',end='')
        exit_code = os.system(command)
        if exit_code != 0:
            print(f'the command: {command} returned a non-zero exit code')
            raise CommandFailedError

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
    ins.start()
