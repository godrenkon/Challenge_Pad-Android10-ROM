# 日本語標準のAndroid 10 GSIソース設定

**ソース差分を実装した段階です。system.imgのコンパイル、実機起動、書き込みは未検証です。**
`download-base.cmd` が取得する既存GSIには、この差分は適用されません。

## 実装内容

| 項目 | ソース設定 | 未確認事項 |
| --- | --- | --- |
| 初期言語 | `PRODUCT_LOCALES := ja_JP en_US`。初期値は日本語、英語も選択肢に残す | 実機の初期設定画面。既存userdataの言語は強制変更しない |
| ビルド対象 | `suiram_ctz10-userdebug`、PHH arm64/SAR vanilla/N派生 | 全Androidツリーでのコンパイル・起動 |
| ボード | `phhgsi_arm64_ab` を保持 | CTZの物理スロット構成を意味しない |
| ADB | PHHの `base.mk` と `system.prop` の両方で `ro.adb.secure=0` を `1` に変更 | stock vendor側のプロパティを含む実機の最終挙動 |
| USB初期構成 | PHHの `persist.sys.usb.config=adb` を `mtp` に変更 | 実機でのMTP動作 |
| 外部リバースデバッグ | PHHのdbclient・リバースデバッグ用script・init設定のコピーを除外 | 標準ADBの実機動作。OS全体の安全性を保証するものではない |
| 追加アプリ | `phh-su`・`me.phh.superuser`・GAppsを追加しない | userdebug自体は開発用。安全性・認証は保証しない |

日本語UIと日本語キーボードは別です。Android 10ツリーで確認できていないIMEモジュールを
推測で追加せず、日本語入力の組み込みと動作確認は残作業とします。
[nicoWnnGの別APKビルド](japanese-ime.ja.md)を実装しましたが、製品の `PRODUCT_PACKAGES` へはまだ追加していません。
timezone、画面回転、タッチ、HAL、kernel、SELinux設定はこの差分で変更しません。

## 上流の固定範囲

[source-profile.json](../config/source-profile.json) にAOSPタグ、PHH各コンポーネントのcommitと
入力10ファイルのGit blob SHAを記録しています。v222公開時期に対応する履歴から選んだ
コンポーネントのスナップショットであり、**v222配布バイナリと完全一致するmanifestではありません**。
SHA1は入力変更の検出用で、署名や配布物の真正性の証明ではありません。
残りの依存を含む[統合manifestとcommit記録ツール](source-build.ja.md)も実装しました。
実際の全同期・commit記録・ライセンス確認・Androidビルドはまだ必要です。

確認した上流：

- [v222 build.sh](https://github.com/phhusson/treble_experimentations/blob/4a5cabb317a69ccf646c5742f88d3345a9ccbecf/build.sh)
- [PHHの製品生成レシピ](https://github.com/phhusson/device_phh_treble/blob/64289357288a82fc9771c013b54f9e0833689599/generate.sh)
- [PHH版Android build](https://github.com/phhusson/platform_build/tree/165f02822b54b3651fb388fc425ea9f3b416b496)
- [PHH VNDK](https://github.com/phhusson/vendor_vndk/tree/cea8e7093616005e68fd527a2acd81f9f2af30c3)
- [PHH manifestの履歴](https://github.com/phhusson/treble_manifest/tree/b66f014948ac17c700fc4eb746c3b56b381611c2)
- [PHH system.prop](https://github.com/phhusson/device_phh_treble/blob/64289357288a82fc9771c013b54f9e0833689599/system.prop)
- [Android 10の起動時プロパティ読み込み](https://github.com/phhusson/platform_system_core/blob/67841c06d5c532acfd83cab9b38ab9c909ef5a2a/init/property_service.cpp)

`board-base.mk` はPHHの `system.prop` を `TARGET_SYSTEM_PROP` に追加します。
Android buildはこれをsystemの `build.prop` へ含めます。Android 10のinitでは後から読む
`build.prop` の値が `prop.default` の値を上書きできるため、`base.mk` だけの修正では
ADB認証を一貫して有効にできません。2ファイルを同じ値へ修正し、生成後の検査でも
system側の実効値を確認します。stock vendorの値はこのソース検査では確認できません。

上流 `build.sh` のreset/clean/force-syncを自動実行しません。
この適用コマンドはソース同期、ダウンロード、Androidビルド、端末操作を実行しません。
全同期・ビルドは別の工程ランナーとGitHub Actionsで行います。

## 専用ソースディレクトリへの適用

LinuxとPython 3.9以上を想定します。まず別ディレクトリに上流Android 10ソースを準備し、
全依存を含むmanifestの整合性を確認する必要があります。[統合ソース手順](source-build.ja.md)は
実装済みですが、同期・ビルド成功は未確認です。以下の `/path/to/...` は実際の場所へ置き換えてください。

```sh
# デフォルトは検査のみ。端末には何もしない。
python3 /path/to/ctz-rom/scripts/prepare-gsi-source.py /path/to/android

# 検査を通った入力に限り、明示的にソース差分を適用する。
python3 /path/to/ctz-rom/scripts/prepare-gsi-source.py /path/to/android --apply
```

ツールは全入力を検査してから、製品設定と登録を追加し、PHH共通 `base.mk` の2項目と
`system.prop` のADB認証設定を変更し、PHHの外部リバースデバッグ用3ファイルのコピーを除外します。
**これらの共通ファイルの変更は同じツリーの他のPHH製品にも影響します。既存作業ツリーと共有しないでください。**
元のbase.mk・system.prop・AndroidProducts.mkは `.ctz-original` として保存します。
生成後の内容検査は、この3ファイルが存在しないことも確認し、同名symlinkも拒否します。
未知の入力・変更済み出力・競合バックアップ・symlinkを拒否し、同じ状態で再実行すると変更しません。
I/O障害時の全ファイル一括ロールバックはありません。途中で失敗した場合は差分とバックアップを
手動確認し、自動再適用やバックアップ削除で押し切らないでください。

完全なソースが揃った後の**未検証のビルド対象**は次のとおりです。

```sh
cd /path/to/android
source build/envsetup.sh
lunch suiram_ctz10-userdebug
m -j4 systemimage
```

これは成功確認済みのビルド手順ではありません。コンパイル完了の証拠も成果物もまだありません。
この経路では `generate.sh` を実行しません。必要な製品登録は適用ツールが追加します。

## 容量とリリースの条件

上流のgeneric BoardConfigには2GiBのsystemサイズ設定がありますが、これはCTZの実測容量ではありません。
ここでは変更せず、実測容量との一致が確認されるまで生成イメージを書き込めるとは判断しません。
1GBのmicroSDに展開済みイメージが入ることも前提にしません。
stock保存・復旧・AVB・パネル差異・起動ログと全ハードウェア検証が必要です。
ツールの出力は常に `flashReady: false`、`fullAndroidBuildTested: false` です。

## 検証範囲

オフラインテストは検査、拒否条件、バックアップ、二度目の適用、Make式の日本語初期値を確認します。
Makeテストは簡易ハーネスであり、本物のAOSP製品継承処理やコンパイルを再現しません。
開発時には固定した上流10ファイルの実データでもCLIの検査・適用・再実行を確認しましたが、
これも全ソースビルドや実機テストではありません。
