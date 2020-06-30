# EPUB3になろう(NarouToEpub3)
このプログラムは、「小説家になろう」で掲載中の小説を機械的に電子書籍(EPUB3)に変換するプログラムです。

「EPUB3になろう(NarouToEpub3)」で作成した電子書籍ファイルは、個人で楽しむために使用し、他人に配布しないで下さい。「EPUB3になろう(NarouToEpub3)」の使用者はこれに同意したものとみなします。

「EPUB3になろう(NarouToEpub3)」は、「なろうを電子書籍化（narou.nyanpass.jp）」のEPUB出力結果を参考にしているため、比較的互換性があります。ただし、完全互換を目的としたものではありません。（作ってみたら実際かなり異なるものに）

Google Play Books(Androidアプリ)での表示確認を行っています。PC版は表示が崩れます。

## 動作環境
python3、lxml、ebooklib、requests、ArgumentParser、Pillow等。

## インストール方法
誰か書いてくれると嬉しい。
上記ライブラリをpipでインストールすれば動くはず。

## 使用方法
    > python NarouToEpub3.py -n n2267be n4830bu

## TODO
 - 章ページのローカル保存と、処理済み更新無し時の再利用処理。
 - 章の階層構造化。ebooklibでの実現方法が分からない。
