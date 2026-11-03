import QtQuick
import QtQuick.Effects
import qs.Commons

// Wallpaper: the current background, blurred, as on Omarchy's own lock screen.
Item {
  id: root

  // The lock screen's view (LockView.qml): which wallpaper, and whether to load it.
  property var host

  // Fades out while the lock releases, so the wait reads as unlocking.
  function play() { fade.stop(); opacity = 1 }
  function leave() { fade.start() }

  NumberAnimation { id: fade; target: root; property: "opacity"; to: 0; duration: 1100 }

  Image {
    id: wallpaper
    anchors.fill: parent
    // Drawn only through the blur, so neither fade shows the sharp image.
    visible: false
    // A video wallpaper shows its still poster.
    property string path: root.host.video ? root.host.videoPosterPath : root.host.backgroundPath
    // Built as Service.qml builds lockWallpaperUrl, so the service's decode serves this one: ahead
    // of the lock in-process, alongside it in each lock's fresh worker. Never re-read while locked.
    source: root.host.loadBackground && path
      ? Util.fileUrl(path) + (root.host.backgroundVersion ? "?v=" + root.host.backgroundVersion : "")
      : ""
    fillMode: Image.PreserveAspectCrop
    asynchronous: true
    // The same URL and size the service decoded, so this reuses it.
    cache: true
    sourceSize.width: width
    sourceSize.height: height
  }

  MultiEffect {
    anchors.fill: wallpaper
    source: wallpaper
    // Decoded after the lock showed, the wallpaper fades in rather than popping in.
    opacity: wallpaper.status === Image.Ready ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: 250 } }
    autoPaddingEnabled: false
    blurEnabled: wallpaper.status === Image.Ready
    blur: 1.0
    blurMax: 128
    blurMultiplier: 1.25
    contrast: -0.08
  }
}
