# Copyright (C) IBM Corporation 2008

import logging
import re
from datetime import date
from bs4 import BeautifulSoup, Tag
# from NewtifulSoup import NewtifulStoneSoup as BeautifulStoneSoup
from infoslicer.processing.newtiful_soup import NewtifulStoneSoup as BeautifulStoneSoup
logger = logging.getLogger('infoslicer:HTML_Parser')

class NoDocException(Exception):
    """
    Wrap Beautiful Soup HTML parser up in custom class to add some 
    Media Wiki and DITA specific parsing functionality.
    """
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)

class HTMLParser:

    #=======================================================================
    # These lists are used at the pre-parsing stage
    keep_tags = [ "html", "body", "p",  "h1", "h2", "h3", "h4", "h5", "h6",\
                 "img", "table", "tr", "th", "td", "ol", "ul", "li", "sup", "sub"]  
    remove_tags_keep_content= ["div", "span", "strong", "a", "i", "b", "u", "color", "font"]
    remove_classes_regexp = ""
    #=======================================================================

    #=======================================================================
    # These lists are used at the parsing stage
    root_node = "body"
    section_separators = ["h2", "h3", "h4", "h5"]
    reference_separators = ["h1"]
    block_elements = ["img", "table", "ol", "ul"]
    #=======================================================================

    def __init__(self, document_to_parse, title, source_url):
        logger.info(f'Initializing HTMLParser with title: {title}')
        if document_to_parse is None:
            logger.error('No document provided to parse')
            raise NoDocException("No content to parse - supply document to __init__")
        try:
            self.input = BeautifulSoup(document_to_parse)
        except Exception as e:
            logger.error(f'Failed to parse HTML document: {e}')
            raise
        self.source = source_url
        self.output_soup = BeautifulStoneSoup('<?xml version="1.0" encoding="utf-8"?><reference><title>%s</title></reference>' % title)
        # First ID issued will be id below + 1
        self.ids = {"reference" : 1,\
                    "section" : 1,\
                    "p" : 1,\
                    "ph" : 1\
                    }
        self.image_list = self.tag_generator("reference", self.tag_generator("refbody"),[("id", "imagelist")])
        logger.debug('HTMLParser initialized successfully')

    def create_paragraph(self, text, tag="p"):
        logger.debug(f'Creating new paragraph with tag: {tag}')
        """
            Creates a new paragraph containing <ph> tags, surrounded by the specified tag
            @param text: Text to mark up
            @param tag: Tag to surround with (defaults to "p")
            @return: new tag
        """
        new_para = self.tag_generator(tag)
        sentences = re.split(re.compile(r"[\.\!\?\"] "), text)
        separators = re.findall(re.compile(r"[\.\!\?\"](?= )"), text)
        for i in range(len(sentences) - 1):
            new_para.append(self.tag_generator("ph", sentences[i] + separators[i]))
        new_para.append(self.tag_generator("ph", sentences[-1]))
        return new_para

    def get_publisher(self):
        logger.debug(f'Extracting publisher from source: {self.source}')
        """
            Extracts publisher from source URL
            @return: name of publisher
        """
        output = self.source.replace("http://", "").split("/")[0].split(".")
        logger.debug(f'Publisher extracted: {".".join([output[-2], output[-1]])}')
        return ".".join([output[-2], output[-1]])

    def image_handler(self):
        logger.info('Processing images')
        try:
            for img in self.input.findAll("img"):
                try:
                    too_small = False
                    image_path = img.get('src', '')
                    if not image_path:
                        logger.warning('Image found without src attribute')
                        continue
                    
                    alt_text = ""
                    try:
                        if img.get("width") and img.get("height") and \
                           int(img['width']) <= 70 and int(img['height']) <= 70:
                            too_small = True
                    except ValueError:
                        logger.warning(f'Invalid image dimensions for {image_path}')
                    
                    alt_text = img.get("alt", image_path.split("/")[-1])
                    
                    if (not too_small) and self.image_list.refbody.find(attrs={"href": image_path}) is None:
                        logger.debug(f'Adding image: {image_path}')
                        self.image_list.refbody.append(
                            self.tag_generator("image", f"<alt>{alt_text}</alt>", [("href", image_path)])
                        )
                    img.extract()
                except Exception as e:
                    logger.error(f'Error processing individual image: {e}')
                    continue
        except Exception as e:
            logger.error(f'Error in image handling: {e}')

    def make_shortdesc(self):
        logger.debug('Creating short description')
        """
            Extracts 1st paragraph from input, and makes it a 'shortdesc' tag
            @return: new <shortdesc> tag containing contents of 1st paragraph
        """
        paragraphs = self.input.findAll("p")
        for p in paragraphs:
            contents = p.renderContents()
            if len(contents) > 20 and (("." in contents) or ("?" in contents) or ("!" in contents)):
                p.extract()
                return self.create_paragraph(contents, "shortdesc")
        return self.tag_generator("shortdesc")

    def parse(self):
        logger.info('Starting document parsing')
        try:
            #remove images
            self.image_handler()
            # pre-parse
            self.pre_parse()
            #identify the containing reference tag
            output_reference = self.output_soup.find("reference")
            #add the short description
            output_reference.append(self.make_shortdesc())
            #add the <prolog> tag to hold metadata
            output_reference.append(self.tag_generator("prolog"))
            #add the source url
            output_reference.prolog.append(f'<source href="{self.source}" />')
            #add the publisher
            output_reference.prolog.append(self.tag_generator("publisher", self.get_publisher()))
            the_date = date.today().strftime("%Y-%m-%d")
            #add created and modified dates
            output_reference.prolog.append(
                self.tag_generator(
                    'critdates', 
                    f'<created date="{the_date}" /><revised modified="{the_date}" />'
                )
            )
            #add the first refbody
            output_reference.append(self.tag_generator("refbody"))
            #track whether text should be inserted in a section or into the refbody
            in_section = False
            #set current refbody and section pointers
            current_refbody = output_reference.refbody
            current_section = None
            #call specialised method (redundant in this class, used for inheritance)
            self.specialise()
            #find the first tag
            tag = self.input.find(self.root_node)
            if not tag:
                logger.error(f'Root node {self.root_node} not found')
                raise ValueError(f'Root node {self.root_node} not found')
                
            tag = tag.findChild()
            while tag is not None:
                try:
                    logger.debug(f'Processing tag: {tag.name}')
                    #set variable to avoid hammering the string conversion function
                    tag_name = tag.name
                    #for debugging:
                    #ignore the root node
                    if tag_name == self.root_node:
                        pass
                    #paragraph action:
                    elif tag_name == "p":
                        if in_section:
                            #tag contents as sentences and add to current section
                            current_section.append(self.create_paragraph(tag.renderContents()))
                        else:
                            #tag contents as sentences and add to current refbody
                            current_refbody.append(self.create_paragraph(tag.renderContents()))
                    #section separator action
                    elif tag_name in self.section_separators:
                        #create a new section tag
                        new_section = self.tag_generator("section")
                        #make a title for the tag from heading contents
                        new_section.append(self.tag_generator("title", tag.renderContents()))
                        #hold a pointer to the new section
                        current_section = new_section
                        #add the new section to the current refbody
                        current_refbody.append(new_section)
                        #currently working in a section, not a refbody
                        in_section = True
                    #reference separator action:
                    elif tag_name in self.reference_separators:
                        #no longer working in a section
                        in_section = False
                        #create a new reference tag
                        new_reference = self.tag_generator("reference")
                        #make a title for the tag from heading contents
                        new_reference.append(self.tag_generator("title", tag.renderContents()))
                        #create a refbody tag for the reference
                        new_refbody = self.tag_generator("refbody")
                        #add refbody to the reference tag
                        new_reference.append(new_refbody)
                        #remember the current refbody tag
                        current_refbody = new_refbody
                        #add the new reference to the containing reference tag in the output
                        output_reference.append(new_reference)
                    #block element action
                    elif tag_name in self.block_elements:
                        current_refbody.append(
                            self.tag_generator(
                                "section", 
                                self.tag_generator(tag_name, tag.renderContents())
                            )
                        )
                        #add block element to current section
                        current_section.append(self.tag_generator(tag_name, tag.renderContents()))
                    else:
                        #add block element to new section
                        current_refbody.append(self.tag_generator("section", self.tag_generator(tag_name, tag.renderContents())))
                except Exception as e:
                    logger.error(f'Error processing tag {tag.name}: {e}')
                    tag = tag.findNextSibling()
                    continue
                #find the next tag and continue
                tag = tag.findNextSibling()
            logger.info('Document parsing completed')
            #append the image list
            self.output_soup.reference.append(self.image_list)
            #return output as a properly indented string
            return self.output_soup.prettify()
        except Exception as e:
            logger.error(f'Error during parsing: {e}')
            raise

    def pre_parse(self):
        logger.info('Starting pre-parse phase')
        """
            Prepares the input for parsing
        """
        for tag in self.input.findAll(True, recursive=False):
            self.unTag(tag)
        logger.info('Pre-parse phase completed')

    def specialise(self):
        logger.debug('Running specialise step')
        """
            Allows for specialised calls when inheriting
        """
        pass

    def tag_generator(self, tag, contents=None, attrs=None):
        logger.debug(f'Generating new tag: {tag}')
        try:
            if not tag:
                logger.error('Empty tag name provided')
                raise ValueError('Tag name cannot be empty')
                
            if attrs is None:
                attrs = {}
            elif isinstance(attrs, list):
                # Convert list of tuples to dictionary
                attrs = dict(attrs)
                
            # Ensure tag is a string
            tag = str(tag).strip()
            if not tag:
                logger.error('Invalid tag name after conversion')
                raise ValueError('Invalid tag name')

            # Create new tag using BeautifulSoup's parser
            new_tag = self.output_soup.new_tag(tag, **attrs)

            # Add ID if needed
            if tag in self.ids and not attrs:
                self.ids[tag] += 1
                new_tag['id'] = str(self.ids[tag])

            # Handle contents
            if contents is not None:
                try:
                    if isinstance(contents, (str, bytes)):
                        new_tag.string = str(contents)
                    else:
                        new_tag.append(contents)
                except Exception as e:
                    logger.error(f'Failed to insert contents into tag: {e}')
                    new_tag.string = ''

            return new_tag

        except Exception as e:
            logger.error(f'Error generating tag {tag}: {e}')
            raise ValueError(f'Failed to generate tag: {e}')

    def unTag(self, tag):
        logger.debug(f'Processing tag for removal: {tag.name}')
        try:
            """
                recursively removes unwanted tags according to defined lists
                @param tag: tag hierarchy to work on
            """
            for child in tag.findChildren(True, recursive=False):
                try:
                    self.unTag(child)
                except Exception as e:
                    logger.error(f'Error untagging child: {e}')
                    continue
                    
            if (self.remove_classes_regexp != "") and \
               (tag.get("class") and re.match(self.remove_classes_regexp, tag["class"])):
                tag.extract()
            elif tag.name in self.keep_tags:
                try:
                    new_tag = Tag(self.input, tag.name)
                    new_tag.contents = tag.contents
                    tag.replaceWith(new_tag)
                except Exception as e:
                    logger.error(f'Error replacing tag: {e}')
            elif tag.name in self.remove_tags_keep_content:
                children = tag.findChildren(True, recursive=False)
                if len(children)==1:
                    tag.replaceWith(children[0])
                elif len(children) > 1:
                    new_tag = Tag(self.input, "p")
                    for child in tag.findChildren(True, recursive=False):
                        new_tag.append(child)
                    tag.replaceWith(new_tag)
                else:
                    tag.replaceWith(tag.renderContents())
            else:
                tag.extract()
        except Exception as e:
            logger.error(f'Error in unTag: {e}')
