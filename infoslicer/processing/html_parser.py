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
        """
        Parses the HTML document and converts it to a structured format.
        """
        logger.info('Starting document parsing')
        try:
            try:
                self.image_handler()
            except Exception as e:
                logger.error('Error during image handling %s', e)
            try:
                self.pre_parse()
            except Exception as e:
                logger.error('Error during pre_parse %s', e)
            try:
                output_reference = self.output_soup.find("reference")
            except Exception as e:
                logger.error('Error finding reference in output_soup: %s', e)
                raise

            # try:
            #     self.add_metadata(output_reference)
            # except Exception as e:
            #     logger.error('Error adding metadata: %s', e)
            #     raise

            try:
                self.process_tags(output_reference)
            except Exception as e:
                logger.error('Error processing tags: %s', e)
                raise
            logger.info('Document parsing completed')
            self.output_soup.reference.append(self.image_list)
            return self.output_soup.prettify()
        except Exception as e:
            logger.error('Error during parsing: %s', e)
            raise

    def add_metadata(self, output_reference):
        """
        Adds metadata to the output reference.
        """
        logger.debug('Adding metadata to output reference')
        output_reference.append(self.make_shortdesc())
        output_reference.prolog.append(f'<source href="{self.source}" />')
        output_reference.prolog.append(self.tag_generator("publisher", self.get_publisher()))
        the_date = date.today().strftime("%Y-%m-%d")
        output_reference.prolog.append(
            self.tag_generator(
                'critdates', 
                f'<created date="{the_date}" /><revised modified="{the_date}" />'
            )
        )
        output_reference.append(self.tag_generator("refbody"))

    def process_tags(self, output_reference):
        """
        Processes the tags in the input document.
        """
        in_section = False
        current_refbody = output_reference.refbody
        current_section = None
        self.specialise()
        tag = self.input.find(self.root_node)
        if not tag:
            logger.error('Root node %s not found', self.root_node)
            raise ValueError('Root node %s not found' % self.root_node)
        tag = tag.findChild()
        while tag is not None:
            try:
                logger.debug('Processing tag: %s', tag.name)
                tag_name = tag.name
                if tag_name == self.root_node:
                    pass
                elif tag_name == "p":
                    self.process_paragraph(tag, in_section, current_section, current_refbody)
                elif tag_name in self.section_separators:
                    current_section = self.process_section_separator(tag, current_refbody)
                    in_section = True
                elif tag_name in self.reference_separators:
                    in_section = False
                    current_refbody = self.process_reference_separator(tag, output_reference)
                elif tag_name in self.block_elements:
                    self.process_block_element(tag, current_refbody, current_section)
                else:
                    current_refbody.append(self.tag_generator("section", self.tag_generator(tag_name, tag.renderContents())))
            except Exception as e:
                logger.error('Error processing tag %s: %s', tag.name, e)
                tag = tag.findNextSibling()
                continue
            tag = tag.findNextSibling()

    def process_paragraph(self, tag, in_section, current_section, current_refbody):
        """
        Processes a paragraph tag.
        """
        if in_section:
            current_section.append(self.create_paragraph(tag.renderContents()))
        else:
            current_refbody.append(self.create_paragraph(tag.renderContents()))

    def process_section_separator(self, tag, current_refbody):
        """
        Processes a section separator tag.
        """
        new_section = self.tag_generator("section")
        new_section.append(self.tag_generator("title", tag.renderContents()))
        current_refbody.append(new_section)
        return new_section

    def process_reference_separator(self, tag, output_reference):
        """
        Processes a reference separator tag.
        """
        new_reference = self.tag_generator("reference")
        new_reference.append(self.tag_generator("title", tag.renderContents()))
        new_refbody = self.tag_generator("refbody")
        new_reference.append(new_refbody)
        output_reference.append(new_reference)
        return new_refbody

    def process_block_element(self, tag, current_refbody, current_section):
        """
        Processes a block element tag.
        """
        current_refbody.append(
            self.tag_generator(
                "section", 
                self.tag_generator(tag.name, tag.renderContents())
            )
        )
        current_section.append(self.tag_generator(tag.name, tag.renderContents()))

    def pre_parse(self):
        """
        Prepares the input for parsing.
        """
        logger.info('Starting pre-parse phase')
        try:
            # Ensure we're working with a valid BeautifulSoup object
            if not hasattr(self.input, 'findAll'):
                logger.error('Invalid input: not a BeautifulSoup object')
                raise ValueError('Input must be a BeautifulSoup object')

            # Find all tags at the root level, recursively
            root_tags = self.input.findAll(True, recursive=False)
            
            if not root_tags:
                logger.warning('No tags found in the input document')
                return

            for tag in root_tags:
                try:
                    logger.debug(f'Processing tag: {tag.name}')
                    self.untag(tag)
                except Exception as tag_err:
                    logger.error(f'Error processing tag {tag.name}: {tag_err}')
                    # Optionally continue processing other tags
                    continue

        except Exception as e:
            logger.error(f'Error during pre-parse: {e}')
            raise
        finally:
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
            if not tag or not isinstance(tag, str):
                logger.error('Invalid tag name provided: %s', tag)
                raise ValueError('Tag name must be a non-empty string')
                
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

    def untag(self, tag):
        """
        Recursively removes unwanted tags according to defined lists.
        
        Args:
            tag: Tag hierarchy to work on.
        """
        logger.debug('Processing tag for removal: %s', getattr(tag, 'name', 'Unknown'))
        
        try:
            # Handle different possible input types
            if isinstance(tag, bytes):
                logger.warning(f'Skipping byte object: {tag}')
                return
            
            if not isinstance(tag, Tag):
                logger.warning(f'Skipping non-Tag object: {type(tag)}')
                return

            # Process only children that are actually Tag objects, not strings or NavigableString
            children = [c for c in tag.children if isinstance(c, Tag)]
            
            # Recursively process children
            for child in children:
                try:
                    self.untag(child)
                except Exception as child_err:
                    logger.error(f'Error processing child: {child_err}')
                    continue

            # Tag handling logic
            if (self.remove_classes_regexp != "") and \
            (tag.get("class") and re.match(self.remove_classes_regexp, " ".join(tag.get("class")) if isinstance(tag.get("class"), list) else tag.get("class"))):
                tag.extract()
            elif tag.name in self.keep_tags:
                try:
                    # Ensure we're working with the correct parser
                    new_tag = Tag(self.input, tag.name)
                    new_tag.contents = tag.contents
                    tag.replaceWith(new_tag)
                except Exception as replace_err:
                    logger.error(f'Error replacing tag: {replace_err}')
            elif tag.name in self.remove_tags_keep_content:
                # Find only children that are Tag objects, not strings
                children = [c for c in tag.children if isinstance(c, Tag)]
                if len(children) == 1:
                    tag.replaceWith(children[0])
                elif len(children) > 1:
                    new_tag = Tag(self.input, "p")
                    for child in children:
                        new_tag.append(child)
                    tag.replaceWith(new_tag)
                else:
                    tag.replaceWith(tag.renderContents())
            else:
                tag.extract()
        except Exception as e:
            logger.error(f'Unexpected error in untag: {e}')
            # Log additional context
            logger.error(f'Tag type: {type(tag)}')
            logger.error(f'Tag attributes: {tag.attrs if hasattr(tag, "attrs") else "N/A"}')
            
            # Re-raise or handle as needed
            raise
