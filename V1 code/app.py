import io
import math
import datetime as dt
from typing import Dict, List, Tuple
import pandas as pd
import streamlit as st
import os
from pathlib import Path
import numpy as np
from zipfile import ZipFile, ZIP_DEFLATED

# Import the GEC parser
def parse_gec_timesheet(file_path_or_buffer, rate_mapping=None) -> pd.DataFrame:
    """
    Parse the GEC timesheet Excel format and return a normalized DataFrame
    """
    # Read the raw Excel data
    raw_df = pd.read_excel(file_path_or_buffer)
    
    # Extract employee information
    employee_name = None
    employee_no = None
    pay_period = None
    
    # Look for employee name
    for i, row in raw_df.iterrows():
        if pd.notna(row.iloc[0]) and 'Employee Name' in str(row.iloc[0]):
            if len(row) > 3 and pd.notna(row.iloc[3]):
                employee_name = str(row.iloc[3]).strip()
        
        # Look for pay period
        if pd.notna(row.iloc[0]) and 'Pay Period' in str(row.iloc[0]):
            if len(row) > 2 and pd.notna(row.iloc[2]):
                try:
                    pay_period = pd.to_datetime(row.iloc[2])
                except:
                    pass
    
    # Find the data start (look for date headers)
    data_start_row = None
    date_row = None
    
    for i, row in raw_df.iterrows():
        # Look for a row with multiple dates
        date_count = 0
        for j in range(3, min(len(row), 15)):  # Check columns 3-15 for dates
            try:
                if pd.notna(row.iloc[j]):
                    pd.to_datetime(row.iloc[j])
                    date_count += 1
            except:
                pass
        
        if date_count >= 3:  # Found a row with multiple dates
            date_row = i
            data_start_row = i + 1
            break
    
    if data_start_row is None:
        raise ValueError("Could not find data start row in timesheet")
    
    # Extract date headers
    date_headers = []
    if date_row is not None:
        for j in range(3, len(raw_df.columns)):
            try:
                if pd.notna(raw_df.iloc[date_row, j]):
                    date_val = pd.to_datetime(raw_df.iloc[date_row, j])
                    date_headers.append(date_val)
                else:
                    break
            except:
                break
    
    # Process data rows
    processed_data = []
    
    for i in range(data_start_row, len(raw_df)):
        row = raw_df.iloc[i]
        
        # Check if this row has meaningful data
        if pd.isna(row.iloc[0]) and pd.isna(row.iloc[2]):
            continue
            
        location = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        description = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
        
        if not location and not description:
            continue
            
        # Skip total rows
        if 'total' in location.lower():
            continue
            
        # Extract daily values
        for j, date_val in enumerate(date_headers):
            col_idx = j + 3  # Dates start from column 3
            if col_idx < len(row):
                value = row.iloc[col_idx]
                if pd.notna(value) and value != 0:
                    try:
                        hours = float(value)
                        if hours > 0:
                            processed_data.append({
                                'date': date_val,
                                'employee_name': employee_name or 'Unknown',
                                'employee_no': employee_no or '',
                                'location': location,
                                'description': description,
                                'units': hours,
                                'rate': 0.0,  # Will be calculated later
                                'amount': 0.0  # Will be calculated later
                            })
                    except (ValueError, TypeError):
                        pass
    
    if not processed_data:
        raise ValueError("No timesheet data found")
    
    # Create DataFrame
    df = pd.DataFrame(processed_data)
    
    # Get rate mapping from session state (will be set in UI)
    if rate_mapping is None:
        rate_mapping = {
            'days off': 350.0,
            'rig days': 400.0,
            'standby days': 200.0,
            'travel days': 350.0,
            'Bonus In Country': 150.0,
            'Premium In-country': 180.0,
            'bonus': 150.0,  # Fallback for bonus variations
            'premium': 180.0,  # Fallback for premium variations
        }
    
    # Apply rates with improved matching
    for desc, rate in rate_mapping.items():
        # Use case-insensitive partial matching with better logic
        desc_lower = desc.lower()
        mask = df['description'].str.lower().str.contains(desc_lower, na=False, regex=False)
        df.loc[mask, 'rate'] = rate
    
    # Special handling for partial matches that might not work with simple contains
    # Handle "Bonus In Country" variations
    bonus_mask = df['description'].str.lower().str.contains('bonus.*country', na=False, regex=True)
    df.loc[bonus_mask, 'rate'] = rate_mapping.get('Bonus In Country', 150.0)
    
    # Handle "Premium In-country" variations  
    premium_mask = df['description'].str.lower().str.contains('premium.*country', na=False, regex=True)
    df.loc[premium_mask, 'rate'] = rate_mapping.get('Premium In-country', 180.0)
    
    # Calculate amounts
    df['amount'] = df['units'] * df['rate']
    
    # Sort by date in ascending order
    df = df.sort_values('date', ascending=True).reset_index(drop=True)
    
    return df

