#!/bin/bash
# Yerinde ANKA ilk oturum betiği: başlat (kickoff) ikonunu ve duvar kağıdını ayarlar.
set -u

sleep 6

FLAG="$HOME/.config/yerinde-first-run"
[ -f "$FLAG" ] && exit 0

ICON="yerinde"
CS=$(kreadconfig6 --file kdeglobals --group General --key ColorScheme 2>/dev/null)
case "$CS" in
  *Dark*) ICON="yerinde-light" ;;
esac

WP="file:///usr/share/wallpapers/Yerinde-Destek-Yesil/contents/images/wallpaper.png"

set_kickoff_icon_kconfig() {
  local c a plugin
  for c in $(seq 0 40); do
    plugin=$(kreadconfig6 --file plasma-org.kde.plasma.desktop-appletsrc --group Containments --group "$c" --key plugin 2>/dev/null)
    [ "$plugin" = "org.kde.plasma.panel" ] || continue
    for a in $(seq 0 60); do
      plugin=$(kreadconfig6 --file plasma-org.kde.plasma.desktop-appletsrc \
        --group Containments --group "$c" --group Applets --group "$a" --key plugin 2>/dev/null)
      if [ "$plugin" = "org.kde.plasma.kickoff" ]; then
        kwriteconfig6 --file plasma-org.kde.plasma.desktop-appletsrc \
          --group Containments --group "$c" --group Applets --group "$a" \
          --group Configuration --group General --key icon "$ICON"
        return 0
      fi
    done
  done
  return 1
}

SCRIPT="var ICON='$ICON';
var allPanels = panels();
for (var p = 0; p < allPanels.length; p++) {
  var panel = allPanels[p];
  var widgets = panel.widgets();
  for (var w = 0; w < widgets.length; w++) {
    var widget = widgets[w];
    if (widget.type == 'org.kde.plasma.kickoff') {
      widget.currentConfigGroup = ['General'];
      widget.writeConfig('icon', ICON);
    }
  }
}
var allDesktops = desktops();
for (var i = 0; i < allDesktops.length; i++) {
  var d = allDesktops[i];
  d.wallpaperPlugin = 'org.kde.image';
  d.currentConfigGroup = Array('Wallpaper', 'org.kde.image', 'General');
  d.writeConfig('Image', '$WP');
}"

if qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "$SCRIPT" >/dev/null 2>&1; then
  :
else
  set_kickoff_icon_kconfig
  /usr/bin/plasma-apply-wallpaperimage /usr/share/wallpapers/Yerinde-Destek-Yesil/contents/images/wallpaper.png >/dev/null 2>&1 || true
fi

: > "$FLAG"

if [ -x /usr/bin/yerinde-first-run ]; then
  /usr/bin/yerinde-first-run
fi
exit 0
