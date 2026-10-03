# Android 10の実装方針

## 第1段階：純正boot/vendorを残すGSI移植

TAB-A05-BA1の公開stockはAndroid 9、arm64、Treble、system-as-root、VNDK 28。
最初は既存のAndroid 10 GSIをsystem側のベース候補にして、純正kernel/vendor HALとの
適合を実機で調べる。Treble対応だけでは、GSIの起動・全機能動作は保証されない。

| 構成要素 | 初期方針 | 現時点 |
| --- | --- | --- |
| Android framework/system | PHH AOSP 10 v222 arm64-ab vanillaを検証ベースにする | 上流ファイル選定済み、実機未検証 |
| boot/kernel | 対象stockのものを保存・維持 | イメージ未取得 |
| vendor/HAL/firmware | VNDK 28の対象stockを維持 | イメージ未取得 |
| CTZ固有修正 | 起動ログと差分から必要なoverlay/修正を実装 | 未着手、値を推測して適用しない |
| 言語 | 最終成果物は日本語標準、英語は追加選択肢 | ツールは日本語標準。上流GSIの言語は未変更 |
| GMS | OS起動・ハードウェア検証後に別途検証 | Play動作・認証未保証 |

`arm64-ab` の `ab` はPHH側のsystem-as-root向けイメージ名称として選んでいる。
この名称だけで、CTZに物理的なA/Bスロットがあると断定したり、`system_a` へ
書き込んだりしてはいけない。実際のfstabとブロック構成で再確認する。

PHH v222は2020年の古いAndroid 10検証ベースで、最新の安全性を提供するものではない。
Web閲覧・アカウント利用の安全性、Google Play認証、アプリの長期対応も別問題。
他者の上流GSIをこのプロジェクトがゼロから作ったROMと表記しない。

## 第2段階：CTZ専用差分

初回起動後、画面回転・タッチ・Wi-Fi・Bluetooth・音声・カメラ・スリープ復帰を
1つずつ調べる。純正値を丸ごとGSIへコピーしたり、SELinuxを無条件に無効化したり
しない。ログに対応した最小修正をソースとして管理する。

## 第3段階：再現可能な専用ビルド

上流ベース、CTZ差分、依存バージョン、ビルドログを固定して日本語標準の成果物を作る。
matching kernel sourceとvendor条件がそろえば、端末専用AOSP/LineageOSツリーも検討する。
現在の `device/benesse/ctz` はそのための無効化済み雛形であり、完成device treeではない。

## リリースの条件

実機起動と復旧を確認するまで、flashable releaseは作らない。
少なくとも対象stock、パネル種別、各ハードウェア検証結果、復旧手順、SHA256、
既知の不具合を公開する。「世界初」「完全動作」は証拠がないうちは使わない。
