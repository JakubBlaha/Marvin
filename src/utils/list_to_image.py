from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont

FONT_DIR = 'res/fnt/'
IMAGE_SIZE = (1000, 3000)


class FontMap:
    _data: list
    _fonts: list = []

    def __init__(self, width, height, default_font: ImageFont.FreeTypeFont):
        # Add default font
        self._fonts.append(default_font)

        # Make list
        self._data = [[0 for _ in range(width)] for _ in range(height)]

    def set_at(self, x, y, font: ImageFont.FreeTypeFont):
        try:
            # Get cached font index
            _font_index = self._fonts.index(font)
        except ValueError:
            # Add new font
            self._fonts.append(font)
            _font_index = len(self._fonts) - 1

        # Set the font
        self._data[y][x] = _font_index

    def get_at(self, x, y):
        return self._fonts[self._data[y][x]]

    def _recycle_fonts(self):
        pass
        # TODO


def get_font(filename: str, size: int = 24) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_DIR + filename, size=size)


class ListToImageBuilder:
    # Basic attrs
    data = []
    v_space = 24
    h_space = 32
    chunk_size = 8
    footer = ''
    font_map: FontMap = None
    background_color = (47, 49, 54, 255)

    # Font attrs
    _fnt_header = get_font('uni-sans.heavy-caps.otf')
    _fnt_body = get_font('Roboto-Medium.ttf')
    _fnt_footer = get_font('Roboto-Italic.ttf')

    # Other attrs
    _width = 0
    _height = 0
    _col_sizes = []
    _row_sizes = []
    _draw: ImageDraw.Draw = None
    _img: Image.Image = None

    def __init__(self,
                 data: list,
                 v_space: int = None,
                 h_space: int = None,
                 chunk_size: int = None,
                 footer: str = None,
                 font_map: FontMap = None,
                 font_header: FreeTypeFont = None,
                 font_body: FreeTypeFont = None,
                 font_footer: FreeTypeFont = None,
                 background_color: tuple = None):
        # Set attributes
        self.data = data
        self.v_space = v_space or self.v_space
        self.h_space = h_space or self.h_space
        self.chunk_size = chunk_size or self.chunk_size
        self.footer = footer or self.footer
        self.background_color = background_color or self.background_color

        # Fonts
        self._fnt_header = font_header or self._fnt_header
        self._fnt_body = font_body or self._fnt_body
        self._fnt_footer = font_footer or self._fnt_footer

        # Image, draw
        self._reset_image()

        # Other
        self._width = len(data[0])
        self._height = len(data)
        self.font_map = font_map or FontMap(self._width, self._height,
                                            self._fnt_body)

        self.recalc_sizes()

    def _reset_image(self):
        # Internal use
        self._img = Image.new('RGBA', IMAGE_SIZE, (0, 0, 0, 0))
        self._draw = ImageDraw.Draw(self._img)

    def recalc_sizes(self):
        """ Recalculate row heights and column widths. """
        # Reset sizes
        self._col_sizes = [0] * self._width
        self._row_sizes = [0] * self._height

        # Loop rows
        for ri in range(self._height):
            # Loop cells/cols
            for ci in range(self._width):
                # Get text size
                _w, _h = self._draw.textsize(self.data[ri][ci],
                                             self.font_map.get_at(ci, ri))
                _w += self.h_space
                _h += self.v_space

                # Override
                self._row_sizes[ri] = max(self._row_sizes[ri], _h)
                self._col_sizes[ci] = max(self._col_sizes[ci], _w)

    def set_header(self, font: ImageFont.FreeTypeFont = None, row=0):
        """ Sets the header. """
        font = font or self._fnt_header
        for i in range(0, self._width):
            self.font_map.set_at(i, row, font)

    def generate(self):
        """ Generator yielding images from the data. """
        # Total image width
        _total_img_width = sum(self._col_sizes) + self.h_space

        # Draw parts
        for chi, chunk in enumerate(self.get_chunks()):
            # Make chunk image
            for ri, row in enumerate(chunk):
                # Calculate position
                y = sum(self._row_sizes[:ri]) + self.v_space

                # Absolute row index
                abs_ri = chi * self.chunk_size + ri

                # Draw background
                if abs_ri % 2:
                    _rect_y = y - self.v_space // 2 + 1
                    _rect_h = self._row_sizes[abs_ri]
                    self._draw.rectangle(
                        (0, _rect_y, _total_img_width, _rect_y + _rect_h),
                        self.background_color, (0, 0, 0, 0))

                for ci, col in enumerate(row):
                    # Calculate position
                    x = sum(self._col_sizes[:ci]) + self.h_space

                    # Draw text
                    self._draw.text((x, y),
                                    col,
                                    font=self.font_map.get_at(ci, abs_ri))

            # Crop the image
            l, t, r, b = self._img.getbbox()
            self._img = self._img.crop((0, t, _total_img_width, b))

            # Yield chunk image
            yield self._img
            self._reset_image()

        # Footer
        if not self.footer:
            return

        self._draw.line((0, 0, _total_img_width, 0))
        self._draw.text((self.h_space, self.v_space),
                        self.footer,
                        font=self._fnt_footer)
        self._img = self._img.crop(
            (0, 0, _total_img_width, self._img.getbbox()[3]))
        yield self._img
        self._reset_image()

    def get_chunks(self):
        return [
            self.data[i:i + self.chunk_size]
            for i in range(0, self._height, self.chunk_size)
        ]
