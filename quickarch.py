#!/usr/bin/python

import os
import sys
import json
import subprocess


class CommandFailedError(Exception):
    """ I'm too lazy to do this properly """
    pass


class Installer:
    def __init__(self, config):
        # partition and file system stuff
        self.boot_part = config['boot_part']
        self.root_part = config['root_part']
        self.root_fs = config['root_fs']
        self.home_part = config['home_part']
        self.home_fs = config['home_fs']
        # this one is just... there
        self.root = '/mnt'
        # locale and timezone stuff
        self.locale = config['locale']
        self.timezone = config['timezone']
        # hostname
        self.hostname = config['hostname']
        # packages and services
        self.kernels = config['kernels']
        self.custom_packages = config['custom_packages']
        self.custom_services = config['custom_services']
        # desktop env
        self.de = config['de']

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
        self.run('clear')
        print('set passwords for users and other configuration stuff')
        print('use command \'passwd\' to set root password')
        print('use command \'passwd <user>\' to set password of user with username <user>')
        print('press ctrl + D when done')
        self.run('arch-chroot /mnt')

        # done
        print("setup complete. type poweroff to shutdown or reboot to restart")

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


def gen_config():
    def get_input(prompt, choices=None, default=None):
        pass
    conf = {}
    # partition and file system stuff
    conf['boot_part'] = get_input('boot partition\nexample: /dev/sda1')
    conf['root_part'] = get_input('root partition\nexample: /dev/sda2')
    conf['home_part'] = get_input('home partition\nexample: /dev/sda2\nleave blank for no home partition')
    conf['root_fs'] = get_input('root filesystem\ndefault: ext-4', choices=['bfs', 'btrfs', 'cramfs', 'ext2', 'ext3', 'ext4', 'fat', 'minix', 'msdos', 'vfat', 'xfs'])
    if conf['home_part']:
        conf['home_fs'] = get_input('home filesystem\ndefault: ext-4', choices=['bfs', 'btrfs', 'cramfs', 'ext2', 'ext3', 'ext4', 'fat', 'minix', 'msdos', 'vfat', 'xfs'])
    # locale and timezone stuff
    conf['locale'] = get_input('locale\nexample: en_IN utf-8\nsee /etc/locale/gen for more locales')
    conf['timezone'] = get_input('timezone\nexample: Asia/Kolkata')
    # hostname
    conf['root_fs'] = get_input('hostname\ndefault: arch')
    # packages and services

    # desktop env

    return json.dumps(conf)


if __name__ == '__main__':
    if '-f' in sys.argv:
        conf_path = sys.argv[sys.argv.index('-f') + 1]
        with open(conf_path, 'r') as f:
            conf = json.loads(f.read())
        ins = Installer(conf)
    else:
        conf = gen_config()
        print(conf)
