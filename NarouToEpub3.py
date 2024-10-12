# -*- coding: utf-8 -*-
#--------------------------------------------------
# EPUB3になろう
#   NarouToEpub3.py
# 2020/05/30 Jaken
#
# TODO: 章の階層構造化。ebooklibでの実現方法が分からない。
#--------------------------------------------------
import os
import sys
import re
import time
import datetime
import random

from argparse import ArgumentParser
import requests
import urllib.parse

import lxml.html
import lxml.etree
from lxml.builder import E

import ebooklib
from ebooklib import epub
from ebooklib.utils import create_pagebreak
from collections import OrderedDict

from ebooklib.utils import debug

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap

# https://qiita.com/YuukiMiyoshi/items/6ce77bf402a29a99f1bf
ZEN = re.sub(r"[ａ-ｚＡ-Ｚ０-９]", r'', "".join(chr(0xff01 + i) for i in range(94)))
HAN = re.sub(r"[a-zA-Z0-9]", r'', "".join(chr(0x21 + i) for i in range(94)))
ZEN2HAN = str.maketrans(ZEN, HAN)
HAN2ZEN = str.maketrans(HAN, ZEN)

def USER_AGENT():
  return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " \
        "AppleWebKit/537.36 (KHTML, like Gecko) " \
        "Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0"

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


class NovelChapters():
  def __init__(self):
    self.__novel_chapters = []

  def append(self, item):
    self.__novel_chapters.append(item)

  @property
  def items(self):
    return self.__novel_chapters


class ScrapingNcode():
  def __init__(self, ncode):
    self.__ncode = ncode
    self.__page = 1
    self.__next = True

    self.url = r"https://ncode.syosetu.com/{0}/?p={1}".format(self.__ncode, self.__page)
    print(self.url)

    response = requests.get(self.url, headers={"User-Agent": USER_AGENT()})
    self.__root = lxml.html.fromstring(response.content)

    self.series_title = ""
    find_series_title_a = self.__root.xpath(r"//*[@class='p-novel__series']/a")
    if len(find_series_title_a) >= 1:
      self.series_title = str(self.__root.xpath(r"//*[@class='p-novel__series']/a")[0].text)
    print(self.series_title)

    self.novel_title = str(self.__root.xpath(r"//h1[@class='p-novel__title']")[0].text)
    print(self.novel_title)

    self.novel_writername = ""
    find_novel_writername_a = self.__root.xpath(r"//*[@class='p-novel__author']/a")
    if len(find_novel_writername_a) >= 1:
      self.novel_writername = str(self.__root.xpath(r"//*[@class='p-novel__author']/a")[0].text)
    else:
      self.novel_writername = str(self.__root.xpath(r"//*[@class='p-novel__author']")[0].text_content()).replace("作者：","")
    print(self.novel_writername)

    self.novel_ex = self.__root.xpath(r"//div[@id='novel_ex']")[0].text_content()
    print("-----")
    print(self.novel_ex)
    print("-----")

    self.chapters = NovelChapters()

    while self.__next:

      for child in self.__root.xpath(r"//div[@class='p-eplist']/child::*"):
        item = ChapterItem()
        if 'p-eplist__chapter-title' in child.attrib.values():
          chapter_title = str(child.text)
          # print(chapter_title)
          item.setChapter(chapter_title)
        else:
          subtitle = child.xpath(r"a[@class='p-eplist__subtitle']")[0]
          subtitle_text = str(subtitle.text)
          subtitle_href = str(subtitle.attrib['href'])
          # print(subtitle_href + " " + subtitle_text)
          item.setSubtitle(subtitle_text, subtitle_href)

        self.chapters.append(item)

      # リンク無しの「次へ」があるなら終了
      next_page = self.__root.xpath(r"//span[contains(@class, 'c-pager__item--next')]")
      if len(next_page) == 0:
        self.__page += 1

        self.url = r"https://ncode.syosetu.com/{0}/?p={1}".format(self.__ncode, self.__page)
        print(self.url)

        response = requests.get(self.url, headers={"User-Agent": USER_AGENT()})
        self.__root = lxml.html.fromstring(response.content)
        # 連続アクセスの自制
        self.sleep()

      else:
        self.__next = False

    counter = 0
    for item in self.chapters.items:
      counter += 1
      print(item)
      if item.isSubtitle():
        item.scrapingChapterItem = ScrapingChapterItem(item)
      # 連続アクセスの自制
      self.sleep()

  def sleep(self):
    time.sleep(random.randint(2, 7))

