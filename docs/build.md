# ベース取得と将来のソースビルド

現在の主経路は[実装方針](architecture.ja.md)にあるAndroid 10 GSI適合検証です。
[準備ツール](preparation.ja.md)で既存の上流ベースを取得します。
この取得はビルドではなく、CTZ専用の完成イメージも生成しません。

## ソースツリーの現状

`gsi/` に日本語初期言語・英語追加のPHH派生製品設定を実装しました。
`scripts/prepare-gsi-source.py` は固定した上流10ファイルを照合し、明示的な `--apply` でのみ
専用ソースツリーへ適用します。[内容・使い方・検証の限界](source-product.ja.md)を確認してください。
全ソース同期・コンパイル・system.img生成はまだ完了していません。
[統合manifestとソース固定/ビルド手順](source-build.ja.md)を追加しました。
AOSPタグと27個の固定commitを統合した762プロジェクトが対象です。
約32GiBのローカル環境ではフルビルドせず、[クラウド工程](cloud-rom-build.ja.md)を実行しています。
初回は失敗し、再試行中です。全同期完了とsystem.img生成の成功はまだ確認できていません。
[工程ランナー](build-workflow.ja.md)で準備からビルドまでをまとめ、失敗後の再開も記録付きで行えます。

`device/benesse/ctz` は将来用の雛形です。stock bootヘッダー、kernel integration、
vendor/HAL、partition geometryが足りないため、BoardConfig.mkは明示的にビルドを停止します。
停止行だけを削除しても起動可能にはなりません。
仮のfstab、推測したkernel offsetやboot page sizeはイメージへ入れません。

以前のlocal manifestはプロジェクト全体を `device/benesse/ctz` に配置し、
device treeが二重階層になる不正な構成でした。現在はツール・資料用として
`vendor/suiram/ctz-rom` へ配置するだけです。自動的にlunch targetを登録しません。
現段階で `lunch lineage_ctz-userdebug` / `mka bacon` を完成手順として案内しません。

## 将来の再現可能ビルドに必要なもの

- 実機で起動したベース、対応する上流ソース/manifest/patchsetと固定revision
- そのstock vendorへのVNDK 28適合検証
- 実機ログに基づくCTZ差分と、実装済み日本語product設定の本物のAndroidビルド/実機検証
- 実測system容量、AVB条件、確実な純正復旧
- matching kernelを使う場合は、そのソース、defconfig、boot geometry

端末専用ビルドへ進む場合は、kernel/vendor/device treeを分割してAndroid buildへ正しく登録する。
GSI適合方式では、初期段階でvendorを再生成しない。

## 開発ツールのテスト

```powershell
powershell -NoProfile -File .\tests\test-tools.ps1
```

```sh
python3 -m unittest discover -s tests -v
```

GitHub ActionsでもWindows PowerShell 5.1とLinux PowerShell 7、Pythonテストを実行します。
通信・端末接続を必要としないテストであり、ROMの実機起動テストではありません。
