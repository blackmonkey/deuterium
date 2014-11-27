"""

EvTable

This is an advanced ASCII table creator. It was inspired
by prettytable but shares no code.

Note: to test ANSI colors on the command line you need to
call the printed table in a unicode() call, like print unicode(table).
This is due to a bug in the python interpreter and print.

Example usage:

    table = EvTable("Heading1", "Heading2", table=[[1,2,3],[4,5,6],[7,8,9]], border="cells")
    table.add_column("This is long data", "This is even longer data")
    table.add_row("This is a single row")
    print table

Result:

+----------------------+----------+---+--------------------------+
|       Heading1       | Heading2 |   |                          |
+~~~~~~~~~~~~~~~~~~~~~~+~~~~~~~~~~+~~~+~~~~~~~~~~~~~~~~~~~~~~~~~~+
|           1          |     4    | 7 |     This is long data    |
+----------------------+----------+---+--------------------------+
|           2          |     5    | 8 | This is even longer data |
+----------------------+----------+---+--------------------------+
|           3          |     6    | 9 |                          |
+----------------------+----------+---+--------------------------+
| This is a single row |          |   |                          |
+----------------------+----------+---+--------------------------+

As seen, the table will automatically expand with empty cells to make
the table symmetric.

Tables can be restricted to a given width.

table.reformat(width=50, align="l")

(We could just have added these keywords to the table creation call)

This yields the following result:

+-----------+------------+-----------+-----------+
| Heading1  | Heading2   |           |           |
+~~~~~~~~~~~+~~~~~~~~~~~~+~~~~~~~~~~~+~~~~~~~~~~~+
| 1         | 4          | 7         | This is   |
|           |            |           | long data |
+-----------+------------+-----------+-----------+
|           |            |           | This is   |
| 2         | 5          | 8         | even      |
|           |            |           | longer    |
|           |            |           | data      |
+-----------+------------+-----------+-----------+
| 3         | 6          | 9         |           |
+-----------+------------+-----------+-----------+
| This is a |            |           |           |
|  single   |            |           |           |
| row       |            |           |           |
+-----------+------------+-----------+-----------+

Table-columns can be individually formatted. Note that if an
individual column is set with a specific width, table auto-balancing
will not affect this column (this may lead to the full table being too
wide, so be careful mixing fixed-width columns with auto- balancing).
Here we change the width and alignment of the column at index 3
(Python starts from 0):

table.reformat_column(3, width=30, align="r")
print table

+-----------+-------+-----+-----------------------------+---------+
| Heading1  | Headi |     |                             |         |
|           | ng2   |     |                             |         |
+~~~~~~~~~~~+~~~~~~~+~~~~~+~~~~~~~~~~~~~~~~~~~~~~~~~~~~~+~~~~~~~~~+
| 1         | 4     | 7   |           This is long data | Test1   |
+-----------+-------+-----+-----------------------------+---------+
| 2         | 5     | 8   |    This is even longer data | Test3   |
+-----------+-------+-----+-----------------------------+---------+
| 3         | 6     | 9   |                             | Test4   |
+-----------+-------+-----+-----------------------------+---------+
| This is a |       |     |                             |         |
|  single   |       |     |                             |         |
| row       |       |     |                             |         |
+-----------+-------+-----+-----------------------------+---------+

When adding new rows/columns their data can have its own alignments
(left/center/right, top/center/bottom).

If the height is restricted, cells will be restricted from expanding
vertically. This will lead to text contents being cropped. Each cell
can only shrink to a minimum width and height of 1.

EvTable is intended to be used with ANSIString for supporting
ANSI-coloured string types.

When a cell is auto-wrapped across multiple lines, ANSI-reset
sequences will be put at the end of each wrapped line. This means that
the colour of a wrapped cell will not "bleed", but it also means that
eventual colour outside

"""
#from textwrap import wrap
from textwrap import TextWrapper
from copy import deepcopy, copy
from src.utils.utils import to_unicode
from src.utils.ansi import ANSIString

def make_iter(obj):
    "Makes sure that the object is always iterable."
    return not hasattr(obj, '__iter__') and [obj] or obj

def _to_ansi(obj):
    "convert to ANSIString"
    if hasattr(obj, "__iter__"):
        return [_to_ansi(o) for o in obj]
    else:
        return ANSIString(to_unicode(obj))


