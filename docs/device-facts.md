# TAB-A05-BA1の確認済み情報と未確認項目

これは公開stockファイルの記録であり、ユーザーの実機測定結果ではありません。
別ビルド・改変済み端末・別パネルに同じ条件が成立するとは限りません。

| 項目 | 公開stockで確認できた値 | 根拠 |
| --- | --- | --- |
| モデル | TAB-A05-BA1 | build.prop |
| 純正ビルド | 01.03.000 / Android 9 / SDK 28 | build.prop |
| ABI | arm64-v8a, armeabi-v7a, armeabi | build.prop |
| Treble | true | build.prop |
| system-as-root | true | build.prop |
| board platform | mt8168 | vendor_build.prop |
| VNDK | 28 | default.prop |
| 標準言語 | ja-JP | build.prop |
| LCD density | 240 | build.prop |
| vendorの画面回転値 | 270 | vendor_build.prop |
| セキュリティパッチ | 2022-01-05 | build.prop |

## 推論・候補（実機確認前）

- PHH Android 10の `arm64-ab` が最初の候補。ABIとSAR条件から選定しているだけで、起動成功の証明ではない。
- PHHの `ab` 名称と物理的なA/B更新スロットは区別する。スロット構成は未確定。
- `ro.oem_unlock_supported=1` は解除済み・必ず解除可能という意味ではない。
- タッチパネルのNVT/FTS差分があるため、stock kernel/firmwareを初期段階で置換しない。
- `ro.sf.hwrotation=270` をGSIへそのまま設定して正しく回転するとは限らない。Android 10側のHWC/SurfaceFlingerと実機で確認する。

## 未確認で、書き込み前に必要な情報

systemの実測容量、物理パーティション一覧、bootヘッダー、fstab、AVB/vbmetaの条件、
kernelのAndroid 10互換性、解除状態、復旧に使える純正イメージ、実機でのGSI起動結果。
公開情報に見当たらない項目を「なし」「false」と決めつけない。

## 情報源

- [CTZ stock build.prop](https://github.com/s1204IT/DchaLibraries-CTZ/blob/main/Common/build.prop)
- [CTZ stock vendor_build.prop](https://github.com/s1204IT/DchaLibraries-CTZ/blob/main/Common/vendor_build.prop)
- [CTZ stock default.prop](https://github.com/s1204IT/DchaLibraries-CTZ/blob/main/Common/default.prop)
- [EasyBLU（タッチパネル差分のソース）](https://github.com/Kobold831/EasyBLU/blob/59d56f3ff412e3bcce2fc5dfcf3aea8459b8894f/app/src/main/java/com/saradabar/easyblu/MainActivity.java)
- [AOSP GSIの構成・前提条件](https://source.android.com/docs/core/tests/vts/gsi)
- [PHH Android 10 v222の上流配布](https://github.com/phhusson/treble_experimentations/releases/tag/v222)

値の照合基準は `config/ctz-stock.json`。取得ベースは `config/gsi-base.json`。
