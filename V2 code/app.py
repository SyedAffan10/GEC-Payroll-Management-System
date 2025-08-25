import pandas as pd
import streamlit as st
import sqlite3
import json

# Database setup and management functions
def init_database():
    """Initialize the employee database"""
    conn = sqlite3.connect('employees.db')
    cursor = conn.cursor()
    
    # Create employees table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE NOT NULL,
            employee_name TEXT NOT NULL,
            employment_type TEXT NOT NULL,
            currency TEXT DEFAULT 'EUR',
            payments TEXT,
            deductions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add currency column if it doesn't exist (for backward compatibility)
    try:
        cursor.execute('ALTER TABLE employees ADD COLUMN currency TEXT DEFAULT "EUR"')
        conn.commit()
    except sqlite3.OperationalError:
        pass
    
    # Add additional_daily_payments column if it doesn't exist
    try:
        cursor.execute('ALTER TABLE employees ADD COLUMN additional_daily_payments TEXT DEFAULT "{}"')
        conn.commit()
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()

def add_employee(employee_id, employee_name, employment_type, currency, payments, deductions, additional_daily_payments=None):
    """Add a new employee to the database"""
    conn = sqlite3.connect('employees.db')
    cursor = conn.cursor()
    
    try:
        payments_json = json.dumps(payments) if payments else json.dumps({})
        deductions_json = json.dumps(deductions) if deductions else json.dumps({})
        additional_payments_json = json.dumps(additional_daily_payments) if additional_daily_payments else json.dumps({})
        
        cursor.execute('''
            INSERT INTO employees (employee_id, employee_name, employment_type, currency, payments, deductions, additional_daily_payments)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (employee_id, employee_name, employment_type, currency, payments_json, deductions_json, additional_payments_json))
        
        conn.commit()
        return True, "Employee added successfully!"
    except sqlite3.IntegrityError:
        return False, "Employee ID already exists!"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def get_employee_by_name(employee_name):
    """Get employee data by name"""
    conn = sqlite3.connect('employees.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM employees WHERE employee_name = ? COLLATE NOCASE
    ''', (employee_name,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'employee_id': result[1],
            'employee_name': result[2],
            'employment_type': result[3],
            'currency': result[4] if len(result) > 4 and result[4] else 'EUR',
            'payments': json.loads(result[5]) if result[5] else {},
            'deductions': json.loads(result[6]) if result[6] else {},
            'additional_daily_payments': json.loads(result[9]) if len(result) > 9 and result[9] else {},
            'created_at': result[7] if len(result) > 7 else '',
            'updated_at': result[8] if len(result) > 8 else ''
        }
    return None

def get_all_employees():
    """Get all employees from database"""
    conn = sqlite3.connect('employees.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM employees ORDER BY employee_name')
    results = cursor.fetchall()
    conn.close()
    
    employees = []
    for result in results:
        try:
            try:
                payments_data = json.loads(result[5]) if result[5] else {}
            except json.JSONDecodeError:
                payments_data = {}
            
            try:
                deductions_data = json.loads(result[6]) if result[6] else {}
            except json.JSONDecodeError:
                deductions_data = {}
            
            try:
                additional_payments_data = json.loads(result[9]) if len(result) > 9 and result[9] else {}
            except json.JSONDecodeError:
                additional_payments_data = {}
            
            employees.append({
                'id': result[0],
                'employee_id': result[1],
                'employee_name': result[2],
                'employment_type': result[3],
                'currency': result[4] if len(result) > 4 and result[4] else 'EUR',
                'payments': payments_data,
                'deductions': deductions_data,
                'additional_daily_payments': additional_payments_data,
                'created_at': result[7] if len(result) > 7 else '',
                'updated_at': result[8] if len(result) > 8 else ''
            })
        except Exception as e:
            continue
    
    return employees

def update_employee(emp_id, employee_id, employee_name, employment_type, currency, payments, deductions, additional_daily_payments=None):
    """Update employee data"""
    conn = sqlite3.connect('employees.db')
    cursor = conn.cursor()
    
    try:
        payments_json = json.dumps(payments) if payments else json.dumps({})
        deductions_json = json.dumps(deductions) if deductions else json.dumps({})
        additional_payments_json = json.dumps(additional_daily_payments) if additional_daily_payments else json.dumps({})
        
        cursor.execute('''
            UPDATE employees 
            SET employee_id = ?, employee_name = ?, employment_type = ?, currency = ?, 
                payments = ?, deductions = ?, additional_daily_payments = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (employee_id, employee_name, employment_type, currency, payments_json, deductions_json, additional_payments_json, emp_id))
        
        conn.commit()
        return True, "Employee updated successfully!"
    except sqlite3.IntegrityError:
        return False, "Employee ID already exists!"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def delete_employee(emp_id):
    """Delete employee from database"""
    conn = sqlite3.connect('employees.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM employees WHERE id = ?', (emp_id,))
        conn.commit()
        return True, "Employee deleted successfully!"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

# Initialize database on app start
init_database()

# Currency mapping
CURRENCY_OPTIONS = {
    'EUR': '€', 'USD': '$', 'GBP': '£', 'PKR': 'Rs', 'AED': 'د.إ',
    'SAR': 'ر.س', 'QAR': 'ر.ق', 'KWD': 'د.ك', 'BHD': 'د.ب',
    'OMR': 'ر.ع.', 'JPY': '¥', 'INR': '₹', 'CAD': 'C$', 'AUD': 'A$',
    'XAF': 'CFA'
}

def get_currency_symbol(currency_code):
    """Get currency symbol from currency code"""
    return CURRENCY_OPTIONS.get(currency_code, currency_code)

def parse_gec_timesheet(file_path_or_buffer) -> pd.DataFrame:
    """Parse the GEC timesheet Excel format and return a normalized DataFrame"""
    raw_df = pd.read_excel(file_path_or_buffer)
    
    # Extract employee information
    employee_name = None
    for i, row in raw_df.iterrows():
        if pd.notna(row.iloc[0]) and 'Employee Name' in str(row.iloc[0]):
            if len(row) > 3 and pd.notna(row.iloc[3]):
                employee_name = str(row.iloc[3]).strip()
    
    # Find the data start (look for date headers)
    data_start_row = None
    date_row = None
    
    for i, row in raw_df.iterrows():
        date_count = 0
        for j in range(3, min(len(row), 15)):
            try:
                if pd.notna(row.iloc[j]):
                    pd.to_datetime(row.iloc[j])
                    date_count += 1
            except:
                pass
        
        if date_count >= 3:
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
        
        if pd.isna(row.iloc[0]) and pd.isna(row.iloc[2]):
            continue
            
        location = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        description = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
        
        if not location and not description:
            continue
            
        if 'total' in location.lower():
            continue
            
        # Extract daily values
        for j, date_val in enumerate(date_headers):
            col_idx = j + 3
            if col_idx < len(row):
                value = row.iloc[col_idx]
                if pd.notna(value) and value != 0:
                    try:
                        hours = float(value)
                        if hours > 0:
                            processed_data.append({
                                'date': date_val,
                                'employee_name': employee_name or 'Unknown',
                                'location': location,
                                'description': description,
                                'units': hours,
                                'rate': 0.0,
                                'amount': 0.0
                            })
                    except (ValueError, TypeError):
                        pass
    
    if not processed_data:
        raise ValueError("No timesheet data found")
    
    # Create DataFrame
    df = pd.DataFrame(processed_data)
    
    # Default rate mapping
    rate_mapping = {
        'days off': 350.0,
        'rig days': 400.0,
        'standby days': 200.0,
        'travel days': 350.0,
        'bonus': 150.0,
        'premium': 180.0,
    }
    
    # Apply rates
    for desc, rate in rate_mapping.items():
        mask = df['description'].str.lower().str.contains(desc.lower(), na=False, regex=False)
        df.loc[mask, 'rate'] = rate
    
    # Calculate amounts
    df['amount'] = df['units'] * df['rate']
    
    return df.sort_values('date', ascending=True).reset_index(drop=True)

# Set page config at the very beginning
st.set_page_config(page_title="GEC Timesheet Analyzer & Payslip Generator", page_icon="💼", layout="wide")

# Simple version - start with just employee management
st.title("💼 GEC Employee Management & Payslip System")

# Create tabs
tab1, tab2 = st.tabs(["👥 Employee Management", "📊 Payslip Generation"])

with tab1:
    st.header("👥 Employee Database Management")
    
    # Add Employee Button - opens popup form
    col_btn, col_space = st.columns([1, 3])
    with col_btn:
        if st.button("➕ Add New Employee", use_container_width=True, type="primary"):
            st.session_state['show_add_employee_form'] = True
    
    # Add Employee Form (popup style)
    if st.session_state.get('show_add_employee_form', False):
        with st.container():
            st.markdown("---")
            st.subheader("➕ Add New Employee")
            
            # Payment, Deduction and Additional Daily Payments management buttons (outside form)
            col_pay_btn, col_ded_btn, col_add_daily_btn, col_space = st.columns([1, 1, 1, 1])
            with col_pay_btn:
                if st.button("➕ Add Payment"):
                    st.session_state.payment_items.append({"name": "", "value": 0.0})
                    st.rerun()
            with col_ded_btn:
                if st.button("➕ Add Deduction"):
                    st.session_state.deduction_items.append({"name": "", "percentage": 0.0})
                    st.rerun()
            with col_add_daily_btn:
                if st.button("➕ Add Daily Payment"):
                    if 'additional_daily_items' not in st.session_state:
                        st.session_state.additional_daily_items = []
                    st.session_state.additional_daily_items.append({"name": "", "value": 0.0})
                    st.rerun()
            
            with st.form("add_employee_form"):
                # Basic employee information
                col1, col2 = st.columns(2)
                
                with col1:
                    new_emp_id = st.text_input("Employee ID*", placeholder="e.g., EMP001", key="new_emp_id")
                    new_emp_name = st.text_input("Employee Name*", placeholder="e.g., John Doe", key="new_emp_name")
                    
                    col_type, col_currency = st.columns(2)
                    with col_type:
                        employment_type = st.selectbox("Employment Type*", ["Full-time", "Part-time", "Contract", "Temporary"], key="new_emp_type")
                    with col_currency:
                        currency = st.selectbox("Currency*", list(CURRENCY_OPTIONS.keys()), 
                                               index=0, key="new_emp_currency",
                                               format_func=lambda x: f"{x} ({CURRENCY_OPTIONS[x]})")
                    
                    currency_symbol = get_currency_symbol(currency)
                    st.info(f"Selected Currency: {currency} ({currency_symbol})")
                
                with col2:
                    st.markdown("### 💰 Payment Categories")
                    
                    # Initialize session state for dynamic inputs
                    if 'payment_items' not in st.session_state:
                        st.session_state.payment_items = []
                    
                    # Payment section
                    payment_dict = {}
                    for i, item in enumerate(st.session_state.payment_items):
                        col_name, col_value, col_remove = st.columns([3, 2, 0.8])
                        with col_name:
                            payment_name = st.text_input(f"Category", key=f"payment_name_{i}", 
                                                       value=item["name"], placeholder="e.g., days off")
                        with col_value:
                            payment_value = st.number_input(f"Rate ({currency_symbol})", key=f"payment_value_{i}", 
                                                          value=float(item["value"]), min_value=0.0, step=10.0)
                        with col_remove:
                            remove_payment = st.checkbox("❌", key=f"remove_payment_{i}", help="Check to remove this payment")
                        
                        if payment_name.strip() and not remove_payment:
                            payment_dict[payment_name.strip()] = payment_value
                    
                    st.markdown("### ➖ Deduction Categories")
                    
                    # Get basic salary for percentage calculations
                    basic_salary = 0.0
                    for name, value in payment_dict.items():
                        if 'basic' in name.lower() or 'salary' in name.lower():
                            basic_salary = value
                            break
                    
                    if basic_salary > 0:
                        st.info(f"📊 Basic Salary: {currency_symbol}{basic_salary:,.2f} - Deductions calculated as percentages")
                    else:
                        st.warning("⚠️ No basic salary found. Add a payment with 'salary' or 'basic' in the name.")
                    
                    # Initialize session state for deductions
                    if 'deduction_items' not in st.session_state:
                        st.session_state.deduction_items = []
                    
                    # Deduction section with percentage input
                    deduction_dict = {}
                    for i, item in enumerate(st.session_state.deduction_items):
                        col_name, col_percentage, col_amount, col_remove = st.columns([3, 1.5, 2, 0.8])
                        with col_name:
                            deduction_name = st.text_input(f"Category", key=f"deduction_name_{i}", 
                                                         value=item["name"], placeholder="e.g., tax")
                        with col_percentage:
                            deduction_percentage = st.number_input(f"Percentage (%)", key=f"deduction_percentage_{i}", 
                                                                 value=float(item.get("percentage", 0.0)), min_value=0.0, max_value=100.0, step=0.5)
                        with col_amount:
                            # Calculate amount based on percentage
                            calculated_amount = (basic_salary * deduction_percentage / 100) if basic_salary > 0 else 0.0
                            st.markdown(f"**{currency_symbol}{calculated_amount:,.2f}**")
                            st.caption(f"= {deduction_percentage}% of basic salary")
                        with col_remove:
                            remove_deduction = st.checkbox("❌", key=f"remove_deduction_{i}", help="Check to remove this deduction")
                        
                        if deduction_name.strip() and not remove_deduction and basic_salary > 0:
                            deduction_dict[deduction_name.strip()] = calculated_amount
                            # Update session state with percentage
                            st.session_state.deduction_items[i]["percentage"] = deduction_percentage
                    
                    st.markdown("### 💰 Additional Daily Payments")
                    
                    # Initialize session state for additional daily payments
                    if 'additional_daily_items' not in st.session_state:
                        st.session_state.additional_daily_items = []
                    
                    # Additional Daily Payments section
                    additional_payments = {}
                    for i, item in enumerate(st.session_state.additional_daily_items):
                        col_name, col_value, col_remove = st.columns([3, 2, 0.8])
                        with col_name:
                            daily_payment_name = st.text_input(f"Category", key=f"daily_payment_name_{i}", 
                                                       value=item["name"], placeholder="e.g., Field Bonus")
                        with col_value:
                            daily_payment_value = st.number_input(f"Daily Rate ({currency_symbol})", key=f"daily_payment_value_{i}", 
                                                          value=float(item["value"]), min_value=0.0, step=1.0)
                        with col_remove:
                            remove_daily_payment = st.checkbox("❌", key=f"remove_daily_payment_{i}", help="Check to remove this daily payment")
                        
                        if daily_payment_name.strip() and not remove_daily_payment:
                            additional_payments[daily_payment_name.strip()] = daily_payment_value
                
                # Form buttons
                col_save, col_cancel = st.columns(2)
                with col_save:
                    save_button = st.form_submit_button("💾 Save Employee", use_container_width=True, type="primary")
                with col_cancel:
                    cancel_button = st.form_submit_button("❌ Cancel", use_container_width=True)
                
                if save_button:
                    # Remove items marked for deletion
                    st.session_state.payment_items = [item for i, item in enumerate(st.session_state.payment_items) 
                                                     if not st.session_state.get(f"remove_payment_{i}", False)]
                    st.session_state.deduction_items = [item for i, item in enumerate(st.session_state.deduction_items) 
                                                       if not st.session_state.get(f"remove_deduction_{i}", False)]
                    st.session_state.additional_daily_items = [item for i, item in enumerate(st.session_state.additional_daily_items) 
                                                             if not st.session_state.get(f"remove_daily_payment_{i}", False)]
                    
                    if new_emp_id and new_emp_name and employment_type and currency:
                        success, message = add_employee(new_emp_id, new_emp_name, employment_type, currency, payment_dict, deduction_dict)
                        
                        if success:
                            if any(value > 0 for value in additional_payments.values()):
                                try:
                                    conn = sqlite3.connect('employees.db')
                                    cursor = conn.cursor()
                                    additional_payments_json = json.dumps(additional_payments)
                                    cursor.execute('''
                                        UPDATE employees 
                                        SET additional_daily_payments = ? 
                                        WHERE employee_id = ?
                                    ''', (additional_payments_json, new_emp_id))
                                    conn.commit()
                                    conn.close()
                                    st.success(f"{message} Additional daily payments also saved!")
                                except Exception as e:
                                    st.warning(f"Employee created but failed to save additional payments: {str(e)}")
                            else:
                                st.success(message)
                            
                            st.session_state.payment_items = []
                            st.session_state.deduction_items = []
                            st.session_state.additional_daily_items = []
                            st.session_state['show_add_employee_form'] = False
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Please fill in all required fields (marked with *)")
                
                if cancel_button:
                    st.session_state.payment_items = []
                    st.session_state.deduction_items = []
                    st.session_state.additional_daily_items = []
                    st.session_state['show_add_employee_form'] = False
                    st.rerun()
            
            st.markdown("---")
    
    # Display Existing Employees
    st.subheader("📋 Existing Employees")
    
    employees = get_all_employees()
    
    if employees:
        for emp in employees:
            with st.expander(f"👤 {emp['employee_name']} ({emp['employee_id']})", expanded=False):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown(f"**Employee ID:** {emp['employee_id']}")
                    st.markdown(f"**Name:** {emp['employee_name']}")
                    st.markdown(f"**Employment Type:** {emp['employment_type']}")
                    currency_symbol = get_currency_symbol(emp.get('currency', 'EUR'))
                    st.markdown(f"**Currency:** {emp.get('currency', 'EUR')} ({currency_symbol})")
                    st.markdown(f"**Created:** {emp['created_at'][:10] if emp['created_at'] else 'Unknown'}")
                
                with col2:
                    currency_symbol = get_currency_symbol(emp.get('currency', 'EUR'))
                    
                    if emp['payments']:
                        st.markdown("**Payment Categories:**")
                        total_payments = 0
                        if isinstance(emp['payments'], dict):
                            payment_data = []
                            for payment_name, payment_value in emp['payments'].items():
                                payment_data.append({
                                    'Category': payment_name,
                                    'Amount': f"{currency_symbol}{payment_value:,.2f}"
                                })
                                total_payments += payment_value
                            
                            if payment_data:
                                payment_df = pd.DataFrame(payment_data)
                                st.dataframe(payment_df, use_container_width=True, hide_index=True)
                            
                            st.markdown(f"**Total Payment Rate:** {currency_symbol}{total_payments:,.2f}")
                        else:
                            for payment in emp['payments']:
                                st.markdown(f"• {payment}")
                            st.markdown("*Note: Old format - no rates stored*")
                    
                    if emp['deductions']:
                        st.markdown("**Deduction Categories:**")
                        total_deductions = 0
                        
                        display_basic_salary = 0.0
                        if emp['payments'] and isinstance(emp['payments'], dict):
                            for payment_name, payment_value in emp['payments'].items():
                                if 'basic' in payment_name.lower() or 'salary' in payment_name.lower():
                                    display_basic_salary = payment_value
                                    break
                        
                        if isinstance(emp['deductions'], dict):
                            deduction_data = []
                            for deduction_name, deduction_value in emp['deductions'].items():
                                percentage_info = ""
                                if display_basic_salary > 0:
                                    percentage = (deduction_value / display_basic_salary) * 100
                                    percentage_info = f"{percentage:.1f}%"
                                else:
                                    percentage_info = "N/A"
                                
                                deduction_data.append({
                                    'Category': deduction_name,
                                    'Amount': f"{currency_symbol}{deduction_value:,.2f}",
                                    'Percentage': percentage_info
                                })
                                total_deductions += deduction_value
                            
                            if deduction_data:
                                deduction_df = pd.DataFrame(deduction_data)
                                st.dataframe(deduction_df, use_container_width=True, hide_index=True)
                            
                            st.markdown(f"**Total Deductions:** {currency_symbol}{total_deductions:,.2f}")
                        else:
                            for deduction in emp['deductions']:
                                st.markdown(f"• {deduction}")
                            st.markdown("*Note: Old format - no amounts stored*")
                    
                    if emp.get('additional_daily_payments'):
                        st.markdown("**Additional Daily Payments:**")
                        total_additional = 0
                        
                        if isinstance(emp['additional_daily_payments'], dict):
                            additional_data = []
                            for payment_name, payment_value in emp['additional_daily_payments'].items():
                                if payment_value > 0:
                                    additional_data.append({
                                        'Category': payment_name,
                                        'Daily Rate': f"{currency_symbol}{payment_value:,.2f}"
                                    })
                                    total_additional += payment_value
                            
                            if additional_data:
                                additional_df = pd.DataFrame(additional_data)
                                st.dataframe(additional_df, use_container_width=True, hide_index=True)
                                st.markdown(f"**Total Daily Rate:** {currency_symbol}{total_additional:,.2f}")
                            else:
                                st.markdown("*No additional daily payments set*")
                        else:
                            st.markdown("*Old format - no additional payments data*")
                
                with col3:
                    # Edit button
                    if st.button("✏️ Edit", key=f"edit_{emp['id']}"):
                        st.session_state[f"editing_{emp['id']}"] = True
                        st.rerun()
                    
                    # Delete button
                    if st.button("🗑️ Delete", key=f"delete_{emp['id']}"):
                        success, message = delete_employee(emp['id'])
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                
                # Edit form (appears when edit button is clicked)
                if st.session_state.get(f"editing_{emp['id']}", False):
                    st.markdown("### ✏️ Edit Employee")
                    
                    # Initialize session state for new items during editing
                    if f"edit_new_payments_{emp['id']}" not in st.session_state:
                        st.session_state[f"edit_new_payments_{emp['id']}"] = []
                    if f"edit_new_deductions_{emp['id']}" not in st.session_state:
                        st.session_state[f"edit_new_deductions_{emp['id']}"] = []
                    if f"edit_new_daily_payments_{emp['id']}" not in st.session_state:
                        st.session_state[f"edit_new_daily_payments_{emp['id']}"] = []
                    
                    # Buttons to add new categories (outside form)
                    col_add_pay, col_add_ded, col_add_daily, col_space = st.columns([1, 1, 1, 1])
                    with col_add_pay:
                        if st.button("➕ Add New Payment", key=f"add_new_payment_{emp['id']}"):
                            st.session_state[f"edit_new_payments_{emp['id']}"].append({"name": "", "value": 0.0})
                            st.rerun()
                    with col_add_ded:
                        if st.button("➕ Add New Deduction", key=f"add_new_deduction_{emp['id']}"):
                            st.session_state[f"edit_new_deductions_{emp['id']}"].append({"name": "", "percentage": 0.0})
                            st.rerun()
                    with col_add_daily:
                        if st.button("➕ Add Daily Payment", key=f"add_new_daily_{emp['id']}"):
                            st.session_state[f"edit_new_daily_payments_{emp['id']}"].append({"name": "", "value": 0.0})
                            st.rerun()
                    
                    with st.form(f"edit_form_{emp['id']}"):
                        edit_col1, edit_col2 = st.columns(2)
                        
                        with edit_col1:
                            edit_emp_id = st.text_input("Employee ID", value=emp['employee_id'], key=f"edit_id_{emp['id']}")
                            edit_emp_name = st.text_input("Employee Name", value=emp['employee_name'], key=f"edit_name_{emp['id']}")
                            
                            col_type, col_currency = st.columns(2)
                            with col_type:
                                edit_employment_type = st.selectbox(
                                    "Employment Type", 
                                    ["Full-time", "Part-time", "Contract", "Temporary"],
                                    index=["Full-time", "Part-time", "Contract", "Temporary"].index(emp['employment_type']),
                                    key=f"edit_type_{emp['id']}"
                                )
                            with col_currency:
                                current_currency = emp.get('currency', 'EUR')
                                try:
                                    currency_index = list(CURRENCY_OPTIONS.keys()).index(current_currency)
                                except ValueError:
                                    currency_index = 0
                                
                                edit_currency = st.selectbox(
                                    "Currency",
                                    list(CURRENCY_OPTIONS.keys()),
                                    index=currency_index,
                                    key=f"edit_currency_{emp['id']}",
                                    format_func=lambda x: f"{x} ({CURRENCY_OPTIONS[x]})"
                                )
                            
                            edit_currency_symbol = get_currency_symbol(edit_currency)
                        
                        with edit_col2:
                            st.markdown(f"**Edit Payment Categories ({edit_currency_symbol}):**")
                            edit_payments = {}
                            payment_index = 0
                            
                            # Handle both old list format and new dict format
                            if isinstance(emp['payments'], dict):
                                for payment_name, payment_value in emp['payments'].items():
                                    col_name, col_value, col_delete = st.columns([2, 1, 0.8])
                                    with col_name:
                                        new_payment_name = st.text_input(f"Category", value=payment_name, key=f"edit_payment_name_{emp['id']}_{payment_index}")
                                    with col_value:
                                        new_payment_value = st.number_input(f"Rate ({edit_currency_symbol})", value=float(payment_value), min_value=0.0, step=10.0, key=f"edit_payment_value_{emp['id']}_{payment_index}")
                                    with col_delete:
                                        delete_payment = st.checkbox("❌", key=f"delete_payment_{emp['id']}_{payment_index}", help="Check to delete this payment")
                                    
                                    if new_payment_name.strip() and not delete_payment:
                                        edit_payments[new_payment_name.strip()] = new_payment_value
                                    payment_index += 1
                            else:
                                # Convert old list format to dict format
                                for payment_name in emp['payments']:
                                    col_name, col_value, col_delete = st.columns([2, 1, 0.8])
                                    with col_name:
                                        new_payment_name = st.text_input(f"Category", value=payment_name, key=f"edit_payment_name_{emp['id']}_{payment_index}")
                                    with col_value:
                                        new_payment_value = st.number_input(f"Rate ({edit_currency_symbol})", value=0.0, min_value=0.0, step=10.0, key=f"edit_payment_value_{emp['id']}_{payment_index}")
                                    with col_delete:
                                        delete_payment = st.checkbox("❌", key=f"delete_payment_{emp['id']}_{payment_index}", help="Check to delete this payment")
                                    
                                    if new_payment_name.strip() and not delete_payment:
                                        edit_payments[new_payment_name.strip()] = new_payment_value
                                    payment_index += 1
                            
                            # Add new payment categories
                            if st.session_state[f"edit_new_payments_{emp['id']}"]:
                                st.markdown("**New Payment Categories:**")
                                for i, new_payment in enumerate(st.session_state[f"edit_new_payments_{emp['id']}"]):
                                    col_name, col_value, col_remove = st.columns([2, 1, 0.8])
                                    with col_name:
                                        new_payment_name = st.text_input(f"New Category", key=f"new_payment_name_{emp['id']}_{i}", 
                                                                       value=new_payment["name"], placeholder="e.g., bonus")
                                    with col_value:
                                        new_payment_value = st.number_input(f"Rate ({edit_currency_symbol})", key=f"new_payment_value_{emp['id']}_{i}", 
                                                                          value=float(new_payment["value"]), min_value=0.0, step=10.0)
                                    with col_remove:
                                        remove_new_payment = st.checkbox("❌", key=f"remove_new_payment_{emp['id']}_{i}", help="Check to remove this new payment")
                                    
                                    if new_payment_name.strip() and not remove_new_payment:
                                        edit_payments[new_payment_name.strip()] = new_payment_value
                            
                            st.markdown(f"**Edit Deduction Categories ({edit_currency_symbol}):**")
                            
                            # Get basic salary for percentage calculations in edit mode
                            edit_basic_salary = 0.0
                            for payment_name, payment_value in edit_payments.items():
                                if 'basic' in payment_name.lower() or 'salary' in payment_name.lower():
                                    edit_basic_salary = payment_value
                                    break
                            
                            if edit_basic_salary > 0:
                                st.info(f"📊 Basic Salary: {edit_currency_symbol}{edit_basic_salary:,.2f} - Deductions calculated as percentages")
                            else:
                                st.warning("⚠️ No basic salary found. Add a payment with 'salary' or 'basic' in the name.")
                            
                            edit_deductions = {}
                            deduction_index = 0
                            
                            # Handle both old list format and new dict format
                            if isinstance(emp['deductions'], dict):
                                for deduction_name, deduction_value in emp['deductions'].items():
                                    col_name, col_percentage, col_amount, col_delete = st.columns([2, 1, 1.5, 0.8])
                                    with col_name:
                                        new_deduction_name = st.text_input(f"Category", value=deduction_name, key=f"edit_deduction_name_{emp['id']}_{deduction_index}")
                                    with col_percentage:
                                        existing_percentage = (deduction_value / edit_basic_salary * 100) if edit_basic_salary > 0 and deduction_value > 0 else 0.0
                                        new_deduction_percentage = st.number_input(f"Percentage (%)", value=existing_percentage, min_value=0.0, max_value=100.0, step=0.5, key=f"edit_deduction_percentage_{emp['id']}_{deduction_index}")
                                    with col_amount:
                                        calculated_amount = (edit_basic_salary * new_deduction_percentage / 100) if edit_basic_salary > 0 else 0.0
                                        st.markdown(f"**{edit_currency_symbol}{calculated_amount:,.2f}**")
                                        st.caption(f"= {new_deduction_percentage}% of basic")
                                    with col_delete:
                                        delete_deduction = st.checkbox("❌", key=f"delete_deduction_{emp['id']}_{deduction_index}", help="Check to delete this deduction")
                                    
                                    if new_deduction_name.strip() and not delete_deduction and edit_basic_salary > 0:
                                        edit_deductions[new_deduction_name.strip()] = calculated_amount
                                    deduction_index += 1
                            else:
                                # Convert old list format to dict format with percentage input
                                for deduction_name in emp['deductions']:
                                    col_name, col_percentage, col_amount, col_delete = st.columns([2, 1, 1.5, 0.8])
                                    with col_name:
                                        new_deduction_name = st.text_input(f"Category", value=deduction_name, key=f"edit_deduction_name_{emp['id']}_{deduction_index}")
                                    with col_percentage:
                                        new_deduction_percentage = st.number_input(f"Percentage (%)", value=0.0, min_value=0.0, max_value=100.0, step=0.5, key=f"edit_deduction_percentage_{emp['id']}_{deduction_index}")
                                    with col_amount:
                                        calculated_amount = (edit_basic_salary * new_deduction_percentage / 100) if edit_basic_salary > 0 else 0.0
                                        st.markdown(f"**{edit_currency_symbol}{calculated_amount:,.2f}**")
                                        st.caption(f"= {new_deduction_percentage}% of basic")
                                    with col_delete:
                                        delete_deduction = st.checkbox("❌", key=f"delete_deduction_{emp['id']}_{deduction_index}", help="Check to delete this deduction")
                                    
                                    if new_deduction_name.strip() and not delete_deduction and edit_basic_salary > 0:
                                        edit_deductions[new_deduction_name.strip()] = calculated_amount
                                    deduction_index += 1
                            
                            # Add new deduction categories
                            if st.session_state[f"edit_new_deductions_{emp['id']}"]:
                                st.markdown("**New Deduction Categories:**")
                                for i, new_deduction in enumerate(st.session_state[f"edit_new_deductions_{emp['id']}"]):
                                    col_name, col_percentage, col_amount, col_remove = st.columns([2, 1, 1.5, 0.8])
                                    with col_name:
                                        new_deduction_name = st.text_input(f"New Category", key=f"new_deduction_name_{emp['id']}_{i}", 
                                                                         value=new_deduction["name"], placeholder="e.g., insurance")
                                    with col_percentage:
                                        new_deduction_percentage = st.number_input(f"Percentage (%)", key=f"new_deduction_percentage_{emp['id']}_{i}", 
                                                                                 value=float(new_deduction.get("percentage", 0.0)), min_value=0.0, max_value=100.0, step=0.5)
                                    with col_amount:
                                        calculated_amount = (edit_basic_salary * new_deduction_percentage / 100) if edit_basic_salary > 0 else 0.0
                                        st.markdown(f"**{edit_currency_symbol}{calculated_amount:,.2f}**")
                                        st.caption(f"= {new_deduction_percentage}% of basic")
                                    with col_remove:
                                        remove_new_deduction = st.checkbox("❌", key=f"remove_new_deduction_{emp['id']}_{i}", help="Check to remove this new deduction")
                                    
                                    if new_deduction_name.strip() and not remove_new_deduction and edit_basic_salary > 0:
                                        edit_deductions[new_deduction_name.strip()] = calculated_amount
                            
                            st.markdown("### 💰 Additional Daily Payments")
                            
                            # Handle existing additional daily payments
                            edit_additional_payments = {}
                            additional_index = 0
                            
                            if emp.get('additional_daily_payments') and isinstance(emp['additional_daily_payments'], dict):
                                for payment_name, payment_value in emp['additional_daily_payments'].items():
                                    col_name, col_value, col_delete = st.columns([2, 1, 0.8])
                                    with col_name:
                                        new_payment_name = st.text_input(f"Category", value=payment_name, key=f"edit_additional_name_{emp['id']}_{additional_index}")
                                    with col_value:
                                        new_payment_value = st.number_input(f"Daily Rate ({edit_currency_symbol})", value=float(payment_value), min_value=0.0, step=1.0, key=f"edit_additional_value_{emp['id']}_{additional_index}")
                                    with col_delete:
                                        delete_additional = st.checkbox("❌", key=f"delete_additional_{emp['id']}_{additional_index}", help="Check to delete this daily payment")
                                    
                                    if new_payment_name.strip() and not delete_additional:
                                        edit_additional_payments[new_payment_name.strip()] = new_payment_value
                                    additional_index += 1
                            
                            # Add new additional daily payment categories
                            if st.session_state[f"edit_new_daily_payments_{emp['id']}"]:
                                st.markdown("**New Additional Daily Payment Categories:**")
                                for i, new_payment in enumerate(st.session_state[f"edit_new_daily_payments_{emp['id']}"]):
                                    col_name, col_value, col_remove = st.columns([2, 1, 0.8])
                                    with col_name:
                                        new_payment_name = st.text_input(f"New Category", key=f"new_additional_name_{emp['id']}_{i}", 
                                                                       value=new_payment["name"], placeholder="e.g., Field Bonus")
                                    with col_value:
                                        new_payment_value = st.number_input(f"Daily Rate ({edit_currency_symbol})", key=f"new_additional_value_{emp['id']}_{i}", 
                                                                          value=float(new_payment["value"]), min_value=0.0, step=1.0)
                                    with col_remove:
                                        remove_new_payment = st.checkbox("❌", key=f"remove_new_additional_{emp['id']}_{i}", help="Check to remove this new daily payment")
                                    
                                    if new_payment_name.strip() and not remove_new_payment:
                                        edit_additional_payments[new_payment_name.strip()] = new_payment_value
                        
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            save_button = st.form_submit_button("💾 Save Changes", use_container_width=True)
                        with col_cancel:
                            if st.form_submit_button("❌ Cancel", use_container_width=True):
                                # Clean up session state for new items
                                if f"edit_new_payments_{emp['id']}" in st.session_state:
                                    del st.session_state[f"edit_new_payments_{emp['id']}"]
                                if f"edit_new_deductions_{emp['id']}" in st.session_state:
                                    del st.session_state[f"edit_new_deductions_{emp['id']}"]
                                if f"edit_new_daily_payments_{emp['id']}" in st.session_state:
                                    del st.session_state[f"edit_new_daily_payments_{emp['id']}"]
                                st.session_state[f"editing_{emp['id']}"] = False
                                st.rerun()
                        
                        if save_button:
                            # Remove items marked for removal from new items lists
                            if st.session_state[f"edit_new_payments_{emp['id']}"]:
                                st.session_state[f"edit_new_payments_{emp['id']}"] = [
                                    item for i, item in enumerate(st.session_state[f"edit_new_payments_{emp['id']}"])
                                    if not st.session_state.get(f"remove_new_payment_{emp['id']}_{i}", False)
                                ]
                            
                            if st.session_state[f"edit_new_deductions_{emp['id']}"]:
                                st.session_state[f"edit_new_deductions_{emp['id']}"] = [
                                    item for i, item in enumerate(st.session_state[f"edit_new_deductions_{emp['id']}"])
                                    if not st.session_state.get(f"remove_new_deduction_{emp['id']}_{i}", False)
                                ]
                            
                            if st.session_state[f"edit_new_daily_payments_{emp['id']}"]:
                                st.session_state[f"edit_new_daily_payments_{emp['id']}"] = [
                                    item for i, item in enumerate(st.session_state[f"edit_new_daily_payments_{emp['id']}"])
                                    if not st.session_state.get(f"remove_new_additional_{emp['id']}_{i}", False)
                                ]
                            
                            success, message = update_employee(
                                emp['id'], edit_emp_id, edit_emp_name, edit_employment_type, 
                                edit_currency, edit_payments, edit_deductions, edit_additional_payments
                            )
                            
                            if success:
                                st.success(message)
                                # Clean up session state for new items after successful save
                                if f"edit_new_payments_{emp['id']}" in st.session_state:
                                    del st.session_state[f"edit_new_payments_{emp['id']}"]
                                if f"edit_new_deductions_{emp['id']}" in st.session_state:
                                    del st.session_state[f"edit_new_deductions_{emp['id']}"]
                                if f"edit_new_daily_payments_{emp['id']}" in st.session_state:
                                    del st.session_state[f"edit_new_daily_payments_{emp['id']}"]
                                st.session_state[f"editing_{emp['id']}"] = False
                                st.rerun()
                            else:
                                st.error(message)
        
        # Summary statistics
        st.markdown("### 📊 Employee Statistics")
        stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
        
        with stats_col1:
            st.metric("Total Employees", len(employees))
        
        with stats_col2:
            fulltime_count = len([e for e in employees if e['employment_type'] == 'Full-time'])
            st.metric("Full-time", fulltime_count)
        
        with stats_col3:
            parttime_count = len([e for e in employees if e['employment_type'] == 'Part-time'])
            st.metric("Part-time", parttime_count)
        
        with stats_col4:
            contract_count = len([e for e in employees if e['employment_type'] in ['Contract', 'Temporary']])
            st.metric("Contract/Temp", contract_count)
    
    else:
        st.info("No employees found. Add your first employee above!")

with tab2:
    st.header("📊 Payslip Generation")
    
    # File upload section
    st.subheader("📁 Upload Timesheet")
    
    uploaded = st.file_uploader(
        "Upload GEC Timesheet Excel File", 
        type=["xls", "xlsx"],
        help="Upload your GEC template timesheet file"
    )

    if uploaded:
        st.success(f"✅ File uploaded: {uploaded.name}")
        
        try:
            df = parse_gec_timesheet(uploaded)
            st.success("📊 Timesheet parsed successfully!")
            
            timesheet_employees = df['employee_name'].unique() if 'employee_name' in df.columns else []
            
            if len(timesheet_employees) > 0:
                st.subheader("🔍 Employee Database Matching")
                
                matched_employees = []
                unmatched_employees = []
                
                for ts_emp in timesheet_employees:
                    db_employee = get_employee_by_name(ts_emp)
                    if db_employee:
                        matched_employees.append((ts_emp, db_employee))
                    else:
                        unmatched_employees.append(ts_emp)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### ✅ Matched Employees")
                    if matched_employees:
                        for ts_name, db_emp in matched_employees:
                            employee_currency = get_currency_symbol(db_emp.get('currency', 'EUR'))
                            with st.expander(f"👤 {ts_name} ({db_emp['employee_id']}) - {employee_currency}", expanded=False):
                                st.markdown(f"**Employment Type:** {db_emp['employment_type']}")
                                st.markdown(f"**Currency:** {db_emp.get('currency', 'EUR')} ({employee_currency})")
                                
                                if db_emp['payments'] and isinstance(db_emp['payments'], dict):
                                    st.markdown("**Payment Categories:**")
                                    for payment_name, payment_value in db_emp['payments'].items():
                                        st.markdown(f"• **{payment_name}**: {employee_currency}{payment_value:.2f}")
                                
                                if db_emp['deductions'] and isinstance(db_emp['deductions'], dict):
                                    st.markdown("**Deduction Categories:**")
                                    for deduction_name, deduction_value in db_emp['deductions'].items():
                                        st.markdown(f"• **{deduction_name}**: {employee_currency}{deduction_value:.2f}")
                    else:
                        st.info("No employees matched yet.")
                
                with col2:
                    st.markdown("### ⚠️ Unmatched Employees")
                    if unmatched_employees:
                        for unmatched in unmatched_employees:
                            st.markdown(f"• {unmatched}")
                        st.warning("Add these employees in the Employee Management tab.")
                    else:
                        st.success("✅ All employees matched!")
                
                # Show summary
                total_employees = len(timesheet_employees)
                matched_count = len(matched_employees)
                match_percentage = (matched_count / total_employees * 100) if total_employees > 0 else 0
                
                st.markdown("### 📊 Matching Summary")
                summary_col1, summary_col2, summary_col3 = st.columns(3)
                with summary_col1:
                    st.metric("Total Employees", total_employees)
                with summary_col2:
                    st.metric("Matched", matched_count)
                with summary_col3:
                    st.metric("Match %", f"{match_percentage:.1f}%")
                
                st.subheader("📊 Timesheet Data Preview")
                st.dataframe(df.head(10), use_container_width=True)
                
        except Exception as e:
            st.error(f"❌ Error parsing timesheet: {str(e)}")
    else:
        st.info("👆 Please upload an Excel file to continue")
