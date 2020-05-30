#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#--------------------------------------------------
# EPUB3になろう
#   NarouToEpub3.py
# 2020/05/30 Jaken
#
# TODO: ページ内の行別処理
#       ⇒ ルビの処理
#       ⇒ リンクの処理
#       ⇒ 埋め込み画像の処理（ダウンロード処理が必要）
#
# TODO: 章の階層構造化。ebooklibでの実現方法が分からない。
# TODO: 複数ncode連続実行対応
#--------------------------------------------------
import os
import sys
import re
import time
import datetime

from argparse import ArgumentParser
import requests
import urllib.parse

import lxml.html
import lxml.etree
from lxml.builder import E

from ebooklib import epub

def USER_AGENT():
  return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6)" \
        "AppleWebKit/537.36 (KHTML, like Gecko)" \
        "Chrome/60.0.3112.113"

def CLASS(*args): # class is a reserved word in Python
  return {"class":' '.join(args)}

class ChapterItem():
  D_ITEM_TYPE_CHAPTER = 'Chapter'
  D_ITEM_TYPE_SUBTITLE = 'Subtitle'

  def __init__(self):
    self.__item_type = None

    self.__chapter_title = ""
    self.__subtitle_text = ""
    self.__subtitle_href = ""
    self.scrapingChapterItem = None

  def __str__(self):
    return r"{0} {1}{2} : {3}".format(self.__item_type, self.chapter_title, self.subtitle_text, self.subtitle_url).strip()

  @property
  def chapter_title(self):
    return self.__chapter_title

  @property
  def subtitle_text(self):
    return self.__subtitle_text

  @property
  def subtitle_href(self):
    return self.__subtitle_href

  @property
  def subtitle_url(self):
    url = ""
    if self.isSubtitle():
      url = urllib.parse.urljoin(r"https://ncode.syosetu.com/", self.__subtitle_href)
    return url

  @property
  def subtitle_index(self):
    index = ""
    if self.isSubtitle():
      # /n4750dy/6/
      match = re.search(r"[/]n[0-9]{4,}[a-z]{1,}[/](\d+)[/]", self.__subtitle_href)
      if match:
        index = str(match.group(1))
    return index

  def setChapter(self, chapter_title):
    self.__item_type = ChapterItem.D_ITEM_TYPE_CHAPTER
    self.__chapter_title = chapter_title
    return self

  def setSubtitle(self, subtitle_text, subtitle_href):
    self.__item_type = ChapterItem.D_ITEM_TYPE_SUBTITLE
    self.__subtitle_text = subtitle_text
    self.__subtitle_href = subtitle_href
    return self

  def isChapter(self):
    return self.__item_type == ChapterItem.D_ITEM_TYPE_CHAPTER

  def isSubtitle(self):
    return self.__item_type == ChapterItem.D_ITEM_TYPE_SUBTITLE

class ScrapingNcode():
  def __init__(self, ncode):
    self.__ncode = ncode
    self.url = r"https://ncode.syosetu.com/{0}/".format(self.__ncode)
    print(self.url)

    response = requests.get(self.url, headers={"User-Agent": USER_AGENT()})
    self.__root = lxml.html.fromstring(response.content)

    self.novel_title = str(self.__root.xpath(r"//p[@class='novel_title']")[0].text)
    print(self.novel_title)

    self.novel_writername = ""
    find_novel_writername_a = self.__root.xpath(r"//*[@class='novel_writername']/a")
    if len(find_novel_writername_a) >= 1:
      self.novel_writername = str(self.__root.xpath(r"//*[@class='novel_writername']/a")[0].text)
    else:
      self.novel_writername = str(self.__root.xpath(r"//*[@class='novel_writername']")[0].text_content()).replace("作者：","")
    print(self.novel_writername)

    self.novel_ex = self.__root.xpath(r"//div[@id='novel_ex']")[0].text_content()
    print("-----")
    print(self.novel_ex)
    print("-----")

    self.novel_chapters = []
    for child in self.__root.xpath(r"//div[@class='index_box']/child::*"):
      item = ChapterItem()
      if 'chapter_title' in child.attrib.values():
        chapter_title = str(child.text)
        #print(chapter_title)
        item.setChapter(chapter_title)
      else:
        subtitle = child.xpath(r"dd[@class='subtitle']/a")[0]
        subtitle_text = str(subtitle.text)
        subtitle_href = str(subtitle.attrib['href'])
        #print(subtitle_href + " " + subtitle_text)
        item.setSubtitle(subtitle_text, subtitle_href)

      self.novel_chapters.append(item)

    for item in self.novel_chapters:
      print(item)
      if item.isSubtitle():
        item.scrapingChapterItem = ScrapingChapterItem(item)
      # 連続アクセスの自制
      time.sleep(0.6)

