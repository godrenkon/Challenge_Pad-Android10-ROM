# 完成イメージの検査

mainへのpushで実行した「Compile Android 10 systemimage」が成功すると、
「Verify compiled Android 10 image contents」が同じrunのイメージとビルド記録を取得する。
別ブランチ・別リポジトリからの実行は対象にしない。

検査では圧縮ファイルのSHA-256、展開後のサイズとSHA-256を照合する。
展開後の照合元は`build-receipt.json`で、圧縮ファイルに同梱されたチェックサムとは別に確認する。
XZの展開量と辞書メモリーを制限し、切れたデータや追加ストリームを拒否する。
既存の検査用イメージを上書きしない。

`verify-rom-content.py`で読み取り専用のext4検査、Android 10 / SDK29、
日本語設定、認証付きADB、必要なアプリ、ARM64の実行ライブラリ、VNDK28の
32/64bit互換性ファイルを確認する。実機で計測したsystem-as-root構成も必須とする。

TAB-A05-BA1の実機Fastbootで計測したsystem領域は **1,413,480,448 bytes（1348MiB）**。
圧縮サイズではなく、sparseの場合も展開後のサイズをこの容量と比較する。
容量を超える場合は終了コード3と`content-checked-capacity-exceeded`を記録する。
これは今回の実機に対する検査値で、ほかの機種の容量を表すものではない。

検査結果は`android10-systemimage-content-verification` artifactに保存する。
内容検査に失敗した場合もJSONに理由を保存する。
成功しても`bootTested=false` / `restorationVerified=false` / `flashReady=false`のまま。
AVBの検証、復旧手段の確認、端末での起動やタッチ・音声・Wi-Fiの確認は別途必要。
この工程は端末の変更、アンロック、データ消去、flashを行わない。