def analyze_multiple_location_issue(df: pd.DataFrame) -> Dict:
    """
    Analyze the GEC timesheet for multiple location/rate type calculations on same day
    This addresses the issue where employees work 2 different roles in same day
    """
    analysis_results = {
        'has_multiple_entries': False,
        'problem_dates': [],
        'corrected_data': None,
        'original_total': 0.0,
        'corrected_total': 0.0,
        'summary': ""
    }
    
    if df.empty or 'date' not in df.columns:
        return analysis_results
    
    # Find dates with multiple entries for same employee
    if 'employee_name' in df.columns:
        daily_counts = df.groupby(['date', 'employee_name']).size()
        multiple_entry_dates = daily_counts[daily_counts > 1]
        
        if not multiple_entry_dates.empty:
            analysis_results['has_multiple_entries'] = True
            
            # Analyze each problem date
            for (date, employee), count in multiple_entry_dates.items():
                day_entries = df[(df['date'] == date) & (df['employee_name'] == employee)]
                
                original_total = day_entries['amount'].sum()
                entries_detail = []
                for _, row in day_entries.iterrows():
                    entries_detail.append({
                        'description': row.get('description', ''),
                        'units': row.get('units', 0),
                        'rate': row.get('rate', 0),
                        'amount': row.get('amount', 0)
                    })
                
                analysis_results['problem_dates'].append({
                    'date': date,
                    'employee': employee,
                    'entry_count': count,
                    'entries': entries_detail,
                    'total_amount': original_total,
                    'total_units': day_entries['units'].sum() if 'units' in day_entries.columns else 0
                })
            
            # Create corrected data - group by date and employee, sum amounts and calculate proper rates
            corrected_daily = df.groupby(['date', 'employee_name']).agg({
                'location': lambda x: ' + '.join(x.unique()) if len(x.unique()) > 1 else x.iloc[0],
                'units': 'sum',
                'amount': 'sum',
                'description': lambda x: ' + '.join(x) if len(x) > 1 else x.iloc[0]
            }).reset_index()
            
            # Calculate effective rate for multiple entries (amount/units)
            corrected_daily['rate'] = corrected_daily.apply(
                lambda row: round(row['amount'] / row['units'], 2) if row['units'] > 0 else 0, 
                axis=1
            )
            
            # Create a display-friendly version for showing rate details
            rate_details = df.groupby(['date', 'employee_name']).agg({
                'rate': lambda x: f"Multiple rates: {', '.join(map(str, x))}" if len(x) > 1 else f"{x.iloc[0]}"
            }).reset_index()
            
            corrected_daily['rate_info'] = rate_details['rate']
            
            analysis_results['corrected_data'] = corrected_daily
            analysis_results['original_total'] = df['amount'].sum()
            analysis_results['corrected_total'] = corrected_daily['amount'].sum()
            
            # Generate summary
            problem_count = len(analysis_results['problem_dates'])
            analysis_results['summary'] = f"Found {problem_count} dates with multiple entries that need correction."
    
    return analysis_results