class ScrapingChapterItem():
  def __init__(self, chapterItem):
    self.__item = chapterItem
    self.url = self.__item.subtitle_url

    response = requests.get(self.url, headers={"User-Agent": USER_AGENT()})
    self.__root = lxml.html.fromstring(response.content)

    # 前書き
    self.novel_p = None
    find_novel_p = self.__root.xpath(r"//div[@id='novel_p']")
    if len(find_novel_p) >= 1:
      self.novel_p = find_novel_p[0].text_content()

    # 後書き
    self.novel_a = None
    find_novel_a = self.__root.xpath(r"//div[@id='novel_a']")
    if len(find_novel_a) >= 1:
      self.novel_a = find_novel_a[0].text_content()

    # 本文
    self.novel_h = None
    find_novel_h = self.__root.xpath(r"//div[@id='novel_honbun']")
    if len(find_novel_h) >= 1:
      self.novel_h = find_novel_h[0].text_content()

    self.novel_honbun = self.__root.xpath(r"//div[@id='novel_honbun']/child::p[contains(@id, 'L')]")

class TextFileManager():
  def __init__(self, fileName, defaultEncoding="utf-8", defaultErrors="strict"):
    self.__fileName = fileName
    self.__defaultEncoding = defaultEncoding
    self.__defaultErrors = defaultErrors

  def __createPathFolder(self):
    dirPath = os.path.dirname(self.__fileName)
    os.makedirs(dirPath, exist_ok=True)
    return self

  def save(self, value, force=False, encoding="", errors=""):
    self.__createPathFolder()
    if force and os.path.isfile(self.__fileName):
      os.remove(self.__fileName)
      print("上書き作成: " + self.__fileName)

    if encoding == "":
      encoding = self.__defaultEncoding

    if errors == "":
      errors = self.__defaultErrors

    with open(self.__fileName, "w", encoding=encoding, errors=errors) as file:
      file.write(value)

  def load(self, encoding="", errors=""):
    result = ""
    if encoding == "":
      encoding = self.__defaultEncoding

    if errors == "":
      errors = self.__defaultErrors

    with open(self.__fileName, "r", encoding=encoding, errors=errors) as file:
      result = file.read()
    return result

class PageObject():
  def __init__(self, uid=None, file_name='', media_type='', content=None, title='', lang=None, direction=None, media_overlay=None, media_duration=None):
    # epub.EpubHtml() param
    self.uid = uid
    self.file_name = file_name
    self.media_type = media_type
    self.content = content
    self.title = title
    self.lang = lang
    self.direction = direction
    self.media_overlay = media_overlay
    self.media_duration = media_duration

    self.document_root = E.html(E.head(), E.body())

    self.__document_body = self.document_root.xpath(r"//body")[0]

  def appendBody(self, element):
    self.__document_body.append(element)

