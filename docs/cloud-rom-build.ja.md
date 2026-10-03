# OS本体のクラウドビルド

`Compile Android 10 systemimage` は、762プロジェクトのソースを同期し、全commitを記録、
製品差分を適用して `lunch suiram_ctz10-userdebug` → `m -j2 systemimage` を実際に実行する工程です。
入力アプリ単体のビルドや、配布済みGSIの名前変更ではありません。

完成時の目標は、NEXTで通常のホーム画面・設定・アプリインストールが使えるAndroid 10です。
純正boot/kernel/vendorを使い、systemをPHH系AOSP Android 10へ置き換える構成です。
Google Play/GMSはこの製品に含めていません。端末での起動と全ハードウェア動作は未確認です。

## 実行環境と成果物

GitHub-hosted Ubuntu 22.04の使い捨てrunnerで、ビルドに不要なプリインストールSDK等を削除し、
ホスト依存と固定Repo launcherを用意します。ユーザーのPCには適用しません。
ソースは固定revisionの全プロジェクトを、浅い履歴・blob遅延取得で同期します。
プロジェクトの省略、固定入力の照合省略、端末への書き込みはしません。

通常のローカル工程は400GiB/150GiBの保守的ポリシーを維持します。
クラウドの試行は同期前60GiB・ビルド前20GiB・有効RAM8GiBを開始条件にします。
これは「その容量で必ず完了する」という推定ではなく、容量を測りながら進める実験です。
GitHub-hosted runnerでのみ使える入口として分離し、容量不足やコンパイル失敗は失敗として記録します。
最大355分。成功を確認する前にROM完成とは扱いません。

成功時は `android10-systemimage-engineering-untested` artifactに圧縮system.imgとSHA256が入ります。
成功・失敗とも `android10-systemimage-build-report` に工程ログ、source lock、ビルドreceiptを保存します。
どちらも30日保存です。成果物はGitのソースツリーへ入れません。

ソース取得・コンパイル・イメージ生成・CTZでの起動は別の検証段階です。
system.img生成に成功しても、実測パーティション容量、AVB条件、復旧手段、実機検証が揃うまで
完成したインストール用ROMとして配布しません。