_unicode = unicode
_whitespace = '\t\n\x0b\x0c\r '
class ANSITextWrapper(TextWrapper):

    def _munge_whitespace(self, text):
        """_munge_whitespace(text : string) -> string

        Munge whitespace in text: expand tabs and convert all other
        whitespace characters to spaces.  Eg. " foo\tbar\n\nbaz"
        becomes " foo    bar  baz".
        """
        # ignore expand_tabs/replace_whitespace until ANSISTring handles them
        return text
        if self.expand_tabs:
            text = text.expandtabs()
        if self.replace_whitespace:
            if isinstance(text, str):
                text = text.translate(self.whitespace_trans)
            elif isinstance(text, _unicode):
                text = text.translate(self.unicode_whitespace_trans)
        return text


    def _split(self, text):
        """_split(text : string) -> [string]

        Split the text to wrap into indivisible chunks.  Chunks are
        not quite the same as words; see _wrap_chunks() for full
        details.  As an example, the text
          Look, goof-ball -- use the -b option!
        breaks into the following chunks:
          'Look,', ' ', 'goof-', 'ball', ' ', '--', ' ',
          'use', ' ', 'the', ' ', '-b', ' ', 'option!'
        if break_on_hyphens is True, or in:
          'Look,', ' ', 'goof-ball', ' ', '--', ' ',
          'use', ' ', 'the', ' ', '-b', ' ', option!'
        otherwise.
        """
        # only use unicode wrapper
        if self.break_on_hyphens:
            pat = self.wordsep_re_uni
        else:
            pat = self.wordsep_simple_re_uni
        chunks = pat.split(_to_ansi(text))
        chunks = filter(None, chunks)  # remove empty chunks
        return chunks

    def _wrap_chunks(self, chunks):
        """_wrap_chunks(chunks : [string]) -> [string]

        Wrap a sequence of text chunks and return a list of lines of
        length 'self.width' or less.  (If 'break_long_words' is false,
        some lines may be longer than this.)  Chunks correspond roughly
        to words and the whitespace between them: each chunk is
        indivisible (modulo 'break_long_words'), but a line break can
        come between any two chunks.  Chunks should not have internal
        whitespace; ie. a chunk is either all whitespace or a "word".
        Whitespace chunks will be removed from the beginning and end of
        lines, but apart from that whitespace is preserved.
        """
        lines = []
        if self.width <= 0:
            raise ValueError("invalid width %r (must be > 0)" % self.width)

        # Arrange in reverse order so items can be efficiently popped
        # from a stack of chucks.
        chunks.reverse()

        while chunks:

            # Start the list of chunks that will make up the current line.
            # cur_len is just the length of all the chunks in cur_line.
            cur_line = []
            cur_len = 0

            # Figure out which static string will prefix this line.
            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent

            # Maximum width for this line.
            width = self.width - len(indent)

            # First chunk on line is whitespace -- drop it, unless this
            # is the very beginning of the text (ie. no lines started yet).
            if self.drop_whitespace and chunks[-1].strip() == '' and lines:
                del chunks[-1]

            while chunks:
                l = len(chunks[-1])

                # Can at least squeeze this chunk onto the current line.
                if cur_len + l <= width:
                    cur_line.append(chunks.pop())
                    cur_len += l

                # Nope, this line is full.
                else:
                    break

            # The current line is full, and the next chunk is too big to
            # fit on *any* line (not just this one).
            if chunks and len(chunks[-1]) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)

            # If the last chunk on this line is all whitespace, drop it.
            if self.drop_whitespace and cur_line and cur_line[-1].strip() == '':
                del cur_line[-1]

            # Convert current line back to a string and store it in list
            # of all lines (return value).
            if cur_line:
                l = ""
                for w in cur_line:   # ANSI fix
                    l += w           #
                lines.append(indent + l)
        return lines


# -- Convenience interface ---------------------------------------------

def wrap(text, width=70, **kwargs):
    """Wrap a single paragraph of text, returning a list of wrapped lines.

    Reformat the single paragraph in 'text' so it fits in lines of no
    more than 'width' columns, and return a list of wrapped lines.  By
    default, tabs in 'text' are expanded with string.expandtabs(), and
    all other whitespace characters (including newline) are converted to
    space.  See TextWrapper class for available keyword args to customize
    wrapping behaviour.
    """
    w = ANSITextWrapper(width=width, **kwargs)
    return w.wrap(text)

def fill(text, width=70, **kwargs):
    """Fill a single paragraph of text, returning a new string.

    Reformat the single paragraph in 'text' to fit in lines of no more
    than 'width' columns, and return a new string containing the entire
    wrapped paragraph.  As with wrap(), tabs are expanded and other
    whitespace characters converted to space.  See TextWrapper class for
    available keyword args to customize wrapping behaviour.
    """
    w = ANSITextWrapper(width=width, **kwargs)
    return w.fill(text)

# EvCell class (see further down for the EvTable itself)