class BookManager():
  def __init__(self, identifier, title, contributor):
    self.__identifier = identifier
    self.__title = title
    self.__contributor = contributor

    self.book = epub.EpubBook()
    self.book.FOLDER_NAME = r"OEBPS"

    self.book.set_identifier(self.__identifier)
    self.book.set_title(self.__title)
    self.book.set_language('ja')
    self.book.set_direction('rtl')

    self.book.add_metadata('DC', 'contributor', self.__contributor)
    self.book.add_metadata('DC', 'rights', "All rights reserved by the contributor")
    self.book.add_author(self.__contributor)

    self.tocs = []

    currentPath = os.path.dirname(os.path.abspath(__file__))
    css_path = os.path.abspath(os.path.join(currentPath, r"assets/stylesheet.css"))
    style = TextFileManager(css_path).load()

    self.default_css = epub.EpubItem(uid="style", file_name="stylesheet.css", media_type="text/css", content=style)
    self.book.add_item(self.default_css)

    # nav (auto generate)
    self.tocs.append('nav')

  def commitPage(self, pageObject):
    c = epub.EpubHtml(pageObject.uid, pageObject.file_name, pageObject.media_type, pageObject.content, pageObject.title, pageObject.lang, pageObject.direction, pageObject.media_overlay, pageObject.media_duration)
    c.content=lxml.etree.tostring(pageObject.document_root, pretty_print=True)
    c.set_language(pageObject.lang)

    c.add_item(self.default_css)
    self.book.add_item(c)
    self.tocs.append(c)

  def commitBook(self, outputEpubFileName):
    self.outputEpubFileName = outputEpubFileName
    self.book.toc = tuple(self.tocs)

    self.book.add_item(epub.EpubNcx())

    nav = epub.EpubNav()
    nav.add_item(self.default_css)
    self.book.add_item(nav)

    self.book.spine = self.tocs

    epub.write_epub(self.outputEpubFileName, self.book, {})

