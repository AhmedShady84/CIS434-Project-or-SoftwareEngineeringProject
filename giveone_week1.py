# giveone_app.py
# GiveOne — modern daily micro-donation demo
# Tkinter UI, local JSON storage only (no real payments)

import json
import os
import datetime
import hashlib
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
    """Tiny password hash (demo only, not for production)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def month_donated_cents(donations: list) -> int:
    """Sum donations for the current month."""
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
            continue
    return total

# ----------------------------
# Streak helpers
# ----------------------------

def update_streak_on_donate(data):
    """
    Update user's daily donation streak when they make a donation.

    Rules:
    - First donation ever → streak = 1
    - Another donation same day → streak unchanged
    - Next donation within 24 hours but on a new calendar day → streak + 1
    - Donation after >24 hours since last donation → streak = 1
    """
    now = datetime.datetime.now()
    user = data.get("user") or {}
    streak = user.get("streak_days", 0)
    last_ts_str = user.get("streak_last_ts")

    last_ts = None
    if last_ts_str:
        try:
            last_ts = datetime.datetime.fromisoformat(last_ts_str)
        except Exception:
            last_ts = None

    if last_ts is None:
        streak = 1
    else:
        delta = now - last_ts
        if now.date() == last_ts.date():
            # same day, don't change
            pass
        elif delta.total_seconds() <= 24 * 3600:
            streak += 1
        else:
            streak = 1

    user["streak_days"] = streak
    user["streak_last_ts"] = now.isoformat(timespec="seconds")
    data["user"] = user

def break_streak_if_inactive(data):
    """If more than 24 hours have passed since the last donation, reset the user's streak to 0."""
    user = data.get("user")
    if not user:
        return

    last_ts_str = user.get("streak_last_ts")
    if not last_ts_str:
        return

    try:
        last_ts = datetime.datetime.fromisoformat(last_ts_str)
    except Exception:
        return

    delta = datetime.datetime.now() - last_ts
    if delta.total_seconds() > 24 * 3600:
        user["streak_days"] = 0
        data["user"] = user
        save_data(data)

# ----------------------------
# Seed data (hospital + categories)
# ----------------------------

DEFAULT_CASES = [
    {
        "case_id": 301,
        "title": "Cleveland Clinic – Heart Patient Support",
        "org_name": "Cleveland Clinic (Demo)",
        "goal_cents": 500_000,
        "raised_cents": 120_000,
        "status": "Open",
        "description": (
            "Help families cover parking, meals, and lodging while a loved one "
            "undergoes cardiac surgery at a major heart center."
        ),
        "category": "Hospital",
        "city": "Cleveland, OH",
        "image": "cleveland_clinic.png",
    },
    {
        "case_id": 302,
        "title": "St. Jude – Pediatric Cancer Travel",
        "org_name": "St. Jude (Demo)",
        "goal_cents": 600_000,
        "raised_cents": 300_000,
        "status": "Open",
        "description": (
            "Provide travel stipends for families flying in for pediatric "
            "cancer treatment so money is never a reason to skip care."
        ),
        "category": "Hospital",
        "city": "Memphis, TN",
        "image": "st_jude.png",
    },
    {
        "case_id": 303,
        "title": "Mayo Clinic – Transplant Housing",
        "org_name": "Mayo Clinic (Demo)",
        "goal_cents": 750_000,
        "raised_cents": 425_000,
        "status": "Open",
        "description": (
            "Support short-term housing for transplant patients and their "
            "caregivers staying near the hospital during recovery."
        ),
        "category": "Hospital",
        "city": "Rochester, MN",
        "image": "mayo_clinic.png",
    },
    {
        "case_id": 304,
        "title": "Johns Hopkins – NICU Family Meals",
        "org_name": "Johns Hopkins (Demo)",
        "goal_cents": 300_000,
        "raised_cents": 80_000,
        "status": "Open",
        "description": (
            "Parents of babies in the NICU can spend 12+ hours bedside. "
            "Fund hot meals so they don't have to choose between food and time with their child."
        ),
        "category": "Hospital",
        "city": "Baltimore, MD",
        "image": "johns_hopkins.png",
    },
    {
        "case_id": 305,
        "title": "Mass General – Emergency Hardship",
        "org_name": "Mass General (Demo)",
        "goal_cents": 400_000,
        "raised_cents": 150_000,
        "status": "Open",
        "description": (
            "A small emergency grant can keep the lights on or cover a "
            "co-pay after a sudden illness. You help social workers say 'yes'."
        ),
        "category": "Hospital",
        "city": "Boston, MA",
        "image": "mass_general.png",
    },
    {
        "case_id": 306,
        "title": "Community Counseling Sessions",
        "org_name": "Mindful City (Demo)",
        "goal_cents": 250_000,
        "raised_cents": 90_000,
        "status": "Open",
        "description": (
            "Sponsor therapy sessions for people on waiting lists so they "
            "can access mental health care before they’re in crisis."
        ),
        "category": "Mental Health",
        "city": "Cleveland, OH",
        "image": "mental_health_1.png",
    },
    {
        "case_id": 307,
        "title": "Student Mental Health Hotline",
        "org_name": "Campus Support (Demo)",
        "goal_cents": 300_000,
        "raised_cents": 120_000,
        "status": "Open",
        "description": (
            "Fund trained counselors for a 24/7 text line so college students "
            "can reach out anonymously any time they need support."
        ),
        "category": "Mental Health",
        "city": "Nationwide",
        "image": "mental_health_2.png",
    },
    {
        "case_id": 308,
        "title": "Plant a Tree in Your City",
        "org_name": "GreenEarth (Demo)",
        "goal_cents": 200_000,
        "raised_cents": 65_000,
        "status": "Open",
        "description": (
            "A community lost its shade after storms. Every $5 plants a sapling. "
            "Kids walk to school under the sun—your help grows a living canopy."
        ),
        "category": "Environment",
        "city": "Multiple cities",
        "image": "environment_trees.png",
    },
    {
        "case_id": 309,
        "title": "School Lunch for a Month",
        "org_name": "BrightPlates (Demo)",
        "goal_cents": 200_000,
        "raised_cents": 80_000,
        "status": "Open",
        "description": (
            "Hungry students can’t focus. $10 covers a child’s lunches for a month—"
            "a small lift that changes their whole day."
        ),
        "category": "Education",
        "city": "Local districts",
        "image": "education_lunch.png",
    },
]