class ScrapingChapterItem():
  def __init__(self, chapterItem):
    self.__item = chapterItem
    self.url = self.__item.subtitle_url

    response = requests.get(self.url, headers={"User-Agent": USER_AGENT()})
    self.__root = lxml.html.fromstring(response.content)

    # 前書き
    self.novel_p = None
    find_novel_p = self.__root.xpath(r"//div[@class='p-novel__body']/child::div[contains(@class, 'p-novel__text--preface')]")
    if len(find_novel_p) >= 1:
      self.novel_p = find_novel_p[0].text_content()

    # 後書き
    self.novel_a = None
    find_novel_a = self.__root.xpath(r"//div[@class='p-novel__body']/child::div[contains(@class, 'p-novel__text--afterword')]")
    if len(find_novel_a) >= 1:
      self.novel_a = find_novel_a[0].text_content()

    # 本文
    # self.novel_h = None
    # find_novel_h = self.__root.xpath(r"//div[@class='p-novel__body']")
    # if len(find_novel_h) >= 1:
    #   self.novel_h = find_novel_h[0].text_content()

    self.novel_honbun = self.__root.xpath(r"//div[@class='p-novel__body']/div/child::p[contains(@id, 'L1')]/parent::div/child::p[contains(@id, 'L')]")

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

class ImageObject():
  def __init__(self, subtitle_index, number, file_name=''):
    # epub.EpubItem() param
    self.uid = r"image_" + str(subtitle_index) + r"_" + str(number).zfill(3)
    self.org_file_name = file_name
    self.file_name = self.__createResizeImage(self.org_file_name)
    self.relativePath = r"images/" + str(subtitle_index) + r"/" + os.path.basename(file_name)

  def __createResizeImage(self, srcFileName, resize_max_width=400):
    result = srcFileName

    im = Image.open(srcFileName)
    im_width, im_height = im.size

    # 指定幅より大きい場合は、リサイズが必要
    if im_width > resize_max_width:
      filepath, ext = os.path.splitext(srcFileName)
      dstFileName = filepath + "_w400" + ext

      # リサイズ
      resize_height = resize_max_width / im_width * im_height
      im = im.resize((int(resize_max_width), int(resize_height)), Image.LANCZOS)
      im.save(dstFileName)

      result = dstFileName
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

    self.__objectImagesNumber = 0
    self.objectImages = []

    self.document_root = E.html(E.head(), E.body())
    self.__document_body = self.document_root.xpath(r"//body")[0]

  def appendBody(self, element):
    self.__document_body.append(element)

  def createImageObject(self, file_name):
    imageObject = ImageObject(self.uid, self.__objectImagesNumber, file_name)
    self.__objectImagesNumber += 1
    return imageObject

  def appendImageObject(self, imageObject):
    self.objectImages.append(imageObject)

