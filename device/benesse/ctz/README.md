# CTZ device treeの現状

将来の端末専用ビルド用メモ/雛形です。完成device treeではありません。
BoardConfig.mkは明示的にビルドを停止し、未確認のboot geometryやfstabを使いません。
停止行だけの削除で完成ROMは生成できません。

最初の実機移植はstock boot/kernel/vendor + Android 10 GSIで進めます。
詳細は[実装方針](../../../docs/architecture.ja.md)と[ビルドの現状](../../../docs/build.md)へ。
