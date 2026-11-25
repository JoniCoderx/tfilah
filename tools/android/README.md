# תפילה for Android (native)

A native app: home, siddur in three nusachim, the Psalms, a reader (size, nikud, saved, share) and the "what blessing" tool.
All texts are bundled from `data/` and `tools/brachot/out.json`; nothing is typed here. Shared reading and the times pages open the site inside the app.

    python3 tools/android/prep.py tools/android/app/src/main/assets   # texts and fonts into the app (needs fonttools, brotli)
    cd tools/android && gradle testReleaseUnitTest assembleRelease     # needs the Android SDK (local.properties: sdk.dir=...)

`prep.py` expects the folders `p`, `t` and `fonts` to exist under the assets folder. The test opens every screen, every prayer file and every food.
Signing: the build reads a keystore from `TFILAH_KEYSTORE`. The store key is never kept in this repository.
