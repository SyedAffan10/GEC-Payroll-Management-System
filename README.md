# GEC Payroll Management System

A comprehensive employee payroll and HR management platform built with modern web technologies. Streamlined salary processing, payslip generation, and employee data management in one integrated solution.

---

## ✨ Features

### Employee Management
- Create and manage employee records
- Support for multiple employment types
- Employee ID generation and tracking
- Real-time employee database

### Salary & Payments
- Monthly salary tracking and calculations
- Multi-currency support (EUR and more)
- Flexible payment structures
- Deduction management

### Payslip Generation
- Automated payslip PDF generation
- Professional payslip templates
- Batch payslip processing
- Export capabilities

### Data Management
- SQLite database for reliable data storage
- Data backup and export functionality
- Excel file support for imports/exports
- Comprehensive data validation

### User Interface
- Intuitive Streamlit-based web interface
- Real-time data visualization
- Interactive dashboard
- Responsive design

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | Streamlit 1.48.0 |
| **Backend** | Python 3.12 |
| **Database** | SQLite3 |
| **Data Processing** | Pandas 2.3.1, NumPy 2.3.2 |
| **PDF Generation** | ReportLab 4.4.3 |
| **Excel Support** | OpenPyXL 3.1.5 |
| **Visualization** | Altair 5.5.0 |
| **Containerization** | Docker |

---

## 📋 Prerequisites

- Python 3.12 or higher
- pip (Python package manager)
- Docker & Docker Compose (optional, for containerized deployment)
- Modern web browser

---

## 🚀 Installation

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/SyedAffan10/GEC-Payroll-Management-System.git
   cd GEC-Payroll-Management-System
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Docker Setup

```bash
docker-compose up -d
```

---

## ⚡ Quick Start

### Run Locally

```bash
cd Code
streamlit run app.py
```

The application will be available at `http://localhost:8501`

### Run with Docker

```bash
docker-compose up
```

Access the application at `http://localhost:8501`

---

## 📁 Project Structure

```
GEC-Payroll-Management-System/
├── Code/
│   ├── app.py                 # Main Streamlit application
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile             # Docker configuration
│   ├── docker-compose.yml     # Docker Compose configuration
│   └── employees.db           # SQLite database (generated)
├── Samples/
│   ├── GEC monthly data.xlsx  # Sample monthly data
│   ├── GEC Payslip *.pdf      # Sample payslip templates
│   └── GEC template *.xlsx    # Sample timesheet templates
├── video/                     # Video documentation
└── README.md                  # This file
```

---

## 📝 License

This project is proprietary. All rights reserved.