class EvCell(object):
    """
    Holds a single data cell for the table. A cell has a certain width
    and height and contains one or more lines of data. It can shrink
    and resize as needed.
    """
    def __init__(self, data, **kwargs):
        """
        data - the un-padded data of the entry.
        kwargs:
            width - desired width of cell. It will pad
                    to this size.
            height - desired height of cell. it will pad
                    to this size
            pad_width - general padding width. This can be overruled
                       by individual settings below
            pad_left - number of extra pad characters on the left
            pad_right - extra pad characters on the right
            pad_top - extra pad lines top (will pad with vpad_char)
            pad_bottom - extra pad lines bottom (will pad with vpad_char)

            pad_char - pad character to use for padding. This is overruled
                       by individual settings below (default " ")
            hpad_char - pad character to use both for extra horizontal
                      padding (default " ")
            vpad_char - pad character to use for extra vertical padding
                       and for vertical fill (default " ")

            fill_char - character used to filling (expanding cells to
                        desired size). This can be overruled by individual
                        settings below.
            hfill_char - character used for horizontal fill (default " ")
            vfill_char - character used for vertical fill (default " ")

            align - "l", "r" or  "c", default is left-aligned
            valign - "t", "b" or "c", default is centered

            border_width -general border width. This is overruled
                        - by individual settings below.
            border_left - left border width
            border_right - right border width
            border_top - top border width
            border_bottom - bottom border width

            border_char - this will use a single border char for all borders.
                          overruled by individual settings below
            border_left_char - char used for left border
            border_right_char - char used for right border
            border_top_char   - char used for top border
            border_bottom_char - char user for bottom border

            corner_char - character used when two borders cross.
                          (default is ""). This is overruled by
                          individual settings below.
            corner_top_left_char  - char used for "nw" corner
            corner_top_right_char   - char used for "nw" corner
            corner_bottom_left_char  - char used for "sw" corner
            corner_bottom_right_char - char used for "se" corner

            crop_string - string to use when cropping sideways,
                          default is '[...]'
            crop - crop content of cell rather than expand vertically,
                   default=False


            enforce_size - if true, the width/height of the
                           cell is strictly enforced and
                           extra text will be cropped rather
                           than the cell growing vertically.
        """

        padwidth = kwargs.get("pad_width", None)
        padwidth = int(padwidth) if padwidth is not None else None
        self.pad_left = int(kwargs.get("pad_left", padwidth if padwidth is not None else 1))
        self.pad_right = int(kwargs.get("pad_right", padwidth if padwidth is not None else 1))
        self.pad_top = int( kwargs.get("pad_top", padwidth if padwidth is not None else 0))
        self.pad_bottom = int(kwargs.get("pad_bottom", padwidth if padwidth is not None else 0))

        self.enforce_size = kwargs.get("enforce_size", False)

        # avoid multi-char pad_chars messing up counting
        pad_char = kwargs.get("pad_char", " ")
        pad_char = pad_char[0] if pad_char else " "
        hpad_char = kwargs.get("hpad_char", pad_char)
        self.hpad_char = hpad_char[0] if hpad_char else pad_char
        vpad_char = kwargs.get("vpad_char", pad_char)
        self.vpad_char = vpad_char[0] if vpad_char else pad_char

        fill_char = kwargs.get("fill_char", " ")
        fill_char = fill_char[0] if fill_char else " "
        hfill_char = kwargs.get("hfill_char", fill_char)
        self.hfill_char = hfill_char[0] if hfill_char else " "
        vfill_char = kwargs.get("vfill_char", fill_char)
        self.vfill_char = vfill_char[0] if vfill_char else " "

        self.crop_string = kwargs.get("crop_string", "[...]")

        # borders and corners
        borderwidth = kwargs.get("border_width", 0)
        self.border_left = kwargs.get("border_left", borderwidth)
        self.border_right = kwargs.get("border_right", borderwidth)
        self.border_top = kwargs.get("border_top", borderwidth)
        self.border_bottom = kwargs.get("border_bottom", borderwidth)

        borderchar = kwargs.get("border_char", None)
        self.border_left_char = kwargs.get("border_left_char", borderchar if borderchar else "|")
        self.border_right_char = kwargs.get("border_right_char", borderchar if borderchar else "|")
        self.border_top_char = kwargs.get("border_topchar", borderchar if borderchar else "-")
        self.border_bottom_char = kwargs.get("border_bottom_char", borderchar if borderchar else "-")

        corner_char = kwargs.get("corner_char", "+")
        self.corner_top_left_char = kwargs.get("corner_top_left_char", corner_char)
        self.corner_top_right_char = kwargs.get("corner_top_right_char", corner_char)
        self.corner_bottom_left_char = kwargs.get("corner_bottom_left_char", corner_char)
        self.corner_bottom_right_char = kwargs.get("corner_bottom_right_char", corner_char)

        # alignments
        self.align = kwargs.get("align", "l")
        self.valign = kwargs.get("valign", "c")

        #self.data = self._split_lines(unicode(data))
        self.data = self._split_lines(_to_ansi(data))
        self.raw_width = max(len(line) for line in self.data)
        self.raw_height = len(self.data)

        # width/height is given without left/right or top/bottom padding
        if "width" in kwargs:
            width = kwargs.pop("width")
            self.width = width - self.pad_left - self.pad_right - self.border_left - self.border_right
            if self.width <= 0:
                raise Exception("Cell width too small - no space for data.")
        else:
            self.width = self.raw_width
        if "height" in kwargs:
            height = kwargs.pop("height")
            self.height = height - self.pad_top - self.pad_bottom - self.border_top - self.border_bottom
            if self.height <= 0:
                raise Exception("Cell height too small - no space for data.")
        else:
            self.height = self.raw_height

        # prepare data
        self.formatted = self._reformat()

    def _crop(self, text, width):
        "Apply cropping of text"
        if len(text) > width:
            crop_string = self.crop_string
            return text[:width-len(crop_string)] + crop_string
        return text

    def _reformat(self):
        "Apply formatting"
        return self._border(self._pad(self._valign(self._align(self._fit_width(self.data)))))

    def _split_lines(self, text):
        "Simply split by linebreak"
        return text.split("\n")

    def _fit_width(self, data):
        """
        Split too-long lines to fit the desired width of the Cell.
        Note that this also updates raw_width
        """
        width = self.width
        adjusted_data = []
        for line in data:
            if 0 < width < len(line):
                # replace_whitespace=False, expand_tabs=False is a
                # fix for ANSIString not supporting expand_tabs/translate
                adjusted_data.extend([ANSIString(part + ANSIString("{n"))
                    for part in wrap(line, width=width, drop_whitespace=False)])
            else:
                adjusted_data.append(line)
        if self.enforce_size:
            # don't allow too high cells
            excess = len(adjusted_data) - self.height
            if excess > 0:
                # too many lines. Crop and mark last line with ...
                adjusted_data = adjusted_data[:-excess]
                if len(adjusted_data[-1]) > 3:
                    adjusted_data[-1] = adjusted_data[-1][:-2] + ".."
            elif excess < 0:
                # too few lines. Fill to height.
                adjusted_data.extend(["" for i in range(excess)])

        return adjusted_data

    def _center(self, text, width, pad_char):
        "Horizontally center text on line of certain width, using padding"
        excess = width - len(text)
        if excess <= 0:
            return text
        if excess % 2:
            # uneven padding
            narrowside = (excess // 2) * pad_char
            widerside = narrowside + pad_char
            if width % 2:
                return narrowside + text + widerside
            else:
                return widerside + text + narrowside
        else:
            # even padding - same on both sides
            side = (excess // 2) * pad_char
            return side + text + side

    def _align(self, data):
        "Align list of rows of cell"
        align = self.align
        if align == "l":
            return [line.ljust(self.width, self.hfill_char) for line in data]
        elif align == "r":
            return [line.rjust(self.width, self.hfill_char) for line in data]
        else:
            return [self._center(line, self.width, self.hfill_char) for line in data]

    def _valign(self, data):
        "align cell vertically"
        valign = self.valign
        height = self.height
        cheight = len(data)
        excess = height - cheight
        padline = self.vfill_char * self.width

        if excess <= 0:
            return data
        # only care if we need to add new lines
        if valign == 't':
            return data + [padline for i in range(excess)]
        elif valign == 'b':
            return [padline for i in range(excess)] + data
        else: # center
            narrowside = [padline  for i in range(excess // 2)]
            widerside = narrowside + [padline]
            if excess % 2:
                # uneven padding
                if height % 2:
                    return widerside + data + narrowside
                else:
                    return narrowside + data + widerside
            else:
                # even padding, same on both sides
                return narrowside + data + narrowside

    def _pad(self, data):
        "Pad data with extra characters on all sides"
        left = self.hpad_char * self.pad_left
        right = self.hpad_char * self.pad_right
        vfill = (self.width + self.pad_left + self.pad_right) * self.vpad_char
        top = [vfill for i in range(self.pad_top)]
        bottom = [vfill for i in range(self.pad_bottom)]
        return top + [left + line + right for line in data] + bottom

    def _border(self, data):
        "Add borders to the cell"

        left = self.border_left_char * self.border_left
        right = self.border_right_char * self.border_right

        cwidth = self.width + self.pad_left + self.pad_right + \
                 max(0,self.border_left-1) + max(0, self.border_right-1)

        vfill = self.corner_top_left_char if left else ""
        vfill += cwidth * self.border_top_char
        vfill += self.corner_top_right_char if right else ""
        top = [vfill for i in range(self.border_top)]

        vfill = self.corner_bottom_left_char if left else ""
        vfill += cwidth * self.border_bottom_char
        vfill += self.corner_bottom_right_char if right else ""
        bottom = [vfill for i in range(self.border_bottom)]

        return top + [left + line + right for line in data] + bottom

    def get_min_height(self):
        """
        Get the minimum possible height of cell, including at least
        one line for data.
        """
        return self.pad_top + self.pad_bottom + self.border_bottom + self.border_top + 1

    def get_min_width(self):
        """
        Get the minimum possible width of cell, including at least one
        character-width for data.
        """
        return self.pad_left + self.pad_right + self.border_left + self.border_right + 1

    def get_height(self):
        "Get natural height of cell, including padding"
        return len(self.formatted)

    def get_width(self):
        "Get natural width of cell, including padding"
        return len(self.formatted[0]) if self.formatted else 0

    def replace_data(self, data, **kwargs):
        """
        Replace cell data. This causes a full reformat of the cell.

        kwargs - like when creating the cell anew.
        """
        #self.data = self._split_lines(unicode(data))
        self.data = self._split_lines(_to_ansi(data))
        self.raw_width = max(len(line) for line in self.data)
        self.raw_height = len(self.data)
        self.reformat(**kwargs)

    def reformat(self, **kwargs):
        """
        Reformat the EvCell with new options
        kwargs:
            as the class __init__
        """

        # keywords that require manipulation

        padwidth = kwargs.get("pad_width", None)
        padwidth = int(padwidth) if padwidth is not None else None
        self.pad_left = int(kwargs.pop("pad_left", padwidth if padwidth is not None else self.pad_left))
        self.pad_right = int(kwargs.pop("pad_right", padwidth if padwidth is not None else self.pad_right))
        self.pad_top = int( kwargs.pop("pad_top", padwidth if padwidth is not None else self.pad_top))
        self.pad_bottom = int(kwargs.pop("pad_bottom", padwidth if padwidth is not None else self.pad_bottom))

        self.enforce_size = kwargs.get("enforce_size", False)

        pad_char = kwargs.pop("pad_char", None)
        hpad_char = kwargs.pop("hpad_char", pad_char)
        self.hpad_char = hpad_char[0] if hpad_char else self.hpad_char
        vpad_char = kwargs.pop("vpad_char", pad_char)
        self.vpad_char = vpad_char[0] if vpad_char else self.vpad_char

        fillchar = kwargs.pop("fill_char", None)
        hfill_char = kwargs.pop("hfill_char", fillchar)
        self.hfill_char = hfill_char[0] if hfill_char else self.hfill_char
        vfill_char = kwargs.pop("vfill_char", fillchar)
        self.vfill_char = vfill_char[0] if vfill_char else self.vfill_char

        borderwidth = kwargs.get("border_width", None)
        self.border_left = kwargs.pop("border_left", borderwidth if borderwidth is not None else self.border_left)
        self.border_right = kwargs.pop("border_right", borderwidth if borderwidth is not None else self.border_right)
        self.border_top = kwargs.pop("border_top", borderwidth if borderwidth is not None else self.border_top)
        self.border_bottom = kwargs.pop("border_bottom", borderwidth if borderwidth is not None else self.border_bottom)

        borderchar = kwargs.get("border_char", None)
        self.border_left_char = kwargs.pop("border_left_char", borderchar if borderchar else self.border_left_char)
        self.border_right_char = kwargs.pop("border_right_char", borderchar if borderchar else self.border_right_char)
        self.border_top_char = kwargs.pop("border_topchar", borderchar if borderchar else self.border_top_char)
        self.border_bottom_char = kwargs.pop("border_bottom_char", borderchar if borderchar else self.border_bottom_char)

        corner_char = kwargs.get("corner_char", None)
        self.corner_top_left_char = kwargs.pop("corner_top_left", corner_char if corner_char is not None else self.corner_top_left_char)
        self.corner_top_right_char = kwargs.pop("corner_top_right", corner_char if corner_char is not None else self.corner_top_right_char)
        self.corner_bottom_left_char = kwargs.pop("corner_bottom_left", corner_char if corner_char is not None else self.corner_bottom_left_char)
        self.corner_bottom_right_char = kwargs.pop("corner_bottom_right", corner_char if corner_char is not None else self.corner_bottom_right_char)

        # fill all other properties
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Handle sizes
        if "width" in kwargs:
            width = kwargs.pop("width")
            self.width = width - self.pad_left - self.pad_right - self.border_left - self.border_right
            if self.width <= 0:
                raise Exception("Cell width too small, no room for data.")
        if "height" in kwargs:
            height = kwargs.pop("height")
            self.height = height - self.pad_top - self.pad_bottom - self.border_top - self.border_bottom
            if self.height <= 0:
                raise Exception("Cell height too small, no room for data.")

        # reformat (to new sizes, padding, header and borders)
        self.formatted = self._reformat()

    def get(self):
        """
        Get data, padded and aligned in the form of a list of lines.
        """
        return self.formatted

    def __repr__(self):
        return ANSIString("EvCel<%s>" % self.formatted)

    def __str__(self):
        "returns cell contents on string form"
        return ANSIString("\n").join(self.formatted)

    def __unicode__(self):
        "returns cell contents"
        return unicode(ANSIString("\n").join(self.formatted))


## EvColumn class

class EvColumn(object):
    """
    Column class

    This class holds a list of Cells to represent a column of a table.
    It holds operations and settings that affect *all* cells in the
    column.

    Columns are not intended to be used stand-alone; they should be
    incorporated into an EvTable (like EvCells)
    """
    def __init__(self, *args,  **kwargs):
        """
        Args:
            Data for each row in the column
        Keywords:
            All EvCell keywords are available, these settings
            will be persistently applied to every Cell in the column.
        """
        self.options = kwargs  # column-specific options
        self.column = [EvCell(data, **kwargs) for data in args]
        self._balance()

    def _balance(self, **kwargs):
        """
        Make sure to adjust the width of all cells so we form a
        coherent and lined-up column. Will enforce column-specific
        options to cells.
        """
        col = self.column
        kwargs.update(self.options)
        # use fixed width or adjust to the largest cell
        kwargs["width"] = kwargs.get("width") or max(cell.get_width() for cell in col) if col else 0
        [cell.reformat(**kwargs) for cell in col]

    def add_rows(self, *args, **kwargs):
        """
        Add new cells to column. They will be inserted as
        a series of rows. It will inherit the options
        of the rest of the column's cells (use update to change
        options).

        Args:j
            data for the new cells
        Keywords:
            ypos - index position in table before which to insert the
                   new column. Uses Python indexing, so to insert at the top,
                   use ypos=0. If not given, data will be inserted at the end
                   of the column.
        """
        ypos = kwargs.get("ypos", None)
        if ypos is None or ypos > len(self.column):
            # add to the end
            self.column.extend([EvCell(data, **self.options) for data in args])
        else:
            # insert cells before given index
            ypos = min(len(self.column)-1, max(0, int(ypos)))
            new_cells = [EvCell(data, **self.options) for data in args]
            self.column = self.column[:ypos] + new_cells + self.column[ypos:]
        self._balance(**kwargs)

    def reformat(self, **kwargs):
        """
        Change the options for the collumn.
        """
        self._balance(**kwargs)

    def reformat_cell(self, index, **kwargs):
        """
        reformat cell at given index, keeping column
        options if necessary
        """
        kwargs.update(self.options)
        self.column[index].reformat(**kwargs)

    def __repr__(self):
        return "EvColumn<%i cels>" % len(self.column)
    def __len__(self):
        return len(self.column)
    def __iter__(self):
        return iter(self.column)
    def __getitem__(self, index):
        return self.column[index]
    def __setitem__(self, index, value):
        self.column[index] = value
    def __delitem__(self, index):
        del self.column[index]


## Main Evtable class

class EvTable(object):
    """
    Table class.

    The table holds a list of EvColumns, each consisting of EvCells so
    that the result is a 2D matrix.
    """

    def __init__(self, *args, **kwargs):
        """
         Args:
            headers for the table

         Keywords:
            table - list of columns (lists of lists, or lists of EvColumns) for seeding
                    the table. If not given, the table will start
                    out empty
            header - True/False - turn off header being treated
                    as a header (like extra underlining)

            pad_width - how much empty space to pad your cells with
                        (default is 1)
            border - None, or one of
                    "table" - only a border around the whole table
                    "tablecols" - table and column borders
                    "header" - only border under header
                    "cols" - only vertical borders
                    "incols" - vertical borders, no outer edges
                    "rows" - only borders between rows
                    "cells" - border around all cells
            border_width - width of table borders, if border is active.
                          Note that widths wider than 1 may give artifacts in the
                          corners. Default is 1.
            corner_char - character to use in corners when border is
                          active.
            corner_top_left_char - character to use in upper left corner of table
                                (defaults to corner_char)
            corner_top_right_char
            corner_bottom_left_char
            corner_bottom_right_char
            pretty_corners - (default True): use custom characters to make
                             the table corners look "rounded". Uses UTF-8
                             characters.

            header_line_char - characters to use for underlining
                                    the header row (default is '~')
                                    Requires border to be active.

            width - fixed width of table. If not set, width is
                    set by the total width of each column.
                    This will resize individual columns in
                    the vertical direction to fit.
            height - fixed height of table. Defaults to unset.
                     Width is still given precedence. If
                     height is given, table cells will crop
                     text rather than expand vertically.
            evenwidth - (default False). Used with the width keyword.
                     Adjusts collumns to have as even width as
                     possible. This often looks best also for
                     mixed-length tables.
            maxwidth - This will set a maximum width of the table
                    while allowing it to be smaller. Only if it
                    grows wider than this size will it be resized.
                    This has no meaning if width is set.

            See Cell class for further kwargs. These will be passed
            to each cell in the table.

        """
        # at this point table is a 2D grid - a list of columns
        # x is the column position, y the row
        table = kwargs.pop("table", [])

        # header is a list of texts. We merge it to the table's top
        header = list(args)
        self.header = header != []
        if self.header:
            if table:
                excess = len(header) - len(table)
                if excess > 0:
                    # header bigger than table
                    self.table.extend([] for i in range(excess))
                elif excess < 0:
                    # too short header
                    header.extend(_to_ansi(["" for i in range(abs(excess))]))
                for ix, heading in enumerate(header):
                    table[ix].insert(0, heading)
            else:
                table = [[heading] for heading in header]
        # even though we inserted the header, we can still turn off
        # header border underling etc. We only allow this if a header
        # was actually set
        self.header = kwargs.pop("header", self.header) if self.header else False
        hchar = kwargs.pop("header_line_char", "~")
        self.header_line_char = hchar[0] if hchar else "~"

        border = kwargs.pop("border", "tablecols")
        if border is None:
            border = "none"
        if not border in ("none", "table", "tablecols",
                          "header", "incols", "cols", "rows", "cells"):
            raise Exception("Unsupported border type: '%s'" % border)
        self.border = border

        # border settings are passed into Cell as well (so kwargs.get and not pop)
        self.border_width = kwargs.get("border_width", 1)
        self.corner_char = kwargs.get("corner_char", "+")
        pcorners = kwargs.pop("pretty_corners", False)
        self.corner_top_left_char = _to_ansi(kwargs.pop("corner_top_left_char", '.' if pcorners else  self.corner_char))
        self.corner_top_right_char = _to_ansi(kwargs.pop("corner_top_right_char", '.' if pcorners else self.corner_char))
        self.corner_bottom_left_char = _to_ansi(kwargs.pop("corner_bottom_left_char", ' ' if pcorners else self.corner_char))
        self.corner_bottom_right_char = _to_ansi(kwargs.pop("corner_bottom_right_char", ' ' if pcorners else self.corner_char))

        self.width = kwargs.pop("width", None)
        self.height = kwargs.pop("height", None)
        self.evenwidth = kwargs.pop("evenwidth", False)
        self.maxwidth = kwargs.pop("maxwidth", None)
        if self.maxwidth and self.width and self.maxwidth < self.width:
            raise Exception("table maxwidth < table width!")
        # size in cell cols/rows
        self.ncols = 0
        self.nrows = 0
        # size in characters
        self.nwidth = 0
        self.nheight = 0
        # save options
        self.options = kwargs

        # use the temporary table to generate the table on the fly, as a list of EvColumns
        self.table = [EvColumn(*col, **kwargs) for col in table]

        # this is the actual working table
        self.worktable = None

        # balance the table
        self._balance()

    def _cellborders(self, ix, iy, nx, ny, kwargs):
        """
        Adds borders to the table by adjusting the input
        kwarg to instruct cells to build a border in
        the right positions. Returns a copy of the
        kwarg to return to the cell. This is called
        by self._borders.
        """

        ret = kwargs.copy()

        def corners(ret):
            "Handle corners of table"
            if ix == 0 and iy == 0:
                ret["corner_top_left_char"] = self.corner_top_left_char
            if ix == nx and iy == 0:
                ret["corner_top_right_char"] = self.corner_top_right_char
            if ix == 0 and iy == ny:
                ret["corner_bottom_left_char"] = self.corner_bottom_left_char
            if ix == nx and iy == ny:
                ret["corner_bottom_right_char"] = self.corner_bottom_right_char
            return ret

        def left_edge(ret):
            "add vertical border along left table edge"
            if ix == 0:
                ret["border_left"] = bwidth
            return ret

        def top_edge(ret):
            "add border along top table edge"
            if iy == 0:
                ret["border_top"] = bwidth
            return ret

        def right_edge(ret):
            "add vertical border along right table edge"
            if ix == nx:# and 0 < iy < ny:
                ret["border_right"] = bwidth
            return ret

        def bottom_edge(ret):
            "add border along bottom table edge"
            if iy == ny:
                ret["border_bottom"] = bwidth
            return ret

        def cols(ret):
            "Adding vertical borders inside the table"
            if 0 <= ix < nx:
                ret["border_right"] = bwidth
            return ret

        def rows(ret):
            "Adding horizontal borders inside the table"
            if 0 <= iy < ny:
                ret["border_bottom"] = bwidth
            return ret

        def head(ret):
            "Add header underline"
            if iy == 0:
                # put different bottom line for header
                ret["border_bottom"] = bwidth
                ret["border_bottom_char"] = headchar
            return ret


        # handle the various border modes
        border = self.border
        header = self.header

        bwidth = self.border_width
        headchar = self.header_line_char

        # use the helper functions to define various
        # table "styles"

        if border in ("table", "tablecols","cells"):
            ret = bottom_edge(right_edge(top_edge(left_edge(corners(ret)))))
        if border in ("cols", "tablecols", "cells"):
            ret = cols(right_edge(left_edge(ret)))
        if border in ("incols"):
            ret = cols(ret)
        if border in ("rows", "cells"):
            ret = rows(bottom_edge(top_edge(ret)))
        if header and not border in ("none", None):
            ret = head(ret)

        return ret

    def _borders(self):
        """
        Add borders to table. This is called from self._balance
        """
        nx, ny = self.ncols-1, self.nrows-1
        options = self.options
        for ix, col in enumerate(self.worktable):
            for iy, cell in enumerate(col):
                col.reformat_cell(iy, **self._cellborders(ix,iy,nx,ny,options))

    def _balance(self):
        """
        Balance the table. This means to make sure
        all cells on the same row have the same height,
        that all columns have the same number of rows
        and that the table fits within the given width.
        """

        # we make all modifications on a working copy of the
        # actual table. This allows us to add columns/rows
        # and re-balance over and over without issue.
        self.worktable = deepcopy(self.table)
        options = copy(self.options)

        # balance number of rows to make a rectangular table
        ncols = len(self.worktable)
        nrows = [len(col) for col in self.worktable]
        nrowmax = max(nrows) if nrows else 0
        for icol, nrow in enumerate(nrows):
            if nrow < nrowmax:
                # add more rows to too-short columns
                empty_rows = ["" for i in range(nrowmax-nrow)]
                self.worktable[icol].add_rows(*empty_rows)
        self.ncols = ncols
        self.nrows = nrowmax

        # add borders - these add to the width/height, so we must do this before calculating width/height
        self._borders()

        # equalize widths within each column
        cwidths = [max(cell.get_width() for cell in col) for col in self.worktable]

        if self.width or self.maxwidth and self.maxwidth < sum(cwidths):
            # we set a table width. Horizontal cells will be evenly distributed and
            # expand vertically as needed (unless self.height is set, see below)

            # use fixed width, or set to maxwidth
            width = self.width if self.width else self.maxwidth

            if ncols:
                # get minimum possible cell widths for each row
                cwidths_min = [max(cell.get_min_width() for cell in col) for col in self.worktable]
                cwmin = sum(cwidths_min)

                if cwmin > width:
                    # we cannot shrink any more
                    raise Exception("Cannot shrink table width to %s. Minimum size is %s." % (self.width, cwmin))

                excess = width - cwmin
                if self.evenwidth:
                    # make each collumn of equal width
                    for i in range(excess):
                        # flood-fill the minimum table starting with the smallest collumns
                        ci = cwidths_min.index(min(cwidths_min))
                        cwidths_min[ci] += 1
                    cwidths = cwidths_min
                else:
                    # make each collumn expand more proportional to their data size
                    for i in range(excess):
                        # fill wider collumns first
                        ci = cwidths.index(max(cwidths))
                        cwidths_min[ci] += 1
                        cwidths[ci] -= 3
                    cwidths = cwidths_min

        # reformat worktable (for width align)
        for ix, col in enumerate(self.worktable):
            try:
                col.reformat(width=cwidths[ix], **options)
            except Exception, e:
                msg = "ix=%s, width=%s: %s" % (ix, cwidths[ix], e.message)
                raise #Exception ("Error in horizontal allign:\n %s" % msg)

        # equalize heights for each row (we must do this here, since it may have changed to fit new widths)
        cheights = [max(cell.get_height() for cell in (col[iy] for col in self.worktable)) for iy in range(nrowmax)]

        if self.height:
            # if we are fixing the table height, it means cells must crop text instead of resizing.
            if nrowmax:

                # get minimum possible cell heights for each collumn
                cheights_min = [max(cell.get_min_height() for cell in (col[iy] for col in self.worktable)) for iy in range(nrowmax)]
                chmin = sum(cheights_min)
                #print "cheights_min:", cheights_min

                if chmin > self.height:
                    # we cannot shrink any more
                    raise Exception("Cannot shrink table height to %s. Minimum size is %s." % (self.height, chmin))

                # now we add all the extra height up to the desired table-height.
                # We do this so that the tallest cells gets expanded first (and
                # thus avoid getting cropped)

                excess = self.height - chmin
                even = self.height % 2 == 0
                for i in range(excess):
                    # expand the cells with the most rows first
                    if 0 <= i < nrowmax and nrowmax > 1:
                        # avoid adding to header first round (looks bad on very small tables)
                        ci = cheights[1:].index(max(cheights[1:])) + 1
                    else:
                        ci = cheights.index(max(cheights))
                    cheights_min[ci] += 1
                    if ci == 0 and self.header:
                        # it doesn't look very good if header expands too fast
                        cheights[ci] -= 2 if even else 3
                    cheights[ci] -= 2 if even else 1
                cheights = cheights_min

                # we must tell cells to crop instead of expanding
            options["enforce_size"] = True
        #print "cheights2:", cheights

        # reformat table (for vertical align)
        for ix, col in enumerate(self.worktable):
            for iy, cell in enumerate(col):
                try:
                    col.reformat_cell(iy, height=cheights[iy], **options)
                except Exception, e:
                    msg = "ix=%s, iy=%s, height=%s: %s" % (ix, iy, cheights[iy], e.message)
                    raise Exception ("Error in vertical allign:\n %s" % msg)

        # calculate actual table width/height in characters
        self.cwidth = sum(cwidths)
        self.cheight = sum(cheights)
        #print "actual table width, height:", self.cwidth, self.cheight, self.width, self.height

    def _generate_lines(self):
        """
        Generates lines across all columns
        (each cell may contain multiple lines)
        Before calling, the table must be
        balanced.
        """
        for iy in range(self.nrows):
            cell_row = [col[iy] for col in self.worktable]
            # this produces a list of lists, each of equal length
            cell_data = [cell.get() for cell in cell_row]
            cell_height = min(len(lines) for lines in cell_data)
            for iline in range(cell_height):
                yield ANSIString("").join(_to_ansi(celldata[iline] for celldata in cell_data))

    def add_header(self, *args, **kwargs):
        """
        Add header to table. This is a number of texts to
        be put at the top of the table. They will replace
        an existing header.
        """
        self.header = True
        self.add_row(ypos=0, *args, **kwargs)

    def add_column(self, *args, **kwargs):
        """
        Add a column to table. If there are more
        rows in new column than there are rows in the
        current table, the table will expand with
        empty rows in the other columns. If too few,
        the new column with get new empty rows. All
        filling rows are added to the end.
        Args:
            Either a single EvColumn instance or
            a number of data to be used to create a new column
        keyword-
            header - the header text for the column
            xpos - index position in table before which
                   to input new column. If not given,
                   column will be added to the end. Uses
                   Python indexing (so first column is xpos=0)
        See Cell class for other keyword arguments
        """
        # this will replace default options with new ones without changing default
        options = dict(self.options.items() + kwargs.items())

        xpos = kwargs.get("xpos", None)
        column = EvColumn(*args, **options)
        htable = self.nrows
        excess = self.ncols - htable

        if excess > 0:
            # we need to add new rows to table
            for col in self.table:
                empty_rows = ["" for i in range(excess)]
                col.add_rows(*empty_rows, **options)
        elif excess < 0:
            # we need to add new rows to new column
            empty_rows = ["" for i in range(abs(excess))]
            column.add_rows(*empty_rows, **options)

        header = kwargs.get("header", None)
        if header:
            column.add_rows(unicode(header), ypos=0, **options)
            self.header = True
        elif self.header:
            # we have a header already. Offset
            column.add_rows("", ypos=0, **options)
        if xpos is None or xpos > len(self.table) - 1:
            # add to the end
            self.table.append(column)
        else:
            # insert column
            xpos = min(len(self.table)-1, max(0, int(xpos)))
            self.table.insert(xpos, column)
        self._balance()

    def add_row(self, *args, **kwargs):
        """
        Add a row to table (not a header). If there are
        more cells in the given row than there are cells
        in the current table the table will be expanded
        with empty columns to match. These will be added
        to the end of the table. In the same way, adding
        a line with too few cells will lead to the last
        ones getting padded.
        keyword
          ypos - index position in table before which to
                 input new row. If not given, will be added
                 to the end. Uses Python indexing (so first row is
                 ypos=0)
        See EvCell class for other keyword arguments
        """
        # this will replace default options with new ones without changing default
        row = list(args)
        options = dict(self.options.items() + kwargs.items())

        ypos = kwargs.get("ypos", None)
        htable = len(self.table[0]) if len(self.table)>0 else 0 # assuming balanced table
        excess = len(row) - len(self.table)

        if excess > 0:
            # we need to add new empty columns to table
            empty_rows = ["" for i in range(htable)]
            self.table.extend([EvColumn(*empty_rows, **options) for i in range(excess)])
        elif excess < 0:
            # we need to add more cells to row
            row.extend(["" for i in range(abs(excess))])

        if ypos is None or ypos > htable - 1:
            # add new row to the end
            for icol, col in enumerate(self.table):
                col.add_rows(row[icol], **options)
        else:
            # insert row elsewhere
            ypos = min(htable-1, max(0, int(ypos)))
            for icol, col in enumerate(self.table):
                col.add_rows(row[icol], ypos=ypos, **options)
        self._balance()

    def reformat(self, **kwargs):
        """
        Force a re-shape of the entire table
        """
        self.width = kwargs.pop("width", self.width)
        self.height = kwargs.pop("height", self.height)
        for key, value in kwargs.items():
            setattr(self, key, value)

        hchar = kwargs.pop("header_line_char", self.header_line_char)

        # border settings are also passed on into EvCells (so kwargs.get, not kwargs.pop)
        self.header_line_char = hchar[0] if hchar else self.header_line_char
        self.border_width = kwargs.get("border_width", self.border_width)
        self.corner_char = kwargs.get("corner_char", self.corner_char)
        self.header_line_char = kwargs.get("header_line_char", self.header_line_char)

        self.corner_top_left_char = _to_ansi(kwargs.pop("corner_top_left_char", self.corner_char))
        self.corner_top_right_char = _to_ansi(kwargs.pop("corner_top_right_char", self.corner_char))
        self.corner_bottom_left_char = _to_ansi(kwargs.pop("corner_bottom_left_char", self.corner_char))
        self.corner_bottom_right_char = _to_ansi(kwargs.pop("corner_bottom_right_char", self.corner_char))

        self.options.update(kwargs)
        self._balance()

    def reformat_column(self, index, **kwargs):
        """
        Sends custom options to a specific column in the table. The column
        is identified by its index in the table (0-Ncol)
        """
        if index > len(self.table):
            raise Exception("Not a valid column index")
        self.table[index].options.update(kwargs)
        self.table[index].reformat(**kwargs)
        self._balance()

    def get(self):
        """
        Return lines of table as a list
        """
        return [line for line in self._generate_lines()]

    def __str__(self):
        "print table"
        return  ANSIString("\n").join([line for line in self._generate_lines()])

    def __unicode__(self):
        return  unicode(ANSIString("\n").join([line for line in self._generate_lines()]))

def _test():
    "Test"
    table = EvTable("{yHeading1{n", "{gHeading2{n", table=[[1,2,3],[4,5,6],[7,8,9]], border="cells", align="l")
    table.add_column("{rThis is long data{n", "{bThis is even longer data{n")
    table.add_row("This is a single row")
    print unicode(table)
    table.reformat(width=50)
    print unicode(table)
    table.reformat_column(3, width=30, align='r')
    print unicode(table)
    return table


