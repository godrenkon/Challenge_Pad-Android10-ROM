# ソース準備からビルドまでをまとめて実行

**ランナーを実装した段階で、全同期・Android本体のコンパイル・実機起動は未検証です。**
Linuxで実行するROM開発用ツールです。日本語が標準、`--language en` で英語表示にできます。
この工程にタブレット接続は不要です。

## まとめた工程

`scripts/build-workflow.py` は次の順に進み、失敗した時点で停止します。

1. 固定commitからRepo manifestを取得する。
2. 753プロジェクトのソースを同期・検査する。
3. 全commitを記録した新規manifestを保存する。
4. 日本語標準の製品設定と確認済み差分を適用する。
5. 新規出力ディレクトリでsystemimageをビルドし、成否とログを保存する。

内部では既存の[ソース固定・ビルドツール](source-build.ja.md)を使用します。
`reset --hard`、clean、force-sync、端末への書き込み、GMSのインストールは行いません。

## 準備と実行

Linux x86_64、Python 3.9以上、Git、Bash、Make、Android Repoコマンドと、
Android 10向けビルド依存を準備します。ホスト依存を自動で導入する機能はありません。
新規作業場所は、既存の親ディレクトリの下にある**まだ存在しない名前**を指定します。
ソースZIPを展開したプロジェクトの内側・親ディレクトリには配置できません。

新規作業の事前検査は空き400GiB、実効メモリ8GiB以上をプロジェクトの目安として要求します。
再開時とビルド直前は出力先の空き150GiB以上を検査します。
これらは公式最小要件やビルド成功の保証ではなく、ソース容量・並列数・ホスト依存によって変わります。
この開発環境はディスク全体が約32GiBのため、本物の全同期・ビルドに進めていません。

```sh
# デフォルトは工程表示と基本条件の検査のみ。何も取得・変更しない。
python3 /path/to/ctz-rom/scripts/build-workflow.py /mnt/builds/ctz10-work

# 条件を満たす環境で、明示的に準備からビルドまで進める。
python3 /path/to/ctz-rom/scripts/build-workflow.py /mnt/builds/ctz10-work --run --jobs 4
```

既定のmanifest取得commitは
[`38974bf7945751ad9eb38e29420c329c07f56a89`](https://github.com/godrenkon/Challenge_Pad-Android10-ROM/tree/38974bf7945751ad9eb38e29420c329c07f56a89)
です。手元の統合manifestと取得内容が一致すること、実際に使用するmanifestと全project選択も検査します。
別のmanifest版を指定する場合は `--project-revision` に40桁commitを渡します。`main` は指定できません。
手元の実行ツールと設定は別にSHA256を記録するので、取得commitと実行ツールを混同しません。

## 失敗・中断後の再開

元のRepo/ビルドプロセスが終了していることを確認してから、同じ作業場所で明示的に再開します。

```sh
python3 /path/to/ctz-rom/scripts/build-workflow.py /mnt/builds/ctz10-work --resume --run --jobs 2
```

完了した工程を再検査してから、失敗した工程以降を実行します。
同期の再開前には、取得済みソースの編集やGitの変更隠蔽フラグを検出します。
差分適用後に同期へ戻ることはなく、既存の取得済みソースを削除してやり直しません。
失敗したビルド出力は保存し、新しい番号の出力先で次のビルドを行います。
同じ作業場所の同時実行はOSのファイルロックで拒否します。

作業場所、manifest commit、ツール、製品設定が記録と異なる場合や、未知の既存ディレクトリには
自動で再開・上書きしません。状態JSONの編集やファイル削除で検査を回避せず、
記録したツール版を使うか、[個別の手順](source-build.ja.md)で状況を確認してください。
ファイル全体の一括ロールバックや、強制終了時に残る子プロセスの自動回収はありません。

## 保存するもの

| 場所 | 内容 |
| --- | --- |
| `workflow-state.json` | 入力SHA256、完了工程、各試行の成否・時刻 |
| `records/logs/` | 取得・同期など各試行のログ。過去ログを上書きしない |
| `records/source-locked.xml` | 変更前の全projectのcommit記録 |
| `records/build-attempt-番号/` | 新規ビルド出力、ログ、製品設定、manifest、成否JSON |

JSONの工程記録は一時ファイルから置き換えて保存します。
I/O障害や電源断で途中の記録が残った場合は、内容を確認してから再開します。
基本条件の検査だけではソースやビルドの成功を証明しません。
完了表示もsystemimage生成までを示すもので、実機の全機能やGoogle Play動作は未確認です。
`flashReady` と `bootTested` は常にfalseです。

オフラインテストは小さなGit fixtureや代替工程・ビルドコマンドを使っています。
実際のソース全同期やAndroidコンパイルを再現したテストではありません。