class BookManager():
  def __init__(self, identifier, title, contributor, series_title):
    self.__identifier = identifier
    self.__title = title
    self.__contributor = contributor
    self.__series_title = series_title

    self.book = epub.EpubBook()
    self.book.FOLDER_NAME = r"OEBPS"

    self.book.set_identifier(self.__identifier)
    self.book.set_title(self.__title)
    self.book.set_language('ja')
    self.book.set_direction('rtl')

    self.book.add_metadata('DC', 'contributor', self.__contributor)
    self.book.add_metadata('DC', 'rights', "All rights reserved by the contributor")
    self.book.add_author(self.__contributor)

    if len(self.__series_title) >= 1:
      self.book.add_metadata(None, 'meta', self.__series_title, OrderedDict([('property', 'belongs-to-collection'), ('id', 'series_id')]))
      self.book.add_metadata(None, 'meta', r"series", OrderedDict([('refines', '#series_id'), ('property', 'collection-type')]))

    self.tocs = []

    currentPath = os.path.dirname(os.path.abspath(__file__))

    css_path = os.path.abspath(os.path.join(currentPath, r"assets/stylesheet.css"))
    style = TextFileManager(css_path).load()
    self.default_css = epub.EpubItem(uid="style", file_name="stylesheet.css", media_type="text/css", content=style)
    self.book.add_item(self.default_css)

    cover_css_path = os.path.abspath(os.path.join(currentPath, r"assets/cover.css"))
    style_cover = TextFileManager(cover_css_path).load()
    self.cover_css = epub.EpubItem(uid="style_cover", file_name="cover.css", media_type="text/css", content=style_cover)
    self.book.add_item(self.cover_css)

  def appendCover(self, imageFileName):
    with open(imageFileName, 'rb') as f:
        self.book.set_cover(r"cover/cover.png", f.read(), create_page=True)
    self.tocs.append('cover')
    # cover.xhtml
    cover_item = self.book.get_item_with_id("cover")
    #cover_item.is_linear = True
    cover_item.add_item(self.cover_css)

  def appendNavPage(self):
    # nav (auto generate)
    self.tocs.append('nav')

  def commitPage(self, pageObject):
    c = epub.EpubHtml(pageObject.uid, pageObject.file_name, pageObject.media_type, pageObject.content, pageObject.title, pageObject.lang, pageObject.direction, pageObject.media_overlay, pageObject.media_duration)
    c.content=lxml.etree.tostring(pageObject.document_root, pretty_print=True)
    c.set_language(pageObject.lang)

    c.add_item(self.default_css)
    self.book.add_item(c)
    self.tocs.append(c)

    # 画像ファイルの差し込み
    for imageObject in pageObject.objectImages:
      image_item = epub.EpubItem(uid=imageObject.uid, file_name=imageObject.relativePath)
      with open(imageObject.file_name, 'rb') as f:
          image_item.content = f.read()
      self.book.add_item(image_item)

  def commitBook(self, outputEpubFileName):
    self.outputEpubFileName = outputEpubFileName
    self.book.toc = tuple(self.tocs)

    self.book.add_item(epub.EpubNcx())

    nav = epub.EpubNav()
    nav.add_item(self.default_css)
    self.book.add_item(nav)

    self.book.spine = self.tocs

    epub.write_epub(self.outputEpubFileName, self.book, {"package_direction" : True})