DEFAULT_DATA = {
    "user": None,
    "wallet": {"balance_cents": 0, "last_updated": ""},
    "cases": deepcopy(DEFAULT_CASES),
    "donations": [],
    "autopay": {
        "enabled": False,
        "amount_cents": 100,
        "case_id": None,
        "last_run_ts": "",
    },
    "friends": [],
    "settings": {
        "theme": "light",
    },
    "payment": {
        "preferred_bank": "Wallet only (demo)",
    },
}

# ----------------------------
# Persistence helpers
# ----------------------------

def ensure_data_shape(data):
    if "wallet" not in data:
        data["wallet"] = {"balance_cents": 0, "last_updated": ""}
    if "cases" not in data:
        data["cases"] = deepcopy(DEFAULT_CASES)
    if "donations" not in data:
        data["donations"] = []
    if "autopay" not in data:
        data["autopay"] = {
            "enabled": False,
            "amount_cents": 100,
            "case_id": None,
            "last_run_ts": "",
        }
    if "friends" not in data:
        data["friends"] = []
    if "settings" not in data:
        data["settings"] = {"theme": "light"}
    if "payment" not in data:
        data["payment"] = {"preferred_bank": "Wallet only (demo)"}
    if data.get("user") and "streak_freeze_tokens" not in data["user"]:
        data["user"]["streak_freeze_tokens"] = 1
    return data

def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA)
        return json.loads(json.dumps(DEFAULT_DATA))
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ensure_data_shape(data)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ----------------------------
# Services
# ----------------------------

class WalletService:
    def __init__(self, data):
        self.data = data

    def add_funds(self, dollars: float):
        add_cents = int(round(dollars * 100))
        if add_cents <= 0:
            raise ValueError("Amount must be greater than 0.")
        self.data["wallet"]["balance_cents"] += add_cents
        self.data["wallet"]["last_updated"] = now_iso()
        save_data(self.data)

    def can_donate(self, cents: int) -> bool:
        return self.data["wallet"]["balance_cents"] >= cents

    def deduct(self, cents: int):
        if not self.can_donate(cents):
            raise ValueError("Insufficient funds.")
        self.data["wallet"]["balance_cents"] -= cents
        self.data["wallet"]["last_updated"] = now_iso()

class CaseService:
    def __init__(self, data):
        self.data = data

    def list_cases(self):
        return self.data["cases"]

    def find_case(self, case_id):
        return next((c for c in self.data["cases"] if c["case_id"] == case_id), None)

    def get_next_open_case_id(self, exclude_case_id=None):
        for c in self.data["cases"]:
            if c["status"] == "Open" and c["case_id"] != exclude_case_id:
                return c["case_id"]
        return None

    def donate(self, case_id, cents):
        WalletService(self.data).deduct(cents)

        case = self.find_case(case_id)
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

        update_streak_on_donate(self.data)
        save_data(self.data)

# ----------------------------
# Autopay logic
# ----------------------------

def check_and_run_autopay(data):
    autopay = data.get("autopay") or {}
    if not autopay.get("enabled"):
        return False

    amount_cents = int(autopay.get("amount_cents") or 0)
    if amount_cents <= 0:
        return False

    case_service = CaseService(data)
    case_id = autopay.get("case_id")
    case = case_service.find_case(case_id) if case_id else None

    if not case or case.get("status") != "Open":
        new_id = case_service.get_next_open_case_id(exclude_case_id=case_id)
        if not new_id:
            return False
        autopay["case_id"] = new_id
        case_id = new_id
        case = case_service.find_case(case_id)

    last_ts_str = autopay.get("last_run_ts")
    now = datetime.datetime.now()
    if last_ts_str:
        try:
            last_ts = datetime.datetime.fromisoformat(last_ts_str)
            if (now - last_ts).total_seconds() < 24 * 3600:
                return False
        except Exception:
            pass

    wallet = data.get("wallet") or {}
    if wallet.get("balance_cents", 0) < amount_cents:
        return False

    case_service.donate(case_id, amount_cents)
    autopay["last_run_ts"] = now.isoformat(timespec="seconds")

    if case.get("status") != "Open":
        next_id = case_service.get_next_open_case_id(exclude_case_id=case_id)
        autopay["case_id"] = next_id

    data["autopay"] = autopay
    save_data(data)
    return True

# ----------------------------
# Auth screens (start / signup / login)
# ----------------------------

class StartScreen(ttk.Frame):
    def __init__(self, master, has_user, on_create, on_login):
        super().__init__(master, style="App.TFrame")
        self.on_create = on_create
        self.on_login = on_login

        container = ttk.Frame(self, style="App.TFrame", padding=40)
        container.pack(expand=True, fill=tk.BOTH)

        card = ttk.Frame(container, style="Card.TFrame", padding=40)
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.7)

        card.columnconfigure(0, weight=3)
        card.columnconfigure(1, weight=2)

        left = ttk.Frame(card, style="Card.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 40))

        ttk.Label(left, text="GiveOne", style="HeroTitle.TLabel") \
            .pack(anchor="w", pady=(0, 8))
        ttk.Label(
            left,
            text="Turn $1 a day into support for hospital, mental health, and education cases.",
            style="HeroSub.TLabel",
            wraplength=500,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))
        ttk.Label(
            left,
            text="• Daily streaks and auto-pay\n"
                 "• Cases from major US hospitals (demo data)\n"
                 "• Wallet, history, and friend leaderboard\n"
                 "• Local-only demo (no real payments)",
            style="Body.TLabel",
            justify="left",
        ).pack(anchor="w")

        right = ttk.Frame(card, style="Card.TFrame")
        right.grid(row=0, column=1, sticky="nsew")

        ttk.Label(right, text="Welcome", style="Title.TLabel") \
            .pack(anchor="w", pady=(0, 10))
        ttk.Label(
            right,
            text="Create a local account or sign in if you already set one up.",
            style="Body.TLabel",
            wraplength=340,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))

        ttk.Button(right, text="Create an account", style="Accent.TButton",
                   command=self.on_create) \
            .pack(anchor="w", pady=(0, 10), ipadx=10, ipady=4)

        login_btn = ttk.Button(right, text="Already a member", style="Ghost.TButton",
                               command=self.on_login)
        if not has_user:
            login_btn.state(["disabled"])
        login_btn.pack(anchor="w", pady=(2, 0), ipadx=10, ipady=4)

        self.pack(fill=tk.BOTH, expand=True)

