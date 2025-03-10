# Copyright (C) IBM Corporation 2008

import re
import logging
from infoslicer.processing.html_parser import HTMLParser, NoDocException

logger = logging.getLogger('infoslicer')

class MediaWiki_Parser(HTMLParser):

    #Overwriting the regexp so that various non-data content (see also, table of contents etc.) is removed
    remove_classes_regexp = re.compile("toc|noprint|metadata|sisterproject|boilerplate|reference(?!s)|thumb|navbox|editsection")

    def __init__(self, document_to_parse, revid, title, source_url):
        if document_to_parse is None:
            raise NoDocException("No content to parse - supply document to __init__")

        logger.debug('MediaWiki_Parser: %s' % source_url)
        # import xml.etree.ElementTree as ET
        #call the normal constructor
        HTMLParser.__init__(self, "<body>" + document_to_parse + "</body>", title, source_url)
        #overwrite the source variable
        self.source = "http://" + source_url.replace("http://", "").split("/")[0] + "/w/index.php?oldid=%s" % revid

    def specialise(self):
        """
            Uses DITA_Parser class's specialise() call to find the infobox in a wiki article
        """
        #infobox should be first table
        first_table = self.soup.find("table")
        #the word "infobox" should be in the class name somewhere
        if first_table is not None and first_table.has_key("class")  and (re.match(re.compile("infobox"), first_table["class"]) is not None):
            #make a new output tag to work with
            infobox_tag = self.tag_generator("section", attrs=[("id", "infobox")])
            #sometimes infobox data is in an inner table
            inner_table = first_table.table
            #sometimes it isn't :-(
            if inner_table is None:
                #if there isn't an inner table, work on the outer table
                inner_table = first_table
                # the title _should_ be in a "colspan == 2" tag
                inner_table_title = first_table.find(attrs={ "colspan" : "2"})
                #don't break if title can't be found
                if inner_table_title is not None:
                    #get the title
                    inner_table_title_temp = inner_table_title.renderContents()
                    #remove the title so it isn't processed twice
                    inner_table_title.extract()
                    inner_table_title = inner_table_title_temp
            else:
                # if there is an inner table, the title will be in the containing table - hunt it down.
                inner_table_title = inner_table.findParent("tr").findPreviousSibling("tr").findChild("th").renderContents()
            #finally append the title to the tag
            infobox_tag.append(self.tag_generator("title", inner_table_title))
            #generate the properties list
            properties_tag = self.tag_generator("properties")
            infobox_tag.append(properties_tag)
            #each property is a row in the table
            for tr in inner_table.findAll("tr"):
                #make sure the row isn't empty
                if tr.findChild() is not None:
                    #make a new <property> tag
                    property_tag = self.tag_generator("property")
                    #table cells are either th or td
                    table_cells = tr.findAll(re.compile("th|td"))
                    if len(table_cells) == 0:
                        pass
                    elif len(table_cells) == 1:
                        #if there's only one cell on the row, make it a value
                        property_tag.append(self.tag_generator("propvalue", table_cells[0].renderContents()))
                    else:
                        #if there are two cells on the row, the first is the property type, the second is the value
                        property_tag.append(self.tag_generator("proptype", table_cells[0].renderContents().replace(":", "")))
                        property_tag.append(self.tag_generator("propvalue", table_cells[1].renderContents()))
                    #add the property to the <properties> tag
                    properties_tag.append(property_tag)
            #add the infobox to the output
            self.output_soup.refbody.append(infobox_tag)
            #remove the first table to avoid parsing twice
            first_table.extract()
