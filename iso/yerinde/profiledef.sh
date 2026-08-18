#!/usr/bin/env bash
# shellcheck disable=SC2034

iso_name="yerinde-anka"
iso_label="YERINDE_ANKA"
iso_publisher="Yerinde Project"
iso_application="Yerinde ANKA"
iso_version="$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y.%m.%d)"
install_dir="arch"
buildmodes=('iso')
bootmodes=('bios.syslinux'
           'uefi.systemd-boot')
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '15')
bootstrap_tarball_compression=('zstd' '-c' '-T0' '--auto-threads=logical' '--long' '-19')
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/root"]="0:0:750"
  ["/root/.automated_script.sh"]="0:0:755"
  ["/root/.gnupg"]="0:0:700"
  ["/usr/local/bin/choose-mirror"]="0:0:755"
  ["/usr/local/bin/Installation_guide"]="0:0:755"
  ["/usr/local/bin/livecd-sound"]="0:0:755"
  ["/usr/local/bin/yerinde-finalize.sh"]="0:0:755"
  ["/usr/local/bin/yerinde-keyring-init"]="0:0:755"
  ["/usr/local/bin/yerinde-asistan-kur"]="0:0:755"
  ["/usr/local/bin/yerinde-live-user"]="0:0:755"
  ["/etc/sudoers.d/wheel"]="0:0:440"
)
