"""
GUI.py

Requirements:
- Streamlab.py (027 or greater)
- uiassets folder

Changelog:

001:
- Initial upload
002:
- Now uses MessagePool class delete_message method instead of own deletion method when deleting chat messages.
003:
- Chat messages are now deleted through the new delete button/pressing enter with the chat listbox focused. Chat must
be locked for deletions to happen.
004:
- Added side prompts section.
005:
- GUI class now takes AIko.MessageList class as a parameter instead of a simple list.
006:
- Added CommandLine class and the command line section to the GUI class.
007:
- CommandLine class now takes dict with commands: functions as parameter.
- Added add_command to CommandLine class.
- Command line section of GUI class is now functional - commands can be added by giving a CommandLine format dictionary
as a parameter when instantiating the class, or by using the add_command method.
008:
- Added set_close_protocol method to GUI class.
- Can now select and delete multiple items from chat/sp list boxes.
- Chat listbox will switch between disabled/enabled states when locking/unlocking.
009:
- CommandLine class now supports commands with (single) arguments.
010:
- Added scrollbars to chat and sp listboxes.
"""
from tkinter import *
from tkinter import ttk
from Streamlab import MessagePool
from AIko import MessageList


def return_message_content(item):
    if item != '':
        return item['content']
    else:
        return ''


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
    def __init__(self, commands: dict):
        self.__commands = commands

    def add_command(self, command: str, function: callable):
        self.__commands[command] = function

    def input(self, command: str):
        # splits command and argument
        command = command.split(maxsplit=1)

        # if command includes an argument
        if len(command) > 1:
            if command[0] in self.__commands:
                try:
                    self.__commands[command[0]](command[1])
                    return True
                except TypeError as e:
                    print(e)
        # if command doesn't include an argument
        elif command[0] in self.__commands:
            self.__commands[command[0]]()
            return True

        return False



class LiveGUI:
    def __init__(self, pool: MessagePool, side_prompts: MessageList, commands: dict = None):
        if len(side_prompts.get_reference()) > 5:
            raise ValueError('side_prompts list must be at most 5 items long')
        if commands is None:
            commands = {}

        self.__interpreter = CommandLine(commands)

        self.__root = Tk()
        self.__scrolling_log = False
        self.__scrolling_cmd = False

        self.__mainframe = ttk.Frame(self.__root)
        self.__mainframe.grid()

        self.__pool = pool
        self.__side_prompts = side_prompts

        self.__create_log_widgets()
        self.__create_command_line_widgets()
        self.__create_chat_widgets()
        self.__create_side_prompt_widgets()

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
        # self.__cmd_frame.bind('<Return>', self.__cmd_button_send.invoke())

    def add_command(self, command: str, func: callable):
        self.__interpreter.add_command(command, func)

    def print_cmd(self, text: str):
        self.__cmd_terminal['state'] = 'normal'
        self.__cmd_terminal.insert(END, f'{text}\n')
        self.__cmd_terminal['state'] = 'disabled'

        if not self.__scrolling_cmd:
            self.__cmd_terminal.see(END)

    def __execute_command(self, anything=None):
        if self.__interpreter.input(self.__cmd_entry.get()):
            self.print_cmd('Success!')
        else:
            self.print_cmd('Invalid command.')
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

    def __delete_chat_message(self, anything=None):
        if self.__chat_locked:
            selection = self.__chat_listbox.curselection()
            for i in selection:
                self.__pool.delete_message(i)
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
        for i in self.__sp_listbox.curselection():
            self.__side_prompts.delete_item(i)
        self.update_side_prompts_widget()
        self.__sp_listbox.selection_clear(0, -1)

    def print(self, text):
        self.__log_terminal['state'] = 'normal'
        self.__log_terminal.insert(END, f'{text}\n')
        self.__log_terminal['state'] = 'disabled'

        if not self.__scrolling_log:
            self.__log_terminal.see(END)

    def run(self):
        self.__root.mainloop()

    def close_app(self):
        self.__root.destroy()

    def set_close_protocol(self, protocol: callable):
        self.__root.protocol("WM_DELETE_WINDOW", protocol)


if __name__ == '__main__':
    pass
