import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import simpledialog, filedialog
from vault import encrypt_vault, decrypt_vault, load_vault_file, atomic_write
import tkinter as tk


class VaultApp(tb.Window):
    def __init__(self):
        super().__init__(themename="litera")  # 选择 Bootstrap 主题
        self.title("Vault 管理工具")
        self.geometry("800x600")
        self.vault = None
        self.file_path = None

        # ————— 主内容区 —————
        self.main_frame = tb.Frame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        # —— 子容器 A：列表视图 ——
        self.list_frame = tb.Frame(self.main_frame)
        self.list_frame.pack(fill="both", expand=True)

        #卡片
        self.canvas = tb.Canvas(self.list_frame)
        self.scrollbar = tb.Scrollbar(self.list_frame, orient="vertical", command=self.canvas.yview)
        self.cards_frame = tb.Frame(self.canvas)
        self.canvas.create_window((0,0), window=self.cards_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.cards_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.view_frame = tb.Frame(self.main_frame)
        self.view_frame.pack(fill="both", expand=True)

        # 菜单
        menubar = tb.Menu(self)
        filemenu = tb.Menu(menubar, tearoff=0)
        filemenu.add_command(label="新建 Vault", command=self.new_vault)
        filemenu.add_command(label="打开 Vault", command=self.open_vault)
        filemenu.add_separator()
        filemenu.add_command(label="退出", command=self.quit)
        menubar.add_cascade(label="文件", menu=filemenu)
        self.config(menu=menubar)
        # 操作按钮
        self.btn_frame = tb.Frame(self)
        self.btn_frame.pack(fill="x", side="bottom", pady=5)
        tb.Button(self.btn_frame, text="添加", style="success", command=self.add_entry).pack(side=LEFT, padx=5)
        tb.Button(self.btn_frame, text="更新", style="info", command=self.update_entry).pack(side=LEFT, padx=5)
        tb.Button(self.btn_frame, text="删除", style="danger", command=self.delete_entry).pack(side=LEFT, padx=5)
        tb.Button(self.btn_frame, text="保存", style="warning.TButton", command=self.save_vault).pack(side=LEFT, padx=5)
        tb.Button(self.btn_frame, text="测试插入1条", style="secondary", command=self.test_insert).pack(side=LEFT, padx=5)
        tb.Button(self.btn_frame, text="测试删除10条", style="secondary", command=self.test_delete_ten).pack(side=LEFT, padx=5)


        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        # 状态栏
        self.status_label = tb.Label(self, text="", anchor='w')
        self.status_label.pack(fill='x', side='bottom')

        # 自动保存设置（每60秒保存一次）
        self.auto_save_interval = 10000  # 毫秒
        self.after(self.auto_save_interval, self._auto_save)

    def show_detail(self, name):
        self.clear_main_area()

        entry = next(e for e in self.vault["entries"] if e["name"] == name)
        # 在 detail_container 里居中放置 Labelframe
        detail = tb.Labelframe(self.view_frame,
                               text=name,
                               bootstyle="info",
                               padding=20)
        detail.place(relx=0.5, rely=0.5, anchor="center")
        detail.grid_columnconfigure(1, weight=1)

        for i, (k, v) in enumerate(entry.items()):
            tb.Label(detail, text=f"{k}:", bootstyle="secondary")\
              .grid(row=i, column=0, sticky="e", padx=5, pady=2)
            ent = tb.Entry(detail, state="readonly", bootstyle="secondary")
            ent.insert(0, v)
            ent.grid(row=i, column=1, sticky="ew", padx=5, pady=2)

        tb.Button(detail,
                  text="← 返回列表",
                  bootstyle="outline-info",
                  command=self.refresh_cards)\
          .grid(row=len(entry), column=0, columnspan=2, pady=10)

    def clear_main_area(self):
        for w in self.view_frame.winfo_children():
            w.destroy()

    def refresh_cards(self):
        self.clear_main_area()
        # 确保列表区可见
        # self.list_frame.pack_forget()  # 如果之前你 hide 过它
        # self.list_frame = tb.Frame(self.view_frame)
        # self.list_frame.pack(fill="both", expand=True)
        for entry in self.vault.get("entries", []):
            card = tb.Labelframe(self.cards_frame, text=entry["name"], bootstyle="primary")
            card.pack(fill="x", padx=20, pady=10)
            lbl = tb.Label(card,
                           text=f"{entry['username']} | {entry['account']}",
                           cursor="hand2")
            lbl.pack(anchor="w")
            lbl.bind("<Button-1>", lambda e, n=entry["name"]: self.show_detail(n))

    def new_vault(self):
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[("JSON Vault", '*.json')])
        if not path: return
        pw = simpledialog.askstring("设置主密码","输入主密码：",show='*')
        if not pw: return
        data={"entries":[]}
        atomic_write(path, encrypt_vault(pw,data))
        self.file_path,self.master_password,self.vault = path,pw,data
        self.refresh_cards()
        self._set_status("已初始化 Vault: " + path)

    def open_vault(self):
        path=filedialog.askopenfilename(filetypes=[("JSON Vault", '*.json')])
        if not path: return
        pw=simpledialog.askstring("输入主密码","主密码：",show='*')
        try:
            data=decrypt_vault(pw,load_vault_file(path))
        except Exception as e:
            self._set_status("错误: " + str(e))
            return
        self.file_path,self.master_password,self.vault=path,pw,data
        self.refresh_cards()
        self._set_status("已打开 Vault: " + path)

    def show_add_form(self):
        # 1. 清空
        self.clear_main_area()

        # 3. 内嵌表单容器
        form = tb.Labelframe(self.view_frame, text="添加新条目",
                             style="secondary", padding=20)
        form.place(relx=0.5, rely=0.5, anchor="center")
        form.grid_columnconfigure(1, weight=1)

        # 4. 动态生成字段
        fields = ['name','username','account','password','website','phone','email']
        entries = {}
        for i, f in enumerate(fields):
            tb.Label(form, text=f+":", style="secondary") \
              .grid(row=i, column=0, sticky="e", padx=5, pady=2)
            ent = tb.Entry(form, style="secondary.TEntry")
            ent.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
            entries[f] = ent

        # 5. 保存 & 取消
        def on_save():
            data = {f: entries[f].get() for f in fields if entries[f].get()}
            self.vault['entries'].append(data)
            self.save_vault()
            self.refresh_cards()

        tb.Button(form, text="保存", style="success", command=on_save) \
          .grid(row=len(fields), column=0, pady=10)
        tb.Button(form, text="取消", style="outline-danger",
                  command=self.refresh_cards) \
          .grid(row=len(fields), column=1, pady=10)

    def add_entry(self):
        # 现在只调用内嵌表单
        self.show_add_form()

    def update_entry(self):
        dlg=UpdateDialog(self,"更新条目",self.vault.get('entries',[]))
        self.wait_window(dlg)
        if dlg.result:
            name,new=dlg.result
            for i,e in enumerate(self.vault['entries']):
                if e['name']==name: self.vault['entries'][i].update(new);break
            self.save_vault();self.refresh_cards();self._set_status(f"已更新条目: {name}")

    def delete_entry(self):
        dlg=DeleteDialog(self,"删除条目",self.vault.get('entries',[]))
        self.wait_window(dlg)
        if dlg.result:
            name=dlg.result
            self.vault['entries']=[e for e in self.vault['entries'] if e['name']!=name]
            self.save_vault();self.refresh_cards();self._set_status("已删除条目: " + name)

    def test_insert(self):
        if not self.vault: return
        idx=len(self.vault['entries'])
        entry={f:f"test_{f}_{idx+1}" for f in ['name','username','account','password','website','phone','email']}
        self.vault['entries'].append(entry)
        self.save_vault();self.refresh_cards();self._set_status("已插入1条测试数据")

    def test_delete_ten(self):
        if not self.vault: return
        cnt=min(10,len(self.vault['entries']))
        self.vault['entries']=self.vault['entries'][cnt:]
        self.save_vault();self.refresh_cards();self._set_status(f"已删除{cnt}条测试数据")

    def save_vault(self):
        atomic_write(self.file_path, encrypt_vault(self.master_password,self.vault))

    def _auto_save(self):
        if self.vault and self.file_path:
            self.save_vault()
            self._set_status("自动保存完成")
        self.after(self.auto_save_interval, self._auto_save)

    def _set_status(self, msg, duration=2000):
        self.status_label.config(text=msg)
        self.after(duration, lambda: self.status_label.config(text=""))

    def _on_mousewheel(self, event):
        # event.delta 在 Windows 下一次滚动大约等于 ±120
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# 对话框类省略（保持不变）
class EntryDialog(tk.Toplevel):
    def __init__(self,parent,title,initial=None):
        super().__init__(parent);self.title(title)
        self.transient(parent)
        self.grab_set()
        self.result=None
        fields=['name','username','account','password','website','phone','email']
        self.vars={}
        for i,f in enumerate(fields):
            tk.Label(self,text=f).grid(row=i,column=0)
            var=tk.StringVar(value=(initial.get(f) if initial else ''))
            tk.Entry(self,textvariable=var).grid(row=i,column=1)
            self.vars[f]=var
        tk.Button(self,text="确认",command=self.on_ok).grid(row=len(fields),column=0)
        tk.Button(self,text="取消",command=self.destroy).grid(row=len(fields),column=1)

    def on_ok(self):
        self.result={f:self.vars[f].get() for f in self.vars if self.vars[f].get()}
        self.grab_release()
        self.destroy()

class UpdateDialog(EntryDialog):
    def __init__(self,parent,title,entries):
        super().__init__(parent,title)
        names=[e.get('name') for e in entries]
        tk.Label(self,text="选择名称：").grid(row=0,column=2)
        self.name_var=tk.StringVar()
        tk.OptionMenu(self,self.name_var,*names).grid(row=0,column=3)
    def on_ok(self):
        self.result=(self.name_var.get(),{f:self.vars[f].get() for f in self.vars if self.vars[f].get()})
        self.grab_release()
        self.destroy()


class DeleteDialog(tk.Toplevel):
    def __init__(self, parent, title, entries):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        names = [e.get('name') for e in entries]
        tk.Label(self, text="选择名称：").pack(pady=5)
        self.name_var = tk.StringVar()
        tk.OptionMenu(self, self.name_var, *names).pack(pady=5)
        tk.Button(self, text="确认", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(self, text="取消", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        self.result = None

    def on_ok(self):
        self.result = self.name_var.get()
        self.grab_release()
        self.destroy()

if __name__=='__main__':
    VaultApp().mainloop()
