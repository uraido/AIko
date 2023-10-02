"""
AIkoStreamingGUI.py

Requirements:
- AIkoStreamingTools.py (027 or greater)
- uiassets folder

Changelog:

011:
- Fixed side prompt listbox selection not clearing after deleting messages.
- Inputting commands no longer prints them to command line text widget.
- Successful commands no longer print 'Success!'. Positive output should be handled by added commands instead.
012:
- Added time (hh:mm:ss) to printouts.
- Documented CommandLine class, added comments to GUI class.
013:
- Added button panel section.
014:
- Enter key now sends commands when the cmd entry is focused.
- Configured weights for each one of the section frames. GUI now has barebones resizability.
"""
from tkinter import *
from tkinter import ttk
from AIkoStreamingTools import MessagePool
from AIko.AIko import MessageList
from datetime import datetime


def return_message_content(item):
    if item != '':
        return item['content']
    return item


def parse_message_list(message_list: MessageList):
    return list(map(return_message_content, message_list.get_reference()))


class ImageButton(ttk.Button):
    def __init__(self, master, on_image, off_image, *args, **kwargs):
        self.on_image = PhotoImage(file=on_image)
        self.off_image = PhotoImage(file=off_image)
        super().__init__(master, *args, image=self.off_image, **kwargs)
        self.toggleState = 1
        self.bind("<Button-1>", self.click_function)

    def click_function(self, anything):
        # Ignore click if button is disabled
        if self.cget("state") != "disabled":
            self.toggleState *= -1
            if self.toggleState == -1:
                self.config(image=self.on_image)
            else:
                self.config(image=self.off_image)


class CommandLine:
    """
    A simple command line interface class that associates commands with functions and allows
    you to execute functions based on user input.

    Args:
        commands (dict): A dictionary containing command-function mappings.

    Attributes:
        __commands (dict): A private dictionary to store the command-function mappings.

    Methods:
        add_command(command, function):
            Add a new command and its associated function to the internal command dictionary.

        input(command):
            Parse the user input, execute the associated function, and handle arguments when provided.

    Example usage:
        cmd = CommandLine({"print_hello": print_hello})
        cmd.input("print_hello")
        Hello, world!
    """
    def __init__(self, commands: dict):
        # command dictionary {"command": function, [...]}
        self.__commands = commands

    def add_command(self, command: str, function: callable):
        """
        Add a new command and its associated function to the internal command dictionary.

        Args:
            command (str): The name of the command.
            function (callable): The function to be executed when the command is called.
        """
        self.__commands[command] = function

    def input(self, command: str):
        """
        Parse the user input, execute the associated function, and handle arguments when provided.

        Args:
            command (str): The user input, which may include a command and an optional argument.

        Returns:
            bool: True if the command was recognized and executed, False otherwise.
        """
        # splits command and argument (when included)
        command = command.split(maxsplit=1)

        # if command includes an argument
        if len(command) > 1:
            if command[0] in self.__commands:
                try:
                    # calls recognized function from command dictionary
                    self.__commands[command[0]](command[1])
                    return True
                except TypeError as e:
                    print(e)
        # if command doesn't include an argument
        elif command[0] in self.__commands:
            # calls recognized function from command dictionary
            self.__commands[command[0]]()
            return True

        return False


