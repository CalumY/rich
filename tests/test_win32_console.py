import dataclasses
import sys
from io import StringIO
from unittest import mock
from unittest.mock import call, patch

import pytest

import rich
from rich.style import Style

try:
    from rich._win32_console import COORD, LegacyWindowsTerm, WindowsCoordinates

    CURSOR_X = 1
    CURSOR_Y = 2
    CURSOR_POSITION = WindowsCoordinates(row=CURSOR_Y, col=CURSOR_X)
    SCREEN_WIDTH = 20
    SCREEN_HEIGHT = 30
    DEFAULT_STYLE_ATTRIBUTE = 16

    @dataclasses.dataclass
    class StubScreenBufferInfo:
        dwCursorPosition: COORD = COORD(CURSOR_X, CURSOR_Y)
        dwSize: COORD = COORD(SCREEN_WIDTH, SCREEN_HEIGHT)
        wAttributes: int = DEFAULT_STYLE_ATTRIBUTE

except ImportError:
    pass

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="windows only")


def test_windows_coordinates_to_ctype():
    coord = WindowsCoordinates.from_param(WindowsCoordinates(row=1, col=2))
    assert coord.X == 2
    assert coord.Y == 1


@pytest.fixture
def win32_handle():
    handle = mock.sentinel
    with mock.patch.object(rich._win32_console, "GetStdHandle", return_value=handle):
        yield handle


@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_cursor_position(_):
    term = LegacyWindowsTerm()
    assert term.cursor_position == WindowsCoordinates(row=CURSOR_Y, col=CURSOR_X)


@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_screen_size(_):
    term = LegacyWindowsTerm()
    assert term.screen_size == WindowsCoordinates(row=SCREEN_HEIGHT, col=SCREEN_WIDTH)


@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_write_text(_):
    f = StringIO()
    text = "Hello, world!"
    term = LegacyWindowsTerm(file=f)

    term.write_text(text)

    assert f.getvalue() == text


@patch.object(rich._win32_console, "SetConsoleTextAttribute")
@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_write_styled(_, SetConsoleTextAttribute, win32_handle):
    f = StringIO()
    style = Style.parse("black on red")
    text = "Hello, world!"
    term = LegacyWindowsTerm(file=f)

    term.write_styled(text, style)

    call_args = SetConsoleTextAttribute.call_args_list

    assert f.getvalue() == text
    # Ensure we set the text attributes and then reset them after writing styled text
    assert call_args[0].args == (win32_handle,)
    assert call_args[0].kwargs["attributes"].value == 64
    assert call_args[1] == call(win32_handle, attributes=DEFAULT_STYLE_ATTRIBUTE)


@patch.object(rich._win32_console, "FillConsoleOutputCharacter", return_value=None)
@patch.object(rich._win32_console, "FillConsoleOutputAttribute", return_value=None)
@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_erase_line(
    _, FillConsoleOutputAttribute, FillConsoleOutputCharacter, win32_handle
):
    term = LegacyWindowsTerm()
    term.erase_line()
    start = WindowsCoordinates(row=CURSOR_Y, col=0)
    FillConsoleOutputCharacter.assert_called_once_with(
        win32_handle, " ", length=SCREEN_WIDTH, start=start
    )
    FillConsoleOutputAttribute.assert_called_once_with(
        win32_handle, DEFAULT_STYLE_ATTRIBUTE, length=SCREEN_WIDTH, start=start
    )


@patch.object(rich._win32_console, "FillConsoleOutputCharacter", return_value=None)
@patch.object(rich._win32_console, "FillConsoleOutputAttribute", return_value=None)
@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_erase_end_of_line(
    _, FillConsoleOutputAttribute, FillConsoleOutputCharacter, win32_handle
):
    term = LegacyWindowsTerm()
    term.erase_end_of_line()

    FillConsoleOutputCharacter.assert_called_once_with(
        win32_handle, " ", length=SCREEN_WIDTH - CURSOR_X, start=CURSOR_POSITION
    )
    FillConsoleOutputAttribute.assert_called_once_with(
        win32_handle,
        DEFAULT_STYLE_ATTRIBUTE,
        length=SCREEN_WIDTH - CURSOR_X,
        start=CURSOR_POSITION,
    )


@patch.object(rich._win32_console, "FillConsoleOutputCharacter", return_value=None)
@patch.object(rich._win32_console, "FillConsoleOutputAttribute", return_value=None)
@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_erase_start_of_line(
    _, FillConsoleOutputAttribute, FillConsoleOutputCharacter, win32_handle
):
    term = LegacyWindowsTerm()
    term.erase_start_of_line()

    start = WindowsCoordinates(CURSOR_Y, 0)

    FillConsoleOutputCharacter.assert_called_once_with(
        win32_handle, " ", length=CURSOR_X, start=start
    )
    FillConsoleOutputAttribute.assert_called_once_with(
        win32_handle, DEFAULT_STYLE_ATTRIBUTE, length=CURSOR_X, start=start
    )


@patch.object(rich._win32_console, "SetConsoleCursorPosition", return_value=None)
@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_move_cursor_to(_, SetConsoleCursorPosition, win32_handle):
    coords = WindowsCoordinates(row=4, col=5)
    term = LegacyWindowsTerm()

    term.move_cursor_to(coords)

    SetConsoleCursorPosition.assert_called_once_with(win32_handle, coords=coords)


@patch.object(rich._win32_console, "SetConsoleCursorPosition", return_value=None)
@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_move_cursor_to_out_of_bounds_row(_, SetConsoleCursorPosition, win32_handle):
    coords = WindowsCoordinates(row=-1, col=4)
    term = LegacyWindowsTerm()

    term.move_cursor_to(coords)

    assert not SetConsoleCursorPosition.called