class NarouToEpub3():
  def __init__(self, ncode):
    if not re.match(r"n[0-9]{4,}[a-z]{1,}", ncode):
      raise Exception(r"The ncode entered is invalid: " + ncode)

    self.ncode = ncode
    self.__createDate = datetime.datetime.now()

    # なろうスクレイピング
    self.__scrapingNcode = ScrapingNcode(self.ncode)

    # 基本情報取得
    identifier = "com.tojc.epub3." + self.ncode
    title = self.__scrapingNcode.novel_title
    contributor = self.__scrapingNcode.novel_writername
    series_title = self.__scrapingNcode.series_title

    print(identifier)
    print(title)
    print(contributor)
    print(series_title)

    #出力ファイル名
    currentPath = os.path.dirname(os.path.abspath(__file__))
    filename = title.translate(HAN2ZEN) + "_" + self.ncode.upper() + "_" + datetime.datetime.now().strftime(r'%Y%m%d')
    self.__outputEpubFileName = os.path.join(currentPath, 'output', filename + ".epub")
    print(self.__outputEpubFileName)

    # ダウンロード ベースパス
    self.__downloadLocalBasePath = os.path.join(currentPath, 'output', 'download', self.ncode)

    # Book作成開始
    self.__manager = BookManager(identifier, title, contributor, series_title)

    # Cover
    coverImageFileName = self.createCoverImage(title, contributor, self.__createDate)
    self.__manager.appendCover(coverImageFileName)

    # タイトルページ
    self.createTitlePage(self.ncode, title, contributor, self.__createDate)
    # あらすじ
    self.createArasujiPage(self.__scrapingNcode.novel_ex)

    self.__manager.appendNavPage()

    # チャプター
    for item in self.__scrapingNcode.chapters.items:
      print(item)
      if item.isSubtitle():
        # 前書き
        if item.scrapingChapterItem.novel_p:
          self.createChapterPageWithText(item.subtitle_index, "p", item.subtitle_text + r"【前書き】", item.scrapingChapterItem.novel_p)

        # 本文
        # if item.scrapingChapterItem.novel_h:
        if item.scrapingChapterItem.novel_honbun:
          #self.createChapterPageWithText(item.subtitle_index, "h", item.subtitle_text, item.scrapingChapterItem.novel_h)
          self.createChapterPageWithElements(item.subtitle_index, "h", item.subtitle_text, item.scrapingChapterItem.novel_honbun)

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

    downloadLocalPath = os.path.join(self.__downloadLocalBasePath, str(index))
    dlm = DownloadManager(downloadLocalPath)

    for element in elements:
      #print(lxml.etree.tostring(element, pretty_print=True))
      img_list = element.xpath(r".//img")
      for img in img_list:
        imgsrc = str(img.attrib['src'])
        print(imgsrc)

        # 画像ファイルのダウンロード
        dlm.download(imgsrc)
        # 格納用オブジェクトの作成
        imageObject = page.createImageObject(dlm.localfullPathFileName)
        # imgタグのsrcをEPUB用のリンク先に入れ替え
        img.attrib['src'] = imageObject.relativePath

        page.appendImageObject(imageObject)

      # NOTE: rubyやaは無視してそのまま書き込む
      page.appendBody(element)

    self.__manager.commitPage(page)

  def createCoverImage(self, title, contributor, createDate):
    colorNarou = (24, 183, 205) #18b7cd
    colorWhite = (255, 255, 255)
    colorGray = (235, 235, 235)

    im = Image.new('RGB', (400, 600), colorNarou)
    draw = ImageDraw.Draw(im)

    fontname = r'C:\Windows\Fonts\msmincho.ttc'
    fontTitle = ImageFont.truetype(fontname, 36)
    fontContributor = ImageFont.truetype(fontname, 26)
    fontCreateDate = ImageFont.truetype(fontname, 20)

    draw.rectangle((10, 10, 390, 590), fill=colorWhite)
    draw.rectangle((20, 20, 380, 580), fill=colorGray)

    dt = DrawText(im, draw)
    box = dt.drawHorizontal((35, 70), title, (0,0,0), fontTitle, DrawText.ALIGN_LEFT, 9)

    #draw.rectangle((box[0]-10,box[1]-20,box[2]+10,box[3]+20), outline=colorNarou, width=3)
    rightbottom_y = box[3]

    y = rightbottom_y + 60
    draw.line((35, y, 365, y), fill=colorNarou, width=4)

    y += fontContributor.size
    dt.drawHorizontal((200, y), contributor, (0,0,0), fontContributor, DrawText.ALIGN_CENTER, 12)

    dateString = "EPUB更新日: " + createDate.strftime(r"%Y/%m/%d %H:%M:%S")
    dt.drawHorizontal((200, 550), dateString, (0,0,0), fontCreateDate, DrawText.ALIGN_CENTER)

    coverImageFileName = os.path.join(self.__downloadLocalBasePath, 'cover.png')
    dirPath = os.path.dirname(coverImageFileName)
    os.makedirs(dirPath, exist_ok=True)
    im.save(coverImageFileName, quality=95)

    return coverImageFileName

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