def create_corrected_excel(df: pd.DataFrame, analysis: Dict, pay_period_end: dt.date) -> bytes:
    """
    Create an Excel file showing both the problem and corrected calculations
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Original data
        df_clean = df.copy()
        # Ensure all columns are properly formatted for Excel
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                df_clean[col] = df_clean[col].astype(str)
        df_clean.to_excel(writer, sheet_name="Original Data", index=False)
        
        # Problem analysis
        if analysis['has_multiple_entries']:
            problem_data = []
            for problem in analysis['problem_dates']:
                for entry in problem['entries']:
                    problem_data.append({
                        'Date': problem['date'].strftime('%Y-%m-%d') if hasattr(problem['date'], 'strftime') else str(problem['date']),
                        'Employee': str(problem['employee']),
                        'Description': str(entry['description']),
                        'Units': float(entry['units']) if entry['units'] else 0.0,
                        'Rate': float(entry['rate']) if entry['rate'] else 0.0,
                        'Amount': float(entry['amount']) if entry['amount'] else 0.0,
                        'Issue': 'Multiple entries for same date'
                    })
            
            if problem_data:
                problem_df = pd.DataFrame(problem_data)
                problem_df.to_excel(writer, sheet_name="Problem Analysis", index=False)
            
            # Corrected data
            if analysis['corrected_data'] is not None:
                corrected_clean = analysis['corrected_data'].copy()
                # Clean the corrected data for Excel export
                for col in corrected_clean.columns:
                    if col == 'date':
                        corrected_clean[col] = corrected_clean[col].dt.strftime('%Y-%m-%d')
                    elif corrected_clean[col].dtype == 'object':
                        corrected_clean[col] = corrected_clean[col].astype(str)
                    elif col in ['units', 'amount', 'rate']:
                        corrected_clean[col] = pd.to_numeric(corrected_clean[col], errors='coerce').fillna(0)
                
                corrected_clean.to_excel(writer, sheet_name="Corrected Daily Summary", index=False)
        
        # Instructions sheet
        instructions = pd.DataFrame({
            'Step': [
                '1. Issue Identification',
                '2. Problem Analysis',
                '3. Corrected Calculation',
                '4. Implementation'
            ],
            'Description': [
                'When employee works multiple roles in same day, amounts need to be summed',
                'Check "Problem Analysis" sheet for dates with multiple entries',
                'Check "Corrected Daily Summary" sheet for proper daily totals',
                'Use SUMIFS formula: =SUMIFS(Amount, Date, Target_Date, Employee, Target_Employee)'
            ]
        })
        instructions.to_excel(writer, sheet_name="Instructions", index=False)
        
        # Meta information
        meta = pd.DataFrame({
            "Field": ["Pay Period End", "Analysis Date", "Original Total", "Corrected Total", "Has Issues"],
            "Value": [
                pay_period_end.strftime("%d-%b-%Y"),
                dt.datetime.now().strftime("%d-%b-%Y %H:%M"),
                f"€{analysis['original_total']:,.2f}",
                f"€{analysis['corrected_total']:,.2f}",
                "Yes" if analysis['has_multiple_entries'] else "No"
            ]
        })
        meta.to_excel(writer, sheet_name="Meta", index=False)
    
    return output.getvalue()

# Optional but helpful: formatting money
def eur(x):
    try:
        return f"€ {x:,.2f}"
    except Exception:
        return x

# --- Heuristics to guess columns if headers differ slightly ---
CANDIDATES = {
    "date": ["date", "pay date", "paydate", "day", "txn date"],
    "employee_name": ["employee name", "name", "employee", "emp name"],
    "employee_no": ["employee no", "employee id", "emp id", "id", "number"],
    "location": ["location", "site", "office"],
    "description": ["description", "item", "earning type", "pay item", "narration"],
    "units": ["units", "qty", "quantity", "hours", "days"],
    "rate": ["rate", "unit rate", "amount per unit", "price"],
    "amount": ["amount", "total", "line total", "value"]
}

def normalize_cols(cols: List[str]) -> List[str]:
    return [c.strip().lower() for c in cols]

def auto_map_columns(df: pd.DataFrame) -> Dict[str, str]:
    colmap = {}
    low = normalize_cols(df.columns.tolist())
    for need, opts in CANDIDATES.items():
        mapped = None
        for cand in opts:
            if cand in low:
                mapped = df.columns[low.index(cand)]
                break
        # fallback: try partial contains
        if mapped is None:
            for i, c in enumerate(low):
                if any(cand in c for cand in opts):
                    mapped = df.columns[i]
                    break
        if mapped:
            colmap[need] = mapped
    return colmap

def coerce_numeric(s):
    if pd.isna(s):
        return 0.0
    try:
        s = str(s).replace(",", "").replace("€", "").strip()
        return float(s)
    except Exception:
        return pd.to_numeric(s, errors="coerce")

def prepare_frame(df: pd.DataFrame, mapping: Dict[str, str], rate_mapping=None) -> pd.DataFrame:
    # Keep only mapped cols
    keep = {k: v for k, v in mapping.items() if v in df.columns}
    out = df[list(keep.values())].copy()
    out.columns = list(keep.keys())

    # Parse date if present
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce")

    # Coerce numeric fields
    if "units" in out.columns:
        out["units"] = out["units"].apply(coerce_numeric)
    if "rate" in out.columns:
        out["rate"] = out["rate"].apply(coerce_numeric)
    if "amount" in out.columns:
        # If amount blank, compute units*rate
        out["amount"] = out["amount"].apply(coerce_numeric)
        needs_compute = out["amount"].isna() | (out["amount"] == 0)
        if "units" in out.columns and "rate" in out.columns:
            out.loc[needs_compute, "amount"] = out.loc[needs_compute, "units"] * out.loc[needs_compute, "rate"]
    else:
        # create amount if not given
        if "units" in out.columns and "rate" in out.columns:
            out["amount"] = out["units"] * out["rate"]

    # Apply rate mapping if provided and description column exists
    if rate_mapping and "description" in out.columns:
        # Apply rates based on description with improved matching
        for desc, rate in rate_mapping.items():
            # Use case-insensitive partial matching with better logic
            desc_lower = desc.lower()
            mask = out['description'].str.lower().str.contains(desc_lower, na=False, regex=False)
            if "rate" in out.columns:
                out.loc[mask, 'rate'] = rate
        
        # Special handling for partial matches that might not work with simple contains
        if "rate" in out.columns:
            # Handle "Bonus In Country" variations
            bonus_mask = out['description'].str.lower().str.contains('bonus.*country', na=False, regex=True)
            out.loc[bonus_mask, 'rate'] = rate_mapping.get('Bonus In Country', 150.0)
            
            # Handle "Premium In-country" variations  
            premium_mask = out['description'].str.lower().str.contains('premium.*country', na=False, regex=True)
            out.loc[premium_mask, 'rate'] = rate_mapping.get('Premium In-country', 180.0)
        
        # Recalculate amounts after applying rates
        if "units" in out.columns and "rate" in out.columns:
            out["amount"] = out["units"] * out["rate"]

    # Clean text cols
    for c in ["employee_name", "employee_no", "location", "description"]:
        if c in out.columns:
            out[c] = out[c].astype(str).str.strip()

    # Sort by date in ascending order if date column exists
    if "date" in out.columns:
        out = out.sort_values('date', ascending=True).reset_index(drop=True)

    return out


def split_by_employee(df: pd.DataFrame) -> List[Tuple[str, pd.DataFrame]]:
    # key = employee_no if exists else employee_name
    if "employee_no" in df.columns:
        keys = df["employee_no"].fillna("").astype(str)
        label_col = "employee_no"
    elif "employee_name" in df.columns:
        keys = df["employee_name"].fillna("").astype(str)
        label_col = "employee_name"
    else:
        # single batch
        return [("Unknown", df.copy())]
    groups = []
    for key, sub in df.groupby(keys):
        groups.append((f"{label_col}:{key}", sub.copy()))
    return groups

# --- PDF payslip generator using reportlab ---
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def draw_payslip_pdf(buff: io.BytesIO,
                     company: str,
                     location: str,
                     employee_no: str,
                     employee_name: str,
                     period_label: str,
                     lines: List[Tuple[str, float, float, float]],
                     deductions: List[Tuple[str, float]]):
    # lines: [(description, units, rate, amount), ...]
    # deductions: [(description, amount), ...] amount should be positive; we'll show as negative.

    c = canvas.Canvas(buff, pagesize=A4)
    W, H = A4
    margin = 18 * mm
    y = H - margin

    styles = getSampleStyleSheet()
    title = f"GEC Payslip – {employee_name}"
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, title)
    y -= 10*mm

    # Header box
    header = [
        ["LOCATION", location or "-", "EMPLOYEE NO.", employee_no or "-"],
        ["COMPANY", company or "WIS Global Resources Ltd", "EMPLOYEE", employee_name or "-"],
        ["PERIOD", period_label or "-", "", ""],
    ]
    t = Table(header, colWidths=[30*mm, 60*mm, 30*mm, 60*mm])
    t.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONT', (0,0), (-1,-1), 'Helvetica', 9),
        ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 9),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ]))
    tw, th = t.wrapOn(c, W-2*margin, y)
    t.drawOn(c, margin, y - th)
    y -= th + 8*mm

    # Earnings table
    data_e = [["Month End Description", "Units", "Rate", "Amount"]]
    total_pay = 0.0
    for desc, units, rate, amount in lines:
        data_e.append([desc, f"{units:.2f}", eur(rate), eur(amount)])
        total_pay += amount

    te = Table(data_e, colWidths=[90*mm, 25*mm, 30*mm, 35*mm])
    te.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 9),
        ('FONT', (0,1), (-1,-1), 'Helvetica', 9),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    tw, th = te.wrapOn(c, W-2*margin, y)
    te.drawOn(c, margin, y - th)
    y -= th + 6*mm

    # Deductions table
    data_d = [["Deductions", "Amount"]]
    total_ded = 0.0
    for desc, amount in deductions:
        data_d.append([desc, f"- {eur(amount)}"])
        total_ded += amount

    td = Table(data_d, colWidths=[115*mm, 65*mm])
    td.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 9),
        ('FONT', (0,1), (-1,-1), 'Helvetica', 9),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    tw, th = td.wrapOn(c, W-2*margin, y)
    td.drawOn(c, margin, y - th)
    y -= th + 8*mm

    # Totals
    net = total_pay - total_ded
    totals = [
        ["TOTAL PAYMENTS", eur(total_pay)],
        ["TOTAL DEDUCTIONS", f"- {eur(total_ded)}"],
        ["TOTAL NET PAY", eur(net)]
    ]
    tt = Table(totals, colWidths=[115*mm, 65*mm])
    tt.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONT', (0,0), (-1,-1), 'Helvetica-Bold', 10),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    tw, th = tt.wrapOn(c, W-2*margin, y)
    tt.drawOn(c, margin, y - th)
    y -= th + 6*mm

    c.showPage()
    c.save()

def build_employee_payslip_bytes(emp_df: pd.DataFrame,
                                 period_end: dt.date,
                                 company: str = "WIS Global Resources Ltd") -> Tuple[str, bytes]:
    # Extract meta
    employee_no = str(emp_df.get("employee_no", pd.Series([""])).iloc[0]) if "employee_no" in emp_df.columns else ""
    employee_name = str(emp_df.get("employee_name", pd.Series([""])).iloc[0]) if "employee_name" in emp_df.columns else ""
    location = str(emp_df.get("location", pd.Series([""])).iloc[0]) if "location" in emp_df.columns else ""
    period_label = period_end.strftime("%d-%b-%y")

    # Split earnings and deductions based on sign of amount
    lines, deds = [], []
    for _, r in emp_df.iterrows():
        desc = r.get("description", "")
        units = float(r.get("units", 0.0)) if pd.notna(r.get("units", None)) else 0.0
        rate = float(r.get("rate", 0.0)) if pd.notna(r.get("rate", None)) else 0.0
        amount = float(r.get("amount", 0.0)) if pd.notna(r.get("amount", None)) else 0.0
        if amount >= 0:
            lines.append((desc, units, rate, amount))
        else:
            deds.append((desc, abs(amount)))

    # Aggregate same descriptions
    def collapse_lines(items, is_ded=False):
        df = pd.DataFrame(items, columns=["desc","units","rate","amount"] if not is_ded else ["desc","amount"])
        if df.empty:
            return items
        if is_ded:
            df = df.groupby("desc", as_index=False)["amount"].sum()
            return list(df.itertuples(index=False, name=None))
        else:
            # for earnings: sum units and amount; rate = weighted avg if possible
            if (df["units"] > 0).any():
                df["weighted"] = df["rate"] * df["units"]
                rate = df["weighted"].sum() / (df["units"].sum() or 1)
            else:
                rate = df["rate"].mean() if not df["rate"].empty else 0.0
            total_units = df["units"].sum()
            total_amount = df["amount"].sum()
            # If multiple desc rows, keep a single combined row per desc
            out = []
            for desc, sub in df.groupby("desc"):
                # recompute per desc
                tu = sub["units"].sum()
                if (sub["units"] > 0).any():
                    sub["weighted"] = sub["rate"] * sub["units"]
                    tr = sub["weighted"].sum() / (sub["units"].sum() or 1)
                else:
                    tr = sub["rate"].mean() if not sub["rate"].empty else 0.0
                ta = sub["amount"].sum()
                out.append((desc, float(tu), float(tr), float(ta)))
            return out

    lines = collapse_lines(lines, is_ded=False)
    deds = collapse_lines(deds, is_ded=True)

    buff = io.BytesIO()
    draw_payslip_pdf(
        buff,
        company=company,
        location=location,
        employee_no=employee_no,
        employee_name=employee_name,
        period_label=period_label,
        lines=lines,
        deductions=deds
    )
    pdf_bytes = buff.getvalue()
    emp_label = (employee_name or employee_no or "Employee").replace("/", "_").replace("\\", "_")
    filename = f"GEC Payslip – {emp_label}.pdf"
    return filename, pdf_bytes

# ---------------- Streamlit UI ----------------

st.set_page_config(page_title="GEC Timesheet Analyzer & Payslip Generator", page_icon="💼", layout="wide")

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1e3a8a;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(90deg, #f0f9ff, #e0f2fe);
        border-radius: 10px;
        border: 2px solid #0ea5e9;
    }
    .step-header {
        background-color: #f8fafc;
        padding: 0.8rem;
        border-left: 4px solid #0ea5e9;
        margin: 1rem 0;
        font-weight: bold;
        color: #1e40af;
    }
    .success-box {
        background-color: #f0fdf4;
        border: 1px solid #22c55e;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #fefce8;
        border: 1px solid #eab308;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fef2f2;
        border: 1px solid #ef4444;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .analysis-box {
        background-color: #f0f9ff;
        border: 1px solid #3b82f6;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">💼 GEC Timesheet Analyzer & Payslip Generator</div>', unsafe_allow_html=True)

# Initialize rate mapping in session state if not exists
if 'rate_mapping' not in st.session_state:
    st.session_state.rate_mapping = {
        'days off': 350.0,
        'rig days': 400.0,
        'standby days': 200.0,
        'travel days': 350.0,
        'Bonus In Country': 150.0,
        'Premium In-country': 180.0,
    }

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    st.info("Upload your GEC timesheet Excel file and configure the processing parameters.")
    
    # Company settings
    st.subheader("Company Settings")
    company_name = st.text_input("Company Name", value="WIS Global Resources Ltd")
    
    # Period settings
    st.subheader("Pay Period")
    default_period = dt.date.today().replace(day=1) + pd.offsets.MonthEnd(0)
    period_end = st.date_input("Pay Period End", value=pd.to_datetime(default_period).date())
    
    # Rate Mapping Configuration
    st.subheader("💰 Rate Configuration")
    st.info("Configure rates for different work types. Changes are saved automatically.")
    
    # Display and edit existing rates
    rate_mapping = st.session_state.rate_mapping.copy()
    
    # Create expandable section for rate management
    with st.expander("📝 Manage Rates", expanded=False):
        # Edit existing rates
        st.markdown("**Edit Existing Rates:**")
        for key in list(rate_mapping.keys()):
            col1, col2 = st.columns([3, 1])
            with col1:
                new_rate = st.number_input(
                    f"{key.title()}",
                    value=float(rate_mapping[key]),
                    min_value=0.0,
                    step=10.0,
                    format="%.2f",
                    key=f"rate_{key}"
                )
                rate_mapping[key] = new_rate
            with col2:
                if st.button("🗑️", key=f"delete_{key}", help=f"Delete {key}"):
                    del rate_mapping[key]
                    st.session_state.rate_mapping = rate_mapping
                    st.rerun()
        
        # Add new rate mapping
        st.markdown("**Add New Rate:**")
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            new_key = st.text_input("Work Type", placeholder="e.g., overtime", key="new_rate_key")
        with col2:
            new_rate_value = st.number_input("Rate (€)", value=0.0, min_value=0.0, step=10.0, key="new_rate_value")
        with col3:
            if st.button("➕ Add", disabled=not new_key.strip()):
                if new_key.strip() and new_key.lower().strip() not in [k.lower() for k in rate_mapping.keys()]:
                    rate_mapping[new_key.lower().strip()] = new_rate_value
                    st.session_state.rate_mapping = rate_mapping
                    st.success(f"Added {new_key} with rate €{new_rate_value}")
                    st.rerun()
                elif new_key.lower().strip() in [k.lower() for k in rate_mapping.keys()]:
                    st.error("This work type already exists!")
    
    # Update session state with modified rates
    st.session_state.rate_mapping = rate_mapping
    
    # Display current rates summary
    st.markdown("**Current Rates:**")
    for key, value in rate_mapping.items():
        st.markdown(f"• {key.title()}: €{value:.2f}")
    
    # Reset to defaults button
    if st.button("🔄 Reset to Defaults"):
        st.session_state.rate_mapping = {
            'days off': 350.0,
            'rig days': 400.0,
            'standby days': 200.0,
            'travel days': 350.0,
            'Bonus In Country': 150.0,
            'Premium In-country': 180.0,
        }
        st.success("Rates reset to default values!")
        st.rerun()

st.markdown("""
<div class="info-box">
<h4>📋 How to use:</h4>
<ol>
<li><strong>Upload</strong> your GEC timesheet Excel file</li>
<li><strong>Generate</strong> employee payslips</li>
<li><strong>Download</strong> the generated payslip files</li>
</ol>
</div>
""", unsafe_allow_html=True)

# File upload section
st.markdown('<div class="step-header">📁 Step 1: Upload Timesheet</div>', unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])
with col1:
    uploaded = st.file_uploader(
        "Upload GEC Timesheet Excel File", 
        type=["xls", "xlsx"],
        help="Upload your GEC template timesheet file (e.g., 'GEC template timesheet Single 08.08.2025.xlsx')"
    )

with col2:
    if uploaded:
        st.success(f"✅ File uploaded: {uploaded.name}")
    else:
        st.info("👆 Please upload an Excel file to continue")

if uploaded is not None:
    try:
        # Try reading the Excel file with specialized GEC parser first
        try:
            df = parse_gec_timesheet(uploaded, st.session_state.get('rate_mapping'))
            st.markdown('<div class="success-box">📊 GEC Timesheet parsed successfully using specialized parser!</div>', unsafe_allow_html=True)
            
            # Show basic file info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Records", len(df))
            with col2:
                unique_employees = df['employee_name'].nunique() if 'employee_name' in df.columns else 0
                st.metric("Employees", unique_employees)
            with col3:
                total_amount = df['amount'].sum() if 'amount' in df.columns else 0
                st.metric("Total Amount", f"€{total_amount:,.2f}")
                
            # Show preview of parsed data
            with st.expander("📊 Preview Parsed Data", expanded=True):
                st.dataframe(df, use_container_width=True, height=400)
                
                # Show statistics
                if len(df) > 0:
                    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
                    with stats_col1:
                        st.metric("Date Range", f"{df['date'].min().strftime('%d %b')} - {df['date'].max().strftime('%d %b')}")
                    with stats_col2:
                        unique_locations = df['location'].nunique() if 'location' in df.columns else 0
                        st.metric("Locations", unique_locations)
                    with stats_col3:
                        unique_descriptions = df['description'].nunique() if 'description' in df.columns else 0
                        st.metric("Pay Elements", unique_descriptions)
                    with stats_col4:
                        total_units = df['units'].sum() if 'units' in df.columns else 0
                        st.metric("Total Units", f"{total_units:.1f}")
            
            # Perform background analysis (no display)
            analysis = analyze_multiple_location_issue(df)
                        
            # Auto-skip to processing since we have the data
            use_specialized_parser = True
            
        except Exception as parser_error:
            # Fall back to generic parser
            st.warning(f"⚠️ Specialized parser failed: {parser_error}. Trying generic parser...")
            raw = pd.read_excel(uploaded)
            use_specialized_parser = False
            
            st.markdown('<div class="success-box">📊 Excel file loaded with generic parser!</div>', unsafe_allow_html=True)
            
            # Show basic file info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Rows", len(raw))
            with col2:
                st.metric("Total Columns", len(raw.columns))
            with col3:
                st.metric("File Size", f"{uploaded.size / 1024:.1f} KB")
            
    except Exception as e:
        st.error(f"❌ Error reading Excel file: {e}")
        st.stop()

    if use_specialized_parser:
        # Skip column mapping for specialized parser
        st.markdown('<div class="step-header">⚙️ Step 2: Process & Generate (Auto-mapped)</div>', unsafe_allow_html=True)
        
        # Show processing options
        process_col1, process_col2 = st.columns([1, 1])
        
        with process_col1:
            st.markdown("**🎯 What will be generated:**")
            st.markdown("-  Individual employee payslip PDFs")
            st.markdown("- 📦 ZIP file with all payslips")
            
        with process_col2:
            st.markdown("**⚙️ Processing settings:**")
            st.markdown(f"- Company: {company_name}")
            st.markdown(f"- Period End: {period_end.strftime('%d %B %Y')}")
            st.markdown(f"- Records: {len(df)}")
            
        # Show discovered data summary
        st.markdown("**📋 Discovered Data:**")
        summary_col1, summary_col2 = st.columns(2)
        with summary_col1:
            st.markdown(f"- **Employee:** {df['employee_name'].iloc[0]}")
            st.markdown(f"- **Locations:** {', '.join(df['location'].unique())}")
        with summary_col2:
            st.markdown(f"- **Pay Elements:** {', '.join(df['description'].unique())}")
            st.markdown(f"- **Period:** {df['date'].min().strftime('%d %b')} to {df['date'].max().strftime('%d %b %Y')}")
        
        # Main process button
        if st.button("🚀 Generate Payslip Files", type="primary", use_container_width=True):
            with st.spinner("🔄 Generating payslip files..."):
                try:
                    # Perform analysis again for processing
                    analysis = analyze_multiple_location_issue(df)
                    
                    # Generate Employee PDFs
                    st.markdown("### 📄 Generating Employee Payslip PDFs...")
                    zip_buf = io.BytesIO()
                    
                    employee_count = 0
                    with ZipFile(zip_buf, "w", ZIP_DEFLATED) as zf:
                        for key, emp_df in split_by_employee(df):
                            fname, pdf_bytes = build_employee_payslip_bytes(emp_df, period_end, company_name)
                            zf.writestr(fname, pdf_bytes)
                            employee_count += 1
                    
                    zip_buf.seek(0)

                    st.markdown('<div class="success-box">🎉 Employee payslip files generated successfully!</div>', unsafe_allow_html=True)
                    
                    # Download section
                    st.markdown('<div class="step-header">📥 Step 3: Download Files</div>', unsafe_allow_html=True)
                    
                    st.markdown("#### Employee Payslips")
                    st.download_button(
                        label="📥 Download Payslip PDFs (ZIP)",
                        data=zip_buf.getvalue(),
                        file_name=f"GEC_Payslips_{period_end.strftime('%Y_%m')}.zip",
                        mime="application/zip",
                        use_container_width=True,
                        key="employee_payslips_download"
                    )
                    st.info(f"📦 Contains {employee_count} individual payslip PDFs")

                    st.markdown('<div class="success-box">✅ Processing complete! You can now download your payslip files.</div>', unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"❌ Error during processing: {str(e)}")
                    st.exception(e)
    else:
        # Generic parser path (original column mapping approach)
        st.markdown('<div class="step-header">🔗 Step 2: Column Mapping</div>', unsafe_allow_html=True)
        
        # Auto-detect columns
        auto = auto_map_columns(raw)
        
        st.info("💡 Auto-detection has been applied. Please verify the column mappings below:")

        # Show mapping selectors in a more organized way
        ui_map = {}
        cols = ["(not used)"] + list(raw.columns)
        
        # Create two columns for better layout
        map_col1, map_col2 = st.columns(2)
        
        mapping_fields = [
            ("date", "📅 Date"),
            ("employee_name", "👤 Employee Name"), 
            ("employee_no", "🆔 Employee Number"),
            ("location", "📍 Location"),
            ("description", "📝 Description"),
            ("units", "🔢 Units/Hours"),
            ("rate", "💰 Rate"),
            ("amount", "💵 Amount")
        ]
        
        for i, (need, label) in enumerate(mapping_fields):
            pre = auto.get(need, None)
            with map_col1 if i % 2 == 0 else map_col2:
                ui_map[need] = st.selectbox(
                    label,
                    options=cols,
                    index=(cols.index(pre) if pre in cols else 0),
                    key=f"map_{need}",
                    help=f"Select the column that contains {need} data"
                )

        # Build final mapping dict excluding "(not used)"
        final_map = {k: v for k, v in ui_map.items() if v and v != "(not used)"}
        
        # Show preview of mappings
        if final_map:
            st.markdown("### 📋 Active Column Mappings:")
            mapping_df = pd.DataFrame([
                {"Field": k.replace('_', ' ').title(), "Excel Column": v} 
                for k, v in final_map.items()
            ])
            st.dataframe(mapping_df, use_container_width=True)

        # Raw data preview
        with st.expander("👀 Preview Raw Data (First 10 rows)", expanded=False):
            st.dataframe(raw.head(10), use_container_width=True)

        # Processing section for generic parser
        st.markdown('<div class="step-header">⚙️ Step 3: Process & Generate</div>', unsafe_allow_html=True)
        
        if not final_map:
            st.warning("⚠️ Please map at least one column to proceed.")
        else:
            # Show processing options
            process_col1, process_col2 = st.columns([1, 1])
            
            with process_col1:
                st.markdown("**🎯 What will be generated:**")
                st.markdown("-  Individual employee payslip PDFs")
                st.markdown("- 📦 ZIP file with all payslips")
                
            with process_col2:
                st.markdown("**⚙️ Processing settings:**")
                st.markdown(f"- Company: {company_name}")
                st.markdown(f"- Period End: {period_end.strftime('%d %B %Y')}")
                st.markdown(f"- Active mappings: {len(final_map)}")
            
            # Main process button
            if st.button("🚀 Process Timesheet & Generate Files", type="primary", use_container_width=True):
                with st.spinner("🔄 Processing your timesheet data..."):
                    try:
                        # Process the data
                        df = prepare_frame(raw, final_map, st.session_state.get('rate_mapping'))
                        if df.empty:
                            st.error("❌ No data found after mapping. Please check your column mappings.")
                            st.stop()

                        st.markdown('<div class="success-box">✅ Data processed successfully!</div>', unsafe_allow_html=True)
                        
                        # Show processed data preview
                        with st.expander("📊 Preview Processed Data", expanded=True):
                            st.dataframe(df.head(15), use_container_width=True)
                            
                            # Show some statistics
                            stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
                            with stats_col1:
                                st.metric("Total Records", len(df))
                            with stats_col2:
                                unique_employees = df['employee_name'].nunique() if 'employee_name' in df.columns else 0
                                st.metric("Unique Employees", unique_employees)
                            with stats_col3:
                                total_amount = df['amount'].sum() if 'amount' in df.columns else 0
                                st.metric("Total Amount", f"€{total_amount:,.2f}")
                            with stats_col4:
                                unique_locations = df['location'].nunique() if 'location' in df.columns else 0
                                st.metric("Locations", unique_locations)

                        # Generate Employee PDFs
                        st.markdown("### 📄 Generating Employee Payslip PDFs...")
                        from zipfile import ZipFile, ZIP_DEFLATED
                        zip_buf = io.BytesIO()
                        
                        employee_count = 0
                        with ZipFile(zip_buf, "w", ZIP_DEFLATED) as zf:
                            for key, emp_df in split_by_employee(df):
                                fname, pdf_bytes = build_employee_payslip_bytes(emp_df, period_end, company_name)
                                zf.writestr(fname, pdf_bytes)
                                employee_count += 1
                        
                        zip_buf.seek(0)

                        st.markdown('<div class="success-box">🎉 Employee payslip files generated successfully!</div>', unsafe_allow_html=True)
                        
                        # Download section
                        st.markdown('<div class="step-header">📥 Step 4: Download Files</div>', unsafe_allow_html=True)
                        
                        st.markdown("#### �Employee Payslips")
                        st.download_button(
                            label="📥 Download Payslip PDFs (ZIP)",
                            data=zip_buf.getvalue(),
                            file_name=f"GEC_Payslips_{period_end.strftime('%Y_%m')}.zip",
                            mime="application/zip",
                            use_container_width=True,
                            key="employee_payslips_download_2"
                        )
                        st.info(f"� Contains {employee_count} individual payslip PDFs")

                        st.markdown('<div class="success-box">✅ Processing complete! You can now download your payslip files.</div>', unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.error(f"❌ Error during processing: {str(e)}")
                        st.exception(e)

else:
    # Show help when no file is uploaded
    st.markdown("""
    <div class="info-box">
    <h4>🔍 Looking for the sample files?</h4>
    <p>Make sure you have:</p>
    <ul>
    <li><strong>GEC template timesheet Single/Multiple</strong> - Input timesheet file</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

