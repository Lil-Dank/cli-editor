"""
Code browser example.

Run with:

    python code_browser.py PATH
"""

import sys
import json
import os

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.reactive import var
from textual.widgets import DirectoryTree, Footer, Header, TextArea
from textual.binding import Binding


with open(
    os.path.join(
        os.path.realpath(os.path.dirname(__file__)),
        'filetypes_syntax.json'
    )
) as json_file:
    FILETYPES_SYNTAX = json.loads(json_file.read())


def get_syntax_for_file(path) -> str | None:
    file_extension = str(path).replace('\\', '/').split('/')[-1].split('.')[-1]
    if file_extension in FILETYPES_SYNTAX.keys():
        return FILETYPES_SYNTAX[file_extension]
    return None



class ExtendedTextArea(TextArea):
    """A custom subclass of TextArea with extended functionality."""

    previous_character = ''

    BINDINGS = [
        Binding("ctrl+end", "goto_end", "go to end", show = False),
        Binding("ctrl+home", "goto_start", "go to start", show = False),
        Binding("ctrl+j", "add_newline_below", show = False),
        Binding("ctrl+e", "add_newline_above", show = False, priority=True),
    ]


    def _on_key(self, event: events.Key) -> None:
        if event.character == "(":
            self.insert("()")
            self.move_cursor_relative(columns=-1)
            event.prevent_default()
        
        if event.character == "{":
            self.insert("{}")
            self.move_cursor_relative(columns=-1)
            event.prevent_default()
        
        if event.character == "[":
            self.insert("[]")
            self.move_cursor_relative(columns=-1)
            event.prevent_default()

        if not event.is_printable:
            if event.name == 'down' and self.previous_character == 'escape':
                event.prevent_default()
                self.action_move_line_down()
            elif event.name == 'up' and self.previous_character == 'escape':
                event.prevent_default()
                self.action_move_line_up()
            elif event.name == 'backspace' and self.previous_character == 'ctrl_@':
                event.prevent_default()
                self.action_delete_word_left()
            elif event.name == 'ctrl_delete':
                event.prevent_default()
                self.action_delete_word_right()
            elif event.name == 'ctrl_underscore':
                event.prevent_default()
                self.action_comment_lines()
            else:
                self.previous_character = event.name


    def action_goto_end(self):
        self.move_cursor_relative(rows=self.document.line_count)
        self.move_cursor_relative(columns=self.document.line_count*100)


    def action_goto_start(self):
        self.move_cursor_relative(rows=-self.document.line_count)
        self.move_cursor_relative(columns=-self.document.line_count*100)


    def action_move_line_down(self):
        if self.selection.is_empty:
            row1, col1 = self.get_cursor_line_end_location()
            if not row1 + 1 > self.document.line_count:
                line_to_move_down = self.get_text_range((row1,0), (row1, col1))
                
                self.move_cursor_relative(rows=1)

                row2, col2 = self.get_cursor_line_end_location()
                line_to_move_up = self.get_text_range((row2,0), (row2, col2))

                self.replace('', (row1, 0), (row1, col1))
                self.insert(line_to_move_up, (row1, 0))
                self.replace('', (row2, 0), (row2, col2))
                self.insert(line_to_move_down, (row2, 0))
        else:
            row1, start = self.selection.start
            row2, end = self.selection.end
            
            if not row2 + 2 > self.document.line_count:
                lines_to_move_down = self.get_text_range((row1,0), (row2, end*100))
                line_to_move_up = self.get_text_range((row2+1,0), (row2+1, end*100))

                self.replace('', (row1, 0), (row2+1, end*100))
                self.insert(line_to_move_up + '\n', (row1, 0))
                self.insert(lines_to_move_down, (row1+1, 0))
                self.move_cursor((row1+1, start))
                self.move_cursor((row2+1, end), select=True)


    def action_move_line_up(self):
        if self.selection.is_empty:
            row1, col1 = self.get_cursor_line_end_location()
            
            if not row1 - 1 < 0:
                line_to_move_up = self.get_text_range((row1,0), (row1, col1))

                self.move_cursor_relative(rows=-1)

                row2, col2 = self.get_cursor_line_end_location()
                line_to_move_down = self.get_text_range((row2,0), (row2, col2))

                self.replace('', (row1, 0), (row1, col1))
                self.insert(line_to_move_down, (row1, 0))
                self.replace('', (row2, 0), (row2, col2))
                self.insert(line_to_move_up, (row2, 0))
        else:
            row1, start = self.selection.start
            if not row1 - 1 < 0:
                row2, end = self.selection.end

                lines_to_move_up = self.get_text_range((row1,0), (row2, end*100))
                line_to_move_down = self.get_text_range((row1-1,0), (row1-1, end*100))

                self.replace('', (row1-1, 0), (row2, end*100))
                self.insert(lines_to_move_up, (row1-1, 0))
                self.insert(line_to_move_down + '\n', (row2, 0))
                self.move_cursor((row1-1, start))
                self.move_cursor((row2-1, end), select=True)


    def action_add_newline_below(self):
        self.action_cursor_line_end()
        self.insert('\n')


    def action_add_newline_above(self):
        self.action_cursor_line_start
        self.insert('\n')
        self.move_cursor_relative(rows=-1)


    def action_comment_lines(self):
        comment_symbol = ''

        if self.language == 'python' or self.language == 'yaml':
            comment_symbol = '#'
        
        if self.selection.is_empty:
            row1 = self.get_cursor_line_end_location()[0]
            first_symbol = self.get_text_range((row1,0), (row1,1))

            if comment_symbol != '' and first_symbol != comment_symbol:
                self.insert(comment_symbol + ' ', (row1, 0))
            
            elif first_symbol == comment_symbol:
                self.replace('', (row1, 0), (row1, 2))
        
        else:
            row1 = self.selection.start[0]
            row2 = self.selection.end[0]

            for i in range(row1, row2+1):
                first_symbol = self.get_text_range((i,0), (i,1))

                if comment_symbol != '' and first_symbol != comment_symbol:
                    self.insert(comment_symbol + ' ', (i, 0))
                
                elif first_symbol == comment_symbol:
                    self.replace('', (i, 0), (i, 2))



