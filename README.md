# GiveOne – Adjustable Donation App  
**CIS 434 – Software Engineering**  
**Developer:** Ahmed Shady  
**Semester:** Fall 2025  

---

## 📌 Overview  
GiveOne is a simple, micro-donation desktop application built using Python and Tkinter.  
Users can sign up, add funds to a wallet, browse donation cases, donate adjustable amounts (default $1), track total monthly donations, and view a complete donation history.  
All data is stored locally in a JSON file for persistence.

This project was developed as part of the CIS 434 Software Engineering course at Cleveland State University.

---

## 🧩 Features  
- **User Signup** (first name, last name, email, password)  
- **Wallet** with add-funds dialog  
- **Adjustable Donations** ($1, $5, $10, or custom)  
- **Empathetic Cases** with progress bars and story descriptions  
- **Monthly Total Display**  
- **Donation History Table**  
- **Refresh** to reload data  
- **Reset Demo** to wipe all data and restart  
- **Local JSON persistence**  

---

## 🛠 Technology Used  
- **Python 3.x**  
- **Tkinter (GUI)**  
- **JSON for data storage**  
- **Single-file implementation (`giveone_app.py`)**  
- **SHA-256 hashing for password storage (demo-level security)**  

---

## 📁 Project Structure  

```
/CIS434-Project-or-SoftwareEngineeringProject
│── README.md
│── giveone_app.py          main and only source file
│── giveone_data.json       auto-created on first run
│
└── docs/
      ├── Project Plan.pdf
      ├── SRS - GiveOne.pdf
      ├── SDS - GiveOne.pdf
      ├── Test Plan.pdf
      ├── Final Project Report.pdf
      ├── Use Case Specifications.pdf
      ├── Sequence Diagram.png
      └── Any additional diagrams

---

## ▶️ How to Run the Application  

### **1. Install Python 3.x**  
Make sure Python is installed on your computer.

### **2. Run the app**  
Open a terminal inside the project folder and run:

```
python giveone_app.py
```

### **3. On first launch**  
You will see the **signup screen**.  
After creating your account, you can:

- Add funds in the **Wallet** tab  
- Donate adjustable amounts in the **Cases** tab  
- View your donation **History**  
- Use **Refresh** or **Reset Demo**  

---

## 🧪 Testing  
All tests performed manually according to the Test Plan include:

- Signup → Wallet → Donate → History flow  
- Case reaches "Funded" state  
- Wallet updates correctly  
- History logs donation with timestamp & balance  
- Monthly total updates  
- Reset Demo restores all default values  

---

## 🚀 Future Improvements  
- Multi-user login  
- Real payment integration  
- Online backend and cloud sync  
- Organization dashboard for posting cases  
- Mobile app version  

---

## 📌 Repository  
This is the official repository for the project:  
**https://github.com/AhmedShady84/CIS434-Project-or-SoftwareEngineeringProject**

---

## 👤 Author  
**Ahmed Shady**  
Cleveland State University  
CIS 434 – Software Engineering  
