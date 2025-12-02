# giveone_app.py
# GiveOne — adjustable-donation demo with signup, empathetic cases, refresh, and reset-to-start
# Python standard library only (Tkinter UI)

import json, os, datetime, hashlib
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from copy import deepcopy

DATA_FILE = "giveone_data.json"

# ----------------------------
# Helpers: formatting, time, hashing
# ----------------------------
def cents_to_dollars(cents: int) -> str:
    """Format integer cents like $10,000.00."""
    return f"${cents/100:,.2f}"

def now_iso() -> str:
    """Timestamp string for UI/logs."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def sha256(text: str) -> str:
    """Tiny password hash (good for a class demo)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def month_donated_cents(donations: list) -> int:
    """
    Sum donations for the current month.
    We parse the YYYY-mm-dd HH:MM:SS timestamp we write into the log.
    """
    if not donations:
        return 0
    now = datetime.datetime.now()
    total = 0
    for d in donations:
        try:
            ts = datetime.datetime.strptime(d["timestamp"], "%Y-%m-%d %H:%M:%S")
            if ts.year == now.year and ts.month == now.month:
                total += int(d["amount_cents"])
        except Exception:
            # if any old row is malformed, just skip it (keeps demo resilient)
            continue
    return total

# ----------------------------
# Seed data (5 real-feel cases)
# ----------------------------
DEFAULT_CASES = [
    {
        "case_id": 201,
        "title": "Plant a Tree",
        "org_name": "GreenEarth",
        "goal_cents": 250_000,   # $2,500.00
        "raised_cents": 90_000,  # $900.00
        "status": "Open",
        "description": (
            "A community lost its shade after storms. Every $5 plants a sapling. "
            "Kids walk to school under the sun—your help grows a living canopy."
        ),
        "category": "Environment",
    },
    {
        "case_id": 202,
        "title": "Pediatric Cancer Care",
        "org_name": "Hope4Kids",
        "goal_cents": 500_000,   # $5,000.00
        "raised_cents": 120_000, # $1,200.00
        "status": "Open",
        "description": (
            "Maya (age 6) is starting chemo. Donations cover fuel cards for hospital trips "
            "and comfort kits so she isn’t facing treatment empty-handed."
        ),
        "category": "Health",
    },
    {
        "case_id": 203,
        "title": "Emergency Shelter for a Family",
        "org_name": "SafeNights",
        "goal_cents": 300_000,   # $3,000.00
        "raised_cents": 210_000, # $2,100.00
        "status": "Open",
        "description": (
            "After a sudden eviction, the Hassan family is living in their car. "
            "Your gift buys three weeks of shelter so parents can get back to work."
        ),
        "category": "Relief",
    },
    {
        "case_id": 204,
        "title": "Clean Water Well",
        "org_name": "ClearWells",
        "goal_cents": 600_000,   # $6,000.00
        "raised_cents": 305_000, # $3,050.00
        "status": "Open",
        "description": (
            "Women in Kijani walk 4 miles daily for water. A village well turns hours "
            "of walking into minutes of learning and earning."
        ),
        "category": "Water",
    },
    {
        "case_id": 205,
        "title": "School Lunch for a Month",
        "org_name": "BrightPlates",
        "goal_cents": 200_000,   # $2,000.00
        "raised_cents": 65_000,  # $650.00
        "status": "Open",
        "description": (
            "Hungry students can’t focus. $10 covers a child’s lunches for a month—"
            "a small lift that changes their whole day."
        ),
        "category": "Education",
    },
]

# Local JSON state so the demo works offline
DEFAULT_DATA = {
    "user": None,  # set after signup
    "wallet": {"balance_cents": 0, "last_updated": ""},
    "cases": deepcopy(DEFAULT_CASES),
    "donations": [],  # newest first
}

