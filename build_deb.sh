#!/usr/bin/env bash
# build_deb.sh  — собирает автономный .deb‑пакет WireGuard‑UI с фиксированным стилем Adwaita‑Dark
# usage:   ./build_deb.sh 0.1.1

set -euo pipefail

version="${1:-0.1.0}"
pkg="wireguard-ui"
build_dir="$(mktemp -d)"
pkg_dir="$build_dir/${pkg}_${version}"

# multiarch‑подкаталог (x86_64 → x86_64-linux-gnu, arm64 → aarch64-linux-gnu …)
multiarch=$(dpkg-architecture -qDEB_HOST_MULTIARCH)

# --------------------------------------------------------------------------- #
#  каталоги пакета
# --------------------------------------------------------------------------- #
install -d \
  "$pkg_dir/DEBIAN" \
  "$pkg_dir/usr/share/${pkg}" \
  "$pkg_dir/usr/bin" \
  "$pkg_dir/usr/share/applications" \
  "$pkg_dir/usr/share/icons/hicolor/256x256/apps"

# --------------------------------------------------------------------------- #
#  control‑файл
# --------------------------------------------------------------------------- #
cat > "$pkg_dir/DEBIAN/control" <<CONTROL
Package: ${pkg}
Version: ${version}
Section: utils
Priority: optional
Architecture: all
Depends: python3, python3-pyqt6, python3-pyxdg, wireguard, firejail, adwaita-qt6, adwaita-icon-theme
Maintainer: $(git config user.email || echo "unknown@example.com")
Description: Simple WireGuard GUI (Qt6) with unified Adwaita-Dark appearance
CONTROL

# --------------------------------------------------------------------------- #
#  исходники программы
# --------------------------------------------------------------------------- #
cp -r src "$pkg_dir/usr/share/${pkg}/"
install -m 755 install.sh "$pkg_dir/usr/share/${pkg}/install.sh"
install -m 755 patch_desktop_exec.sh "$pkg_dir/usr/share/${pkg}/patch_desktop_exec.sh"

# --------------------------------------------------------------------------- #
#  postinst: запускаем install.sh и обновляем кэши
# --------------------------------------------------------------------------- #
cat > "$pkg_dir/DEBIAN/postinst" <<'POSTINST'
#!/usr/bin/env bash
set -e
/usr/share/wireguard-ui/install.sh

# обновляем кэш .desktop и иконок
command -v update-desktop-database >/dev/null && update-desktop-database -q || true
command -v gtk-update-icon-cache   >/dev/null && gtk-update-icon-cache -q /usr/share/icons/hicolor || true
exit 0
POSTINST
chmod 755 "$pkg_dir/DEBIAN/postinst"

# --------------------------------------------------------------------------- #
#  /usr/bin/wireguard-ui  — wrapper
# --------------------------------------------------------------------------- #
cat > "$pkg_dir/usr/bin/${pkg}" <<SCRIPT
#!/usr/bin/env bash
# Запускает GUI от обычного пользователя и гарантирует стиль Adwaita-Dark.

set -euo pipefail

APP_DIR="/usr/share/wireguard-ui"
PYTHON="\$(command -v python3)"

# -- Qt: подключаем системные плагины даже под pyenv --------------------------------
QT_SYS_PLUGINS="/usr/lib/${multiarch}/qt6/plugins"
export QT_PLUGIN_PATH="\${QT_SYS_PLUGINS}:\${QT_PLUGIN_PATH:-}"
export QT_QPA_PLATFORMTHEME=gtk3          # родные диалоги/иконки GTK
export QT_STYLE_OVERRIDE=adwaita-dark     # единый стиль кнопок/списков

# -- если запустились root'ом, переключаемся на исходного пользователя --------------
if [[ \$EUID -eq 0 ]]; then
    user="\${SUDO_USER:-}"
    [[ -z \$user && -n \${PKEXEC_UID:-} ]] && user=\$(id -nu "\$PKEXEC_UID" 2>/dev/null || true)
    user="\${user:-\$(logname 2>/dev/null || awk -F: '\$3>=1000{print \$1; exit}' /etc/passwd)}"
    exec sudo -u "\$user" -E "\$PYTHON" "\$APP_DIR/src/main.py" "\$@"
else
    exec "\$PYTHON" "\$APP_DIR/src/main.py" "\$@"
fi
SCRIPT
chmod 755 "$pkg_dir/usr/bin/${pkg}"

# --------------------------------------------------------------------------- #
#  .desktop‑файл
# --------------------------------------------------------------------------- #
cat > "$pkg_dir/usr/share/applications/${pkg}.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=WireGuard UI
Comment=Configure WireGuard tunnels
Exec=wireguard-ui %u
Icon=${pkg}
Terminal=false
Categories=Network;Security;
StartupNotify=true
DESKTOP

# --------------------------------------------------------------------------- #
#  иконка
# --------------------------------------------------------------------------- #
install -m 644 src/icons/icon.png \
        "$pkg_dir/usr/share/icons/hicolor/256x256/apps/${pkg}.png"

# --------------------------------------------------------------------------- #
#  сборка .deb
# --------------------------------------------------------------------------- #
dpkg-deb --build "$pkg_dir" "$build_dir/${pkg}_${version}_all.deb"
mv "$build_dir/${pkg}_${version}_all.deb" .
echo "Created  ${pkg}_${version}_all.deb"
