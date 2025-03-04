# Copyright (C) IBM Corporation 2008
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import shutil
import urllib.request, urllib.parse, urllib.error 
import logging
from gettext import gettext as _

from sugar3.activity.activity import get_bundle_path

import book
from infoslicer.processing.newtiful_soup import NewtifulStoneSoup \
        as BeautifulStoneSoup
from infoslicer.processing.media_wiki_Parser import MediaWiki_Parser
from infoslicer.processing.media_wiki_Helper import MediaWiki_Helper
from infoslicer.processing.media_wiki_Helper import PageNotFoundError

logger = logging.getLogger('infoslicer')
elogger = logging.getLogger('infoslicer::except')

proxies = None

def download_wiki_article(title, wiki, progress):
    try:
        progress.set_label(_('"%s" download in progress...') % title)
        try:
            article, url = MediaWiki_Helper().getArticleAsHTMLByTitle(title, wiki)

            # Debug logging
            logger.error(f'Article type: {type(article)}')
            logger.error(f'Article content type: {type(article) if isinstance(article, str) else "mixed"}')
            logger.error(f'Article length: {len(article) if hasattr(article, "__len__") else "N/A"}')
            logger.error(f'Article URL: {url}')

            # Optional: force decode if it's bytes
            if isinstance(article, bytes):
                article = article.decode('utf-8', errors='ignore')

        except Exception as e:
            progress.set_label(_('Error getArticleAsHTMLByTitle: %s') % e)
            raise

        # Rest of the function remains the same
    except Exception as e:
        # More detailed error logging
        logger.error(f'Detailed error: {e}', exc_info=True)
        raise

def image_handler(root, uid, document):
    """
        Takes a DITA article and downloads images referenced in it
        (finding all <image> tags).
        Attemps to fix incomplete paths using source url.
        @param document: DITA to work on
        @return: The document with image tags adjusted to point to local paths
    """
    document = BeautifulStoneSoup(document)
    dir_path =  os.path.join(root, uid, "images")

    logger.debug('image_handler: %s' % dir_path)

    if not os.path.exists(dir_path):
        os.makedirs(dir_path, 0o777)

    for image in document.findAll("image"):
        fail = False
        path = image['href']
        if "#DEMOLIBRARY#" in path:
            path = path.replace("#DEMOLIBRARY#",
                    os.path.join(get_bundle_path(), 'examples'))
            image_title = os.path.split(path)[1]
            shutil.copyfile(path, os.path.join(dir_path, image_title))
        else:
            image_title = path.rsplit("/", 1)[-1]
            # attempt to fix incomplete paths
            if (not path.startswith("http://")) and document.source is not None and "href" in document.source:
                if path.startswith("//upload"):
                    path = 'http:' + path
                elif path.startswith("/"):
                    path = document.source['href'].rsplit("/", 1)[0] + path
                else:
                    path = document.source['href'].rsplit("/", 1)[0] + "/" + path
            logger.debug("Retrieving image: " + path)
            file = open(os.path.join(dir_path, image_title), 'wb')
            image_contents = _open_url(path)
            if image_contents == None:
                fail = True
            else:
                file.write(image_contents)
            file.close()
        #change to relative paths:
        if not fail:
            image['href'] = os.path.join(dir_path.replace(os.path.join(root, ""), "", 1), image_title)
            image['orig_href'] = path
        else:
            image.extract()

    return document.prettify()

def _open_url(url):
    """
        retrieves content from specified url
    """
    urllib.request._urlopener = _new_url_opener()
    try:
        logger.debug("opening " + url)
        logger.debug("proxies: " + str(proxies))
        doc = urllib.request.urlopen(url)
        output = doc.read()
        doc.close()
        logger.debug("url opened succesfully")
        return output
    except IOError as e:
        elogger.debug('_open_url: %s' % e)

class _new_url_opener(urllib.request.FancyURLopener):
    version = "Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1b2)" \
              "Gecko/20081218 Gentoo Iceweasel/3.1b2"

# http proxy

_proxy_file = os.path.join(os.path.split(os.path.split(__file__)[0])[0],
        'proxy.cfg')
_proxylist = {}

if os.access(_proxy_file, os.F_OK):
    proxy_file_handle = open(_proxy_file, "r")
    for line in proxy_file_handle.readlines():
        parts = line.split(':', 1)
        #logger.debug("setting " + parts[0] + " proxy to " + parts[1])
        _proxylist[parts[0].strip()] = parts[1].strip()
    proxy_file_handle.close()

if _proxylist:
    proxies = _proxylist