class ExtendedDirectoryTree(DirectoryTree):
    """A subclass of TextArea with parenthesis-closing functionality."""

    BINDINGS = [
        Binding("left", "closedir", "Close dir"),
        Binding("right", "opendir", "Expand dir"),
    ]

    FILTER_LIST = [
        '.git',
        '.vscode'
    ]


    def on_mount(self) -> None:
        self.show_root = False


    def filter_paths(self, paths):
        return [path for path in paths if path.name not in self.FILTER_LIST]


    def action_closedir(self):
        if not self.cursor_node.is_root: # type: ignore
            if (self.cursor_node.parent.is_expanded and # type: ignore
                not self.cursor_node.parent.is_root): # type: ignore
                self.select_node(self.cursor_node.parent) # type: ignore
                self.cursor_node.collapse() # type: ignore


    def action_opendir(self):
        if self.cursor_node.allow_expand: # type: ignore
            self.cursor_node.expand() # type: ignore


    async def on_tree_node_expanded(self, event: DirectoryTree.NodeExpanded):
        if event.node.is_root:
            self.action_cursor_down()
        else:
            try:
                self.select_node(self.cursor_node.children[0]) # type: ignore
            except IndexError:
                pass



class CodeBrowser(App):
    """Textual code browser app."""

    path = "./" if len(sys.argv) < 2 else sys.argv[1]
    CSS_PATH = "code_browser.tcss"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]
    show_tree = var(True)


    def watch_show_tree(self, show_tree: bool) -> None:
        """Called when show_tree is modified."""
        self.set_class(show_tree, "-show-tree")


    def compose(self) -> ComposeResult:
        """Compose our UI."""
        yield Header()
        with Container():
            if not os.path.isfile(self.path):
                self.bind('ctrl+b', 'toggle_files', description='Toggle Files')
                yield ExtendedDirectoryTree(self.path, id="tree-view")
            yield ExtendedTextArea(id="code")
        yield Footer()


    def on_mount(self) -> None:
        if not os.path.isfile(self.path):
            self.query_one(DirectoryTree).focus()
        else:
            code_view = self.query_one(TextArea)
            code_view.focus()
            with open(str(self.path)) as file:
                syntax = get_syntax_for_file(self.path)
                if syntax:
                    code_view.language = syntax

                code_view.load_text(file.read())


    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Called when the user click a file in the directory tree."""
        event.stop()
        code_view = self.query_one("#code", TextArea)
        
        with open(str(event.path)) as file:
            syntax = get_syntax_for_file(event.path)
            if syntax:
                code_view.language = syntax
            
            code_view.load_text(file.read())

        code_view.focus()
        self.show_tree = not self.show_tree
        self.sub_title = str(event.path)


    def action_toggle_files(self) -> None:
        """Called in response to key binding."""
        self.show_tree = not self.show_tree
        self.query_one(DirectoryTree).focus()



if __name__ == "__main__":
    CodeBrowser().run()