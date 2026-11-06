"""The rebrand rewrites what users read, never the file names the Hermes desktop build produces.

electron-builder names the Windows app ``Hermes.exe`` (apps/desktop/product-identity.cjs); a
rewritten ``Routster.exe`` probe in hermes_cli/main_desktop.py could never find a packaged build.
"""

from scripts.routster_rebrand import rewrite_source


def test_desktop_app_file_names_keep_upstream_spelling() -> None:
    source = 'APP = ["Hermes.exe", "Uninstall Hermes.exe", "Hermes Helper.app", "Hermes.app"]\n'
    assert rewrite_source(source) == source


def test_prose_name_is_still_rebranded() -> None:
    assert rewrite_source('MSG = "Restart Hermes to apply"\n') == 'MSG = "Restart Routster to apply"\n'
