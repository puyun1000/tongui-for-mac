#!/bin/zsh
set -euo pipefail
cd "${0:A:h}"

python_bin="${PYTHON_BIN:-/opt/homebrew/bin/python3.13}"
venv_dir="${VENV_DIR:-.venv}"
if [[ ! -x "$venv_dir/bin/python" ]]; then
  "$python_bin" -m venv "$venv_dir"
fi
"$venv_dir/bin/python" -m pip install -r requirements-mac.txt

# OpenCC resolves config names inside opencc_data. Install the upstream rules
# into this isolated build environment, then include that data in the bundle.
data_root="$("$venv_dir/bin/python" -c 'import opencc_data, pathlib; print(pathlib.Path(opencc_data.__file__).parent / "data")')"
mkdir -p "$data_root/config" "$data_root/jieba_dict"
cp t2gov/*.txt "$data_root/"
cp t2gov/*.json "$data_root/config/"
cp jieba/* "$data_root/jieba_dict/"

"$venv_dir/bin/python" self_test.py
"$venv_dir/bin/python" -m PyInstaller \
  --noconfirm --clean --windowed \
  --name TongguiMac \
  --osx-bundle-identifier tech.terrytian.tongguimac \
  --target-arch arm64 \
  --icon logo.icns \
  --collect-data opencc_data \
  --collect-binaries opencc \
  main.py

dist/TongguiMac.app/Contents/MacOS/TongguiMac --self-test
info_plist="dist/TongguiMac.app/Contents/Info.plist"
plutil -replace CFBundleDisplayName -string '规范繁体字形转换器' "$info_plist"
plutil -replace CFBundleShortVersionString -string '1.4.4' "$info_plist"
plutil -replace CFBundleVersion -string '1.4.4' "$info_plist"
plutil -replace LSMinimumSystemVersion -string '13.0' "$info_plist"
plutil -replace CFBundleDocumentTypes -json '[{"CFBundleTypeName":"可转换文档","CFBundleTypeExtensions":["docx","txt","md","srt","ass","ssa","lrc","epub","pdf"],"CFBundleTypeRole":"Viewer","LSHandlerRank":"Alternate"}]' "$info_plist"
# Finder metadata added by cloud-backed folders can invalidate bundle signing.
# Stage the release on a local temporary volume, remove Finder metadata and
# sign that exact copy before creating the disk image.
stage_dir="$(mktemp -d /private/tmp/tonggui-mac.XXXXXX)"
ditto --noextattr dist/TongguiMac.app "$stage_dir/TongguiMac.app"
find "$stage_dir/TongguiMac.app" -type d -exec xattr -d com.apple.FinderInfo {} \; 2>/dev/null || true
codesign --force --deep --sign - "$stage_dir/TongguiMac.app"
codesign --verify --deep --strict "$stage_dir/TongguiMac.app"
"$stage_dir/TongguiMac.app/Contents/MacOS/TongguiMac" --self-test
cp README.md LICENSE "$stage_dir/"
ln -s /Applications "$stage_dir/Applications"
hdiutil create -volname '规范繁体字形转换器 1.4.4' \
  -srcfolder "$stage_dir" -format UDZO -ov \
  "dist/TongguiMac-1.4.4-arm64.dmg"
hdiutil verify "dist/TongguiMac-1.4.4-arm64.dmg"
echo "Built: $PWD/dist/TongguiMac-1.4.4-arm64.dmg"
