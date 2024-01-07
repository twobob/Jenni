import tkinter as tk

class ToolTip:
    def __init__(self, widget, text=None):
        self.widget = widget
        self.text = text
        self.widget.bind('<Enter>', self.on_enter)
        self.widget.bind('<Leave>', self.on_leave)

    def on_enter(self, event):
        self.tooltip = tk.Toplevel()
        self.tooltip.overrideredirect(True)
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tooltip.geometry(f'+{x}+{y}')

        self.label = tk.Label(self.tooltip, text=self.text, fg="white" , bg='black', relief='solid', borderwidth=1)
        self.label.pack()

    def on_leave(self, event):
        self.tooltip.destroy()

    def update_text(self, new_text):
        """Update the tooltip text."""
        self.text = new_text
        if hasattr(self, 'label'):  # Check if the label attribute exists
            self.label.config(text=new_text)    