# Challenge Pad NEXT Android 10 ROM

[English README](README.en.md)

Panasonic/Benesse **チャレンジパッドNEXT（TAB-A05-BA1 / CTZ）**を、通常のAndroidタブレットとして使えるAndroid 10へ移植する、公開開発プロジェクトです。

> **状態：調査・移植準備中。まだ書き込み可能な完成ROMではありません。**

## 目標

- Android 10（AOSP / LineageOS 17.1ベース）
- 画面、タッチ、ストレージ、Wi‑Fi、音声、センサー、電源管理の動作
- **日本語を標準言語**として搭載し、英語も選択可能
- GMSはライセンスを守った別パッケージとして扱う
- 再現可能なビルドと公開ドキュメント
- 復旧手順を含む安全なリリース

## 対象機種

| 項目 | 値 |
| --- | --- |
| 機種 | Challenge Pad NEXT |
| モデル | TAB-A05-BA1 |
| 内部コード | CTZ |
| SoC | MediaTek MT8168A |
| GPU | Mali-G52 MC1 |
| 純正OS | Android 9 |
| 純正ビルド | 01.03.000 |
| CPU ABI | arm64 |
| 画面 | 1200 × 1920 |

## 現在の状態

公開検索で確認できたNext向けROMはAndroid 9ベースのPixelTouchなどで、TAB-A05-BA1用の検証済みAndroid 10イメージは確認できませんでした。このリポジトリでは、純正ファイルを勝手に再配布せず、ソースと抽出手順を分離しています。

## 重要な注意

- ソースの作成・閲覧だけならUSBケーブルは不要です。
- 純正パーティションの取得、ブートローダー解除、書き込み、実機テストにはUSBデータ接続が必要です。
- ブートローダー解除では通常データが消去されます。
- TAB-A05-BD、TAB-A03、別ビルド用のイメージをTAB-A05-BA1へ書き込まないでください。
- GMSや純正vendorバイナリはこの公開ソースに含めません。

詳細：[移植計画](docs/bring-up.md) / [ビルド手順](docs/build.md) / [パーティション調査表](docs/partition-map.md)
