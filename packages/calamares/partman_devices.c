/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2014-2015 Teo Mrnjavac <teo@kde.org>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Based on parted_devices.c, from partman-base.
 *   <http://anonscm.debian.org/cgit/d-i/partman-base.git>
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

/* final31 (disk-alanı uyarısı düzeltmesi):
 * Orijinal check_big_enough() libparted ped_device_probe_all() ile disk
 * tarıyordu; sanal makinede (virtio/NVMe) probe yanlış negatif veriyor ve
 * 50 GB diske rağmen "en az 4 GB alan gerekli" uyarısı çıkıyordu (UEFI+MBR
 * aynı). Bu sürüm libparted'e hiç benzemez: "size" dosyalarından
 * (/sys/block altında her aygıt için) DETERMINISTIK okuma yapar (512 baytluk
 * sektor sayisi) — ortamdan bagimsizdir, yetki/probe sorunlari yoktur.
 *
 * Hariç tutulanlar (orijinal mantıkla paralel): ram/zram/ramzswap (compcache),
 * cdrom (sr*), floppy (fd*), read-only aygıtlar, loop ve dm- (kurulum
 * ortamının kendi kalıntıları; gerçek disk sda/vda/nvme0n1/hd* sayılır). */

#include "partman_devices.h"

#include <dirent.h>
#include <stdio.h>
#include <string.h>

/* *INDENT-OFF* */
/* clang-format off */

static int
name_skipped(const char* name)
{
    if ( !strncmp( name, "ram", 3 ) ) return 1;
    if ( !strncmp( name, "zram", 4 ) ) return 1;
    if ( !strncmp( name, "ramzswap", 8 ) ) return 1;
    if ( !strncmp( name, "loop", 4 ) ) return 1;
    if ( !strncmp( name, "dm-", 3 ) ) return 1;
    if ( !strncmp( name, "sr", 2 ) ) return 1;   /* optik sürücü */
    if ( !strncmp( name, "fd", 2 ) ) return 1;   /* disket */
    return 0;
}

/* /sys/block/<ad>/ro → "1" ise salt-okunur aygıt (orijinaldeki
 * dev->read_only hariç tutmasının karşılığı). */
static int
is_readonly(const char* name)
{
    char path[ 256 ];
    FILE* f;
    int ro = 0;

    snprintf( path, sizeof( path ), "/sys/block/%s/ro", name );
    f = fopen( path, "r" );
    if ( f )
    {
        int v = 0;
        if ( fscanf( f, "%d", &v ) == 1 )
            ro = ( v == 1 );
        fclose( f );
    }
    return ro;
}

int
check_big_enough( long long required_space )
{
    DIR* d = opendir( "/sys/block" );
    struct dirent* e;

    if ( !d )
        return 0;

    while ( ( e = readdir( d ) ) )
    {
        char path[ 256 ];
        FILE* f;
        long long sectors = -1;

        if ( e->d_name[0] == '.' )
            continue;
        if ( name_skipped( e->d_name ) )
            continue;
        if ( is_readonly( e->d_name ) )
            continue;

        snprintf( path, sizeof( path ), "/sys/block/%s/size", e->d_name );
        f = fopen( path, "r" );
        if ( !f )
            continue;
        if ( fscanf( f, "%lld", &sectors ) != 1 )
            sectors = -1;
        fclose( f );

        if ( sectors > 0 && sectors * 512LL >= required_space )
        {
            closedir( d );
            return 1;
        }
    }

    closedir( d );
    return 0;
}

/*
Local variables:
indent-tabs-mode: nil
c-file-style: "linux"
c-font-lock-extra-types: ("Ped\\sw+")
End:
*/