class LiveGUI:
    def __init__(self, pool: MessagePool, side_prompts: MessageList, commands: dict = None):
        if len(side_prompts.get_reference()) > 5:
            raise ValueError('side_prompts list must be at most 5 items long')
        if commands is None:
            commands = {}

        # CommandLine object for reading terminal commands
        self.__interpreter = CommandLine(commands)

        # instantiates tkinter
        self.__root = Tk()

        # customizes window
        self.__root.title('AILiveGUI')
        self.__set_icon('uiassets/main_icon.png')
        self.__root.resizable(True, True)

        # bools to monitor whether the user is scrolling text widgets
        self.__scrolling_log = False
        self.__scrolling_cmd = False

        # creates mainframe
        self.__mainframe = ttk.Frame(self.__root)
        self.__mainframe.grid()

        # attributes necessary for displaying chat and side_prompts
        self.__pool = pool
        self.__side_prompts = side_prompts

        # creates widgets
        self.__create_log_widgets()
        self.__create_command_line_widgets()
        self.__create_chat_widgets()
        self.__create_side_prompt_widgets()
        self.__create_button_panel_widgets()

        self.__set_frame_weights()

    def __set_frame_weights(self):
        self.__root.columnconfigure(0, weight=1)
        self.__root.rowconfigure(0, weight=1)

        # set left side as priority
        self.__mainframe.columnconfigure(0, weight=1)
        self.__mainframe.columnconfigure(1, weight=3)

        # set lower side as priority
        self.__mainframe.rowconfigure(0, weight=1)
        self.__mainframe.rowconfigure(1, weight=3)
    def __set_icon(self, icon_file: str):
        icon = PhotoImage(file=icon_file)
        self.__root.iconphoto(False, icon)

    # bools to monitor whether the user is scrolling text widgets
    def __invert_log_scrolling_variable(self, anything):
        self.__scrolling_log = not self.__scrolling_log

    def __invert_cmd_scrolling_variable(self, anything):
        self.__scrolling_cmd = not self.__scrolling_cmd

    def __create_log_widgets(self):
        # creates and configures widget objects
        self.__log_frame = ttk.Frame(self.__mainframe, padding=5)

        self.__log_terminal = Text(self.__log_frame)
        self.__log_scrollbar = ttk.Scrollbar(self.__log_frame, orient=VERTICAL, command=self.__log_terminal.yview)

        self.__log_terminal.configure(yscrollcommand=self.__log_scrollbar.set)
        self.__log_terminal['state'] = 'disabled'

        # grids frame to mainframe
        self.__log_frame.grid(column=0, row=0, rowspan=2)

        # grids widgets to logging frame
        self.__log_terminal.grid(column=0, row=0)
        self.__log_scrollbar.grid(column=1, row=0, sticky=(N, S, W))

        # binds events
        self.__log_terminal.bind('<Enter>', self.__invert_log_scrolling_variable)
        self.__log_terminal.bind('<Leave>', self.__invert_log_scrolling_variable)

    def __create_command_line_widgets(self):
        # creates and configures widget objects
        self.__cmd_frame = ttk.Frame(self.__mainframe, padding=5)

        self.__cmd_terminal = Text(self.__cmd_frame, height=10)
        self.__cmd_scrollbar = ttk.Scrollbar(self.__cmd_frame, orient=VERTICAL, command=self.__cmd_terminal.yview)

        self.__cmd_entry = ttk.Entry(self.__cmd_frame)

        self.__send_icon = PhotoImage(file='uiassets/send.png')
        self.__cmd_button_send = ttk.Button(self.__cmd_frame, image=self.__send_icon, command=self.__execute_command)

        self.__cmd_terminal.configure(yscrollcommand=self.__cmd_scrollbar.set)
        self.__cmd_terminal['state'] = 'disabled'

        # grids frame to mainframe
        self.__cmd_frame.grid(column=0, row=2, sticky=S)

        # grids widgets to cmd frame
        self.__cmd_terminal.grid(column=0, row=0)
        self.__cmd_scrollbar.grid(column=1, row=0, sticky=(N, S, W))
        self.__cmd_entry.grid(column=0, row=1, sticky=(N, W, E))
        self.__cmd_button_send.grid(column=1, row=1, sticky=(N, W))

        # binds events
        self.__cmd_terminal.bind('<Enter>', self.__invert_cmd_scrolling_variable)
        self.__cmd_terminal.bind('<Leave>', self.__invert_cmd_scrolling_variable)
        self.__cmd_entry.bind('<Return>', self.__execute_command)

    def add_command(self, command: str, func: callable):
        self.__interpreter.add_command(command, func)

    def print_to_cmdl(self, text: str):
        time = datetime.now()
        hour = f'[{time.hour:02d}:{time.minute:02d}:{time.second:02d}]'

        self.__cmd_terminal['state'] = 'normal'
        self.__cmd_terminal.insert(END, f'{hour} {text}\n')
        self.__cmd_terminal['state'] = 'disabled'

        if not self.__scrolling_cmd:
            self.__cmd_terminal.see(END)

    def __execute_command(self, anything=None):
        command = self.__cmd_entry.get()

        # if interpreter doesn't recognize command
        if not self.__interpreter.input(command):
            self.print_to_cmdl('Invalid command.')
        self.__cmd_entry.delete(0, 'end')

    def __pause_chat(self):
        self.__pool.pause()
        self.__chat_locked = not self.__chat_locked

        # updates widget states
        if self.__chat_locked:
            self.__chat_button_delete.state(['!disabled'])
            self.__chat_listbox['state'] = 'normal'
        else:
            self.__chat_button_delete.state(['disabled'])
            self.__chat_listbox['state'] = 'disabled'

        # clears selected items in listbox
        try:
            selection = self.__chat_listbox.curselection()
            self.__chat_listbox.selection_clear(selection[0], selection[-1])
        except Exception as e:
            print(e)

    def __create_chat_widgets(self):
        # creates and configures objects
        self.__chat_frame = ttk.Frame(self.__mainframe, padding=5)
        self.__chat_var = StringVar(value=self.__pool.get_pool_reference())

        self.__chat_listbox = Listbox(
            self.__chat_frame, listvariable=self.__chat_var, height=10, width=50, selectmode='extended'
            )
        self.__chat_listbox['state'] = 'disabled'

        # scrollbar
        self.__chat_scrollbar = ttk.Scrollbar(self.__chat_frame, orient=HORIZONTAL, command=self.__chat_listbox.xview)
        self.__chat_listbox.configure(xscrollcommand=self.__chat_scrollbar.set)

        # pause button widget
        self.__chat_button_pause = ImageButton(
            self.__chat_frame, on_image='uiassets/locked.png', off_image='uiassets/unlocked.png',
            command=self.__pause_chat
            )

        # delete message button widget
        self.__x_icon = PhotoImage(file='uiassets/x.png')
        self.__chat_button_delete = ttk.Button(
            self.__chat_frame, image=self.__x_icon, command=self.__delete_chat_message
            )
        self.__chat_button_delete.state(['disabled'])

        # bool to monitor chat state
        self.__chat_locked = False

        # grids frame to mainframe
        self.__chat_frame.grid(column=1, row=0, sticky=N)

        # grids widgets to chat frame
        self.__chat_listbox.grid(column=0, row=0)
        self.__chat_button_pause.grid(column=1, row=0, sticky=(N, W))
        self.__chat_button_delete.grid(column=2, row=0, sticky=(N, W))
        self.__chat_scrollbar.grid(column=0, row=1, sticky=(N, W, E))

        # binds event
        self.__chat_listbox.bind("<Return>", lambda e: self.__chat_button_delete.invoke())

    def __create_side_prompt_widgets(self):
        # creates and configures objects
        self.__sp_var = StringVar(value=parse_message_list(self.__side_prompts))

        self.__sp_listbox = Listbox(
            self.__chat_frame, listvariable=self.__sp_var, height=5, width=50, selectmode='extended'
            )

        # delete message button widget
        self.__sp_button_delete = ttk.Button(
            self.__chat_frame, image=self.__x_icon, command=self.__delete_side_prompt
            )

        # scrollbar
        self.__sp_scrollbar = ttk.Scrollbar(self.__chat_frame, orient=HORIZONTAL, command=self.__sp_listbox.xview)
        self.__sp_listbox.configure(xscrollcommand=self.__sp_scrollbar.set)

        # grids widgets to chat frame
        self.__sp_listbox.grid(column=0, row=2, sticky=(N, W))
        self.__sp_button_delete.grid(column=1, row=2, sticky=(N, W))
        self.__sp_scrollbar.grid(column=0, row=3, sticky=(N, W, E))

        # binds event
        self.__sp_listbox.bind("<Return>", lambda e: self.__sp_button_delete.invoke())

    def __create_button_panel_widgets(self):
        # creates and configures objects
        self.__bp_frame = ttk.Frame(self.__mainframe, padding=5)

        # mute button widget
        self.__bp_button_mute = ImageButton(
            self.__bp_frame, on_image='uiassets/muted.png', off_image='uiassets/unmuted.png',
            # command=None
        )

        # command line buttons
        self.__sp_icon = PhotoImage(file='uiassets/sp.png')
        self.__bp_button_side_prompt = ttk.Button(
            self.__bp_frame, image=self.__sp_icon, command=lambda: self.__insert_cmd('add_sp ')
        )
        self.__sm_icon = PhotoImage(file='uiassets/sm.png')
        self.__bp_button_sys_msg = ttk.Button(
            self.__bp_frame, image=self.__sm_icon, command=lambda: self.__insert_cmd('send_sys_msg ')
        )
        self.__bp_button_clear_cmd = ttk.Button(
            self.__bp_frame, image=self.__x_icon, command=lambda: self.__cmd_entry.delete(0, 'end')
        )

        # grids frame to mainframe
        self.__bp_frame.grid(column=1, row=2, sticky=(S, W))

        # grids widgets to button panel frame
        self.__bp_button_clear_cmd.grid(column=0, row=0, sticky=(S, W))
        self.__bp_button_sys_msg.grid(column=1, row=0, sticky=(S, W))
        self.__bp_button_side_prompt.grid(column=2, row=0, sticky=(S, W))
        self.__bp_button_mute.grid(column=3, row=0, sticky=(S, W))

    def __insert_cmd(self, command: str):
        self.__cmd_entry.delete(0, 'end')
        self.__cmd_entry.insert(0, command)
        self.__cmd_entry.focus()

    def __delete_chat_message(self, anything=None):
        if self.__chat_locked:
            selection = self.__chat_listbox.curselection()
            for i in selection:
                self.__pool.delete_message(i)
            # clears selection
            self.__chat_listbox.selection_clear(selection[0], selection[-1])

            self.update_chat_widget()

    def update_chat_widget(self):
        """
        Must be called each time the MessagePool parameter is modified, so the widget can display the messages
        properly.
        """
        self.__chat_var.set(self.__pool.get_pool_reference())

    def update_side_prompts_widget(self):
        """
        Must be called each time the MessagePool parameter is modified, so the widget can display the messages
        properly.
        """
        self.__sp_var.set(value=parse_message_list(self.__side_prompts))

    def __delete_side_prompt(self, anything=None):
        selection = self.__sp_listbox.curselection()
        for i in selection:
            self.__side_prompts.delete_item(i)
        # clears selection
        self.__sp_listbox.selection_clear(selection[0], selection[-1])

        self.update_side_prompts_widget()

    def print(self, text):
        time = datetime.now()
        hour = f'[{time.hour:02d}:{time.minute:02d}:{time.second:02d}]'

        self.__log_terminal['state'] = 'normal'
        self.__log_terminal.insert(END, f'{hour} {text}\n')
        self.__log_terminal['state'] = 'disabled'

        if not self.__scrolling_log:
            self.__log_terminal.see(END)

    def run(self):
        self.__root.mainloop()

    def close_app(self):
        self.__root.destroy()

    def bind_mute_button(self, func: callable):
        self.__bp_button_mute.configure(command=func)

    def set_close_protocol(self, protocol: callable):
        self.__root.protocol("WM_DELETE_WINDOW", protocol)


if __name__ == '__main__':
    pass
