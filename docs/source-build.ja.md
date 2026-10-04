# 統合ソースの同期・commit固定・systemimageビルド

**クラウドで全ソース同期と製品差分の適用を通過し、本物のAndroidコンパイルを実行中です。system.img生成と実機起動は未確認です。**
ここでできるのはsystem側の開発用GSIであり、純正boot/vendorを置き換える完成ROMではありません。
USBや端末接続はこのソースビルド工程には不要です。
[日本語標準の工程ランナー](build-workflow.ja.md)で、以下の準備からビルドまでをまとめて実行することもできます。

## 固定した構成

[ctz-android10.xml](../manifest/ctz-android10.xml) はAOSPの `android-10.0.0_r41` に、
PHH側の固定27プロジェクトを統合し、上流でDarwin指定のMacホスト専用9プロジェクトを除いた、Linux用753プロジェクトのmanifestです。
AOSP manifest自体はcommit `458a84154e391e7d0cd4f87ab17955bcfb3b4310` の内容を確認しました。
AOSP側はタグ固定、PHH/追加側は40桁commit固定です。
PHHの履歴はv222公開前のスナップショットを選んだもので、配布v222と完全一致する証明ではありません。
`vendor/magisk`、GApps、FOSSアプリの追加manifestは含めません。上流のpre-upload hook登録も除いています。

入力の根拠と固定commitは [source-provenance.json](../config/source-provenance.json)、
上流manifestの内容は [upstream/](../manifest/upstream/) に保存しています。
`generate-source-manifest.py` は入力blobを照合し、統合結果が公開manifestと一致することを検査します。
生成だけでは、全projectが同期可能であること・互いにビルド可能であることは証明できません。

## 必要な実行環境

Linux x86_64、Git、AndroidのRepoコマンド、Python 3.9以上と、Android 10に対応するビルド依存が必要です。
Windows向け準備ツールとは別の工程です。AndroidのJava等の依存は対応する上流prebuiltsを用います。
Repoコマンドの導入とホスト依存は[AOSPのセットアップ手順](https://source.android.com/docs/setup/start)を参照してください。
最新AOSP向けの数値やパッケージ一覧が、そのままAndroid 10の最小要件とは限りません。

このプロジェクトのビルド前検査は、**出力先の空き150GiB、実効メモリ8GiB以上**を保守的な目安として要求します。
これは公式最小要件でも、成功を保証する数値でもありません。ソース保存分の容量は別に必要です。
CPU・並列数・ホストライブラリなどにも依存します。RAMが少ない環境では並列数を下げます。
ローカル環境はディスク全体が約32GiBのため、実コンパイルは[クラウド工程](cloud-rom-build.ja.md)で実行しています。

## 1：新しい専用ディレクトリへ同期

`/path/to/...` と `<project-commit>` を実際の場所と、このリポジトリの40桁commitへ置き換えます。
作業済みディレクトリでreset/clean/force-syncを行う手順はありません。
このリポジトリのソースZIPも別に展開しておきます。

```sh
mkdir /path/to/android-ctz10
cd /path/to/android-ctz10
repo init -u https://github.com/godrenkon/Challenge_Pad-Android10-ROM.git \
  -b <project-commit> -m manifest/ctz-android10.xml -g all
repo sync -c -j4
```

`-g all` は753プロジェクト全体をcommit固定ツールで照合するために必要です。
Repoによる全同期は2026-10-04のクラウド再試行で成功を確認しました。
同期が失敗した場合はエラーを解決し、別revisionへ勝手に差し替えず固定の根拠を見直します。
PHHの `build.sh`・`generate.sh`・FOSSの `update.sh` は、この経路では実行しません。
必要な製品と登録は専用適用ツールが追加します。

## 2：変更前に全projectを40桁commitで記録

記録先はAndroidソースの外に作成します。検査だけなら `--output` を省略できます。

```sh
mkdir /path/to/ctz-records
python3 /path/to/ctz-rom/scripts/lock-source.py /path/to/android-ctz10 \
  --output /path/to/ctz-records/source-locked.xml
```

753箇所のGit checkout、remote URL、HEADとタグ/固定commit、作業差分を照合します。
未追跡・無視対象のファイルも検出し、余分なAndroid.mk/Android.bp等を黙って受け入れません。
全確認後に、各projectの実commitを指定した新規manifestを保存します。既存出力は上書きしません。
これはローカルcheckoutの記録であり、タグの署名・全ファイルの真正性・ビルドの再現性を保証しません。
manifestで宣言していないルート直下のファイル等は、Git project検査の対象外です。
`.repo/local_manifests` を追加したり、他の作業とソースを共有したりしないでください。

## 3：日本語差分を適用

```sh
python3 /path/to/ctz-rom/scripts/prepare-gsi-source.py /path/to/android-ctz10
python3 /path/to/ctz-rom/scripts/prepare-gsi-source.py /path/to/android-ctz10 --apply
```

[日本語製品設定の説明](source-product.ja.md)にある通り、元ファイルを保存し、
日本語初期言語・英語選択肢、ADB認証、USB初期構成の差分を適用します。
以後のビルド検査で認めるGit差分は、このツールが確認した製品設定・登録・base変更・バックアップだけです。
全ソースのロックは変更前に取り、適用後に取り直しません。

## 4：検査と明示的なビルド

```sh
# 検査のみ。ビルド出力や記録ディレクトリは作らない。
python3 /path/to/ctz-rom/scripts/build-ctz.py /path/to/android-ctz10 \
  --locked-manifest /path/to/ctz-records/source-locked.xml \
  --record-dir /path/to/ctz-records/run-01 --jobs 4

# 検査を通った場合にだけ、明示的にビルドする。
python3 /path/to/ctz-rom/scripts/build-ctz.py /path/to/android-ctz10 \
  --locked-manifest /path/to/ctz-records/source-locked.xml \
  --record-dir /path/to/ctz-records/run-01 --jobs 4 --run
```

`--record-dir` は新規の場所を指定します。ソースの内側には配置できません。
全commit、ソース差分、ホストの基本条件を確認してから、専用 `OUT_DIR` で
`lunch suiram_ctz10-userdebug` と `m systemimage` を実行します。ネット同期・clean・flashは実行しません。
上流コードを実行するため、固定ソースの内容を確認した専用環境で使ってください。
実行中にソースやロックを編集しないでください。検査は実行時の連続監視ではありません。

記録ディレクトリには、全commitのmanifest、製品設定とsource-profile、ビルドログ、
ホスト/ツール情報と成否のJSONを保存します。失敗は成功として扱いません。
成功時も新規出力のsystem.imgが存在することと形式/容量だけを検査し、SHA256を記録します。
古いイメージを再利用しません。途中で失敗した記録は残し、次回は別の新規ディレクトリを使います。

`systemimage-produced-unverified-on-device` はファイル生成のみの状態です。
stock保存・復旧・実測パーティション容量・AVB・実機起動・HAL検証が完了するまでは
`bootTested` と `flashReady` は常にfalseです。2GiBのgenericサイズをCTZの容量とみなしません。
Google Play認証、GMS、日本語入力、全ハードウェア動作も未確認です。

## テストの範囲

オフラインテストは、小さなローカルGitリポジトリで固定・不一致・差分拒否を確認します。
ビルド実行テストは偽のenvsetup/mコマンドを使い、失敗記録や古い出力の拒否を確認します。
**これらは本物のAndroidコンパイルではありません。** 通常の検査CIとは別に、`Compile Android 10 systemimage` が本物のAndroidコンパイルを実行しています。
