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
            monthly_basic_salary REAL NOT NULL DEFAULT 0.0,
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
    
    # Add monthly_basic_salary column if it doesn't exist (for backward compatibility)
    try:
        cursor.execute('ALTER TABLE employees ADD COLUMN monthly_basic_salary REAL DEFAULT 0.0')
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

def add_employee(employee_id, employee_name, employment_type, currency, monthly_basic_salary, payments, deductions, additional_daily_payments=None):
    """Add a new employee to the database"""
    conn = sqlite3.connect('employees.db')
    cursor = conn.cursor()
    
    try:
        payments_json = json.dumps(payments) if payments else json.dumps({})
        deductions_json = json.dumps(deductions) if deductions else json.dumps({})
        additional_payments_json = json.dumps(additional_daily_payments) if additional_daily_payments else json.dumps({})
        
        cursor.execute('''
            INSERT INTO employees (employee_id, employee_name, employment_type, currency, monthly_basic_salary, payments, deductions, additional_daily_payments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (employee_id, employee_name, employment_type, currency, monthly_basic_salary, payments_json, deductions_json, additional_payments_json))
        
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
        # Handle monthly_basic_salary with proper type checking
        monthly_salary = result[10] if len(result) > 10 and result[10] is not None else 0.0
        if isinstance(monthly_salary, str):
            try:
                # Try to parse as JSON first (legacy data)
                salary_data = json.loads(monthly_salary)
                if isinstance(salary_data, dict) and 'basic salary' in salary_data:
                    monthly_salary = salary_data['basic salary']
                else:
                    monthly_salary = 0.0
            except (json.JSONDecodeError, KeyError):
                try:
                    monthly_salary = float(monthly_salary)
                except ValueError:
                    monthly_salary = 0.0
        else:
            try:
                monthly_salary = float(monthly_salary) if monthly_salary is not None else 0.0
            except (ValueError, TypeError):
                monthly_salary = 0.0
        
        return {
            'id': result[0],
            'employee_id': result[1],
            'employee_name': result[2],
            'employment_type': result[3],
            'currency': result[4] if len(result) > 4 and result[4] else 'EUR',
            'monthly_basic_salary': monthly_salary,
            'payments': json.loads(result[5]) if len(result) > 5 and result[5] else {},
            'deductions': json.loads(result[6]) if len(result) > 6 and result[6] else {},
            'additional_daily_payments': json.loads(result[9]) if len(result) > 9 and result[9] else {},
            'created_at': result[7] if len(result) > 7 else '',
            'updated_at': result[8] if len(result) > 8 else ''
        }
    return None

def get_all_employees():
    """Get all employees from database"""
    conn = sqlite3.connect('employees.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM employees ORDER BY CAST(employee_id AS INTEGER)')
    results = cursor.fetchall()
    conn.close()
    
    employees = []
    for result in results:
        try:
            try:
                payments_data = json.loads(result[5]) if len(result) > 5 and result[5] else {}
            except json.JSONDecodeError:
                payments_data = {}
            
            try:
                deductions_data = json.loads(result[6]) if len(result) > 6 and result[6] else {}
            except json.JSONDecodeError:
                deductions_data = {}
            
            try:
                additional_payments_data = json.loads(result[9]) if len(result) > 9 and result[9] else {}
            except json.JSONDecodeError:
                additional_payments_data = {}
            
            # Handle monthly_basic_salary with proper type checking
            monthly_salary = result[10] if len(result) > 10 and result[10] is not None else 0.0
            if isinstance(monthly_salary, str):
                try:
                    # Try to parse as JSON first (legacy data)
                    salary_data = json.loads(monthly_salary)
                    if isinstance(salary_data, dict) and 'basic salary' in salary_data:
                        monthly_salary = salary_data['basic salary']
                    else:
                        monthly_salary = 0.0
                except (json.JSONDecodeError, KeyError):
                    try:
                        monthly_salary = float(monthly_salary)
                    except ValueError:
                        monthly_salary = 0.0
            else:
                try:
                    monthly_salary = float(monthly_salary) if monthly_salary is not None else 0.0
                except (ValueError, TypeError):
                    monthly_salary = 0.0
            
            employees.append({
                'id': result[0],
                'employee_id': result[1],
                'employee_name': result[2],
                'employment_type': result[3],
                'currency': result[4] if len(result) > 4 and result[4] else 'EUR',
                'monthly_basic_salary': monthly_salary,
                'payments': payments_data,
                'deductions': deductions_data,
                'additional_daily_payments': additional_payments_data,
                'created_at': result[7] if len(result) > 7 else '',
                'updated_at': result[8] if len(result) > 8 else ''
            })
        except Exception as e:
            continue
    
    return employees

def update_employee(emp_id, employee_id, employee_name, employment_type, currency, monthly_basic_salary, payments, deductions, additional_daily_payments=None):
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
                monthly_basic_salary = ?, payments = ?, deductions = ?, additional_daily_payments = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (employee_id, employee_name, employment_type, currency, monthly_basic_salary, payments_json, deductions_json, additional_payments_json, emp_id))
        
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

def update_existing_employees_with_defaults():
    """Update existing employees to have default payment and deduction categories"""
    conn = sqlite3.connect('employees.db')
    cursor = conn.cursor()
    
    try:
        # Get all employees
        cursor.execute('SELECT * FROM employees')
        employees = cursor.fetchall()
        
        for emp in employees:
            emp_id = emp[0]
            
            # Parse existing payments and deductions
            try:
                existing_payments = json.loads(emp[5]) if len(emp) > 5 and emp[5] else {}
            except json.JSONDecodeError:
                existing_payments = {}
            
            try:
                existing_deductions = json.loads(emp[6]) if len(emp) > 6 and emp[6] else {}
            except json.JSONDecodeError:
                existing_deductions = {}
            
            # Add default payment categories if they don't exist
            default_payments = {
                "Monthly Transport Allowance": 0.0,
                "Monthly Housing Allowance": 0.0,
                "Monthly Geographic Coefficient": 0.0,
                "Monthly Relocation": 0.0,
                "STIP Bonus": 0.0
            }
            
            # Merge with existing payments (existing values take precedence)
            for key, value in default_payments.items():
                if key not in existing_payments:
                    existing_payments[key] = value
            
            # Migrate old spelling to new spelling for Monthly Geographic Coefficient
            if "Monthly Geographic Coeffient" in existing_payments and "Monthly Geographic Coefficient" not in existing_payments:
                existing_payments["Monthly Geographic Coefficient"] = existing_payments["Monthly Geographic Coeffient"]
                del existing_payments["Monthly Geographic Coeffient"]
            elif "Monthly Geographic Coeffient" in existing_payments and "Monthly Geographic Coefficient" in existing_payments:
                # If both exist, keep the new spelling and remove the old one
                del existing_payments["Monthly Geographic Coeffient"]
            
            # Auto-calculate Monthly Geographic Coefficient based on basic salary and housing allowance
            monthly_salary = emp[4] if len(emp) > 4 else 0  # monthly_basic_salary is at index 4
            if isinstance(monthly_salary, str):
                try:
                    monthly_salary = float(monthly_salary)
                except ValueError:
                    monthly_salary = 0.0
            
            housing_allowance = existing_payments.get("Monthly Housing Allowance", 0)
            if monthly_salary > 0 and housing_allowance > 0 and "Monthly Geographic Coefficient" in existing_payments:
                # Auto-calculate as 20% of basic salary only if housing allowance is also present
                existing_payments["Monthly Geographic Coefficient"] = monthly_salary * 0.2
            
            # Add default deduction categories if they don't exist
            default_deductions = {
                "Monthly EMBO": 0.0,
                "Monthly EE Pension Contribution": 0.0
            }
            
            # Merge with existing deductions (existing values take precedence)
            for key, value in default_deductions.items():
                if key not in existing_deductions:
                    existing_deductions[key] = value
            
            # Auto-calculate Monthly EMBO if basic salary, geographic coefficient, or relocation exist
            geographic_coefficient = existing_payments.get("Monthly Geographic Coefficient", 0)
            # Also check for old spelling for backward compatibility
            if geographic_coefficient == 0:
                geographic_coefficient = existing_payments.get("Monthly Geographic Coeffient", 0)
            relocation = existing_payments.get("Monthly Relocation", 0)
            
            # Auto-calculate EMBO only if BOTH geographic coefficient AND relocation have values
            if (geographic_coefficient > 0 and relocation > 0) and "Monthly EMBO" in existing_deductions:
                embo_base = monthly_salary + geographic_coefficient + relocation
                embo_amount = embo_base * 13.0 / 100
                existing_deductions["Monthly EMBO"] = embo_amount
            
            # Parse existing additional daily payments
            try:
                existing_additional_payments = json.loads(emp[9]) if len(emp) > 9 and emp[9] else {}
            except json.JSONDecodeError:
                existing_additional_payments = {}
            
            # Add default additional daily payment categories if they don't exist
            default_additional_payments = {
                "Field Bonus / Job Bonus in Country": 0.0,
                "Rotation Premium - In country": 0.0,
                "Standby Rate - In country": 0.0,
                "Wellsite Rate In country": 0.0
            }
            
            # Merge with existing additional payments (existing values take precedence)
            for key, value in default_additional_payments.items():
                if key not in existing_additional_payments:
                    existing_additional_payments[key] = value
            
            # Update the employee record
            payments_json = json.dumps(existing_payments)
            deductions_json = json.dumps(existing_deductions)
            additional_payments_json = json.dumps(existing_additional_payments)
            
            cursor.execute('''
                UPDATE employees 
                SET payments = ?, deductions = ?, additional_daily_payments = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (payments_json, deductions_json, additional_payments_json, emp_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating existing employees: {e}")
        return False
    finally:
        conn.close()

# Initialize database on app start
init_database()

# Update existing employees with default categories (run once)
if 'defaults_updated' not in st.session_state:
    update_existing_employees_with_defaults()
    st.session_state.defaults_updated = True

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
            # Initialize default categories when opening the form
            if 'payment_items' not in st.session_state or not st.session_state.payment_items:
                st.session_state.payment_items = [
                    {"name": "Monthly Transport Allowance", "value": 0.0},
                    {"name": "Monthly Housing Allowance", "value": 0.0},
                    {"name": "Monthly Geographic Coefficient", "value": 0.0, "auto_calculate": True, "percentage": 20.0},
                    {"name": "Monthly Relocation", "value": 0.0},
                    {"name": "STIP Bonus", "value": 0.0}
                ]
            if 'deduction_items' not in st.session_state or not st.session_state.deduction_items:
                st.session_state.deduction_items = [
                    {"name": "Monthly EMBO", "percentage": 13.0, "formula": "basic_salary+geographic_coefficient+relocation"},
                    {"name": "Monthly EE Pension Contribution", "percentage": 8.0, "formula": "basic_salary+stip_bonus"}
                ]
            if 'additional_daily_items' not in st.session_state or not st.session_state.additional_daily_items:
                st.session_state.additional_daily_items = [
                    {"name": "Field Bonus / Job Bonus in Country", "value": 0.0},
                    {"name": "Rotation Premium - In country", "value": 0.0},
                    {"name": "Standby Rate - In country", "value": 0.0},
                    {"name": "Wellsite Rate In country", "value": 0.0}
                ]
    
    # Add Employee Form (popup style)
    if st.session_state.get('show_add_employee_form', False):
        with st.container():
            st.markdown("---")
            st.subheader("➕ Add New Employee")
            

            
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
                    
                    # Monthly Basic Salary field
                    monthly_basic_salary = st.number_input(f"Monthly Basic Salary* ({currency_symbol})", 
                                                         min_value=0.0, step=100.0, 
                                                         placeholder="Enter monthly basic salary",
                                                         key="new_monthly_basic_salary")
                
                with col2:
                    st.markdown("### 💰 Payment Categories")
                    
                    # Initialize session state for dynamic inputs with default payment categories
                    if 'payment_items' not in st.session_state:
                        # Default payment categories
                        st.session_state.payment_items = [
                            {"name": "Monthly Transport Allowance", "value": 0.0},
                            {"name": "Monthly Housing Allowance", "value": 0.0},
                            {"name": "Monthly Geographic Coefficient", "value": 0.0, "auto_calculate": True, "percentage": 20.0},
                            {"name": "Monthly Relocation", "value": 0.0},
                            {"name": "STIP Bonus", "value": 0.0}
                        ]
                    
                    # Payment section
                    payment_dict = {}
                    for i, item in enumerate(st.session_state.payment_items):
                        col_name, col_value = st.columns([3, 2])
                        with col_name:
                            # Display category name as read-only text
                            st.markdown(f"**{item['name']}**")
                            payment_name = item["name"]  # Use the fixed name from session state
                        with col_value:
                            # Auto-calculate Monthly Geographic Coefficient as 20% of basic salary
                            if item.get("auto_calculate") and "Geographic" in item["name"]:
                                # Get Housing Allowance value from current form inputs
                                housing_allowance = 0.0
                                for j, housing_item in enumerate(st.session_state.payment_items):
                                    if "Housing Allowance" in housing_item["name"]:
                                        housing_key = f"payment_value_{j}"
                                        if housing_key in st.session_state:
                                            housing_allowance = st.session_state[housing_key]
                                        break
                                
                                # Only auto-calculate if both Basic Salary and Housing Allowance have values
                                if monthly_basic_salary > 0 and housing_allowance > 0:
                                    auto_calculated_value = monthly_basic_salary * 0.2
                                    # Update the session state value to reflect the auto-calculation
                                    st.session_state.payment_items[i]["value"] = auto_calculated_value
                                    payment_value = st.number_input(f"Rate ({currency_symbol})", key=f"payment_value_{i}", 
                                                                  value=float(auto_calculated_value), min_value=0.0, step=10.0,
                                                                  help=f"Auto-calculated as 20% of Basic Salary ({currency_symbol}{monthly_basic_salary:,.2f})",
                                                                  disabled=True)
                                    st.caption(f"💡 Auto: 20% of Basic Salary ({currency_symbol}{monthly_basic_salary:,.2f})")
                                else:
                                    # Show 0 when either basic salary or housing allowance is not entered yet
                                    payment_value = st.number_input(f"Rate ({currency_symbol})", key=f"payment_value_{i}", 
                                                                  value=0.0, min_value=0.0, step=10.0,
                                                                  help="Will auto-calculate when both Basic Salary and Housing Allowance are entered",
                                                                  disabled=True)
                                    if monthly_basic_salary == 0:
                                        st.caption(f"💡 Requires Basic Salary to auto-calculate")
                                    elif housing_allowance == 0:
                                        st.caption(f"💡 Requires Housing Allowance to auto-calculate")
                                    else:
                                        st.caption(f"💡 Will auto-calculate as 20% of Basic Salary")
                            else:
                                payment_value = st.number_input(f"Rate ({currency_symbol})", key=f"payment_value_{i}", 
                                                              value=float(item["value"]), min_value=0.0, step=10.0)
                        
                        if payment_name.strip():
                            # For auto-calculated Geographic Coefficient, ensure we use the calculated value
                            if "Geographic Coefficient" in payment_name and monthly_basic_salary > 0:
                                # Get Housing Allowance value to check if auto-calculation should apply
                                housing_allowance = 0.0
                                for j, housing_item in enumerate(st.session_state.payment_items):
                                    if "Housing Allowance" in housing_item["name"]:
                                        housing_key = f"payment_value_{j}"
                                        if housing_key in st.session_state:
                                            housing_allowance = st.session_state[housing_key]
                                        break
                                
                                # Use auto-calculated value if both conditions are met
                                if housing_allowance > 0:
                                    payment_dict[payment_name.strip()] = monthly_basic_salary * 0.2
                                else:
                                    payment_dict[payment_name.strip()] = payment_value
                            else:
                                payment_dict[payment_name.strip()] = payment_value
                    
                    st.markdown("### ➖ Deduction Categories")
                    
                    # Use the monthly basic salary for percentage calculations
                    basic_salary = monthly_basic_salary
                    
                    if basic_salary > 0:
                        st.info(f"📊 Basic Salary: {currency_symbol}{basic_salary:,.2f} - Deductions calculated as percentages")
                    else:
                        st.warning("⚠️ Please enter Monthly Basic Salary to calculate deductions.")
                    
                    # Initialize session state for deductions with default deduction categories
                    if 'deduction_items' not in st.session_state:
                        # Default deduction categories
                        st.session_state.deduction_items = [
                            {"name": "Monthly EMBO", "percentage": 13.0, "formula": "basic_salary+geographic_coefficient+relocation"},
                            {"name": "Monthly EE Pension Contribution", "percentage": 8.0, "formula": "basic_salary+stip_bonus"}
                        ]
                    
                    # Deduction section with percentage input
                    deduction_dict = {}
                    for i, item in enumerate(st.session_state.deduction_items):
                        col_name, col_percentage, col_amount = st.columns([3, 1.5, 2])
                        with col_name:
                            # Display category name as read-only text
                            st.markdown(f"**{item['name']}**")
                            deduction_name = item["name"]  # Use the fixed name from session state
                        with col_percentage:
                            deduction_percentage = st.number_input(f"Percentage (%)", key=f"deduction_percentage_{i}", 
                                                                 value=float(item.get("percentage", 0.0)), min_value=0.0, max_value=100.0, step=0.5)
                        with col_amount:
                            # Calculate amount based on formula and percentage
                            if item.get("formula") and basic_salary > 0:
                                # Get values from payment_dict for calculations
                                geographic_coefficient = payment_dict.get("Monthly Geographic Coefficient", 0)
                                # Also check for old spelling for backward compatibility
                                if geographic_coefficient == 0:
                                    geographic_coefficient = payment_dict.get("Monthly Geographic Coeffient", 0)
                                relocation = payment_dict.get("Monthly Relocation", 0)
                                stip_bonus = payment_dict.get("STIP Bonus", 0)
                                
                                if item["formula"] == "basic_salary+geographic_coefficient+relocation":
                                    # Only calculate EMBO if BOTH geographic coefficient AND relocation have values
                                    if geographic_coefficient > 0 and relocation > 0:
                                        base_amount = basic_salary + geographic_coefficient + relocation
                                        calculated_amount = base_amount * deduction_percentage / 100
                                        st.markdown(f"**{currency_symbol}{calculated_amount:,.2f}**")
                                        st.caption(f"= {deduction_percentage}% of ({currency_symbol}{basic_salary:,.2f} + {currency_symbol}{geographic_coefficient:,.2f} + {currency_symbol}{relocation:,.2f}) = {currency_symbol}{base_amount:,.2f}")
                                    else:
                                        calculated_amount = 0.0
                                        st.markdown(f"**{currency_symbol}0.00**")
                                        st.caption("EMBO requires BOTH Geographic Coefficient AND Relocation")
                                elif item["formula"] == "basic_salary+stip_bonus":
                                    base_amount = basic_salary + stip_bonus
                                    calculated_amount = base_amount * deduction_percentage / 100
                                    st.markdown(f"**{currency_symbol}{calculated_amount:,.2f}**")
                                    st.caption(f"= {deduction_percentage}% of (Basic + STIP Bonus)")
                                else:
                                    calculated_amount = (basic_salary * deduction_percentage / 100) if basic_salary > 0 else 0.0
                                    st.markdown(f"**{currency_symbol}{calculated_amount:,.2f}**")
                                    st.caption(f"= {deduction_percentage}% of basic salary")
                            else:
                                # Standard calculation for custom deductions
                                calculated_amount = (basic_salary * deduction_percentage / 100) if basic_salary > 0 else 0.0
                                st.markdown(f"**{currency_symbol}{calculated_amount:,.2f}**")
                                st.caption(f"= {deduction_percentage}% of basic salary")
                        
                        if deduction_name.strip():
                            # For EMBO, only add if both Geographic Coefficient and Relocation have values
                            if deduction_name.strip() == "Monthly EMBO":
                                geographic_coefficient = payment_dict.get("Monthly Geographic Coefficient", 0)
                                # Also check for old spelling for backward compatibility
                                if geographic_coefficient == 0:
                                    geographic_coefficient = payment_dict.get("Monthly Geographic Coeffient", 0)
                                relocation = payment_dict.get("Monthly Relocation", 0)
                                
                                # Only add EMBO if both conditions are met (regardless of calculated amount)
                                if geographic_coefficient > 0 and relocation > 0:
                                    deduction_dict[deduction_name.strip()] = calculated_amount
                            else:
                                deduction_dict[deduction_name.strip()] = calculated_amount
                            # Update session state with percentage
                            st.session_state.deduction_items[i]["percentage"] = deduction_percentage
                    
                    st.markdown("### ➖ Additional Deduction")
                    
                    # Calculate Monthly ER Pension Contribution (editable percentage of basic_salary + stip_bonus)
                    if basic_salary > 0:
                        stip_bonus = payment_dict.get("STIP Bonus", 0)
                        er_pension_base = basic_salary + stip_bonus
                        
                        col_er_name, col_er_percentage, col_er_amount = st.columns([3, 1.5, 2])
                        with col_er_name:
                            st.markdown("**Monthly ER Pension Contribution**")
                        with col_er_percentage:
                            er_pension_percentage = st.number_input("Percentage (%)", value=6.5, min_value=0.0, max_value=100.0, step=0.5, key="er_pension_percentage")
                        with col_er_amount:
                            er_pension_amount = er_pension_base * er_pension_percentage / 100
                            st.markdown(f"**{currency_symbol}{er_pension_amount:,.2f}**")
                            st.caption(f"= {er_pension_percentage}% of (Basic + STIP Bonus)")
                        
                        # Add to deduction_dict
                        deduction_dict["Monthly ER Pension Contribution"] = er_pension_amount
                        
                    else:
                        st.warning("⚠️ Please enter Monthly Basic Salary to calculate ER Pension Contribution.")
                        
                        # Show in table format similar to deduction categories when basic salary is not available
                        col_er_name, col_er_percentage, col_er_amount = st.columns([3, 1.5, 2])
                        with col_er_name:
                            st.markdown("**Monthly ER Pension Contribution**")
                        with col_er_percentage:
                            er_pension_percentage = st.number_input("Percentage (%)", value=6.5, min_value=0.0, max_value=100.0, step=0.5, key="er_pension_percentage_empty")
                        with col_er_amount:
                            st.markdown(f"**{currency_symbol}0.00**")
                            st.caption(f"= {er_pension_percentage}% of (Basic + STIP Bonus)")
                        
                    
                    st.markdown("### 💰 Additional Daily Payments")
                    
                    # Initialize session state for additional daily payments with default categories
                    if 'additional_daily_items' not in st.session_state:
                        # Default additional daily payment categories
                        st.session_state.additional_daily_items = [
                            {"name": "Field Bonus / Job Bonus in Country", "value": 0.0},
                            {"name": "Rotation Premium - In country", "value": 0.0},
                            {"name": "Standby Rate - In country", "value": 0.0},
                            {"name": "Wellsite Rate In country", "value": 0.0}
                        ]
                    
                    # Additional Daily Payments section
                    additional_payments = {}
                    for i, item in enumerate(st.session_state.additional_daily_items):
                        col_name, col_value = st.columns([3, 2])
                        with col_name:
                            # Display category name as read-only text
                            st.markdown(f"**{item['name']}**")
                            daily_payment_name = item["name"]  # Use the fixed name from session state
                        with col_value:
                            daily_payment_value = st.number_input(f"Daily Rate ({currency_symbol})", key=f"daily_payment_value_{i}", 
                                                          value=float(item["value"]), min_value=0.0, step=1.0)
                        
                        if daily_payment_name.strip():
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
                    
                    if new_emp_id and new_emp_name and employment_type and currency and monthly_basic_salary > 0:
                        success, message = add_employee(new_emp_id, new_emp_name, employment_type, currency, monthly_basic_salary, payment_dict, deduction_dict)
                        
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
                            
                            # Reset to default categories after successful save
                            st.session_state.payment_items = [
                                {"name": "Monthly Transport Allowance", "value": 0.0},
                                {"name": "Monthly Housing Allowance", "value": 0.0},
                                {"name": "Monthly Geographic Coefficient", "value": 0.0, "auto_calculate": True, "percentage": 20.0},
                                {"name": "Monthly Relocation", "value": 0.0},
                                {"name": "STIP Bonus", "value": 0.0}
                            ]
                            st.session_state.deduction_items = [
                                {"name": "Monthly EMBO", "percentage": 13.0, "formula": "basic_salary+geographic_coefficient+relocation"},
                                {"name": "Monthly EE Pension Contribution", "percentage": 8.0, "formula": "basic_salary+stip_bonus"}
                            ]
                            st.session_state.additional_daily_items = [
                                {"name": "Field Bonus / Job Bonus in Country", "value": 0.0},
                                {"name": "Rotation Premium - In country", "value": 0.0},
                                {"name": "Standby Rate - In country", "value": 0.0},
                                {"name": "Wellsite Rate In country", "value": 0.0}
                            ]
                            st.session_state['show_add_employee_form'] = False
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Please fill in all required fields (marked with *) and ensure Monthly Basic Salary is greater than 0")
                
                if cancel_button:
                    # Reset to default categories
                    st.session_state.payment_items = [
                        {"name": "Monthly Transport Allowance", "value": 0.0},
                        {"name": "Monthly Housing Allowance", "value": 0.0},
                        {"name": "Monthly Geographic Coefficient", "value": 0.0, "auto_calculate": True, "percentage": 20.0},
                        {"name": "Monthly Relocation", "value": 0.0},
                        {"name": "STIP Bonus", "value": 0.0}
                    ]
                    st.session_state.deduction_items = [
                        {"name": "Monthly EMBO", "percentage": 13.0, "formula": "basic_salary+geographic_coefficient+relocation"},
                        {"name": "Monthly EE Pension Contribution", "percentage": 8.0, "formula": "basic_salary+stip_bonus"}
                    ]
                    st.session_state.additional_daily_items = [
                        {"name": "Field Bonus / Job Bonus in Country", "value": 0.0},
                        {"name": "Rotation Premium - In country", "value": 0.0},
                        {"name": "Standby Rate - In country", "value": 0.0},
                        {"name": "Wellsite Rate In country", "value": 0.0}
                    ]
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
                    
                    # Handle monthly_basic_salary with proper type checking
                    monthly_salary = emp.get('monthly_basic_salary', 0)
                    try:
                        if isinstance(monthly_salary, str):
                            # If it's a string, try to parse as JSON first, then as float
                            try:
                                import json
                                salary_data = json.loads(monthly_salary)
                                if isinstance(salary_data, dict) and 'basic salary' in salary_data:
                                    monthly_salary = salary_data['basic salary']
                                else:
                                    monthly_salary = 0.0
                            except (json.JSONDecodeError, KeyError):
                                try:
                                    monthly_salary = float(monthly_salary)
                                except ValueError:
                                    monthly_salary = 0.0
                        else:
                            monthly_salary = float(monthly_salary) if monthly_salary is not None else 0.0
                    except (ValueError, TypeError):
                        monthly_salary = 0.0
                    
                    st.markdown(f"**Monthly Basic Salary:** {currency_symbol}{monthly_salary:,.2f}")
                    st.markdown(f"**Created:** {emp['created_at'][:10] if emp['created_at'] else 'Unknown'}")
                
                with col2:
                    currency_symbol = get_currency_symbol(emp.get('currency', 'EUR'))
                    
                    if emp['payments']:
                        st.markdown("**Payment Categories:**")
                        total_payments = 0
                        if isinstance(emp['payments'], dict):
                            payment_data = []
                            # Clean up duplicate Geographic Coefficient entries
                            cleaned_payments = dict(emp['payments'])
                            if "Monthly Geographic Coeffient" in cleaned_payments and "Monthly Geographic Coefficient" in cleaned_payments:
                                # If both exist, remove the old spelling
                                del cleaned_payments["Monthly Geographic Coeffient"]
                            elif "Monthly Geographic Coeffient" in cleaned_payments:
                                # If only old spelling exists, rename it to new spelling
                                cleaned_payments["Monthly Geographic Coefficient"] = cleaned_payments["Monthly Geographic Coeffient"]
                                del cleaned_payments["Monthly Geographic Coeffient"]
                            
                            # Auto-calculate Monthly Geographic Coefficient if basic salary and housing allowance exist
                            monthly_salary = emp.get('monthly_basic_salary', 0)
                            if isinstance(monthly_salary, str):
                                try:
                                    monthly_salary = float(monthly_salary)
                                except ValueError:
                                    monthly_salary = 0.0
                            
                            housing_allowance = cleaned_payments.get("Monthly Housing Allowance", 0)
                            if monthly_salary > 0 and housing_allowance > 0 and "Monthly Geographic Coefficient" in cleaned_payments:
                                # Auto-calculate as 20% of basic salary only if housing allowance is also present
                                cleaned_payments["Monthly Geographic Coefficient"] = monthly_salary * 0.2
                            
                            # Define display order to ensure Geographic Coefficient is 3rd
                            display_order = [
                                "Monthly Transport Allowance",
                                "Monthly Housing Allowance", 
                                "Monthly Geographic Coefficient",
                                "Monthly Relocation",
                                "STIP Bonus"
                            ]
                            
                            # Add payments in the specified order
                            for payment_name in display_order:
                                if payment_name in cleaned_payments:
                                    payment_value = cleaned_payments[payment_name]
                                    payment_data.append({
                                        'Category': payment_name,
                                        'Amount': f"{currency_symbol}{payment_value:,.2f}"
                                    })
                                    total_payments += payment_value
                            
                            # Add any remaining payments not in the standard order
                            for payment_name, payment_value in cleaned_payments.items():
                                if payment_name not in display_order:
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
                            # Auto-calculate Monthly EMBO if basic salary, geographic coefficient, or relocation exist
                            cleaned_deductions = dict(emp['deductions'])
                            monthly_salary = emp.get('monthly_basic_salary', 0)
                            if isinstance(monthly_salary, str):
                                try:
                                    monthly_salary = float(monthly_salary)
                                except ValueError:
                                    monthly_salary = 0.0
                            
                            if emp['payments'] and isinstance(emp['payments'], dict):
                                geographic_coefficient = emp['payments'].get("Monthly Geographic Coefficient", 0)
                                # Also check for old spelling for backward compatibility
                                if geographic_coefficient == 0:
                                    geographic_coefficient = emp['payments'].get("Monthly Geographic Coeffient", 0)
                                relocation = emp['payments'].get("Monthly Relocation", 0)
                                
                                # Auto-calculate EMBO only if BOTH geographic coefficient AND relocation have values
                                if (geographic_coefficient > 0 and relocation > 0) and "Monthly EMBO" in cleaned_deductions:
                                    embo_base = monthly_salary + geographic_coefficient + relocation
                                    embo_amount = embo_base * 13.0 / 100
                                    cleaned_deductions["Monthly EMBO"] = embo_amount
                            
                            deduction_data = []
                            for deduction_name, deduction_value in cleaned_deductions.items():
                                # Exclude ER Pension Contribution from regular deductions display
                                if deduction_name != "Monthly ER Pension Contribution":
                                    deduction_data.append({
                                        'Category': deduction_name,
                                        'Amount': f"{currency_symbol}{deduction_value:,.2f}"
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
                    
                    # Additional Deduction - Monthly ER Pension Contribution (auto-calculated)
                    st.markdown("**Additional Deduction:**")
                    monthly_salary = emp.get('monthly_basic_salary', 0)
                    if isinstance(monthly_salary, str):
                        try:
                            monthly_salary = float(monthly_salary)
                        except ValueError:
                            monthly_salary = 0.0
                    
                    stip_bonus = 0.0
                    if emp['payments'] and isinstance(emp['payments'], dict):
                        stip_bonus = emp['payments'].get("STIP Bonus", 0.0)
                    
                    if monthly_salary > 0:
                        er_pension_base = monthly_salary + stip_bonus
                        er_pension_amount = er_pension_base * 6.5 / 100
                        
                        additional_deduction_data = [{
                            'Category': 'Monthly ER Pension Contribution',
                            'Amount': f"{currency_symbol}{er_pension_amount:,.2f}"
                        }]
                        
                        additional_deduction_df = pd.DataFrame(additional_deduction_data)
                        st.dataframe(additional_deduction_df, use_container_width=True, hide_index=True)
                    else:
                        # Show empty table format similar to deduction categories
                        empty_additional_deduction_data = [{
                            'Category': 'Monthly ER Pension Contribution',
                            'Amount': f"{currency_symbol}0.00"
                        }]
                        
                        empty_additional_deduction_df = pd.DataFrame(empty_additional_deduction_data)
                        st.dataframe(empty_additional_deduction_df, use_container_width=True, hide_index=True)
                    
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
                            
                            # Handle monthly_basic_salary with proper type checking for edit form
                            current_monthly_salary = emp.get('monthly_basic_salary', 0)
                            try:
                                if isinstance(current_monthly_salary, str):
                                    # If it's a string, try to parse as JSON first, then as float
                                    try:
                                        import json
                                        salary_data = json.loads(current_monthly_salary)
                                        if isinstance(salary_data, dict) and 'basic salary' in salary_data:
                                            current_monthly_salary = salary_data['basic salary']
                                        else:
                                            current_monthly_salary = 0.0
                                    except (json.JSONDecodeError, KeyError):
                                        try:
                                            current_monthly_salary = float(current_monthly_salary)
                                        except ValueError:
                                            current_monthly_salary = 0.0
                                else:
                                    current_monthly_salary = float(current_monthly_salary) if current_monthly_salary is not None else 0.0
                            except (ValueError, TypeError):
                                current_monthly_salary = 0.0
                            
                            # Monthly Basic Salary field
                            edit_monthly_basic_salary = st.number_input(
                                f"Monthly Basic Salary ({edit_currency_symbol})", 
                                value=current_monthly_salary,
                                min_value=0.0, step=100.0,
                                key=f"edit_monthly_basic_salary_{emp['id']}"
                            )
                        
                        with edit_col2:
                            st.markdown(f"**Edit Payment Categories ({edit_currency_symbol}):**")
                            edit_payments = {}
                            payment_index = 0
                            
                            # Handle both old list format and new dict format
                            if isinstance(emp['payments'], dict):
                                for payment_name, payment_value in emp['payments'].items():
                                    col_name, col_value = st.columns([2, 1])
                                    with col_name:
                                        # Display category name as read-only text
                                        st.markdown(f"**{payment_name}**")
                                        new_payment_name = payment_name  # Use the existing name, don't allow editing
                                    with col_value:
                                        new_payment_value = st.number_input(f"Rate ({edit_currency_symbol})", value=float(payment_value), min_value=0.0, step=10.0, key=f"edit_payment_value_{emp['id']}_{payment_index}")
                                    
                                    if new_payment_name.strip():
                                        edit_payments[new_payment_name.strip()] = new_payment_value
                                    payment_index += 1
                            else:
                                # Convert old list format to dict format
                                for payment_name in emp['payments']:
                                    col_name, col_value = st.columns([2, 1])
                                    with col_name:
                                        # Display category name as read-only text
                                        st.markdown(f"**{payment_name}**")
                                        new_payment_name = payment_name  # Use the existing name, don't allow editing
                                    with col_value:
                                        new_payment_value = st.number_input(f"Rate ({edit_currency_symbol})", value=0.0, min_value=0.0, step=10.0, key=f"edit_payment_value_{emp['id']}_{payment_index}")
                                    
                                    if new_payment_name.strip():
                                        edit_payments[new_payment_name.strip()] = new_payment_value
                                    payment_index += 1
                            
                            # Add new payment categories
                            if st.session_state[f"edit_new_payments_{emp['id']}"]:
                                st.markdown("**New Payment Categories:**")
                                for i, new_payment in enumerate(st.session_state[f"edit_new_payments_{emp['id']}"]):
                                    col_name, col_value = st.columns([2, 1])
                                    with col_name:
                                        new_payment_name = st.text_input(f"New Category", key=f"new_payment_name_{emp['id']}_{i}", 
                                                                       value=new_payment["name"], placeholder="e.g., bonus")
                                    with col_value:
                                        new_payment_value = st.number_input(f"Rate ({edit_currency_symbol})", key=f"new_payment_value_{emp['id']}_{i}", 
                                                                          value=float(new_payment["value"]), min_value=0.0, step=10.0)
                                    
                                    if new_payment_name.strip():
                                        edit_payments[new_payment_name.strip()] = new_payment_value
                            
                            # Auto-calculate Monthly Geographic Coefficient for edit form
                            housing_allowance = edit_payments.get("Monthly Housing Allowance", 0)
                            if edit_monthly_basic_salary > 0 and housing_allowance > 0 and "Monthly Geographic Coefficient" in edit_payments:
                                edit_payments["Monthly Geographic Coefficient"] = edit_monthly_basic_salary * 0.2
                            
                            st.markdown(f"**Edit Deduction Categories ({edit_currency_symbol}):**")
                            
                            # Use the monthly basic salary for percentage calculations in edit mode
                            edit_basic_salary = edit_monthly_basic_salary
                            
                            if edit_basic_salary > 0:
                                st.info(f"📊 Basic Salary: {edit_currency_symbol}{edit_basic_salary:,.2f} - Deductions calculated as percentages")
                            else:
                                st.warning("⚠️ Please enter Monthly Basic Salary to calculate deductions.")
                            
                            edit_deductions = {}
                            deduction_index = 0
                            
                            # Auto-calculate Monthly EMBO if basic salary, geographic coefficient, or relocation exist
                            cleaned_deductions = dict(emp['deductions']) if isinstance(emp['deductions'], dict) else {}
                            if isinstance(emp['deductions'], dict):
                                geographic_coefficient = edit_payments.get("Monthly Geographic Coefficient", 0)
                                # Also check for old spelling for backward compatibility
                                if geographic_coefficient == 0:
                                    geographic_coefficient = edit_payments.get("Monthly Geographic Coeffient", 0)
                                relocation = edit_payments.get("Monthly Relocation", 0)
                                
                                # Always recalculate EMBO based on current logic
                                if "Monthly EMBO" in cleaned_deductions:
                                    if geographic_coefficient > 0 and relocation > 0:
                                        embo_base = edit_monthly_basic_salary + geographic_coefficient + relocation
                                        embo_amount = embo_base * 13.0 / 100
                                        cleaned_deductions["Monthly EMBO"] = embo_amount
                                    else:
                                        # Set EMBO to 0 if BOTH geographic coefficient AND relocation don't have values
                                        cleaned_deductions["Monthly EMBO"] = 0.0
                            
                            # Handle both old list format and new dict format
                            if isinstance(emp['deductions'], dict):
                                for deduction_name, deduction_value in cleaned_deductions.items():
                                    # Skip ER Pension Contribution as it's handled in Additional Deduction section
                                    if deduction_name == "Monthly ER Pension Contribution":
                                        continue
                                        
                                    col_name, col_percentage, col_amount = st.columns([2, 1, 1.5])
                                    with col_name:
                                        # Display category name as read-only text
                                        st.markdown(f"**{deduction_name}**")
                                        new_deduction_name = deduction_name  # Use the existing name, don't allow editing
                                    with col_percentage:
                                        # Calculate existing percentage more intelligently based on deduction type
                                        if deduction_name == "Monthly EMBO":
                                            # For EMBO, calculate percentage based on (Basic + Geographic + Relocation)
                                            geographic_coefficient = edit_payments.get("Monthly Geographic Coefficient", 0)
                                            # Also check for old spelling for backward compatibility
                                            if geographic_coefficient == 0:
                                                geographic_coefficient = edit_payments.get("Monthly Geographic Coeffient", 0)
                                            relocation = edit_payments.get("Monthly Relocation", 0)
                                            base_amount = edit_basic_salary + geographic_coefficient + relocation
                                            existing_percentage = (deduction_value / base_amount * 100) if base_amount > 0 and deduction_value > 0 else 13.0
                                        elif deduction_name == "Monthly EE Pension Contribution":
                                            # For Pension, calculate percentage based on (Basic + STIP Bonus)
                                            stip_bonus = edit_payments.get("STIP Bonus", 0)
                                            base_amount = edit_basic_salary + stip_bonus
                                            existing_percentage = (deduction_value / base_amount * 100) if base_amount > 0 and deduction_value > 0 else 8.0
                                        else:
                                            # Standard percentage calculation for other deductions
                                            existing_percentage = (deduction_value / edit_basic_salary * 100) if edit_basic_salary > 0 and deduction_value > 0 else 0.0
                                        
                                        new_deduction_percentage = st.number_input(f"Percentage (%)", value=existing_percentage, min_value=0.0, max_value=100.0, step=0.5, key=f"edit_deduction_percentage_{emp['id']}_{deduction_index}")
                                    with col_amount:
                                        # Calculate amount based on formula and percentage (same as add employee form)
                                        if deduction_name == "Monthly EMBO":
                                            # For EMBO: percentage of (Basic + Geographic + Relocation)
                                            geographic_coefficient = edit_payments.get("Monthly Geographic Coefficient", 0)
                                            # Also check for old spelling for backward compatibility
                                            if geographic_coefficient == 0:
                                                geographic_coefficient = edit_payments.get("Monthly Geographic Coeffient", 0)
                                            relocation = edit_payments.get("Monthly Relocation", 0)
                                            base_amount = edit_basic_salary + geographic_coefficient + relocation
                                            calculated_amount = base_amount * new_deduction_percentage / 100
                                            st.markdown(f"**{edit_currency_symbol}{calculated_amount:,.2f}**")
                                            st.caption(f"= {new_deduction_percentage}% of ({edit_currency_symbol}{edit_basic_salary:,.2f} + {edit_currency_symbol}{geographic_coefficient:,.2f} + {edit_currency_symbol}{relocation:,.2f}) = {edit_currency_symbol}{base_amount:,.2f}")
                                        elif deduction_name == "Monthly EE Pension Contribution":
                                            # For Pension: percentage of (Basic + STIP Bonus)
                                            stip_bonus = edit_payments.get("STIP Bonus", 0)
                                            base_amount = edit_basic_salary + stip_bonus
                                            calculated_amount = base_amount * new_deduction_percentage / 100
                                            st.markdown(f"**{edit_currency_symbol}{calculated_amount:,.2f}**")
                                            st.caption(f"= {new_deduction_percentage}% of (Basic + STIP Bonus)")
                                        else:
                                            # Standard calculation for other deductions
                                            calculated_amount = (edit_basic_salary * new_deduction_percentage / 100) if edit_basic_salary > 0 else 0.0
                                            st.markdown(f"**{edit_currency_symbol}{calculated_amount:,.2f}**")
                                            st.caption(f"= {new_deduction_percentage}% of basic salary")
                                    
                                    if new_deduction_name.strip():
                                        # For EMBO, only add if both Geographic Coefficient and Relocation have values
                                        if new_deduction_name.strip() == "Monthly EMBO":
                                            geographic_coefficient = edit_payments.get("Monthly Geographic Coefficient", 0)
                                            # Also check for old spelling for backward compatibility
                                            if geographic_coefficient == 0:
                                                geographic_coefficient = edit_payments.get("Monthly Geographic Coeffient", 0)
                                            relocation = edit_payments.get("Monthly Relocation", 0)
                                            
                                            # Only add EMBO if both conditions are met (regardless of calculated amount)
                                            if geographic_coefficient > 0 and relocation > 0:
                                                edit_deductions[new_deduction_name.strip()] = calculated_amount
                                        else:
                                            edit_deductions[new_deduction_name.strip()] = calculated_amount
                                    deduction_index += 1
                            else:
                                # Convert old list format to dict format with percentage input
                                for deduction_name in emp['deductions']:
                                    col_name, col_percentage, col_amount = st.columns([2, 1, 1.5])
                                    with col_name:
                                        # Display category name as read-only text
                                        st.markdown(f"**{deduction_name}**")
                                        new_deduction_name = deduction_name  # Use the existing name, don't allow editing
                                    with col_percentage:
                                        new_deduction_percentage = st.number_input(f"Percentage (%)", value=0.0, min_value=0.0, max_value=100.0, step=0.5, key=f"edit_deduction_percentage_{emp['id']}_{deduction_index}")
                                    with col_amount:
                                        # Calculate amount based on formula and percentage (same as add employee form)
                                        if new_deduction_name == "Monthly EMBO":
                                            # For EMBO: percentage of (Basic + Geographic + Relocation)
                                            geographic_coefficient = edit_payments.get("Monthly Geographic Coefficient", 0)
                                            # Also check for old spelling for backward compatibility
                                            if geographic_coefficient == 0:
                                                geographic_coefficient = edit_payments.get("Monthly Geographic Coeffient", 0)
                                            relocation = edit_payments.get("Monthly Relocation", 0)
                                            base_amount = edit_basic_salary + geographic_coefficient + relocation
                                            calculated_amount = base_amount * new_deduction_percentage / 100
                                            st.markdown(f"**{edit_currency_symbol}{calculated_amount:,.2f}**")
                                            st.caption(f"= {new_deduction_percentage}% of ({edit_currency_symbol}{edit_basic_salary:,.2f} + {edit_currency_symbol}{geographic_coefficient:,.2f} + {edit_currency_symbol}{relocation:,.2f}) = {edit_currency_symbol}{base_amount:,.2f}")
                                        elif new_deduction_name == "Monthly EE Pension Contribution":
                                            # For Pension: percentage of (Basic + STIP Bonus)
                                            stip_bonus = edit_payments.get("STIP Bonus", 0)
                                            base_amount = edit_basic_salary + stip_bonus
                                            calculated_amount = base_amount * new_deduction_percentage / 100
                                            st.markdown(f"**{edit_currency_symbol}{calculated_amount:,.2f}**")
                                            st.caption(f"= {new_deduction_percentage}% of (Basic + STIP Bonus)")
                                        else:
                                            # Standard calculation for other deductions
                                            calculated_amount = (edit_basic_salary * new_deduction_percentage / 100) if edit_basic_salary > 0 else 0.0
                                            st.markdown(f"**{edit_currency_symbol}{calculated_amount:,.2f}**")
                                            st.caption(f"= {new_deduction_percentage}% of basic salary")
                                    
                                    if new_deduction_name.strip():
                                        # For EMBO, only add if both Geographic Coefficient and Relocation have values
                                        if new_deduction_name.strip() == "Monthly EMBO":
                                            geographic_coefficient = edit_payments.get("Monthly Geographic Coefficient", 0)
                                            # Also check for old spelling for backward compatibility
                                            if geographic_coefficient == 0:
                                                geographic_coefficient = edit_payments.get("Monthly Geographic Coeffient", 0)
                                            relocation = edit_payments.get("Monthly Relocation", 0)
                                            
                                            # Only add EMBO if both conditions are met (regardless of calculated amount)
                                            if geographic_coefficient > 0 and relocation > 0:
                                                edit_deductions[new_deduction_name.strip()] = calculated_amount
                                        else:
                                            edit_deductions[new_deduction_name.strip()] = calculated_amount
                                    deduction_index += 1
                            
                            # Add new deduction categories
                            if st.session_state[f"edit_new_deductions_{emp['id']}"]:
                                st.markdown("**New Deduction Categories:**")
                                for i, new_deduction in enumerate(st.session_state[f"edit_new_deductions_{emp['id']}"]):
                                    col_name, col_percentage, col_amount = st.columns([2, 1, 1.5])
                                    with col_name:
                                        new_deduction_name = st.text_input(f"New Category", key=f"new_deduction_name_{emp['id']}_{i}", 
                                                                         value=new_deduction["name"], placeholder="e.g., insurance")
                                    with col_percentage:
                                        new_deduction_percentage = st.number_input(f"Percentage (%)", key=f"new_deduction_percentage_{emp['id']}_{i}", 
                                                                                 value=float(new_deduction.get("percentage", 0.0)), min_value=0.0, max_value=100.0, step=0.5)
                                    with col_amount:
                                        # Calculate amount based on formula and percentage (same as add employee form)
                                        if new_deduction_name.strip() == "Monthly EMBO":
                                            # For EMBO: percentage of (Basic + Geographic + Relocation)
                                            geographic_coefficient = edit_payments.get("Monthly Geographic Coefficient", 0)
                                            # Also check for old spelling for backward compatibility
                                            if geographic_coefficient == 0:
                                                geographic_coefficient = edit_payments.get("Monthly Geographic Coeffient", 0)
                                            relocation = edit_payments.get("Monthly Relocation", 0)
                                            base_amount = edit_basic_salary + geographic_coefficient + relocation
                                            calculated_amount = base_amount * new_deduction_percentage / 100
                                            st.markdown(f"**{edit_currency_symbol}{calculated_amount:,.2f}**")
                                            st.caption(f"= {new_deduction_percentage}% of ({edit_currency_symbol}{edit_basic_salary:,.2f} + {edit_currency_symbol}{geographic_coefficient:,.2f} + {edit_currency_symbol}{relocation:,.2f}) = {edit_currency_symbol}{base_amount:,.2f}")
                                        elif new_deduction_name.strip() == "Monthly EE Pension Contribution":
                                            # For Pension: percentage of (Basic + STIP Bonus)
                                            stip_bonus = edit_payments.get("STIP Bonus", 0)
                                            base_amount = edit_basic_salary + stip_bonus
                                            calculated_amount = base_amount * new_deduction_percentage / 100
                                            st.markdown(f"**{edit_currency_symbol}{calculated_amount:,.2f}**")
                                            st.caption(f"= {new_deduction_percentage}% of (Basic + STIP Bonus)")
                                        else:
                                            # Standard calculation for other deductions
                                            calculated_amount = (edit_basic_salary * new_deduction_percentage / 100) if edit_basic_salary > 0 else 0.0
                                            st.markdown(f"**{edit_currency_symbol}{calculated_amount:,.2f}**")
                                            st.caption(f"= {new_deduction_percentage}% of basic salary")
                                    
                                    if new_deduction_name.strip() and edit_basic_salary > 0:
                                        # For EMBO, only add if both Geographic Coefficient and Relocation have values
                                        if new_deduction_name.strip() == "Monthly EMBO":
                                            geographic_coefficient = edit_payments.get("Monthly Geographic Coefficient", 0)
                                            # Also check for old spelling for backward compatibility
                                            if geographic_coefficient == 0:
                                                geographic_coefficient = edit_payments.get("Monthly Geographic Coeffient", 0)
                                            relocation = edit_payments.get("Monthly Relocation", 0)
                                            
                                            # Only add EMBO if both conditions are met (regardless of calculated amount)
                                            if geographic_coefficient > 0 and relocation > 0:
                                                edit_deductions[new_deduction_name.strip()] = calculated_amount
                                        else:
                                            edit_deductions[new_deduction_name.strip()] = calculated_amount
                            
                            st.markdown("### ➖ Additional Deduction")
                            
                            # Calculate Monthly ER Pension Contribution (editable percentage of basic_salary + stip_bonus)
                            if edit_monthly_basic_salary > 0:
                                edit_stip_bonus = edit_payments.get("STIP Bonus", 0)
                                edit_er_pension_base = edit_monthly_basic_salary + edit_stip_bonus
                                
                                col_er_name, col_er_percentage, col_er_amount = st.columns([3, 1.5, 2])
                                with col_er_name:
                                    st.markdown("**Monthly ER Pension Contribution**")
                                with col_er_percentage:
                                    edit_er_pension_percentage = st.number_input("Percentage (%)", value=6.5, min_value=0.0, max_value=100.0, step=0.5, key=f"edit_er_pension_percentage_{emp['id']}")
                                with col_er_amount:
                                    edit_er_pension_amount = edit_er_pension_base * edit_er_pension_percentage / 100
                                    st.markdown(f"**{edit_currency_symbol}{edit_er_pension_amount:,.2f}**")
                                    st.caption(f"= {edit_er_pension_percentage}% of (Basic + STIP Bonus)")
                                
                                # Add to edit_deductions
                                edit_deductions["Monthly ER Pension Contribution"] = edit_er_pension_amount
                                
                            else:
                                st.warning("⚠️ Please enter Monthly Basic Salary to calculate ER Pension Contribution.")
                                # Show in table format similar to deduction categories when basic salary is not available
                                col_er_name, col_er_percentage, col_er_amount = st.columns([3, 1.5, 2])
                                with col_er_name:
                                    st.markdown("**Monthly ER Pension Contribution**")
                                with col_er_percentage:
                                    edit_er_pension_percentage = st.number_input("Percentage (%)", value=6.5, min_value=0.0, max_value=100.0, step=0.5, key=f"edit_er_pension_percentage_empty_{emp['id']}")
                                with col_er_amount:
                                    st.markdown(f"**{edit_currency_symbol}0.00**")
                                    st.caption(f"= {edit_er_pension_percentage}% of (Basic + STIP Bonus)")
                                
                            
                            st.markdown("### 💰 Additional Daily Payments")
                            
                            # Handle existing additional daily payments
                            edit_additional_payments = {}
                            additional_index = 0
                            
                            if emp.get('additional_daily_payments') and isinstance(emp['additional_daily_payments'], dict):
                                for payment_name, payment_value in emp['additional_daily_payments'].items():
                                    col_name, col_value = st.columns([2, 1])
                                    with col_name:
                                        # Display category name as read-only text
                                        st.markdown(f"**{payment_name}**")
                                        new_payment_name = payment_name  # Use the existing name, don't allow editing
                                    with col_value:
                                        new_payment_value = st.number_input(f"Daily Rate ({edit_currency_symbol})", value=float(payment_value), min_value=0.0, step=1.0, key=f"edit_additional_value_{emp['id']}_{additional_index}")
                                    
                                    if new_payment_name.strip():
                                        edit_additional_payments[new_payment_name.strip()] = new_payment_value
                                    additional_index += 1
                            
                            # Add new additional daily payment categories
                            if st.session_state[f"edit_new_daily_payments_{emp['id']}"]:
                                st.markdown("**New Additional Daily Payment Categories:**")
                                for i, new_payment in enumerate(st.session_state[f"edit_new_daily_payments_{emp['id']}"]):
                                    col_name, col_value = st.columns([2, 1])
                                    with col_name:
                                        new_payment_name = st.text_input(f"New Category", key=f"new_additional_name_{emp['id']}_{i}", 
                                                                       value=new_payment["name"], placeholder="e.g., Field Bonus")
                                    with col_value:
                                        new_payment_value = st.number_input(f"Daily Rate ({edit_currency_symbol})", key=f"new_additional_value_{emp['id']}_{i}", 
                                                                          value=float(new_payment["value"]), min_value=0.0, step=1.0)
                                    
                                    if new_payment_name.strip():
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
                                edit_currency, edit_monthly_basic_salary, edit_payments, edit_deductions, edit_additional_payments
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
