"""
GUI.py

Requirements:
- Streamlab.py (027 or greater)
- uiassets folder

Changelog:

001:
- Initial upload
"""
from tkinter import *
from tkinter import ttk
from Streamlab import MessagePool


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


class LiveGUI:
    def __init__(self, pool: MessagePool):
        self.__root = Tk()
        self.__scrolling = False

        self.__mainframe = ttk.Frame(self.__root)
        self.__mainframe.grid()

        self.__queue = pool

        self.__create_log_widgets()
        self.__create_chat_widgets()

    def __invert_scrolling_variable(self, anything):
        self.__scrolling = not self.__scrolling

    def __create_log_widgets(self):
        # creates and configures widget objects
        self.__log_frame = ttk.Frame(self.__mainframe)

        self.__log_terminal = Text(self.__log_frame)
        self.__log_scrollbar = ttk.Scrollbar(self.__log_frame, orient=VERTICAL, command=self.__log_terminal.yview)

        self.__log_terminal.configure(yscrollcommand=self.__log_scrollbar.set)
        self.__log_terminal['state'] = 'disabled'

        # grids frame to mainframe
        self.__log_frame.grid(column=0, row=0)

        # grids widgets to logging frame
        self.__log_terminal.grid(column=0, row=0)
        self.__log_scrollbar.grid(column=1, row=0, sticky=(N, S, W))

        # binds events
        self.__log_frame.bind('<Enter>', self.__invert_scrolling_variable)
        self.__log_frame.bind('<Leave>', self.__invert_scrolling_variable)

    def __pause_chat(self):
        self.__queue.pause()

    def __create_chat_widgets(self):
        # creates and configures objects
        self.__chat_frame = ttk.Frame(self.__mainframe)
        self.__chat_var = StringVar(value=self.__queue.get_pool_reference())

        self.__chat_listbox = Listbox(self.__chat_frame, listvariable=self.__chat_var, height=10, width=50)

        # pause button widget
        self.__chat_button_pause = ImageButton(
            self.__chat_frame, on_image='uiassets/locked.png', off_image='uiassets/unlocked.png',
            command=self.__pause_chat
            )

        # bool to control button icon
        self.__chat_locked = False

        # grids frame to mainframe
        self.__chat_frame.grid(column=1, row=0, sticky=N)

        # grids widgets to chat frame
        self.__chat_listbox.grid(column=0, row=0)
        self.__chat_button_pause.grid(column=1, row=0, sticky=(N, W))

        # binds event
        self.__chat_listbox.bind("<ButtonRelease-1>", self.__delete_chat_message)

    def __delete_chat_message(self, anything):
        self.__queue.get_pool_reference()[self.__chat_listbox.curselection()[0]] = ''
        self.__chat_var.set(self.__queue.get_pool_reference())

    def update_chat_widget(self):
        """
        Must be called each time the MessagePool parameter is modified, so the widget can display the messages
        properly.
        """
        self.__chat_var.set(self.__queue.get_pool_reference())

    def print(self, text):
        self.__log_terminal['state'] = 'normal'
        self.__log_terminal.insert(END, f'{text}\n')
        self.__log_terminal['state'] = 'disabled'

        if not self.__scrolling:
            self.__log_terminal.see(END)

    def run(self):
        self.__root.mainloop()

    def close_app(self):
        self.__root.destroy()


if __name__ == '__main__':
    pass