class SignupScreen(ttk.Frame):
    def __init__(self, master, on_done, on_back):
        super().__init__(master, style="App.TFrame")
        self.on_done = on_done
        self.on_back = on_back

        container = ttk.Frame(self, style="App.TFrame", padding=40)
        container.pack(expand=True, fill=tk.BOTH)

        card = ttk.Frame(container, style="Card.TFrame", padding=36)
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.7)

        card.columnconfigure(0, weight=3)
        card.columnconfigure(1, weight=2)

        left = ttk.Frame(card, style="Card.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 40))

        ttk.Label(left, text="Create your GiveOne account", style="HeroTitle.TLabel") \
            .pack(anchor="w", pady=(0, 8))
        ttk.Label(
            left,
            text="We’ll keep your streak, wallet, and giving history locally on this device.",
            style="HeroSub.TLabel",
            wraplength=500,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))
        ttk.Label(
            left,
            text="No real money moves in this demo — it’s safe to click around.",
            style="Hint.TLabel",
        ).pack(anchor="w")

        right = ttk.Frame(card, style="Card.TFrame")
        right.grid(row=0, column=1, sticky="nsew")

        self.fn = tk.StringVar()
        self.ln = tk.StringVar()
        self.un = tk.StringVar()
        self.em = tk.StringVar()
        self.pw = tk.StringVar()

        ttk.Label(right, text="Sign up", style="Title.TLabel") \
            .grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        def add_field(row, label, var, hint=None, is_password=False):
            ttk.Label(right, text=label, style="Body.TLabel") \
                .grid(row=row, column=0, sticky="w", pady=(6, 0))
            entry = ttk.Entry(
                right,
                textvariable=var,
                width=30,
                show="•" if is_password else None,
            )
            entry.grid(row=row, column=1, sticky="ew", pady=(6, 0))
            if hint:
                ttk.Label(right, text=hint, style="Hint.TLabel") \
                    .grid(row=row+1, column=1, sticky="w", pady=(0, 2))

        add_field(1, "First name", self.fn, "e.g., Ahmed")
        add_field(3, "Last name", self.ln, "e.g., Shady")
        add_field(5, "Username", self.un, "e.g., shady_ahmed")
        add_field(7, "Email", self.em, "e.g., you@example.com")
        add_field(9, "Password", self.pw, "At least 6 characters", is_password=True)

        btn_row = ttk.Frame(right, style="Card.TFrame")
        btn_row.grid(row=11, column=0, columnspan=2, pady=(16, 0), sticky="w")

        ttk.Button(btn_row, text="Back", style="Ghost.TButton",
                   command=self.on_back) \
            .pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_row, text="Create account", style="Accent.TButton",
                   command=self._create) \
            .pack(side=tk.LEFT)

        right.columnconfigure(1, weight=1)
        self.pack(fill=tk.BOTH, expand=True)

    def _create(self):
        fn, ln, un, em, pw = (
            self.fn.get().strip(),
            self.ln.get().strip(),
            self.un.get().strip(),
            self.em.get().strip(),
            self.pw.get().strip(),
        )
        if not (fn and ln and em and pw):
            messagebox.showwarning("Missing info", "Please fill at least your name, email, and password.")
            return
        if not un:
            un = em.split("@")[0]

        invite_seed = f"{em}-{now_iso()}"
        invite_code = "GV1-" + sha256(invite_seed)[:6].upper()

        user = {
            "user_id": 1,
            "first_name": fn,
            "last_name": ln,
            "username": un,
            "email": em,
            "password_hash": sha256(pw),
            "created_at": now_iso(),
            "streak_days": 0,
            "streak_last_ts": "",
            "streak_freeze_tokens": 1,
            "invite_code": invite_code,
        }
        self.on_done(user)

class LoginScreen(ttk.Frame):
    def __init__(self, master, on_login, on_back):
        super().__init__(master, style="App.TFrame")
        self.on_login = on_login
        self.on_back = on_back

        container = ttk.Frame(self, style="App.TFrame", padding=40)
        container.pack(expand=True, fill=tk.BOTH)

        card = ttk.Frame(container, style="Card.TFrame", padding=36)
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.7, relheight=0.55)

        card.columnconfigure(0, weight=2)
        card.columnconfigure(1, weight=3)

        left = ttk.Frame(card, style="Card.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 36))

        ttk.Label(left, text="Welcome back", style="HeroTitle.TLabel") \
            .pack(anchor="w", pady=(0, 8))
        ttk.Label(
            left,
            text="Pick up your streak, wallet, and cases exactly where you left off.",
            style="HeroSub.TLabel",
            wraplength=360,
            justify="left",
        ).pack(anchor="w")

        right = ttk.Frame(card, style="Card.TFrame")
        right.grid(row=0, column=1, sticky="nsew")

        self.em = tk.StringVar()
        self.pw = tk.StringVar()

        ttk.Label(right, text="Sign in", style="Title.TLabel") \
            .grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(right, text="Email", style="Body.TLabel") \
            .grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(right, textvariable=self.em, width=30) \
            .grid(row=1, column=1, sticky="ew", pady=(6, 0))
        ttk.Label(right, text="Use the same email you signed up with.", style="Hint.TLabel") \
            .grid(row=2, column=1, sticky="w", pady=(0, 2))

        ttk.Label(right, text="Password", style="Body.TLabel") \
            .grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(right, textvariable=self.pw, width=30, show="•") \
            .grid(row=3, column=1, sticky="ew", pady=(6, 0))
        ttk.Label(right, text="Exact match, including capitalization.", style="Hint.TLabel") \
            .grid(row=4, column=1, sticky="w", pady=(0, 2))

        btn_row = ttk.Frame(right, style="Card.TFrame")
        btn_row.grid(row=5, column=0, columnspan=2, pady=(18, 0), sticky="w")

        ttk.Button(btn_row, text="Back", style="Ghost.TButton",
                   command=self.on_back) \
            .pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_row, text="Sign in", style="Accent.TButton",
                   command=self._submit) \
            .pack(side=tk.LEFT)

        right.columnconfigure(1, weight=1)
        self.pack(fill=tk.BOTH, expand=True)

    def _submit(self):
        self.on_login(self.em.get().strip(), self.pw.get().strip())

# ----------------------------
# Main App
# ----------------------------

