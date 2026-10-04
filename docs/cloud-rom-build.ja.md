# OS本体のクラウドビルド

`Compile Android 10 systemimage` は、762プロジェクトのソースを同期し、全commitを記録、
製品差分を適用して `lunch suiram_ctz10-userdebug` → `m -j2 systemimage` を実行する工程です。
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
ソース同期は4並列、コンパイルは2並列です。取得・コンパイルの工程ログを実行中にも表示し、
10秒ごとに経過時間と空き容量を記録します。空き容量3GiB未満または処理時間315分で
Repo・コンパイラを含む処理グループを停止し、ログ保存用の時間と容量を残します。
GitHub側の本体step制限330分、job制限355分より前に停止する設計です。
成功を確認する前にROM完成とは扱いません。

成功時は `android10-systemimage-engineering-untested` artifactに圧縮system.imgとSHA256が入ります。
成功・通常の失敗とも `android10-systemimage-build-report` に工程ログ、存在するsource lock・ビルドreceiptを保存します。
runner自体の消失など、後続stepが実行されない場合はartifactを保存できません。
どちらも30日保存です。成果物はGitのソースツリーへ入れません。

本体ビルド成功後は、別の `Verify compiled Android 10 image contents` が自動で動きます。
同じリポジトリの成功runから成果物を取得し、圧縮SHA256、展開、読み取り専用e2fsck、
Android 10 / SDK29 / ARM64 / 製品情報、ADB認証とUSB設定、基本アプリのファイル存在を検査します。
PHHの外部リバースデバッグ用3ファイルが含まれないことも検査します。
Android 10のuserdebug後処理はUSBの `mtp` に `adb` を追加するため、`mtp,adb` も正しい出力として扱います。
アプリの存在確認は実行テストではありません。検査成功時はJSONレポートを保存します。
元のsystemイメージへ書き込み・mountはしません。

ソース取得・コンパイル・イメージ生成・CTZでの起動は別の検証段階です。
system.img生成に成功しても、実測パーティション容量、AVB条件、復旧手段、実機検証が揃うまで
完成したインストール用ROMとして配布しません。

## 実際の試行記録

[初回の本体ビルド](https://github.com/godrenkon/Challenge_Pad-Android10-ROM/actions/runs/37159364657)
は2026-10-03 22:42 UTCに開始し、2026-10-04 04:28 UTCに失敗で終了しました。
ホスト準備は成功しましたが、ソース同期・コンパイルの複合stepが進行中のまま終了しています。
ログ保存stepは未実行、artifactは0件、jobログの取得はBlobNotFoundでした。
全同期完了・コンパイル開始・system.img生成は確認できず、停止原因は未特定です。
この結果を受けて、実行中ログ表示と容量・時間の監視を追加して再試行します。

再試行中に、PHHの `system.prop` にADB認証無効の設定が残る問題を確認しました。
`base.mk` と `system.prop` の両方を修正し、上流10ファイルの実データへの適用を確認しています。
すでに開始済みのrunへ後からソース差分を注入しません。
`Queue updated ROM recipe` は本体run終了時に、そのcommitと最新mainのビルド入力blobを比較します。
入力が変わり、そのmain commitに本体ビルドの試行がまだなければ、修正版の本体ビルドを
`workflow_dispatch` で1回開始します。資料だけの更新・同じ入力・試行済みcommitでは開始しません。
キャンセルされたrunからも自動開始しません。
比較する入力は `scripts/queue-updated-rom-build.cjs` の `INPUTS` に列挙しています。
このworkflowの `actions: write` は本体workflowの開始に使い、端末操作やリリース公開は行いません。
