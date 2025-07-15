#!/bin/bash
# Build a simple .deb package for wireguard-ui.

set -e

version="${1:-0.1.0}"
pkg="wireguard-ui"
build_dir="$(mktemp -d)"
pkg_dir="$build_dir/${pkg}_${version}"

mkdir -p "$pkg_dir/DEBIAN" \
         "$pkg_dir/usr/share/${pkg}" \
         "$pkg_dir/usr/bin" \
         "$pkg_dir/usr/share/applications" \
         "$pkg_dir/usr/share/icons/hicolor/256x256/apps"

cat > "$pkg_dir/DEBIAN/control" <<CONTROL
Package: ${pkg}
Version: ${version}
Section: utils
Priority: optional
Architecture: all
Depends: python3, python3-pyqt6, python3-xdg, wireguard, firejail
Maintainer: $(git config user.email || echo "unknown@example.com")
Description: Simple WireGuard GUI
CONTROL

cp -r src "$pkg_dir/usr/share/${pkg}/"
install -m 755 install.sh "$pkg_dir/usr/share/${pkg}/install.sh"

cat > "$pkg_dir/DEBIAN/postinst" <<'POSTINST'
#!/bin/bash
set -e
/usr/share/wireguard-ui/install.sh
POSTINST
chmod 755 "$pkg_dir/DEBIAN/postinst"

cat > "$pkg_dir/usr/bin/${pkg}" <<'SCRIPT'
#!/bin/bash
exec python3 /usr/share/wireguard-ui/src/main.py "$@"
SCRIPT
chmod +x "$pkg_dir/usr/bin/${pkg}"

cat > "$pkg_dir/usr/share/applications/${pkg}.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=WireGuard UI
Exec=/usr/bin/${pkg}
Icon=${pkg}
Terminal=false
Categories=Network;
DESKTOP

install -m 644 src/icons/icon.ico "$pkg_dir/usr/share/icons/hicolor/256x256/apps/${pkg}.ico"

dpkg-deb --build "$pkg_dir" "$build_dir/${pkg}_${version}_all.deb"

mv "$build_dir/${pkg}_${version}_all.deb" .

echo "Created ${pkg}_${version}_all.deb"
