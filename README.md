# EPUB3になろう(NarouToEpub3)
このプログラムは、「小説家になろう」で掲載中の小説を機械的に電子書籍化(EPUB3)に変換するプログラムです。

「EPUB3になろう(NarouToEpub3)」で作成した電子書籍ファイルは、個人で楽しむために使用し、他人に配布しないで下さい。

「EPUB3になろう(NarouToEpub3)」は、「なろうを電子書籍化（narou.nyanpass.jp）」のEPUB出力結果を参考にしているため、比較的互換性があります。ただし、完全互換を目的としたものではありません。（作ってみたら実際かなり違う感じに・・・）

Google Play BooksのAndroidアプリでの表示確認を行っています。PC版は表示が崩れます。

## 動作環境
python3、lxml、ebooklib、requests、ArgumentParser等。

## インストール方法
自分のために作ったプログラムなので、各自頑張って！
誰か書いてくれると嬉しい。

## 使用方法
    > python NarouToEpub3.py -n n2267be

## TODO
 - ページ内の行別処理
 - ルビの処理
 - リンクの処理
 - 埋め込み画像の処理（ダウンロード処理が必要）

 - 章の階層構造化。ebooklibでの実現方法が分からない。
 - 複数ncode連続実行対応
