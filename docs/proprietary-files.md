# 純正・Google・第三者ファイルの取り扱い

このリポジトリは公開です。Panasonic/Benesse/MediaTek/Google等のバイナリは、
明確な再配布許可とライセンス確認なしにコミットしません。
初期GSI移植ではstock vendorを維持し、生成したvendorで置換しません。

## ローカルstock抽出ツール

端末のパーティションを取得するツールではなく、PC上の展開済みstockから
`vendor/benesse/ctz/proprietary-files.txt` に列挙したファイルだけをコピーするツールです。
ADB、fastboot、root、端末への書き込みは使いません。Python 3.9以上が必要です。

```sh
bash scripts/extract-stock.sh /path/to/extracted-stock-root
```

WindowsでPythonがある場合：

```powershell
python .\scripts\extract-stock.py 'C:\stock-root'
```

対象stockはsystemのbuild.prop（SAR二重階層も対応）から、モデル・Android版・build ID・
完全なfingerprintをすべて照合します。TAB-A05-BA1 **または**01.03.000という緩い検査はしません。
sourceまたはsource:destination形式の相対パスだけを受け付け、全件の事前検査を行います。
パストラバーサル、root外へ出るsymlink、重複、既存出力の上書きを拒否します。
コピー途中のIOエラーでは出力が一部残る可能性があります。その場合も自動削除・上書きはしません。
現在のmanifestはコメントだけなので、実際のvendorファイルは抽出しません。

## 公開時の条件

- stockイメージ、個人の端末情報、抽出vendorは公開しない
- CIはバイナリなしでツールだけを検証する
- upstream GSIには上流のライセンスが適用され、取得リンクは再配布許可を意味しない
- GMSはソースに含めず別工程で検証し、Google Play認証も保証しない

将来の配布物には、再配布可能なファイルのみ含め、ソース対応・著作権表示を確認する。
