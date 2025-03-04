# Copyright (C) IBM Corporation 2008

import re
import logging
from bs4 import BeautifulSoup
from infoslicer.processing.html_parser import HTMLParser, NoDocException

logger = logging.getLogger('infoslicer:MediaWiki_Parser')

class MediaWiki_Parser(HTMLParser):
    #Overwriting the regexp so that various non-data content (see also, table of contents etc.) is removed
    remove_classes_regexp = re.compile("toc|noprint|metadata|sisterproject|boilerplate|reference(?!s)|thumb|navbox|editsection")

    def __init__(self, document_to_parse, title, source_url):
        if document_to_parse is None:
            raise NoDocException("No content to parse - supply document to __init__")

        logger.debug('MediaWiki_Parser: %s' % source_url)

        # Ensure document_to_parse is a string
        if isinstance(document_to_parse, bytes):
            document_to_parse = document_to_parse.decode('utf-8', errors='ignore')

        # Split the document to extract text content
        try:
            header, input_content = document_to_parse.split("<text xml:space=\"preserve\">")
        except ValueError:
            # Fallback if split fails
            input_content = document_to_parse

        # Find the revision id
        revid_match = re.findall(r'\<parse.*revid\=\"(?P<rid>[0-9]*)\"', header)
        revid = revid_match[0] if revid_match else '0'

        # Clean up input content
        input_content = input_content.split("</text>")[0] if "</text>" in input_content else input_content
        
        # Use BeautifulSoup instead of custom parsing
        input_content = "<body>" + input_content + "</body>"
        
        # Call the normal constructor
        HTMLParser.__init__(self, input_content, title, source_url)
        
        # Overwrite the source variable with revision-specific URL
        self.source = f"http://{source_url.replace('http://', '').split('/')[0]}/w/index.php?oldid={revid}"

    def specialise(self):
        """
        Uses DITA_Parser class's specialise() call to find the infobox in a wiki article
        """
        # Use BeautifulSoup for more robust parsing
        soup = BeautifulSoup(self.input, 'html.parser')
        
        # Find first table that might be an infobox
        first_table = soup.find('table')
        
        if first_table and first_table.get('class') and re.search(r"infobox", ' '.join(first_table.get('class', []))):
            # Create infobox section
            infobox_tag = self.tag_generator("section", attrs=[("id", "infobox")])
            
            # Try to find inner table or use outer table
            inner_table = first_table.find('table') or first_table
            
            # Find title
            try:
                # Try to find title in a colspan=2 tag or first header
                title_tag = inner_table.find(attrs={"colspan": "2"}) or inner_table.find(['th', 'caption'])
                inner_table_title = title_tag.get_text(strip=True) if title_tag else "Infobox"
            except Exception:
                inner_table_title = "Infobox"
            
            # Add title to infobox
            infobox_tag.append(self.tag_generator("title", inner_table_title))
            
            # Create properties section
            properties_tag = self.tag_generator("properties")
            infobox_tag.append(properties_tag)
            
            # Process table rows
            for tr in inner_table.find_all('tr'):
                cells = tr.find_all(['th', 'td'])
                
                if len(cells) > 0:
                    property_tag = self.tag_generator("property")
                    
                    if len(cells) == 1:
                        # Single cell: use as value
                        property_tag.append(self.tag_generator("propvalue", cells[0].get_text(strip=True)))
                    elif len(cells) >= 2:
                        # Multiple cells: first as type, second as value
                        property_tag.append(self.tag_generator("proptype", cells[0].get_text(strip=True).replace(":", "")))
                        property_tag.append(self.tag_generator("propvalue", cells[1].get_text(strip=True)))
                    
                    properties_tag.append(property_tag)

            # Add infobox to output and remove from further processing
            self.output_soup.refbody.append(infobox_tag)
            first_table.decompose()