@patch.object(rich._win32_console, "SetConsoleCursorPosition", return_value=None)
@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_move_cursor_to_out_of_bounds_col(_, SetConsoleCursorPosition, win32_handle):
    coords = WindowsCoordinates(row=10, col=-4)
    term = LegacyWindowsTerm()

    term.move_cursor_to(coords)

    assert not SetConsoleCursorPosition.called


@patch.object(rich._win32_console, "SetConsoleCursorPosition", return_value=None)
@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_move_cursor_up(_, SetConsoleCursorPosition, win32_handle):
    term = LegacyWindowsTerm()

    term.move_cursor_up()

    SetConsoleCursorPosition.assert_called_once_with(
        win32_handle, coords=WindowsCoordinates(row=CURSOR_Y - 1, col=CURSOR_X)
    )


@patch.object(rich._win32_console, "SetConsoleCursorPosition", return_value=None)
@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_move_cursor_down(_, SetConsoleCursorPosition, win32_handle):
    term = LegacyWindowsTerm()

    term.move_cursor_down()

    SetConsoleCursorPosition.assert_called_once_with(
        win32_handle, coords=WindowsCoordinates(row=CURSOR_Y + 1, col=CURSOR_X)
    )


@patch.object(rich._win32_console, "SetConsoleCursorPosition", return_value=None)
@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_move_cursor_forward(_, SetConsoleCursorPosition, win32_handle):
    term = LegacyWindowsTerm()

    term.move_cursor_forward()

    SetConsoleCursorPosition.assert_called_once_with(
        win32_handle, coords=WindowsCoordinates(row=CURSOR_Y, col=CURSOR_X + 1)
    )


@patch.object(rich._win32_console, "SetConsoleCursorPosition", return_value=None)
def test_move_cursor_forward_newline_wrap(SetConsoleCursorPosition, win32_handle):
    cursor_at_end_of_line = StubScreenBufferInfo(
        dwCursorPosition=COORD(SCREEN_WIDTH - 1, CURSOR_Y)
    )
    with patch.object(
        rich._win32_console,
        "GetConsoleScreenBufferInfo",
        return_value=cursor_at_end_of_line,
    ):
        term = LegacyWindowsTerm()
        term.move_cursor_forward()

    SetConsoleCursorPosition.assert_called_once_with(
        win32_handle, coords=WindowsCoordinates(row=CURSOR_Y + 1, col=0)
    )


@patch.object(rich._win32_console, "SetConsoleCursorPosition", return_value=None)
@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_move_cursor_to_column(_, SetConsoleCursorPosition, win32_handle):
    term = LegacyWindowsTerm()
    term.move_cursor_to_column(5)
    SetConsoleCursorPosition.assert_called_once_with(
        win32_handle, coords=WindowsCoordinates(CURSOR_Y, 5)
    )


@patch.object(rich._win32_console, "SetConsoleCursorPosition", return_value=None)
@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_move_cursor_backward(_, SetConsoleCursorPosition, win32_handle):
    term = LegacyWindowsTerm()
    term.move_cursor_backward()
    SetConsoleCursorPosition.assert_called_once_with(
        win32_handle, coords=WindowsCoordinates(row=CURSOR_Y, col=CURSOR_X - 1)
    )


@patch.object(rich._win32_console, "SetConsoleCursorPosition", return_value=None)
def test_move_cursor_backward_prev_line_wrap(SetConsoleCursorPosition, win32_handle):
    cursor_at_start_of_line = StubScreenBufferInfo(dwCursorPosition=COORD(0, CURSOR_Y))
    with patch.object(
        rich._win32_console,
        "GetConsoleScreenBufferInfo",
        return_value=cursor_at_start_of_line,
    ):
        term = LegacyWindowsTerm()
        term.move_cursor_backward()
    SetConsoleCursorPosition.assert_called_once_with(
        win32_handle, coords=WindowsCoordinates(row=CURSOR_Y - 1, col=SCREEN_WIDTH - 1)
    )


@patch.object(rich._win32_console, "SetConsoleCursorInfo", return_value=None)
@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_hide_cursor(_, SetConsoleCursorInfo, win32_handle):
    term = LegacyWindowsTerm()
    term.hide_cursor()

    call_args = SetConsoleCursorInfo.call_args_list

    assert len(call_args) == 1
    assert call_args[0].kwargs["cursor_info"].bVisible == 0
    assert call_args[0].kwargs["cursor_info"].dwSize == 100


@patch.object(rich._win32_console, "SetConsoleCursorInfo", return_value=None)
@patch.object(
    rich._win32_console, "GetConsoleScreenBufferInfo", return_value=StubScreenBufferInfo
)
def test_show_cursor(_, SetConsoleCursorInfo, win32_handle):
    term = LegacyWindowsTerm()
    term.show_cursor()

    call_args = SetConsoleCursorInfo.call_args_list

    assert len(call_args) == 1
    assert call_args[0].kwargs["cursor_info"].bVisible == 1
    assert call_args[0].kwargs["cursor_info"].dwSize == 100


@patch.object(rich._win32_console, "SetConsoleTitle", return_value=None)
def test_set_title(SetConsoleTitle):
    term = LegacyWindowsTerm()
    term.set_title("title")

    SetConsoleTitle.assert_called_once_with("title")


@patch.object(rich._win32_console, "SetConsoleTitle", return_value=None)
def test_set_title_too_long(_):
    term = LegacyWindowsTerm()

    with pytest.raises(AssertionError):
        term.set_title("a" * 255)