class DownloadManager():
  def __init__(self, downloadLocalPath=None):
    self.__param_url = None
    self.__completed_url = None
    self.__target_url = None

    self.__fileName = None
    #self.__fileExtension = None
    self.__downloadLocalPath = None
    self.__localfullPathFileName = None

    if downloadLocalPath == None:
        currentPath = os.path.dirname(os.path.abspath(__file__))
        self.__downloadLocalPath = os.path.join(currentPath, r"download")
    else:
        self.__downloadLocalPath = str(downloadLocalPath)

  @property
  def paramUrl(self):
    return self.__param_url

  @property
  def completedUrl(self):
    return self.__completed_url

  @property
  def targetUrl(self):
    return self.__target_url

  @property
  def fileName(self):
    return self.__fileName

  @property
  def localfullPathFileName(self):
    return self.__localfullPathFileName

  def download(self, url):
    self.__param_url = url

    if self.__param_url.startswith(('http://', 'https://')):
      self.__completed_url = self.__param_url
    elif self.__param_url.startswith('//'):
      self.__completed_url = 'https:' + self.__param_url
    else:
      raise Exception("Invalid URL: " + self.__param_url)

    print("Download   : " + self.__completed_url)
    response = requests.get(self.__completed_url, headers={"User-Agent": USER_AGENT()}, allow_redirects=True)
    if response.status_code != 200:
        raise Exception("HTTP status: " + response.status_code)
    content_type = response.headers["content-type"]
    if 'image' not in content_type:
        raise Exception("Content-Type: " + content_type)

    self.__target_url = str(response.url)
    print("           : " + self.__target_url)
    self.__fileName = os.path.basename(self.__target_url)
    #print("           : " + self.__fileName)
    #self.__fileExtension = os.path.splitext(self.__target_url)[1]
    #print("           : " + self.__fileExtension)

    self.__localfullPathFileName = os.path.join(self.__downloadLocalPath, self.__fileName)

    dirPath = os.path.dirname(self.__localfullPathFileName)
    os.makedirs(dirPath, exist_ok=True)
    with open(self.__localfullPathFileName, "wb") as fout:
        fout.write(response.content)

    print("   -> Done : " + self.__localfullPathFileName)
    return self.__localfullPathFileName

class DrawText():
  ALIGN_LEFT = "left"
  ALIGN_CENTER = "center"
  ALIGN_RIGHT = "right"

  # NOTE: 縦書きはLibraqmのインストールがめんどくさいので未実装
  def __init__(self, im, draw):
    self.im = im
    self.draw = draw
    im_width, im_height = im.size
    self.canvas_width = im_width
    self.canvas_height = im_height

  def drawHorizontal(self, xy, text, color, font, align, wrap=None):
    result_lefttop_x = self.canvas_width
    result_lefttop_y = self.canvas_height
    result_rightbottom_x = -1
    result_rightbottom_y = -1

    base_x = xy[0]
    base_y = xy[1]
    x = base_x
    y = base_y

    # wrapした後だと、size_heightが文字によって変化する為、あらかじめ全体の文字列で計算する。
    spacing = int(font.size * 0.5)
    #print(font.size)
    #print(spacing)
    height_spacing = self.draw.textsize(text, font)[1] + spacing

    if wrap:
      wrap_list = textwrap.wrap(text, wrap)
    else:
      wrap_list = [text]

    for linetext in wrap_list:
      size_width, size_height = self.draw.textsize(linetext, font)
      #print("SIZE" + str(size_width) + " " + str(size_height))

      if align == DrawText.ALIGN_LEFT:
        pass
      elif align == DrawText.ALIGN_CENTER:
        x = base_x - (size_width / 2.0)
      elif align == DrawText.ALIGN_RIGHT:
        x = base_x - size_width

      self.draw.text((x, y), linetext, fill=color, font=font)

      if x < result_lefttop_x:
        result_lefttop_x = x
      if y < result_lefttop_y:
        result_lefttop_y = y
      if (x + size_width) > result_rightbottom_x:
        result_rightbottom_x = x + size_width
      if (y + size_height) > result_rightbottom_y:
        result_rightbottom_y = y + size_height

      y += height_spacing
    return (result_lefttop_x, result_lefttop_y, result_rightbottom_x, result_rightbottom_y)

if __name__ == '__main__':
    currentPath = os.path.dirname(os.path.abspath(__file__))
    os.chdir(currentPath)
    print(os.getcwd())

    parser = ArgumentParser(description=r"EPUB3になろう")
    parser.add_argument("-n", "--ncode", type=str, help="N-code", nargs='+', required=True)

    ncodes = []
    # for debug
    #ncodes.append("n2267be")
    #ncodes.append("n4750dy")
    #ncodes.append("n4966ek")
    #ncodes.append("n4830bu")
    #ncodes.append("n7835cj")
    #ncodes.append("n7033br")

    if len(ncodes) == 0:
      args = parser.parse_args()
      ncodes = args.ncode

    for ncode in ncodes:
      NarouToEpub3(ncode.lower())
