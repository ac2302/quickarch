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
        # hostname
        self.hostname = config['hostname']
        # packages and services
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
        
        # installing custom packages
        self.install(packages=self.custom_packages)
        # enabling custom services
        self.enable(services=self.custom_services)

        # installing grub
        self.install(['grub', 'efibootmgr', 'dosfstools', 'os-prober', 'mtools'])
        self.run_chroot(f'mount {self.boot_part} /boot/EFI')
        self.run_chroot('grub-install --target=x86_64-efi --bootloader-id=arch_grub --recheck')
        self.run_chroot('grub-mkconfig -o /boot/grub/grub.cfg')

        # configring hostname
        self.run_chroot(f'hostnamectl set-hostname {self.hostname}')
        # setting /etc/hosts
        with open(f'{self.root}/etc/hosts', 'a') as f:
            print('127.0.0.1\tlocalhost', file=f)
            print('::1\t\tlocalhost', file=f)
            print(f'127.0.1.1\t{self.hostname}', file=f)

        # installing the desktop env
        if self.de:
            self.install(['xorg'])
            if self.de == 'kde':
                self.install(['plasma-meta', 'kde-applications'])
                self.enable(['sddm'])
            elif self.de == 'gnome':
                self.install(['gnome', 'gnome-tweaks'])
                self.enable(['ddm'])
            elif self.de == 'mate':
                self.install(['mate', 'mate-extra', 'lightdm', 'lightdm-gtk-greeter'])
                self.enable(['lightdm'])
            elif self.de == 'xfce':
                self.install(['xfce4', 'xfce4-goodies', 'lightdm', 'lightdm-gtk-greeter'])
                self.enable(['lightdm'])

        # setting the passwords
        self.run('clear')
        print('set passwords for users and other configuration stuff')
        print('use command \'passwd\' to set root password')
        print('create new users with useradd')
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
        print('\033[H\033[J', end='')   # sorcery that clears console
        # printing the prompt and options
        print(prompt)
        if choices:
            print('enter the number for the option you want to select')
            for entry in enumerate(choices):
                print(f'{entry[0]}: {entry[1]}')
        # setting the prompt
        prompt = '>> '
        if default:
            prompt = f'default: {default} ' + prompt
        # taking the input
        output = 'NA'   # this variable stores the user input. I need to get beter names for my variables
        while output == 'NA':
            if not choices:
                try:
                    output = input(prompt)
                    if default and (output == ''):
                        output = default
                    elif (not default) and (output == ''):
                        output = 'NA'
                        raise Exception
                except KeyboardInterrupt:
                    break
                except:
                    output = 'NA'
                    print('invalid input. try again')
            else:
                try:
                    user_input = input(prompt)
                    if user_input:
                        index = int(user_input)
                        output = choices[index]
                    else:
                        if default:
                            output = default
                        else:
                            raise Exception
                except KeyboardInterrupt:
                    break
                except:
                    output = 'NA'
                    print('invalid input. try again')
        return output

    def recommended_packages(package_list, service_list):
        def install_prompt(package, service=None, default=True, description='no description'):
            print('*'*40)
            print(package)
            if service:
                print(f'will enable service {service}')
            print(description)
            # setting the prompt and some stuff
            prompt = 'install? '
            deny = 'n'
            if default:
                prompt += '[Y/n]: '
            else:
                prompt += '[y/N]: '
            # getting the input from user
            user_input = input(prompt).casefold()
            selected = default
            if user_input == 'y':
                selected = True
            elif user_input == 'n':
                selected = False
            if selected:
                package_list.append(package)
                if service:
                    service_list.append(service)

        #    package, service, default, description 
        packages = [
            ('linux', None, True, 'the latest linux kernel'),
            ('linux-lts', None, False, 'the linux long term support kernel'),
            ('linux-hardened', None, False, 'the security focussed linux kernel'),
            ('linux-headers', None, True, 'headers for the latest linux kernel'),
            ('linux-lts-headers', None, False, 'headers for the linux lts kernel'),
            ('base-devel', None, True, 'packages for building package from source'),
            ('openssh', 'sshd', False, 'ssd server'),
            ('networkmanager', 'NetworkManager', True, 'used for networking (strongly reccomended)'),
            ('wpa_supplicant', None, True, 'used for networking (strongly reccomended)'),
            ('wireless_tools', None, True, 'used for networking (strongly reccomended)'),
            ('netctl', None, True, 'used for networking (strongly reccomended)'),
            ('dialog', None, True, 'used for networking (strongly reccomended)'),
            ('intel-ucode', None, False, 'install for intel cpu'),
            ('amd-ucode', None, False, 'install for amd cpu'),
            ('mesa', None, False, 'video drivers for amd and intel gpu'),
            ('nvidia', None, False, 'nvidia video drivers for linux kernel'),
            ('nvidia-lts', None, False, 'nvidia video drivers for linux-lts kernel'),
            ('nvidia-utils', None, False, 'nvidia utilities'),
            ('virtualbox-guest-utils', None, False, 'video drivers for virtual machines'),
            ('xf86-video-vmware', None, False, 'video drivers for virtual machines'),
        ]
        # calling install_prompt() for every package
        for package in packages:
            install_prompt(package=package[0], service=package[1], default=package[2], description=package[3])

    conf = {}
    # partition and file system stuff
    conf['boot_part'] = get_input('boot partition\nexample: /dev/sda1')
    conf['root_part'] = get_input('root partition\nexample: /dev/sda2')
    conf['home_part'] = get_input('home partition\nexample: /dev/sda2\nenter \'none\' for no home partition', default=None)
    if conf['home_part'].casefold() == 'none':
        conf['home_part'] = ''
    conf['root_fs'] = get_input('root filesystem',default='ext4', choices=['bfs', 'btrfs', 'cramfs', 'ext2', 'ext3', 'ext4', 'fat', 'minix', 'msdos', 'vfat', 'xfs'])
    if conf['home_part']:
        conf['home_fs'] = get_input('home filesystem',default='ext4', choices=['bfs', 'btrfs', 'cramfs', 'ext2', 'ext3', 'ext4', 'fat', 'minix', 'msdos', 'vfat', 'xfs'])
    else:
        conf['home_fs'] = ''
    
    # hostname
    conf['hostname'] = get_input('hostname', default='arch')

    # packages and services
    packages = []
    services = []
    # recommended packages
    recommended_packages(packages, services)
    # adding the packages and services to config
    conf['custom_packages'] = packages
    conf['custom_services'] = services

    # desktop env
    conf['de'] = get_input('Desktop Env', choices=['nothing', 'kde', 'gnome', 'mate', 'xfce'])
    if conf['de'] == 'nothing':
        conf['de'] = ''

    return json.dumps(conf)


if __name__ == '__main__':
    if '-f' in sys.argv:
        conf_path = sys.argv[sys.argv.index('-f') + 1]
        with open(conf_path, 'r') as f:
            conf = json.loads(f.read())
        ins = Installer(conf)
        ins.start()
    else:
        conf = gen_config()
        print(json.loads(conf))
        if '-s' in sys.argv:
            conf_path = sys.argv[sys.argv.index('-f') + 1]
            with open(conf_path, 'w') as f:
                print(conf, file=f)
        else:
            ins = Installer(json.loads(conf))
            ins.start()
