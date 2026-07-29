from teledrive.i18n import keyset, t, set_language


def test_keysets_match():
    assert keyset("ar") == keyset("en")


def test_toggle():
    set_language("en"); assert t("nav.home") == "Home"
    set_language("ar"); assert t("nav.home") == "الرئيسية"
