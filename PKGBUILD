# Maintainer: SofaTUI Contributors
pkgname=sofatui
pkgver=1.0.0
pkgrel=1
pkgdesc="Rich SofaScore-style Terminal UI (TUI) for live football scores, stats, Attack Momentum, commentary, lineups, and standings"
arch=('any')
url="https://github.com/wthernani/sofatui"
license=('MIT')
depends=(
  'python'
  'python-textual'
  'python-rich'
  'python-curl_cffi'
  'python-httpx'
)
makedepends=(
  'python-build'
  'python-installer'
  'python-setuptools'
)
checkdepends=(
  'python-pytest'
)
source=()
sha256sums=()

# Keep makepkg's work directory in .pkgbuild when invoked from the project root
# so it never collides with the Python src-layout (./src/sofatui) or uses /tmp.
if [[ "${BUILDDIR:-$startdir}" -ef "$startdir" ]]; then
  BUILDDIR="$startdir/.pkgbuild"
  mkdir -p "$BUILDDIR"
fi

prepare() {
  rm -rf "$srcdir/$pkgname-$pkgver"
  mkdir -p "$srcdir/$pkgname-$pkgver"
  cp -a "$startdir/pyproject.toml" "$startdir/README.md" "$startdir/LICENSE" "$startdir/src" "$startdir/tests" \
    "$srcdir/$pkgname-$pkgver/"
}

build() {
  cd "$srcdir/$pkgname-$pkgver"
  python -m build --wheel --no-isolation
}

check() {
  cd "$srcdir/$pkgname-$pkgver"
  PYTHONPATH="$PWD/src" pytest -o cache_dir="$srcdir/.pytest_cache" -k "test_fast_dns_resolver or test_favorites_persistence or test_all_renderers_produce_rich_output"
}

package() {
  cd "$srcdir/$pkgname-$pkgver"
  python -m installer --destdir="$pkgdir" dist/*.whl
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}
