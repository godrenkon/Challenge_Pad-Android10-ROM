# ベース取得と将来のソースビルド

現在の主経路は[実装方針](architecture.ja.md)にあるAndroid 10 GSI適合検証です。
[準備ツール](preparation.ja.md)で既存の上流ベースを取得します。
この取得はビルドではなく、CTZ専用の完成イメージも生成しません。

## ソースツリーの現状

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
- 実機ログに基づくCTZ差分と、日本語標準のproduct設定
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
