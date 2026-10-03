# 日本語入力APKのビルド

日本語UIだけでは日本語入力はできないため、nicoWnnGを固定ソースから別途ビルドします。
元のソースは [gorry/nicoWnnG](https://github.com/gorry/nicoWnnG)、固定commitは
`f0424c773941441124ca2707a5da7fb4816188df`。上流の著作権表示とApache-2.0ライセンスを保持します。
上流の配布APKを装ったものではなく、このプロジェクトの開発用ビルドです。

## 現状と成果物

2026-10-03 UTC、[実際のビルドと成果物検査が成功](https://github.com/godrenkon/Challenge_Pad-Android10-ROM/actions/runs/37158527674)。
未署名APKは9,605,864 bytes、SHA256は
`399ddf0ce58ab2fd07834d24843bc2708412729713e34d4452847c1ae7d5ecc2`。
固定ソース、適用差分、ビルド結果は [記録JSON](../config/japanese-ime-build.json) に保存しています。

`Build Japanese IME for Android 10` のGitHub Actionsで実際のAPKコンパイルを行います。
成功すると `ctz-japanese-ime-unsigned` artifactにAPK、SHA256付きreceipt、ログ、
APKのSDK情報、上流LICENSE/README、変更点のNOTICEが含まれます。artifactは30日保存です。

**APKは未署名で、そのまま端末へインストールできません。ROMへの組み込みと署名は後続工程です。**
現時点ではsystemimageビルドに追加していません。日本語変換、横画面、タブレット上での動作も未検証です。
APKコンパイル成功はAndroid 10 ROMの完成やCTZでの動作確認を意味しません。

## 固定した設定と変更

| 項目 | 設定 |
| --- | --- |
| パッケージ | `net.gorry.android.input.nicownng` |
| minSdk / targetSdk | 24 / 29（Android 10） |
| compileSdk / Build Tools | 36 / 36.0.0 |
| Gradle / Java | 8.13 / 17 |
| NDK | 28.1.13356709、native platform 24 |
| ABI | arm64-v8a / armeabi-v7a |
| 成果物 | release、未署名、非debuggable |

上流の非公開keystore設定を空の設定に置き換え、targetSdkとNDKを固定、x86を除外します。
古いNDKのarmeabi/android-3指定と廃止されたコンパイラオプションを除去し、libdlを明示します。
jcenterも使いません。アプリ本体と辞書データは改変しません。
Android 10 ROM用にtargetSdk 29を選ぶため、Google Play配布向けのLint項目
`ExpiredTargetSdkVersion` だけを除外します。それ以外のrelease Lintは有効です。
Gradle依存は上流のバージョン指定を使用し、全依存の内容ハッシュ固定までは行っていません。
したがって同じAPKのbit-for-bit再現性は未保証です。

## 手元のLinuxで実行

上記SDK、NDK、Gradle、Javaと `ANDROID_HOME` が必要です。
ビルド時はGoogle/Maven等から依存を取得します。チェックアウトは専用ディレクトリに置いてください。

```bash
git clone https://github.com/gorry/nicoWnnG.git /mnt/build/nicownng-source
git -C /mnt/build/nicownng-source checkout --detach f0424c773941441124ca2707a5da7fb4816188df
python3 scripts/build-japanese-ime.py /mnt/build/nicownng-source
python3 scripts/build-japanese-ime.py /mnt/build/nicownng-source \
  --output /mnt/build/ctz-ime-attempt-1 --run
```

既定はソース検査のみ。`--run` がソースを変更してビルドします。失敗でも出力とログを保持します。
既存出力を上書きしません。再試行は新しい専用チェックアウトと出力先を使ってください。
実行前にcommit、主要blob、Gitの変更と未追跡/ignoredファイル、隠されたindexフラグを検査します。
APKではパッケージ、SDK、非debuggable、ARMの辞書/変換ライブラリとELFヘッダを検査します。
これらはコード実行・日本語変換・OS互換性のテストではありません。

Google PlayやGMSは、このIMEビルドには含みません。
