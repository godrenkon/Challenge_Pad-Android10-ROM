# Challenge Pad NEXT Android 10 ROM

[English](README.en.md)

チャレンジパッドNEXT（**TAB-A05-BA1 / CTZ**）を通常のAndroid 10タブレットへ移植する公開開発プロジェクトです。
日本語を標準とし、英語は追加の選択肢として扱います。

> **準備ツール実装済み・実機起動未検証。まだインストールできる完成ROMはありません。**

## 今回実装したもの

- Windows向けの読み取り専用端末検査。モデル・stockビルド・Treble・SAR・ABI・VNDK等を照合
- PHH Android 10 GSIベースの取得ツール。名前/サイズ/取得先を固定、上書き禁止、SHA256の記録
- 展開後のraw ext4 / Android sparseイメージの形式・容量検査
- 日本語標準のメッセージ、英語オプション、エラーを見られるCMD起動口
- Windows PowerShell 5.1 / Linux PowerShell 7向けのオフライン回帰テストとPythonテスト
- 未確認のboot設定・fstabの適用を除去し、未完成の端末ビルドを明示的に停止

実ファイルのダウンロード、GSI起動、ハードウェア動作はこれらのテストでは保証しません。

## 最初の実装方式

公開stockでarm64 / Treble / system-as-root / VNDK 28を確認できたため、
**純正boot/kernel/vendorを維持してAndroid 10 GSIを適合させる**経路を先に検証します。
PHH AOSP 10 v222 `arm64-ab vanilla` は既存の上流ベース候補であり、このプロジェクトが
ゼロから作ったROMでも、CTZで動作確認済みのイメージでもありません。

PHHの `ab` 名称だけで、実機のA/Bスロットを判断しないでください。
端末専用AOSP/LineageOSビルドの雛形は、必要情報が揃うまで無効化しています。

## 準備ツール

[ソースZIP](https://github.com/godrenkon/Challenge_Pad-Android10-ROM/archive/refs/heads/main.zip)をすべて展開して使います。

| 起動口 | 用途 | 端末接続 |
| --- | --- | --- |
| `download-base.cmd` | PCへ既存の上流GSIを取得するだけ | 不要 |
| `inspect-device.cmd` | 対象stockと照合した情報レポートを保存 | 許可済みADB接続が必要 |
| `scripts/inspect-system-image.py` | 展開したsystemイメージの形式と必要容量を確認 | 不要。Python 3が必要 |

**解除・初期化・書き込み・microSDへのコピーは行いません。**
以前のPowerShell文字化けを避けるため、PS1本体はASCII、日本語はUTF-8 JSONから読み込みます。
詳しい使い方は[Windows準備手順](docs/preparation.ja.md)へ。

## 対象と次の実機確認

対象はTAB-A05-BA1、純正Android 9、ビルド01.03.000。別機種・別ビルドへ流用しません。
systemパーティション実測容量、stockイメージ、復旧方法、AVB条件、パネル種別、
Android 10起動ログがまだ必要です。一致レポートや容量検査の成功は書き込み許可ではありません。

目標は画面/タッチ、Wi-Fi、Bluetooth、音声、カメラ、ストレージ、センサー、スリープ/充電の検証、
日本語標準化と再現可能なビルド。GMSは別扱いで、Google Playの動作や認証は未保証です。
純正vendorやGMSバイナリは公開ソースに含めません。

1GBのmicroSDに圧縮GSIが入っても、展開後のイメージ容量は別です。
microSDに入れるだけのOS置換方法は実装・検証できていません。
Android 10は古いOSであり、最新のセキュリティを提供するものでもありません。

[実装方針](docs/architecture.ja.md) / [根拠と未確認項目](docs/device-facts.md) /
[移植工程](docs/bring-up.md) / [ソースビルドの現状](docs/build.md) /
[パーティション調査表](docs/partition-map.md)

オリジナルソースは[Apache-2.0](LICENSE)。上流・純正・Googleの各ファイルにはそれぞれのライセンスが適用されます。
