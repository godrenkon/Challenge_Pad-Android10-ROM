# Windowsでの準備ツール

**まだROMをインストールする手順ではありません。** これらのツールは取得・検査専用です。
解除、初期化、flash、root取得、FRP書き換え、端末設定変更を行いません。

## まずGitHubのZIPを全部展開

[ソースZIP](https://github.com/godrenkon/Challenge_Pad-Android10-ROM/archive/refs/heads/main.zip)を
取得し、ZIPの中から直接実行せず、フォルダー全体を展開してください。
`scripts` と `config` の位置関係を保ちます。管理者として実行する必要はありません。

Windows PowerShell 5.1 / PowerShell 7対応。以前の文字化けによる構文エラーを避けるため、
PS1本体はASCIIのみ、日本語はUTF-8のJSONから明示的に読み込みます。
CMDは最後に一時停止するので、エラーが一瞬で消えることも避けます。
ExecutionPolicyのBypassは起動したプロセスだけに適用し、永続設定は変更しません。

## USBなしでできる作業：上流GSIの取得

`download-base.cmd` をダブルクリックすると、PHH v222のarm64-ab vanillaを取得します。
PCの `downloads` にXZと取得記録ができます。**microSDへ自動コピーはしません。**
ファイルが既にあれば上書きせず再検査します。失敗時の `.partial` は原因確認用に残します。

取得元だけ確認する場合：

```powershell
powershell -NoProfile -File .\scripts\fetch-android10-gsi.ps1 -PlanOnly
```

GApps版を明示的に選ぶ場合（最初の切り分けはvanilla推奨）：

```powershell
powershell -NoProfile -File .\scripts\fetch-android10-gsi.ps1 -Variant gapps
```

上流のURL・名前・サイズを固定しています。公開されている信頼できるSHA256は未登録なので、
サイズ照合とXZヘッダー確認だけで真正性を保証しません。生成したSHA256は取得内容の記録です。
まだ起動確認していない既存GSIであり、Suiram製の完成ROMではありません。
取得ツールの自動テストは通信を行わないため、実ファイルの取得・展開は別途検証が必要です。

XZは[7-Zip](https://www.7-zip.org/)等で別途展開します。約517MBは圧縮サイズであり、
展開した `.img` が1GBのmicroSDに収まる保証はありません。展開先はPCを使ってください。

## 端末接続後：読み取り専用検査

[Google公式Platform-Tools](https://developer.android.com/tools/releases/platform-tools)を用意し、
USBデバッグの許可ができる状態で対象端末を接続します。`adb.exe` がPATH上にあれば
`inspect-device.cmd` を実行できます。PATH上にない場合：

```powershell
powershell -NoProfile -File .\scripts\inspect-ctz.ps1 -AdbPath 'C:\platform-tools\adb.exe'
```

ADBに端末を複数接続した場合、`-Serial` で1台を選びます。許可されていない接続では停止します。
ADBデバッグを許可できない場合は、ツール側で勝手に回避せず接続方法を再検討します。

レポートは `artifacts/ctz-report-*.json` に保存します。
対象の公開stockと一致するか、必要情報が欠けていないかを確認します。
端末シリアル・MAC等は出力せず、照合に必要な一部のプロパティだけ記録します。
`stockProfileMatched: true` でも `flashReady` は常にfalseです。
改変済みOSや別ビルドが不一致でも故障とは限りません。別途調査するための結果です。

保存済みgetpropをネットワーク・端末接続なしで検査することもできます：

```powershell
powershell -NoProfile -File .\scripts\inspect-ctz.ps1 -PropertiesFile '.\my-getprop.txt'
```

終了コードは、0＝検査完了・stock条件一致、3＝不一致/不足、1＝実行エラー。
**0は起動保証や書き込み許可を意味しません。** 既存レポートは上書きしません。

## 展開後のsystemイメージ検査（Python 3があるPC）

```powershell
python .\scripts\inspect-system-image.py '.\downloads\system-quack-arm64-ab-vanilla.img'
```

raw ext4とAndroid sparseに対応し、書き込みに必要なバイト数を表示します。
XZ未展開、HTMLエラーページ、不正ヘッダー、切れたsparse等は拒否します。
systemパーティションの**実測容量**が分かってから `--partition-bytes` にその数値を指定すると、
容量不足時に終了コード3を返します。推測した容量を指定しないでください。
形式・容量だけの検査で、全ファイルの整合性、sparse CRC、OSバージョン、AVB、起動は検証しません。

## この先に必要なもの

読み取り検査に続いて、対象stockのboot/vendor/systemと復旧経路、systemパーティション容量、
AVB条件、パネル種別を確認します。バックアップ・復旧確認ができるまで書き込み手順は提供しません。
microSDへ入れるだけでOSを置換できるインストーラーは、現時点で実装・検証できていません。