class GiveOneApp(ttk.Frame):
    def __init__(self, master, data):
        super().__init__(master)
        self.master = master
        self.data = ensure_data_shape(data)
        self.case_service = CaseService(self.data)
        self.wallet_service = WalletService(self.data)
        self.case_images = {}

        self.master.title("GiveOne — Daily Micro-Donations")
        self.master.geometry("1360x820")
        self.master.minsize(1280, 760)

        try:
            # make everything bigger on high-res displays
            self.master.tk.call("tk", "scaling", 1.5)
        except tk.TclError:
            pass

        self._build_style()
        self.pack(fill=tk.BOTH, expand=True)

        if self.data["user"] is None:
            self._route_start()
        else:
            self._route_main_shell()

    # ----------------------------
    # Styling
    # ----------------------------

    def _build_style(self):
        style = ttk.Style(self.master)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # ---------- New color palette (modern emerald/teal) ----------
        app_bg      = "#f4f4f5"   # neutral-100
        sidebar_bg  = "#ffffff"
        card_bg     = "#ffffff"
        header_bg   = "#ffffff"
        border_grey = "#e4e4e7"   # neutral-200

        text_main   = "#020617"   # slate-950
        text_muted  = "#6b7280"   # gray-500
        text_subtle = "#a1a1aa"   # zinc-400

        accent         = "#10b981"   # emerald-500
        accent_hover   = "#059669"   # emerald-600
        accent_soft    = "#ecfdf5"   # emerald-50

        style.configure("App.TFrame", background=app_bg)
        style.configure(
            "Card.TFrame",
            background=card_bg,
            borderwidth=1,
            relief="solid",
            bordercolor=border_grey,
        )
        style.configure("Header.TFrame", background=header_bg, borderwidth=0)
        style.configure("Sidebar.TFrame", background=sidebar_bg, borderwidth=0)

        # Typography
        style.configure(
            "HeroTitle.TLabel",
            background=card_bg,
            foreground=text_main,
            font=("Segoe UI", 28, "bold"),
        )
        style.configure(
            "HeroSub.TLabel",
            background=card_bg,
            foreground=text_muted,
            font=("Segoe UI", 12),
        )
        style.configure(
            "Title.TLabel",
            background=card_bg,
            foreground=text_main,
            font=("Segoe UI", 20, "bold"),
        )
        style.configure(
            "Body.TLabel",
            background=card_bg,
            foreground=text_main,
            font=("Segoe UI", 13),
        )
        style.configure(
            "Hint.TLabel",
            background=card_bg,
            foreground=text_subtle,
            font=("Segoe UI", 10),
        )

        style.configure(
            "HeaderTitle.TLabel",
            background=header_bg,
            foreground=text_main,
            font=("Segoe UI", 20, "bold"),
        )
        style.configure(
            "HeaderSub.TLabel",
            background=header_bg,
            foreground=text_muted,
            font=("Segoe UI", 11),
        )
        style.configure(
            "HeaderMetric.TLabel",
            background=header_bg,
            foreground=accent,
            font=("Segoe UI", 13, "bold"),
        )

        style.configure(
            "CardTitle.TLabel",
            background=card_bg,
            foreground=text_main,
            font=("Segoe UI", 15, "bold"),
        )
        style.configure(
            "CardBody.TLabel",
            background=card_bg,
            foreground=text_main,
            font=("Segoe UI", 13),
        )

        style.configure(
            "Tag.TLabel",
            background=accent_soft,
            foreground=accent,
            font=("Segoe UI", 10, "bold"),
            padding=(8, 3),
        )

        # Buttons
        style.configure(
            "Accent.TButton",
            font=("Segoe UI", 12, "bold"),
            padding=(14, 8),
            background=accent,
            foreground="#ffffff",
            borderwidth=0,
        )
        style.map(
            "Accent.TButton",
            background=[("active", accent_hover), ("pressed", accent_hover)],
            relief=[("pressed", "sunken")],
        )

        style.configure(
            "Ghost.TButton",
            font=("Segoe UI", 12),
            padding=(10, 6),
            background=card_bg,
            foreground=text_main,
            borderwidth=1,
            relief="solid",
        )
        style.map(
            "Ghost.TButton",
            background=[("active", "#e5e7eb"), ("pressed", "#e5e7eb")],
            bordercolor=[("active", accent)],
        )

        style.configure(
            "Nav.TButton",
            font=("Segoe UI", 12, "bold"),
            padding=(14, 8),
            background=sidebar_bg,
            foreground=text_muted,
            borderwidth=0,
            anchor="w",
        )
        style.map(
            "Nav.TButton",
            background=[("active", "#e5e7eb")],
            foreground=[("active", text_main)],
        )

        style.configure(
            "NavSelected.TButton",
            font=("Segoe UI", 12, "bold"),
            padding=(14, 8),
            background=accent_soft,
            foreground=accent,
            borderwidth=0,
            anchor="w",
        )

        # Treeview
        style.configure(
            "Treeview",
            background=card_bg,
            fieldbackground=card_bg,
            foreground=text_main,
            font=("Segoe UI", 12),
            rowheight=30,
            bordercolor=border_grey,
            borderwidth=1,
        )
        style.configure(
            "Treeview.Heading",
            background="#f3f4f6",
            foreground=text_main,
            font=("Segoe UI", 12, "bold"),
        )

        # Progress bar (thicker + emerald color)
        style.configure(
            "Funding.Horizontal.TProgressbar",
            troughcolor="#e5e7eb",
            background=accent,
            thickness=14,
            bordercolor="#e5e7eb",
            borderwidth=0,
        )

        self.configure(style="App.TFrame")
        self.master.configure(background=app_bg)

    # ----------------------------
    # Routing
    # ----------------------------

    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    def _route_start(self):
        self._clear()
        has_user = self.data.get("user") is not None
        StartScreen(self, has_user, self._show_signup, self._show_login)

    def _show_signup(self):
        self._clear()
        SignupScreen(self, self._finish_signup, self._route_start)

    def _show_login(self):
        self._clear()
        LoginScreen(self, self._handle_login, self._route_start)

    def _handle_login(self, email, password):
        user = self.data.get("user")
        if not user:
            messagebox.showerror("Sign in", "No local user found. Please create an account.")
            return
        if email.strip().lower() != user.get("email", "").lower() or sha256(password) != user.get("password_hash"):
            messagebox.showerror("Sign in", "Email or password is incorrect.")
            return
        self._route_main_shell()

    def _finish_signup(self, user):
        self.data["user"] = user
        self.data["wallet"] = {"balance_cents": 0, "last_updated": now_iso()}
        self.data["cases"] = deepcopy(DEFAULT_CASES)
        self.data["donations"] = []
        self.data["autopay"] = {
            "enabled": False,
            "amount_cents": 100,
            "case_id": None,
            "last_run_ts": "",
        }
        self.data["friends"] = []
        self.data["settings"] = {"theme": "light"}
        self.data["payment"] = {"preferred_bank": "Wallet only (demo)"}
        save_data(self.data)
        self._route_main_shell()

    # ----------------------------
    # Main shell (header + sidebar + content)
    # ----------------------------

    def _route_main_shell(self):
        self._clear()

        shell = ttk.Frame(self, style="App.TFrame")
        shell.pack(fill=tk.BOTH, expand=True)

        # Header
        self.header = ttk.Frame(shell, style="Header.TFrame", padding=(20, 14))
        self.header.pack(side=tk.TOP, fill=tk.X)

        user = self.data.get("user") or {}
        name = user.get("first_name") or "Friend"

        left = ttk.Frame(self.header, style="Header.TFrame")
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(left, text=f"Hey, {name}", style="HeaderTitle.TLabel") \
            .pack(anchor="w")
        self.header_sub_var = tk.StringVar(value="Build a daily giving habit with $1 at a time.")
        ttk.Label(left, textvariable=self.header_sub_var, style="HeaderSub.TLabel") \
            .pack(anchor="w", pady=(2, 0))

        right = ttk.Frame(self.header, style="Header.TFrame")
        right.pack(side=tk.RIGHT)

        self.header_balance_var = tk.StringVar(value="Balance: $0.00")
        ttk.Label(right, textvariable=self.header_balance_var, style="HeaderMetric.TLabel") \
            .pack(anchor="e")

        self.header_streak_var = tk.StringVar(value="Streak: 0 days")
        ttk.Label(right, textvariable=self.header_streak_var, style="HeaderSub.TLabel") \
            .pack(anchor="e")

        btn_row = ttk.Frame(right, style="Header.TFrame")
        btn_row.pack(anchor="e", pady=(6, 0))
        ttk.Button(btn_row, text="Refresh", style="Ghost.TButton",
                   command=self.refresh_all) \
            .pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(btn_row, text="Reset demo", style="Ghost.TButton",
                   command=self._reset_demo) \
            .pack(side=tk.RIGHT)

        # Body: sidebar + content
        body = ttk.Frame(shell, style="App.TFrame")
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.sidebar = ttk.Frame(body, style="Sidebar.TFrame", width=220, padding=(16, 16))
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        self.content = ttk.Frame(body, style="App.TFrame", padding=(8, 8))
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Sidebar nav
        ttk.Label(self.sidebar, text="GiveOne", style="HeroSub.TLabel") \
            .pack(anchor="w", pady=(0, 12))

        self.nav_buttons = {}
        self.pages = {}

        nav_items = [
            ("cases", "Cases"),
            ("wallet", "Wallet"),
            ("history", "History"),
            ("friends", "Friends"),
            ("settings", "Settings"),
        ]

        for key, label in nav_items:
            btn = ttk.Button(
                self.sidebar,
                text=label,
                style="Nav.TButton",
                command=lambda k=key: self._show_page(k),
            )
            btn.pack(fill=tk.X, pady=3)
            self.nav_buttons[key] = btn

        # Content pages
        self._build_pages()

        # initial data load
        self.refresh_all()
        self._show_page("cases")

    def _set_nav_selected(self, key):
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(style="NavSelected.TButton")
            else:
                btn.configure(style="Nav.TButton")

    def _build_pages(self):
        # Create frames for each page and place them stacked
        for key in ("cases", "wallet", "history", "friends", "settings"):
            frame = ttk.Frame(self.content, style="App.TFrame")
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.pages[key] = frame

        # Build page UIs
        self._build_cases_page(self.pages["cases"])
        self._build_wallet_page(self.pages["wallet"])
        self._build_history_page(self.pages["history"])
        self._build_friends_page(self.pages["friends"])
        self._build_settings_page(self.pages["settings"])

    def _show_page(self, key):
        for k, frame in self.pages.items():
            frame.lower()
        self.pages[key].lift()
        self._set_nav_selected(key)

    # ----------------------------
    # Cases page
    # ----------------------------

    def _build_cases_page(self, parent):
        wrapper = ttk.Frame(parent, style="App.TFrame", padding=4)
        wrapper.pack(fill=tk.BOTH, expand=True)

        # Top row: amount + filters
        top = ttk.Frame(wrapper, style="App.TFrame", padding=(4, 4, 4, 8))
        top.pack(fill=tk.X)

        left = ttk.Frame(top, style="App.TFrame")
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(left, text="Donation amount", style="Body.TLabel") \
            .pack(side=tk.LEFT, padx=(0, 8))

        self.amount_var = tk.StringVar(value="1.00")
        ttk.Entry(left, textvariable=self.amount_var, width=10, justify="right") \
            .pack(side=tk.LEFT, padx=(0, 6))

        for quick in (1, 5, 10, 20):
            ttk.Button(
                left,
                text=f"${quick}",
                style="Ghost.TButton",
                command=lambda q=quick: self.amount_var.set(f"{q:.2f}")
            ).pack(side=tk.LEFT, padx=2)

        right = ttk.Frame(top, style="App.TFrame")
        right.pack(side=tk.RIGHT)

        self.case_filter_category = tk.StringVar(value="All")
        self.case_filter_search = tk.StringVar()

        ttk.Label(right, text="Category:", style="Body.TLabel") \
            .pack(side=tk.LEFT, padx=(0, 6))
        self.category_combo = ttk.Combobox(
            right,
            textvariable=self.case_filter_category,
            values=["All"],
            state="readonly",
            width=18,
        )
        self.category_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.category_combo.bind("<<ComboboxSelected>>", lambda e: self._render_case_list())

        ttk.Entry(right, textvariable=self.case_filter_search, width=22) \
            .pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(right, text="Search", style="Ghost.TButton",
                   command=self._render_case_list) \
            .pack(side=tk.LEFT)

        # Scrollable area
        self.cases_canvas = tk.Canvas(wrapper, highlightthickness=0,
                                      bg="#f4f4f5", bd=0)
        self.cases_scroll = ttk.Scrollbar(wrapper, orient="vertical",
                                          command=self.cases_canvas.yview)
        self.cases_inner = ttk.Frame(self.cases_canvas, style="App.TFrame")

        self.cases_inner.bind(
            "<Configure>",
            lambda e: self.cases_canvas.configure(
                scrollregion=self.cases_canvas.bbox("all")
            )
        )
        self.cases_canvas.create_window((0, 0), window=self.cases_inner, anchor="nw")
        self.cases_canvas.configure(yscrollcommand=self.cases_scroll.set)

        self.cases_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.cases_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _render_case_list(self):
        for child in self.cases_inner.winfo_children():
            child.destroy()
        self.case_images.clear()

        term = (self.case_filter_search.get() or "").lower().strip()
        category = self.case_filter_category.get()

        for case in self.case_service.list_cases():
            if category != "All" and case.get("category") != category:
                continue
            if term:
                haystack = f"{case.get('title','')} {case.get('org_name','')} {case.get('description','')}".lower()
                if term not in haystack:
                    continue
            self._render_case_card(self.cases_inner, case)

    def _render_case_card(self, parent, case):
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.pack(fill=tk.X, expand=True, pady=8)

        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill=tk.X)

        img_path = case.get("image")
        if img_path and os.path.exists(img_path):
            try:
                img = tk.PhotoImage(file=img_path)
                self.case_images[case["case_id"]] = img
                ttk.Label(top, image=img, style="Card.TFrame") \
                    .pack(side=tk.LEFT, padx=(0, 14))
            except Exception:
                pass

        text_col = ttk.Frame(top, style="Card.TFrame")
        text_col.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(text_col, text=case["title"], style="CardTitle.TLabel") \
            .pack(anchor="w")
        sub = f"{case['org_name']} • {case.get('city','') or case.get('category','')}"
        ttk.Label(text_col, text=sub, style="HeroSub.TLabel") \
            .pack(anchor="w", pady=(2, 2))

        tag_row = ttk.Frame(text_col, style="Card.TFrame")
        tag_row.pack(anchor="w", pady=(0, 4))
        ttk.Label(tag_row, text=case.get("category", "General"), style="Tag.TLabel") \
            .pack(side=tk.LEFT)

        ttk.Label(
            text_col,
            text=case["description"],
            style="CardBody.TLabel",
            wraplength=820,
            justify="left",
        ).pack(anchor="w", pady=(6, 6))

        pct = min(100, int((case["raised_cents"] / case["goal_cents"]) * 100)) if case["goal_cents"] else 0
        progress = ttk.Progressbar(
            card,
            orient="horizontal",
            mode="determinate",
            length=820,
            style="Funding.Horizontal.TProgressbar",
        )
        progress["value"] = pct
        progress.pack(anchor="w", pady=(2, 0))

        meta = (
            f"{pct}% funded • Goal {cents_to_dollars(case['goal_cents'])} • "
            f"Raised {cents_to_dollars(case['raised_cents'])} • Status: {case['status']}"
        )
        ttk.Label(card, text=meta, style="HeroSub.TLabel") \
            .pack(anchor="w", pady=(2, 8))

        bottom = ttk.Frame(card, style="Card.TFrame")
        bottom.pack(fill=tk.X)

        btn = ttk.Button(
            bottom,
            text="Donate now",
            style="Accent.TButton",
            command=lambda cid=case["case_id"]: self._donate_adjustable(cid),
        )
        btn.pack(side=tk.LEFT)

        if case["status"] not in ("Open",):
            btn.state(["disabled"])

    # ----------------------------
    # Wallet page
    # ----------------------------

    def _build_wallet_page(self, parent):
        frame = ttk.Frame(parent, style="App.TFrame", padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        # Wallet card
        wallet_card = ttk.Frame(frame, style="Card.TFrame", padding=18)
        wallet_card.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(wallet_card, text="Wallet", style="Title.TLabel") \
            .pack(anchor="w", pady=(0, 4))
        self.wallet_balance_var = tk.StringVar(value="Current balance: $0.00")
        ttk.Label(wallet_card, textvariable=self.wallet_balance_var, style="Body.TLabel") \
            .pack(anchor="w")

        ttk.Button(wallet_card, text="Add funds…", style="Accent.TButton",
                   command=self._prompt_add_funds) \
            .pack(anchor="w", pady=(10, 0))

        ttk.Label(
            wallet_card,
            text="This is a simulated wallet just for the demo. No real payments happen.",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(6, 0))

        # Auto-pay card
        autopay_card = ttk.Frame(frame, style="Card.TFrame", padding=18)
        autopay_card.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(autopay_card, text="Daily auto-pay", style="Title.TLabel") \
            .pack(anchor="w", pady=(0, 4))
        ttk.Label(
            autopay_card,
            text="Auto-donate a fixed amount every 24 hours to an open case.",
            style="Body.TLabel",
            wraplength=820,
        ).pack(anchor="w", pady=(0, 8))

        row = ttk.Frame(autopay_card, style="Card.TFrame")
        row.pack(anchor="w", pady=(0, 4))

        self.autopay_enabled_var = tk.BooleanVar(value=False)
        self.autopay_amount_var = tk.StringVar(value="1.00")
        self.autopay_case_var = tk.StringVar(value="(auto-pick)")

        ttk.Checkbutton(
            row,
            text="Enable auto-pay",
            variable=self.autopay_enabled_var,
            command=self._update_autopay_from_ui,
        ).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(row, text="Amount", style="Body.TLabel") \
            .pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.autopay_amount_var,
                  width=8, justify="right") \
            .pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(row, text="Case", style="Body.TLabel") \
            .pack(side=tk.LEFT)
        self.autopay_case_combo = ttk.Combobox(
            row,
            textvariable=self.autopay_case_var,
            state="readonly",
            width=40,
        )
        self.autopay_case_combo.pack(side=tk.LEFT, padx=(4, 0))
        self.autopay_case_combo.bind("<<ComboboxSelected>>", lambda e: self._update_autopay_from_ui())

        self.autopay_status_var = tk.StringVar(value="Auto-pay status: Off")
        ttk.Label(autopay_card, textvariable=self.autopay_status_var, style="Hint.TLabel") \
            .pack(anchor="w", pady=(6, 0))

        # Payment methods card
        pm_card = ttk.Frame(frame, style="Card.TFrame", padding=18)
        pm_card.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(pm_card, text="Payment methods (demo)", style="Title.TLabel") \
            .pack(anchor="w", pady=(0, 4))
        ttk.Label(
            pm_card,
            text="Choose a preferred funding source. In this demo, everything is still simulated and local.",
            style="Body.TLabel",
            wraplength=820,
        ).pack(anchor="w", pady=(0, 8))

        row2 = ttk.Frame(pm_card, style="Card.TFrame")
        row2.pack(anchor="w", pady=(0, 6))

        ttk.Label(row2, text="Preferred funding source", style="Body.TLabel") \
            .pack(side=tk.LEFT, padx=(0, 8))

        self.preferred_bank_var = tk.StringVar(value="Wallet only (demo)")
        self.bank_combo = ttk.Combobox(
            row2,
            textvariable=self.preferred_bank_var,
            state="readonly",
            width=28,
            values=[
                "Wallet only (demo)",
                "Fifth Third Bank",
                "Chase",
                "Bank of America",
                "Wells Fargo",
                "Capital One",
            ],
        )
        self.bank_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.bank_combo.bind("<<ComboboxSelected>>", lambda e: self._update_payment_from_ui())

        ttk.Button(row2, text="Save", style="Ghost.TButton",
                   command=self._update_payment_from_ui) \
            .pack(side=tk.LEFT)

        self.payment_status_var = tk.StringVar(value="Funding source: Wallet only (demo)")
        ttk.Label(pm_card, textvariable=self.payment_status_var, style="Hint.TLabel") \
            .pack(anchor="w", pady=(4, 8))

        row3 = ttk.Frame(pm_card, style="Card.TFrame")
        row3.pack(anchor="w")

        ttk.Button(row3, text="Connect Stripe (demo)", style="Ghost.TButton",
                   command=lambda: messagebox.showinfo("Demo", "Stripe connection is UI-only in this demo.")) \
            .pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row3, text="Add Apple Pay (demo)", style="Ghost.TButton",
                   command=lambda: messagebox.showinfo("Demo", "Apple Pay is UI-only in this demo.")) \
            .pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row3, text="Link Fifth Third (demo)", style="Ghost.TButton",
                   command=lambda: messagebox.showinfo("Demo", "Bank linking is UI-only in this demo.")) \
            .pack(side=tk.LEFT)

    def _update_payment_from_ui(self):
        payment = self.data.get("payment") or {}
        bank = self.preferred_bank_var.get() or "Wallet only (demo)"
        payment["preferred_bank"] = bank
        self.data["payment"] = payment
        save_data(self.data)
        self.payment_status_var.set(f"Funding source: {bank}")
        self._refresh_autopay_status_text()

    def _update_autopay_from_ui(self):
        autopay = self.data.get("autopay") or {}
        autopay["enabled"] = bool(self.autopay_enabled_var.get())

        try:
            amt = float(self.autopay_amount_var.get().strip())
            autopay["amount_cents"] = int(round(amt * 100))
        except Exception:
            autopay["amount_cents"] = 100

        label = self.autopay_case_var.get()
        if label == "(auto-pick)":
            autopay["case_id"] = None
        else:
            if label.endswith("]") and "[" in label:
                try:
                    case_id_str = label.split("[")[-1].rstrip("]")
                    autopay["case_id"] = int(case_id_str)
                except Exception:
                    autopay["case_id"] = None
            else:
                autopay["case_id"] = None

        self.data["autopay"] = autopay
        save_data(self.data)
        self._refresh_autopay_status_text()

    def _refresh_autopay_status_text(self):
        autopay = self.data.get("autopay") or {}
        payment = self.data.get("payment") or {}
        bank = payment.get("preferred_bank", "Wallet only (demo)")
        if not autopay.get("enabled"):
            self.autopay_status_var.set(f"Auto-pay status: Off • Funding source: {bank}")
            return
        amt = cents_to_dollars(int(autopay.get("amount_cents") or 0))
        case_id = autopay.get("case_id")
        case_label = "auto-pick next open case"
        if case_id:
            c = self.case_service.find_case(case_id)
            if c:
                case_label = c["title"]
        last_ts = autopay.get("last_run_ts") or "—"
        self.autopay_status_var.set(
            f"Auto-pay status: On • {amt} every 24h • Case: {case_label} • Bank: {bank} • Last run: {last_ts}"
        )

    # ----------------------------
    # History page
    # ----------------------------

    def _build_history_page(self, parent):
        frame = ttk.Frame(parent, style="App.TFrame", padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        card = ttk.Frame(frame, style="Card.TFrame", padding=16)
        card.pack(fill=tk.BOTH, expand=True)

        ttk.Label(card, text="Donation history", style="Title.TLabel") \
            .pack(anchor="w", pady=(0, 8))

        cols = ("time", "case", "amount", "balance_after")
        self.tree = ttk.Treeview(card, columns=cols, show="headings", height=16)
        for c, w in zip(cols, (200, 420, 120, 160)):
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=w, anchor=("e" if c != "case" else "w"))
        self.tree.pack(fill=tk.BOTH, expand=True)

    # ----------------------------
    # Friends page (leaderboard)
    # ----------------------------

    def _build_friends_page(self, parent):
        frame = ttk.Frame(parent, style="App.TFrame", padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        card = ttk.Frame(frame, style="Card.TFrame", padding=16)
        card.pack(fill=tk.BOTH, expand=True)

        header_row = ttk.Frame(card, style="Card.TFrame")
        header_row.pack(fill=tk.X)

        ttk.Label(header_row, text="Friends & leaderboard", style="Title.TLabel") \
            .pack(side=tk.LEFT, pady=(0, 8))

        ttk.Button(header_row, text="Add friend", style="Accent.TButton",
                   command=self._add_friend) \
            .pack(side=tk.RIGHT)

        ttk.Label(
            card,
            text="Add friends by username and compare streaks. (Everything stays local on this device.)",
            style="Body.TLabel",
            wraplength=820,
        ).pack(anchor="w", pady=(4, 12))

        cols = ("rank", "name", "streak")
        self.lb_tree = ttk.Treeview(card, columns=cols, show="headings", height=12)
        self.lb_tree.heading("rank", text="#")
        self.lb_tree.heading("name", text="Name / Username")
        self.lb_tree.heading("streak", text="Streak (days)")
        self.lb_tree.column("rank", width=40, anchor="center")
        self.lb_tree.column("name", width=420, anchor="w")
        self.lb_tree.column("streak", width=160, anchor="center")
        self.lb_tree.pack(fill=tk.BOTH, expand=True)

    def _add_friend(self):
        username = simpledialog.askstring("Add friend", "Friend's username (e.g., shady_ahmed):")
        if not username:
            return
        try:
            streak = simpledialog.askinteger("Add friend", "Friend's streak (days):", minvalue=0, maxvalue=365)
            if streak is None:
                streak = 0
        except Exception:
            streak = 0

        friends = self.data.get("friends") or []
        friends.append({"username": username.strip(), "streak_days": int(streak)})
        self.data["friends"] = friends
        save_data(self.data)
        self._refresh_leaderboard()

    # ----------------------------
    # Settings page
    # ----------------------------

    def _build_settings_page(self, parent):
        frame = ttk.Frame(parent, style="App.TFrame", padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        card = ttk.Frame(frame, style="Card.TFrame", padding=16)
        card.pack(fill=tk.BOTH, expand=True)

        ttk.Label(card, text="Settings", style="Title.TLabel") \
            .pack(anchor="w", pady=(0, 8))

        user = self.data.get("user") or {}

        profile = ttk.Frame(card, style="Card.TFrame", padding=12)
        profile.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(profile, text="Profile", style="CardTitle.TLabel") \
            .pack(anchor="w", pady=(0, 4))

        full_name = f"{user.get('first_name','')} {user.get('last_name','')}".strip()
        ttk.Label(profile, text=f"Name: {full_name}", style="Body.TLabel") \
            .pack(anchor="w")
        ttk.Label(profile, text=f"Username: {user.get('username','')}", style="Body.TLabel") \
            .pack(anchor="w")
        ttk.Label(profile, text=f"Email: {user.get('email','')}", style="Body.TLabel") \
            .pack(anchor="w")
        ttk.Label(profile, text=f"Invite code: {user.get('invite_code','')}", style="Body.TLabel") \
            .pack(anchor="w")

        export = ttk.Frame(card, style="Card.TFrame", padding=12)
        export.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(export, text="Export data", style="CardTitle.TLabel") \
            .pack(anchor="w", pady=(0, 4))
        ttk.Label(
            export,
            text="Export your local data (user, wallet, cases, donations, friends) into a JSON file.",
            style="Body.TLabel",
            wraplength=820,
        ).pack(anchor="w", pady=(0, 8))
        ttk.Button(export, text="Export JSON", style="Ghost.TButton",
                   command=self._export_data) \
            .pack(anchor="w")

    def _export_data(self):
        filename = f"giveone_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            messagebox.showinfo("Export", f"Exported data to {filename}")
        except Exception as e:
            messagebox.showerror("Export", f"Could not export data: {e}")

    # ----------------------------
    # Actions
    # ----------------------------

    def _reset_demo(self):
        if not messagebox.askyesno("Reset Demo", "Reset everything and return to the start screen?"):
            return
        fresh = json.loads(json.dumps(DEFAULT_DATA))
        save_data(fresh)
        self.data = ensure_data_shape(fresh)
        self._route_start()

    def _prompt_add_funds(self):
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
            case = self.case_service.find_case(case_id)
            if case and case["status"] == "Funded" and case["raised_cents"] >= case["goal_cents"]:
                messagebox.showinfo("🎉 Funded!", f"“{case['title']}” just reached its goal!")
            self.refresh_all()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ----------------------------
    # Refresh & leaderboard
    # ----------------------------

    def refresh_all(self):
        disk = load_data()
        self.data = ensure_data_shape(disk)
        self.case_service = CaseService(self.data)
        self.wallet_service = WalletService(self.data)

        break_streak_if_inactive(self.data)

        try:
            check_and_run_autopay(self.data)
        except Exception:
            pass

        bal = self.data["wallet"]["balance_cents"]
        month_total = month_donated_cents(self.data["donations"])
        user = self.data.get("user") or {}
        streak = user.get("streak_days", 0) or 0

        self.header_balance_var.set(f"Balance: {cents_to_dollars(bal)}")
        self.header_sub_var.set(f"This month you donated {cents_to_dollars(month_total)}")

        if streak == 0:
            self.header_streak_var.set("Streak: 0 days")
        elif streak == 1:
            self.header_streak_var.set("Streak: 1 day 🔥")
        else:
            self.header_streak_var.set(f"Streak: {streak} days 🔥")

        if hasattr(self, "wallet_balance_var"):
            self.wallet_balance_var.set(
                f"Current balance: {cents_to_dollars(bal)} • Updated: {self.data['wallet']['last_updated'] or '—'}"
            )

        if hasattr(self, "preferred_bank_var"):
            bank = self.data.get("payment", {}).get("preferred_bank", "Wallet only (demo)")
            self.preferred_bank_var.set(bank)
            self.payment_status_var.set(f"Funding source: {bank}")

        if hasattr(self, "autopay_case_combo"):
            options = ["(auto-pick)"]
            for c in self.case_service.list_cases():
                label = f"{c['title']} ({c.get('city','') or c.get('category','')}) [{c['case_id']}]"
                options.append(label)
            self.autopay_case_combo["values"] = options

            autopay = self.data.get("autopay") or {}
            self.autopay_enabled_var.set(bool(autopay.get("enabled")))
            amt = (autopay.get("amount_cents") or 100) / 100.0
            self.autopay_amount_var.set(f"{amt:.2f}")

            case_id = autopay.get("case_id")
            selected_label = "(auto-pick)"
            if case_id:
                for c in self.case_service.list_cases():
                    if c["case_id"] == case_id:
                        selected_label = f"{c['title']} ({c.get('city','') or c.get('category','')}) [{c['case_id']}]"
                        break
            self.autopay_case_var.set(selected_label)
            self._refresh_autopay_status_text()

        if hasattr(self, "category_combo"):
            cats = sorted({c.get("category", "Other") for c in self.case_service.list_cases()})
            values = ["All"] + cats
            self.category_combo["values"] = values
            if self.case_filter_category.get() not in values:
                self.case_filter_category.set("All")

        if hasattr(self, "cases_inner"):
            self._render_case_list()

        if hasattr(self, "tree"):
            for row in self.tree.get_children():
                self.tree.delete(row)
            name_by_id = {c["case_id"]: c["title"] for c in self.data["cases"]}
            for d in self.data["donations"][:250]:
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        d["timestamp"],
                        name_by_id.get(d["case_id"], f"Case {d['case_id']}"),
                        cents_to_dollars(d["amount_cents"]),
                        cents_to_dollars(d["running_balance_cents"]),
                    ),
                )

        self._refresh_leaderboard()

    def _refresh_leaderboard(self):
        if not hasattr(self, "lb_tree"):
            return
        for row in self.lb_tree.get_children():
            self.lb_tree.delete(row)

        entries = []
        user = self.data.get("user") or {}
        if user:
            entries.append({
                "name": f"{user.get('first_name','')} {user.get('last_name','')}".strip() or user.get("username","You"),
                "streak": user.get("streak_days", 0) or 0,
            })
        for f in self.data.get("friends") or []:
            entries.append({
                "name": f.get("username", "friend"),
                "streak": f.get("streak_days", 0) or 0,
            })

        entries.sort(key=lambda e: e["streak"], reverse=True)
        for i, e in enumerate(entries, start=1):
            self.lb_tree.insert("", tk.END, values=(i, e["name"], e["streak"]))

# ----------------------------
# App bootstrap
# ----------------------------

if __name__ == "__main__":
    data = load_data()
    root = tk.Tk()
    app = GiveOneApp(root, data)
    root.mainloop()
