import customtkinter as ctk

class LoginView(ctk.CTkFrame):
    def __init__(self, master, on_login_success, **kwargs):
        super().__init__(master, **kwargs)
        self.on_login_success = on_login_success
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 4), weight=1)
        
        self.title_label = ctk.CTkLabel(self, text="LibreView Login", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(40, 20))
        
        self.email_entry = ctk.CTkEntry(self, placeholder_text="Email", width=300)
        self.email_entry.grid(row=1, column=0, padx=20, pady=10)
        
        self.password_entry = ctk.CTkEntry(self, placeholder_text="Password", show="*", width=300)
        self.password_entry.grid(row=2, column=0, padx=20, pady=10)
        
        self.login_button = ctk.CTkButton(self, text="Login", command=self._on_login_click, width=200)
        self.login_button.grid(row=3, column=0, padx=20, pady=20)
        
        self.error_label = ctk.CTkLabel(self, text="", text_color="red")
        self.error_label.grid(row=4, column=0, padx=20, pady=10)

    def _on_login_click(self):
        email = self.email_entry.get()
        password = self.password_entry.get()
        
        if not email or not password:
            self.error_label.configure(text="Please fill in all fields")
            return
            
        self.login_button.configure(state="disabled", text="Logging in...")
        self.on_login_success(email, password)

    def show_error(self, message):
        self.error_label.configure(text=message)
        self.login_button.configure(state="normal", text="Login")