# ----------------------------
# Persistence: load/save JSON
# ----------------------------
def load_data():
    """Load state from disk, or initialize on first run."""
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA)
        return json.loads(json.dumps(DEFAULT_DATA))
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    """Write current state back to disk."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ----------------------------
# Services: keep logic out of the UI
# ----------------------------
class WalletService:
    def __init__(self, data): self.data = data

    def add_funds(self, dollars: float):
        """Increase wallet balance by a user-specified dollar amount."""
        add_cents = int(round(dollars * 100))
        if add_cents <= 0:
            raise ValueError("Amount must be greater than 0.")
        self.data["wallet"]["balance_cents"] += add_cents
        self.data["wallet"]["last_updated"] = now_iso()
        save_data(self.data)

    def can_donate(self, cents: int) -> bool:
        """Check if wallet has enough to cover a donation."""
        return self.data["wallet"]["balance_cents"] >= cents

    def deduct(self, cents: int):
        """Subtract from wallet after donation is confirmed."""
        if not self.can_donate(cents):
            raise ValueError("Insufficient funds.")
        self.data["wallet"]["balance_cents"] -= cents
        self.data["wallet"]["last_updated"] = now_iso()

class CaseService:
    def __init__(self, data): self.data = data

    def list_cases(self):
        """Return all cases."""
        return self.data["cases"]

    def donate(self, case_id, cents):
        """Apply a donation: deduct wallet, update case, log it."""
        WalletService(self.data).deduct(cents)

        case = next((c for c in self.data["cases"] if c["case_id"] == case_id), None)
        if not case:
            raise ValueError("Case not found.")

        case["raised_cents"] += cents
        if case["raised_cents"] >= case["goal_cents"]:
            case["status"] = "Funded"

        self.data["donations"].insert(0, {
            "timestamp": now_iso(),
            "case_id": case_id,
            "amount_cents": cents,
            "running_balance_cents": self.data["wallet"]["balance_cents"],
        })
        save_data(self.data)

# ----------------------------
# UI: Signup screen and main app shell
# ----------------------------
class SignupFrame(ttk.Frame):
    """Simple signup form for first/last/email/password; creates the local user."""
    def __init__(self, master, on_done):
        super().__init__(master, padding=20)
        self.on_done = on_done

        ttk.Label(self, text="Create your GiveOne account", font=("Segoe UI", 16, "bold"))\
            .grid(row=0, column=0, columnspan=2, pady=(0, 14))

        self.fn, self.ln, self.em, self.pw = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()

        ttk.Label(self, text="First name").grid(row=1, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.fn, width=28).grid(row=1, column=1, sticky="ew", pady=3)

        ttk.Label(self, text="Last name").grid(row=2, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.ln, width=28).grid(row=2, column=1, sticky="ew", pady=3)

        ttk.Label(self, text="Email").grid(row=3, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.em, width=28).grid(row=3, column=1, sticky="ew", pady=3)

        ttk.Label(self, text="Password").grid(row=4, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.pw, show="•", width=28).grid(row=4, column=1, sticky="ew", pady=3)

        ttk.Button(self, text="Create Account", command=self._create)\
            .grid(row=5, column=0, columnspan=2, pady=(10,0))

        for i in range(2):
            self.columnconfigure(i, weight=1)

    def _create(self):
        """Validate fields and hand the new user to the parent."""
        fn, ln, em, pw = self.fn.get().strip(), self.ln.get().strip(), self.em.get().strip(), self.pw.get().strip()
        if not (fn and ln and em and pw):
            messagebox.showwarning("Missing info", "Please fill all fields.")
            return
        user = {
            "user_id": 1,
            "first_name": fn,
            "last_name": ln,
            "email": em,
            "password_hash": sha256(pw),
            "created_at": now_iso(),
        }
        self.on_done(user)

class GiveOneApp(ttk.Frame):
    """Main application: header, tabs, actions, and demo reset."""
    def __init__(self, master, data):
        super().__init__(master)
        self.master = master
        self.data = data
        self.case_service = CaseService(self.data)
        self.wallet_service = WalletService(self.data)

        # Window basics
        self.master.title("GiveOne — Donation Demo")
        self.master.geometry("960x640")
        self.master.minsize(920, 600)

        # First-time users see signup
        if self.data["user"] is None:
            self._route_start()
        else:
            self._route_main()

    # ----- Routing
    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    def _route_start(self):
        self._clear()
        self.signup = SignupFrame(self, self._finish_signup)
        self.signup.pack(fill=tk.BOTH, expand=True)
        self.pack(fill=tk.BOTH, expand=True)

    def _route_main(self):
        self._clear()
        self._build_header()
        self._build_tabs()
        self.refresh_all()

    # ----- Signup handler
    def _finish_signup(self, user):
        """On signup: zero wallet, restore default cases, clear history."""
        self.data["user"] = user
        self.data["wallet"] = {"balance_cents": 0, "last_updated": now_iso()}
        self.data["cases"] = deepcopy(DEFAULT_CASES)
        self.data["donations"] = []
        save_data(self.data)
        self._route_main()

    # ----- Header (welcome, monthly total, balance, actions)
    def _build_header(self):
        header = ttk.Frame(self, padding=(12, 8))
        header.pack(side=tk.TOP, fill=tk.X)

        name = self.data["user"]["first_name"] if self.data["user"] else "Friend"
        left = ttk.Frame(header); left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Line 1: Welcome
        ttk.Label(left, text=f"Welcome, {name}!", font=("Segoe UI", 16, "bold")).pack(anchor="w")

        # Line 2: This month's donation total
        self.month_var = tk.StringVar(value="This month you donated $0.00")
        ttk.Label(left, textvariable=self.month_var, font=("Segoe UI", 10)).pack(anchor="w", pady=(2,0))

        # Right: actions + balance
        right = ttk.Frame(header); right.pack(side=tk.RIGHT)
        ttk.Button(right, text="Reset Demo", command=self._reset_demo).pack(side=tk.RIGHT, padx=6)
        ttk.Button(right, text="Refresh", command=self.refresh_all).pack(side=tk.RIGHT, padx=6)

        self.balance_var = tk.StringVar(value="Balance: $0.00")
        ttk.Label(right, textvariable=self.balance_var, font=("Segoe UI", 12)).pack(side=tk.RIGHT)

        self.pack(fill=tk.BOTH, expand=True)

    # ----- Reset to Start (demo helper)
    def _reset_demo(self):
        """
        Clear wallet, cases, and history; remove user; save; and return to the start screen.
        This gives you a true 'fresh demo' in one click.
        """
        if not messagebox.askyesno("Reset Demo", "Reset everything and return to the start screen?"):
            return
        fresh = {
            "user": None,
            "wallet": {"balance_cents": 0, "last_updated": ""},
            "cases": deepcopy(DEFAULT_CASES),
            "donations": [],
        }
        save_data(fresh)
        # Overwrite in-memory state, then route to signup
        self.data.update(fresh)
        self._route_start()

    # ----- Tabs
    def _build_tabs(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.cases_frame = ttk.Frame(self.tabs)
        self.wallet_frame = ttk.Frame(self.tabs)
        self.history_frame = ttk.Frame(self.tabs)

        self.tabs.add(self.cases_frame, text="Cases")
        self.tabs.add(self.wallet_frame, text="Wallet")
        self.tabs.add(self.history_frame, text="History")

        self._build_cases_tab()
        self._build_wallet_tab()
        self._build_history_tab()

    # ----------------------------
    # Cases tab
    # ----------------------------
    def _build_cases_tab(self):
        """Donation amount field + scrollable list of case cards."""
        top = ttk.Frame(self.cases_frame, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Donation amount:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)

        # User can type any amount, defaults to $1.00
        self.amount_var = tk.StringVar(value="1.00")
        ttk.Entry(top, textvariable=self.amount_var, width=8, justify="right").pack(side=tk.LEFT, padx=6)

        # Quick buttons to speed up the demo
        for quick in (1, 5, 10):
            ttk.Button(top, text=f"${quick}",
                       command=lambda q=quick: self.amount_var.set(f"{q:.2f}")).pack(side=tk.LEFT, padx=2)

        # Scrollable area for case cards
        self.cases_canvas = tk.Canvas(self.cases_frame, highlightthickness=0)
        self.cases_scroll = ttk.Scrollbar(self.cases_frame, orient="vertical", command=self.cases_canvas.yview)
        self.cases_inner = ttk.Frame(self.cases_canvas)

        self.cases_inner.bind("<Configure>", lambda e: self.cases_canvas.configure(scrollregion=self.cases_canvas.bbox("all")))
        self.cases_canvas.create_window((0, 0), window=self.cases_inner, anchor="nw")
        self.cases_canvas.configure(yscrollcommand=self.cases_scroll.set)

        self.cases_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)
        self.cases_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=8)

    def _render_case_card(self, parent, case):
        """One card per case: story, progress, percent, and Donate button."""
        card = ttk.Frame(parent, padding=10)
        card.pack(fill=tk.X, expand=True, pady=8)

        ttk.Label(
            card,
            text=f"{case['title']}  —  {case['org_name']}  [{case['category']}]",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w")

        ttk.Label(card, text=case["description"], wraplength=780, justify="left")\
           .pack(anchor="w", pady=(2, 6))

        # Progress bar and percent funded label
        pct = min(100, int((case["raised_cents"] / case["goal_cents"]) * 100)) if case["goal_cents"] else 0
        progress = ttk.Progressbar(card, orient="horizontal", mode="determinate", length=600)
        progress["value"] = pct
        progress.pack(anchor="w")
        ttk.Label(card, text=f"{pct}% funded", foreground="#666").pack(anchor="w", pady=(1, 4))

        meta = (
            f"Goal: {cents_to_dollars(case['goal_cents'])} | "
            f"Raised: {cents_to_dollars(case['raised_cents'])} | "
            f"Funded: {pct}% | "
            f"Status: {case['status']}"
        )
        ttk.Label(card, text=meta, foreground="#444").pack(anchor="w", pady=(2, 6))

        row = ttk.Frame(card); row.pack(anchor="w")
        ttk.Button(row, text="Donate", command=lambda cid=case["case_id"]: self._donate_adjustable(cid)).pack(side=tk.LEFT)

        if case["status"] in ("Funded", "Completed"):
            for c in row.winfo_children():
                c.state(["disabled"])

    # ----------------------------
    # Wallet tab
    # ----------------------------
    def _build_wallet_tab(self):
        """Wallet balance + Add Funds button."""
        inner = ttk.Frame(self.wallet_frame, padding=16)
        inner.pack(fill=tk.BOTH, expand=True)

        ttk.Label(inner, text="Wallet", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 8))
        self.wallet_balance_var = tk.StringVar(value="")
        ttk.Label(inner, textvariable=self.wallet_balance_var, font=("Segoe UI", 11)).pack(anchor="w")

        ttk.Button(inner, text="Add Funds", command=self._prompt_add_funds).pack(anchor="w", pady=10)
        ttk.Label(inner, text="Tip: Use $1, $5, $10 quick picks on the Cases tab, or type a custom amount.",
                  foreground="#555").pack(anchor="w", pady=(6, 0))

    # ----------------------------
    # History tab
    # ----------------------------
    def _build_history_tab(self):
        """Table showing donations (time, case, amount, running balance)."""
        frame = ttk.Frame(self.history_frame, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        cols = ("time", "case", "amount", "balance_after")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=16)
        for c, w in zip(cols, (170, 360, 120, 160)):
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=w, anchor=("e" if c != "case" else "w"))
        self.tree.pack(fill=tk.BOTH, expand=True)

    # ----------------------------
    # Actions (button handlers)
    # ----------------------------
    def _prompt_add_funds(self):
        """Ask for an amount and top up the wallet."""
        try:
            amt = simpledialog.askfloat("Add Funds", "Enter amount (e.g., 5 for $5):", minvalue=0.01)
            if amt is None:
                return
            self.wallet_service.add_funds(amt)
            self.refresh_all()
            messagebox.showinfo("Wallet", f"Added {cents_to_dollars(int(round(amt*100)))} to your wallet.")
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def _donate_adjustable(self, case_id):
        """Donate the amount typed in the Cases tab to the selected case."""
        try:
            dollars = float(self.amount_var.get().strip())
        except Exception:
            messagebox.showwarning("Amount", "Please enter a valid amount like 1 or 2.50.")
            return
        cents = int(round(dollars * 100))
        if cents <= 0:
            messagebox.showwarning("Amount", "Donation must be greater than $0.")
            return

        if not self.wallet_service.can_donate(cents):
            messagebox.showwarning("Wallet", "Insufficient funds! Add funds to donate.")
            return

        try:
            self.case_service.donate(case_id, cents)
            case = next(c for c in self.data["cases"] if c["case_id"] == case_id)
            if case["status"] == "Funded" and case["raised_cents"] >= case["goal_cents"]:
                messagebox.showinfo("🎉 Funded!", f"“{case['title']}” just reached its goal!")
            self.refresh_all()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ----------------------------
    # Refresh everything on screen
    # ----------------------------
    def refresh_all(self):
        """
        Reload state from disk and repaint header, cases, and history.
        Also updates: balance text and 'this month total'.
        """
        disk = load_data()
        self.data["wallet"] = disk["wallet"]
        self.data["cases"] = disk["cases"]
        self.data["donations"] = disk["donations"]
        self.data["user"] = disk["user"]

        # Header: balance + this month's total
        bal = self.data["wallet"]["balance_cents"]
        self.balance_var.set(f"Balance: {cents_to_dollars(bal)}")

        month_total = month_donated_cents(self.data["donations"])
        self.month_var.set(f"This month you donated {cents_to_dollars(month_total)}")

        # Wallet tab text
        if hasattr(self, "wallet_balance_var"):
            self.wallet_balance_var.set(
                f"Current Balance: {cents_to_dollars(bal)} (Updated: {self.data['wallet']['last_updated'] or '—'})"
            )

        # Cases list (rebuild cards)
        if hasattr(self, "cases_inner"):
            for child in self.cases_inner.winfo_children():
                child.destroy()
            for case in self.case_service.list_cases():
                self._render_case_card(self.cases_inner, case)

        # History table (newest first)
        if hasattr(self, "tree"):
            for row in self.tree.get_children():
                self.tree.delete(row)
            name_by_id = {c["case_id"]: c["title"] for c in self.data["cases"]}
            for d in self.data["donations"][:120]:
                self.tree.insert(
                    "", tk.END,
                    values=(
                        d["timestamp"],
                        name_by_id.get(d["case_id"], f"Case {d['case_id']}"),
                        cents_to_dollars(d["amount_cents"]),
                        cents_to_dollars(d["running_balance_cents"]),
                    )
                )

# ----------------------------
# App bootstrap
# ----------------------------
if __name__ == "__main__":
    data = load_data()
    root = tk.Tk()
    app = GiveOneApp(root, data)
    app.mainloop()