class NarouToEpub3():
  def __init__(self, debug=False):
    parser = ArgumentParser(description=r"EPUB3になろう")
    parser.add_argument("-n", "--ncode", type=str, help="N-code", required=True)

    if debug:
      #self.ncode = "n2267be"
      #self.ncode = "n4750dy"
      self.ncode = "n4966ek"
    else:
      self.args = parser.parse_args()
      self.ncode = self.args.ncode.lower()
      if not re.match(r"n[0-9]{4,}[a-z]{1,}", self.ncode):
        raise Exception(r"The ncode entered is invalid.")

    self.__createDate = datetime.datetime.now()

    # なろうスクレイピング
    self.__scrapingNcode = ScrapingNcode(self.ncode)

    # 基本情報取得
    identifier = "com.tojc.epub3." + self.ncode
    title = self.__scrapingNcode.novel_title
    contributor = self.__scrapingNcode.novel_writername

    print(identifier)
    print(title)
    print(contributor)

    #出力ファイル名
    currentPath = os.path.dirname(os.path.abspath(__file__))
    filename = title + "_" + self.ncode.upper() + "_" + datetime.datetime.now().strftime(r'%Y%m%d')
    self.__outputEpubFileName = os.path.join(currentPath, 'output', filename + ".epub")
    print(self.__outputEpubFileName)

    # Book作成開始
    self.__manager = BookManager(identifier, title, contributor)

    # タイトルページ
    self.createTitlePage(self.ncode, title, contributor, self.__createDate)
    # あらすじ
    self.createArasujiPage(self.__scrapingNcode.novel_ex)

    # チャプター
    for item in self.__scrapingNcode.novel_chapters:
      print(item)
      if item.isSubtitle():
        # 前書き
        if item.scrapingChapterItem.novel_p:
          self.createChapterPageWithText(item.subtitle_index, "p", item.subtitle_text + r"【前書き】", item.scrapingChapterItem.novel_p)

        # 本文
        #self.createChapterPageWithElements(item.subtitle_index, "h", item.subtitle_text, item.scrapingChapterItem.novel_honbun)
        if item.scrapingChapterItem.novel_h:
          self.createChapterPageWithText(item.subtitle_index, "h", item.subtitle_text, item.scrapingChapterItem.novel_h)

        # 後書き
        if item.scrapingChapterItem.novel_a:
          self.createChapterPageWithText(item.subtitle_index, "a", item.subtitle_text + r"【後書き】", item.scrapingChapterItem.novel_a)

    self.__manager.commitBook(self.__outputEpubFileName)

  def createChapterPageWithText(self, index, identifier, title, text):
    uid = r"chapter_{0}_{1}".format(identifier, index)
    page = PageObject(uid=uid, file_name=uid + '.xhtml', title=title, lang='ja')
    page.appendBody(E.h2(title))

    content = self.editContentText(text)
    elemContent = self.convertContentTextToElement(content)
    page.appendBody(elemContent)
    self.__manager.commitPage(page)

  def createChapterPageWithElements(self, index, identifier, title, elements):
    uid = r"chapter_{0}_{1}".format(identifier, index)
    page = PageObject(uid=uid, file_name=uid + '.xhtml', title=title, lang='ja')
    page.appendBody(E.h2(title))

    # TODO: elements
    page.appendBody(E.p("TEST TEST"))

    self.__manager.commitPage(page)

  def createTitlePage(self, ncode, title, contributor, createDate):
    page = PageObject(uid="title_page", file_name='title_page.xhtml', title="タイトルページ", lang='ja')
    page.appendBody(E.h1(title))
    page.appendBody(E.h4(r"Ncode:" + ncode.upper()))
    page.appendBody(E.h3(r"作者：" + contributor))
    page.appendBody(E.h3(r"電子書籍 作成：EPUB3になろう(NarouToEpub3)"))

    page.appendBody(
      E.h4(
        r"制作 ",
        E.span(CLASS("tny2"), createDate.strftime(r'%y')), r"年",
        E.span(CLASS("tny2"), createDate.strftime(r'%m')), r"月",
        E.span(CLASS("tny2"), createDate.strftime(r'%d')), r"日",
      )
    )
    page.appendBody(E.hr(CLASS("pagebreak")))
    page.appendBody(
      E.p(
        r"この電子書籍ファイルは「小説家になろう」で掲載中の小説を「EPUB3になろう(NarouToEpub3)」によって、機械的に電子書籍化されたものです。", E.br(),
        r"「EPUB3になろう(NarouToEpub3)」で作成したこの電子書籍ファイルは、個人で楽しむために使用し、他人に配布しない事に同意したものとみなします。", E.br(),
        r"「EPUB3になろう(NarouToEpub3)」は、「なろうを電子書籍化（narou.nyanpass.jp）」のEPUB出力結果を参考にしているため、比較的互換性があります。ただし、完全互換を目的としたものではありません。", E.br(),
        r"著作権に関しましては、作者にあります。", E.br(),
        r"「小説家になろう」は株式会社ヒナプロジェクトの登録商標です。", E.br(),
        r"「EPUB3になろう(NarouToEpub3)」は株式会社ヒナプロジェクト、KADOKAWA / 株式会社はてなが提供するものではありません。", E.br(),
        r"", E.br(),
      )
    )
    self.__manager.commitPage(page)

  def createArasujiPage(self, text):
    page = PageObject(uid="arasuji", file_name='arasuji.xhtml', title="あらすじ", lang='ja')
    page.appendBody(E.h2(r"あらすじ"))

    content = self.editContentText(text)
    elemContent = self.convertContentTextToElement(content)
    page.appendBody(elemContent)

    self.__manager.commitPage(page)

  def editContentText(self, text):
    content = self.html_escape(text)
    # 改行置換
    content = re.sub(r"(\r\n|\r|\n)", r"<br />", content)
    # URLリンク
    content = re.sub(r"((https?|ftp)(:\/\/[-_.!~*\'()a-zA-Z0-9;\/?:\@&=+\$,%#]+))", r'<a href="\1">\1</a>', content)
    return content

  def convertContentTextToElement(self, content):
    content = r'<p>' + content + r'</p>'
    element = lxml.etree.fromstring(content)
    return element

  # html.escape
  def html_escape(self, s, quote=True):
    """
    Replace special characters "&", "<" and ">" to HTML-safe sequences.
    If the optional flag quote is true (the default), the quotation mark
    characters, both double quote (") and single quote (') characters are also
    translated.
    """
    s = s.replace("&", "&amp;") # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if quote:
        s = s.replace('"', "&quot;")
        s = s.replace('\'', "&#x27;")
    return s

if __name__ == '__main__':
    currentPath = os.path.dirname(os.path.abspath(__file__))
    os.chdir(currentPath)
    print(os.getcwd())

    NarouToEpub3(False)
