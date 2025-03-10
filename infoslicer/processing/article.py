# Copyright (C) IBM Corporation 2008
import logging

from gi.repository import GdkPixbuf, Gtk

# from infoslicer.processing.ArticleData import Article_Data, SectionData, SentenceData
from infoslicer.processing.article_data import (
    ArticleData,
    ParagraphData,
    SectionData,
    SentenceData,
)
from infoslicer.processing.paragraph import Paragraph
from infoslicer.processing.section import Section, dummySection
from infoslicer.processing.sentence import Sentence


logger = logging.getLogger("infoslicer::Article")

arrow_xpm = [
    "15 11 4 1",
    "       c None s None",
    ".      c black",
    "r      c #800000",
    "R      c #FF0000",
    "      ..       ",
    "     ....      ",
    "     .rr..     ",
    " .....rRr..    ",
    "..rrrrrRRr..   ",
    "..rRRRRRRRr..  ",
    "..rRRRRRRr..   ",
    " .....rRr..    ",
    "     .rr..     ",
    "     ....      ",
    "      ..       ",
]


class Article:
    """
    Created by Jonathan Mace

    The Article class maintains a concrete representation of the article, 
    in the form of a Gtk.TextBuffer Positions within the text are represented 
    by Gtk.TextIter

    The class contains methods for inserting and deleting new sentences, 
    paragraphs and sections.

    The class also has methods for finding the most appropriate insertion 
    point for new sections.

    The class maintains the section-based structure of the article.

    At any point, the article_data class corresponding to the current 
    state of the article can be retrieved
    """

    def __init__(self, article_data=ArticleData()) -> None:
        """
        Create default text buffer and set to empty
        """
        self.__buf = Gtk.TextBuffer()
        self.__buf.set_text("")
        insertionpoint = self.__buf.get_end_iter()
        insertionmark = self.__buf.create_mark(None, insertionpoint, False)

        """ 
        Set the attributes such as title, theme, id etc. as specified in the article_data parameter
        """
        self.id = article_data.id
        self.article_title = article_data.article_title
        self.article_theme = article_data.article_theme
        self.source_article_id = article_data.source_article_id
        self.image_list = article_data.get_image_list()

        """
        The article is currently blank, so there are no sections
        """
        self.__sections = []

        """
        Create new sections based on the section data in article_data
        At this level, nothing is actually inserted into the textbuffer.
        The text insertion occurs at the sentence level.
        The sentences are created within the initialisation of the Section object.
        """
        sections_data = article_data.sections_data
        for section_data in sections_data:
            insertioniter = self.__buf.get_iter_at_mark(insertionmark)
            self.__sections.append(Section(section_data, self.__buf, insertioniter))

        self.__buf.delete_mark(insertionmark)
        startdummy = dummySection(self.__buf, self.__buf.get_start_iter(), True)
        enddummy = dummySection(self.__buf, self.__buf.get_end_iter(), False)
        self.__sections = [startdummy] + self.__sections + [enddummy]

        self.markmark = None

    def get_data(self) -> ArticleData:
        """
        Returns the article_data object corresponding to the current state of the article.
        """
        try:
            self.check_integrity()
            idz = self.id
            source_article_id = self.source_article_id
            article_title = self.article_title
            article_theme = self.article_theme
            image_list = self.image_list
            sections_data = []
            for section in self.__sections[1 : len(self.__sections) - 1]:
                sections_data.append(section.getData())

            data = ArticleData(
                idz,
                source_article_id,
                article_title,
                article_theme,
                sections_data,
                image_list,
            )

            return data
        except Exception as e:
            logger.error("Error in get_data: %s", e)
            return None

    def check_integrity(self) -> None:
        """
        When a user freely edits the text of an article, they can perform actions
        such as completely deleting a sentence, or concatenating two sections, etc.
        This method reparses the structure of the article.
        """
        try:
            i = 0
            sections = []
            while i < len(self.__sections) - 1:
                section = self.__sections[i]
                nextsection = self.__sections[i + 1]

                if section.getStart().compare(nextsection.getStart()) == -1:
                    text = self.__buf.get_slice(
                        section.getStart(), nextsection.getStart(), True
                    )
                    if len(text) > 2 and text[-2] != "\n":
                        nextsection.paragraphs = section.paragraphs + nextsection.paragraphs
                    else:
                        sections.extend(section.checkIntegrity(nextsection.getStart()))
                else:
                    section.remove()
                    del self.__sections[i]
                    i = i - 1
                i += 1

            section = self.__sections[-1]
            if section.getStart().compare(self.__buf.get_end_iter()) == -1:
                if len(text) > 2 and text[-2] != "\n":
                    pars = section.paragraphs
                    par = pars[-1]
                    if text[-1] != "\n":
                        pars[-2].sentences.append(
                            Sentence(
                                SentenceData(-1, -1, -1, -1, -1, "\n", None),
                                self.__buf,
                                par.getStart(),
                            )
                        )
                        pars.append(
                            Paragraph(
                                ParagraphData(-1, -1, -1, -1, []), self.__buf, par.getEnd()
                            )
                        )
                    elif par.getText() == "\n":
                        pars[-2].sentences.append(
                            Sentence(
                                SentenceData(-1, -1, -1, -1, -1, "\n", None),
                                self.__buf,
                                par.getStart(),
                            )
                        )
                    else:
                        pars.append(
                            Paragraph(
                                ParagraphData(-1, -1, -1, -1, []), self.__buf, par.getEnd()
                            )
                        )
                sections.extend(section.checkIntegrity(self.__buf.get_end_iter()))

            self.__sections = sections + [
                dummySection(self.__buf, self.__buf.get_end_iter(), False)
            ]
            self.generate_ids()

            i = 1
            while i < len(self.__sections) - 1:
                j = 0
                section = self.__sections[i]
                while j < len(section.paragraphs) - 1:
                    k = 0
                    paragraph = section.paragraphs[j]
                    while k < len(paragraph.sentences) - 1:
                        sentence = paragraph.sentences[k]
                        if sentence.getStart().compare(sentence.getEnd()) > -1:
                            sentence.remove()
                            del paragraph.sentences[k]
                            k -= 1
                        k += 1
                    if not paragraph.sentences:
                        del section.paragraphs[j]
                        j -= 1
                    j += 1
                if not section.paragraphs:
                    del self.__sections[i]
                    i -= 1
                i += 1
        except Exception as e:
            logger.error("Error in check_integrity: %s", e)

    def generate_ids(self) -> None:
        for section in self.__sections[1 : len(self.__sections) - 1]:
            section.generateIds()

    def insert(self, objects, lociter) -> None:
        """
        Insert sentences, paragraphs, and sections into the article at the specified location.

        Parameters:
        - objects: List of objects (sentences, paragraphs, sections) to insert.
        - lociter: Location iterator specifying where to insert the objects within the text buffer.
        """

        if not objects:
            return

        try:
            sectionnumber = self.__get_exact_section(lociter)
            # If located at the end of the article, pad with an empty section
            if sectionnumber == len(self.__sections) - 1:
                self.__pad()
                lociter = self.__sections[-2].getStart()
            section = self.__sections[sectionnumber]

            extra = 0
            secstart = section.getStart()
            secend = section.getEnd()

            # Determine if extra offset adjustment is needed
            if (
                secstart.compare(lociter) == 0
                and (secend.get_offset() - secstart.get_offset()) < 4
            ):
                extra = 3
            elif secend.get_offset() - lociter.get_offset() < 4:
                extra = 3

            paragraph = section.getParagraph(lociter)
            # If at the end of the paragraph, pad with an empty paragraph
            if paragraph == section.getParagraphs()[-1]:
                section.pad()
                paragraph = section.getParagraphs()[-2]
                lociter = paragraph.getStart()

            # Determine insertion point for sentences
            insertioniter = paragraph.getBestSentence(lociter).getStart()
            insertionmark = self.__buf.create_mark(None, insertioniter, False)

            # Marks for highlighting the inserted section
            self.insertionsectionstart = self.__buf.create_mark(
                None, section.getStart(), True
            )
            self.insertionsectionend = self.__buf.create_mark(None, section.getEnd(), False)
            self.insertionstartdist = (
                insertioniter.get_offset() - section.getStart().get_offset()
            )
            self.insertionenddist = (
                section.getEnd().get_offset() - insertioniter.get_offset() - extra
            )

            split = False

            # Prepare objects for insertion
            if objects:
                obj = objects[0]

                if obj.type == "section":
                    del objects[0]
                    dummyparagraphdata = ParagraphData(idz=-1, sentences_data=[])
                    objects = obj.paragraphs_data + [dummyparagraphdata] + objects
                    obj = objects[0]
                if obj.type == "paragraph":
                    del objects[0]
                    dummysentencedata = SentenceData(idz=-1, text="")
                    objects = obj.sentences_data + [dummysentencedata] + objects
                    obj = objects[0]

            # Insert sentences or pictures
            while objects and (obj.type == "sentence" or obj.type == "picture"):
                if obj.text != "":
                    insertioniter = self.__buf.get_iter_at_mark(insertionmark)
                    paragraph.insertSentence(obj, insertioniter)
                else:
                    split = True
                    del objects[0]
                    break

                del objects[0]
                if objects:
                    obj = objects[0]

            splititer = self.__buf.get_iter_at_mark(insertionmark)
            splitmark = self.__buf.create_mark(None, splititer, True)

            # Insert ending sentences or pictures
            if objects:
                obj = objects[-1]
            while objects and (obj.type == "sentence" or obj.type == "picture"):
                insertioniter = self.__buf.get_iter_at_mark(splitmark)
                paragraph.insertSentence(obj, insertioniter)

                del objects[-1]
                if objects:
                    obj = objects[-1]

            # Clean up the paragraph and section
            paragraph.clean()
            section.clean()

            # Split paragraph and insert remaining objects as paragraphs
            if split:
                splititer = self.__buf.get_iter_at_mark(splitmark)
                offset = splititer.get_offset()
                section.splitParagraph(splititer)
                insertioniter = self.__buf.get_iter_at_offset(offset)
                if objects:
                    self.__insert_paragraphs(objects, insertioniter)

            # Highlight the inserted section
            self.highlight_drag_result()
        except Exception as e:
            logger.error("Error in insert: %s", e)

    def __insert_paragraphs(self, objects, lociter):
        """
        This method is the same as the above insert method, except that sentence 
        objects are not included.

        So, objects is a list which can take the form: [ paragraph objects ] 
        ++ [ section objects ] ++ [ paragraph objects ]
        And again, if the objects list does contain sections, then the 
        first paragraph array will end with a dummy paragraph object.
        This method is used by the drag and drop handler, when the user drags
        a set of paragraphs into the textbuffer.
        """

        
        try:
            # Find the section which contains the insertion point
            sectionnumber = self.__get_exact_section(lociter)
            section = self.__sections[sectionnumber]

            # Insertion point is offset by one to prevent the insertion of \
            # the paragraphs at the start of the section
            lociter = self.__buf.get_iter_at_offset(lociter.get_offset() + 1)

            # Find the best paragraph gap to insert into
            insertioniter = section.getBestParagraph(lociter).getStart()
            insertionmark = self.__buf.create_mark(None, insertioniter, False)

            split = False

            obj = objects[0]

            if obj.type == "section":
                del objects[0]
                blankparagraph = ParagraphData(idz=-1, sentences_data=[])
                objects = obj.paragraphs_data + [blankparagraph] + objects
                obj = objects[0]

            while objects and obj.type == "paragraph":
                # First, deal with the paragraph triples. We insert these into the current section.
                # Then when we run out of paragraph triples, we split the section.

                # if sentences = [] then we have reached the end of the first list and must break.
                # We do not insert this empty paragraph, it is just a placeholder.
                if obj.sentences_data:
                    insertioniter = self.__buf.get_iter_at_mark(insertionmark)
                    section.insertParagraph(obj, insertioniter)
                else:
                    split = True
                    del objects[0]
                    break

                del objects[0]
                if objects:
                    obj = objects[0]

            splititer = self.__buf.get_iter_at_mark(insertionmark)
            splitmark = self.__buf.create_mark(None, splititer, True)

            if objects != []:
                obj = objects[-1]
            while objects != [] and obj.type == "paragraph":
                # Now, we actually add the ending paragraphs, then split the section at the splitmark
                # which was created between the two while loops
                insertioniter = self.__buf.get_iter_at_mark(splitmark)
                section.insertParagraph(obj, insertioniter)

                del objects[-1]
                if objects != []:
                    obj = objects[-1]

            # Now we simply split the section at the splitmark, then call the insertsections method with
            # the remaining contents of objects
            if split:
                splititer = self.__buf.get_iter_at_mark(splitmark)
                offset = splititer.get_offset()
                splititer = self.get_paragraph(splititer).getStart()
                self.__split_section(splititer)
                insertioniter = self.__buf.get_iter_at_offset(offset)
                if objects != []:
                    self.__insert_sections(objects, insertioniter)
        except Exception as e:
            logger.error("Error in __insert_paragraphs: %s", e)

    def __insert_sections(self, objects, lociter):
        """
        objects is a list of section objects, and lociter is a location in the textbuffer

        We find the closest section gap to the lociter specified, 
        and then insert the sections at this point.
        """
        insertioniter = self.get_best_section(lociter).getStart()
        insertionmark = self.__buf.create_mark(None, insertioniter, False)
        for obj in objects:
            insertioniter = self.__buf.get_iter_at_mark(insertionmark)
            self.insert_section(obj, insertioniter)

    def get_selection(self):
        """
        If the user has highlighted some text, this method returns the sentence/paragraph/section based
        representation of the selection
        """
        buf = self.__buf
        bounds = buf.get_selection_bounds()
        if bounds[0].compare(bounds[1]) == 1:
            start = bounds[1]
            end = bounds[0]
        else:
            start = bounds[0]
            end = bounds[1]
        data = self.get_range(start, end)
        return data

    def get_range(self, startiter, enditer):
        """
        This method returns the section, paragraph and sentence objects between startiter and enditer
        """

        try:
            startindex = self.__get_exact_section(startiter)
            endindex = self.__get_exact_section(enditer)
            if startindex == endindex:
                data = self.__sections[startindex].getDataRange(startiter, enditer)
            else:
                startdata = []
                startsection = self.__sections[startindex]
                if startiter.compare(startsection.getStart()) == 0:
                    startdata.append(self.__sections[startindex].getData())
                else:
                    startdata.extend(
                        startsection.getDataRange(startiter, startsection.getEnd())
                    )
                    startdata.append(ParagraphData(idz=-1, sentences_data=[]))

                middledata = []
                for section in self.__sections[startindex + 1 : endindex]:
                    middledata.append(section.getData())

                enddata = []
                if endindex != len(self.__sections):
                    endsection = self.__sections[endindex]
                    enddata.extend(endsection.getDataRange(endsection.getStart(), enditer))

                data = startdata + middledata + enddata

            return data
        except Exception as e:
            logger.error("Error in get_range: %s", e)

    def get_buffer(self):
        """
        This method simply returns the Gtk.TextBuffer being maintained by this instance of the Article class.
        """
        return self.__buf

    def insert_section(self, section_data, lociter):
        """
        This method inserts a single section into the article.

        The section is represented by section_data, and the insertion point is specified by lociter

        The section is inserted into the closest gap to lociter.
        """
        insertionindex = self.__get_best_section(lociter)
        if insertionindex == 0:
            insertionindex = insertionindex + 1
        insertioniter = self.__sections[insertionindex].getStart()
        section = Section(section_data, self.__buf, insertioniter)
        self.__sections.insert(insertionindex, section)

    def delete_section(self, lociter):
        """
        This method deletes the section which contains lociter.
        """
        deletionindex = self.__get_exact_section(lociter)
        if deletionindex != len(self.__sections) - 1:
            section = self.__sections[deletionindex]
            section.delete()
            del self.__sections[deletionindex]

    def remove_section(self, lociter):
        """
        This method has the same effect as deleteSection
        """
        removalindex = self.__get_exact_section(lociter)
        section = self.__sections[removalindex]
        section.delete()
        del self.__sections[removalindex]

    def delete_selection(self, startiter, enditer):
        """
        This method deletes all sentence, paragraph and data objects from startiter to enditer.
        """
        try:
            startindex = self.__get_exact_section(startiter)
            endindex = self.__get_exact_section(enditer)
            if endindex == len(self.__sections) - 1:
                endindex = endindex - 1
            if startindex == endindex:
                empty = self.__sections[startindex].deleteSelection(startiter, enditer)
                if empty:
                    self.__sections[startindex].delete()
                    del self.__sections[startindex]
            elif startindex < endindex:
                startmark = self.__buf.create_mark(None, startiter, True)
                endmark = self.__buf.create_mark(None, enditer, True)

                endsection = self.__sections[endindex]
                empty = endsection.deleteSelection(
                    endsection.getStart(), self.__buf.get_iter_at_mark(endmark)
                )
                if empty:
                    self.__sections[endindex].delete()
                    del self.__sections[endindex]
                self.__buf.delete_mark(endmark)

                for i in range(startindex + 1, endindex):
                    self.__sections[startindex + 1].delete()
                    del self.__sections[startindex + 1]

                startsection = self.__sections[startindex]
                empty = startsection.deleteSelection(
                    self.__buf.get_iter_at_mark(startmark), startsection.getEnd()
                )
                if empty:
                    self.__sections[startindex].delete()
                    del self.__sections[startindex]
                self.__buf.delete_mark(startmark)
        except Exception as e:
            logger.error("Error in delete_selection: %s", e)

    def remember_selection(self):
        """
        This method is uses to remember a specific selection.

        It is currently used to remember what text the user is dragging around within the article.
        """
        bounds = self.__buf.get_selection_bounds()
        self.selectionlength = bounds[1].get_offset() - bounds[0].get_offset()
        self.selectionstartoffset = bounds[0].get_offset()
        self.selectionstartmark = self.__buf.create_mark(None, bounds[0], True)
        self.selectionendmark = self.__buf.create_mark(None, bounds[1], True)

    def delete_drag_selection(self):
        """
        This method deletes the selection which was saved by the rememberSelection method

        This occurs when a user is rearranging text within the same article; the text will be inserted somewhere,
        and then the old text will be deleted.
        """

        deletestart = self.__buf.get_iter_at_mark(self.selectionstartmark)
        deletestartoffset = deletestart.get_offset()

        if deletestart.get_offset() != self.selectionstartoffset:
            deleteend = self.__buf.get_iter_at_mark(self.selectionendmark)
            deletestart = self.__buf.get_iter_at_offset(
                deleteend.get_offset() - self.selectionlength
            )
        else:
            deleteend = self.__buf.get_iter_at_offset(
                deletestartoffset + self.selectionlength
            )

        self.delete_selection(deletestart, deleteend)
        self.__buf.delete_mark(self.selectionstartmark)
        self.__buf.delete_mark(self.selectionendmark)

    def highlight_drag_result(self):
        """
        When stuff is inserted into the article, the method that deals with the insertion keeps track of where it was inserted.

        This method highlights the inserted text.
        """
        startoffset = (
            self.__buf.get_iter_at_mark(self.insertionsectionstart).get_offset()
            + self.insertionstartdist
        )
        endoffset = (
            self.__buf.get_iter_at_mark(self.insertionsectionend).get_offset()
            - self.insertionenddist
        )
        startiter = self.__buf.get_iter_at_offset(startoffset)
        enditer = self.__buf.get_iter_at_offset(endoffset)
        self.__buf.select_range(startiter, enditer)
        self.__buf.delete_mark(self.insertionsectionstart)
        self.__buf.delete_mark(self.insertionsectionend)

    def __get_best_section(self, lociter):
        """
        Given any position within the buffer, this method determines where the 
        closest section gap is.

        It then returns the index of the section, within the 
        self.__sections list, of the preceeding section.
        """
        sectionindex = self.__get_exact_section(lociter)
        section = self.__sections[sectionindex]
        left = section.getStart().get_offset()
        middle = lociter.get_offset()
        right = section.getEnd().get_offset()
        leftdist = middle - left
        rightdist = right - middle

        if (sectionindex < len(self.__sections)) and (leftdist > rightdist):
            sectionindex = sectionindex + 1
        return sectionindex

    def __get_exact_section(self, lociter):
        """
        Given any position within the buffer, this method determines which 
        section the lociter is inside.
        """
        for i in range(len(self.__sections) - 1):
            start = self.__sections[i + 1].getStart()
            if lociter.compare(start) == -1:
                return i
        return len(self.__sections) - 1

    def highlight(self, startiter, enditer):
        """
        This method highlights the text between startiter and enditer.
        """
        comparison = startiter.compare(enditer)
        if comparison == 0:
            sentence = self.get_sentence(startiter)
            self.__buf.select_range(sentence.getStart(), sentence.getEnd())
        else:
            self.__buf.select_range(startiter, enditer)

    def mark(self, lociter):
        """
        This method puts an arrow image at the start of sentence that lociter is within.
        """
        sentence = self.get_sentence(lociter)
        self.clear_arrow()
        lociter = sentence.getStart()
        self.markmark = self.__buf.create_mark(None, lociter, True)
        self.__buf.insert(lociter, " ")
        lociter = self.__buf.get_iter_at_mark(self.markmark)

    def clear_arrow(self):
        """
        This method removes the arrow image, if there is one.
        """
        if self.markmark is None:
            return
        markiter = self.__buf.get_iter_at_mark(self.markmark)
        markenditer = self.__buf.get_iter_at_offset(markiter.get_offset() + 2)
        self.__buf.delete(markiter, markenditer)
        self.__buf.delete_mark(self.markmark)
        self.markmark = None

    def get_best_sentence(self, lociter):
        """
        This method finds the closest sentence gap to lociter.

        It then returns the sentence object of the first sentence to occur after the gap.
        """
        paragraph = self.get_paragraph(lociter)
        sentence = paragraph.getBestSentence(lociter)
        return sentence

    def get_best_paragraph(self, lociter):
        """
        This method finds the closest paragraph gap to lociter.

        It then returns the paragraph object of the first paragraph to occur after the gap.
        """
        section = self.get_section(lociter)
        paragraph = section.getBestParagraph(lociter)
        return paragraph

    def get_best_section(self, lociter):
        """
        This method finds the closest section gap to lociter.

        It then returns the section object of the first section to occur after the gap.
        """
        sectionindex = self.__get_best_section(lociter)
        if sectionindex == len(self.__sections):
            return self.__sections[-1]
        else:
            return self.__sections[sectionindex]

    def get_sentence(self, lociter):
        """
        This method returns the sentence which contains lociter.
        """
        paragraph = self.get_paragraph(lociter)
        sentence = paragraph.getSentence(lociter)
        return sentence

    def get_paragraph(self, lociter):
        """
        This method returns the paragraph which contains lociter.
        """
        section = self.get_section(lociter)
        paragraph = section.getParagraph(lociter)
        return paragraph

    def get_section(self, lociter):
        """
        This method returns the section which contains lociter.
        """
        sectionindex = self.__get_exact_section(lociter)
        section = self.__sections[sectionindex]
        return section

    def __split_section(self, lociter):
        """
        This method finds the section which contains lociter.

        It then finds the closest paragraph gap to lociter.

        The section is then split into two sections, one containing all the 
        paragraphs before the gap,
        the other containing all the paragraphs after the gap.
        """
        try:
            sectionindex = self.__get_exact_section(lociter)
            section = self.__sections[sectionindex]

            source_article_id = section.source_article_id
            source_section_id = section.source_section_id

            offset = lociter.get_offset()
            section.splitParagraph(lociter)
            lociter = self.__buf.get_iter_at_offset(offset)

            firstdata = section.getDataRange(section.getStart(), lociter)
            seconddata = section.getDataRange(lociter, section.getEnd())
            mark = self.__buf.create_mark(None, lociter, False)
            if firstdata and seconddata:
                self.delete_section(lociter)

                insertioniter = self.__buf.get_iter_at_mark(mark)
                sectiondata = SectionData(
                    None, source_article_id, source_section_id, firstdata
                )
                section = Section(sectiondata, self.__buf, insertioniter)
                self.__sections.insert(sectionindex, section)

                insertioniter = self.__buf.get_iter_at_mark(mark)
                sectiondata = SectionData(
                    None, source_article_id, source_section_id, seconddata
                )
                section = Section(sectiondata, self.__buf, insertioniter)
                self.__sections.insert(sectionindex + 1, section)
        except Exception as e:
            logger.error("Error in __split_section: %s", e)

    def __pad(self):
        """
        This method adds an empty section at the end of the article.

        It is currently used in preparation for something being inserted at the end of the article.
        """
        sentencedata = SentenceData(idz=-1, text=" ")
        paragraphdata = ParagraphData(idz=-1, sentences_data=[sentencedata])
        sectiondata = SectionData(idz=-1, paragraphs_data=[paragraphdata])
        insertioniter = self.__sections[-1].getStart()
        section = Section(sectiondata, self.__buf, insertioniter)
        self.__sections.insert(-1, section)

    def __clean(self):
        """
        Removes the effects of one use of pad.

        If pad has been called more than once, then clean must be called the same number of times.
        """
        if len(self.__sections) > 2:
            section = self.__sections[-2]
            sectionisempty = section.clean()
            if sectionisempty:
                del self.__sections[-2]
