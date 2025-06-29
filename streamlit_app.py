import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
from fpdf import FPDF

# --- Global Configuration ---
CUSTOMERS_FILE = "customers.xlsx"
PAYMENTS_FILE = "debt_payments.xlsx"
TH_FONT_PATH = "THSarabunNew.ttf" # ตรวจสอบให้แน่ใจว่ามีไฟล์ฟอนต์นี้อยู่ในโฟลเดอร์เดียวกับสคริปต์
# TH_FONT_BOLD_PATH = "THSarabunNew Bold.ttf" # uncomment and use if you have a separate bold font file

# --- Helper Function to Determine Fiscal Year ---
def get_fiscal_year_string(input_date):
    """
    Determines the Thai fiscal year (Apr 5 - Mar 5) string (e.g., "2025-2026") for a given date.
    """
    fiscal_year_start_candidate = input_date.year
    
    # If the date is before April 5th, it belongs to the previous fiscal year
    if input_date.month < 4 or (input_date.month == 4 and input_date.day < 5):
        fiscal_year_start = fiscal_year_start_candidate - 1
    else:
        fiscal_year_start = fiscal_year_start_candidate
        
    fiscal_year_end_period = fiscal_year_start + 1
    return f"{fiscal_year_start}-{fiscal_year_end_period}"

# --- Function to Load Data ---
@st.cache_data(ttl=3600)
def load_data():
    """Loads customer and payment data from Excel files."""
    try:
        customers_df = pd.read_excel(CUSTOMERS_FILE)
        # Ensure 'ลำดับที่' column exists and is of integer type
        if 'ลำดับที่' not in customers_df.columns:
            customers_df['ลำดับที่'] = range(1, len(customers_df) + 1)
        # Convert to numeric first, then fill NaNs and convert to int
        customers_df['ลำดับที่'] = pd.to_numeric(customers_df['ลำดับที่'], errors='coerce').fillna(0).astype(int)
        
        # Re-index 'ลำดับที่' to be sequential (1 to N) and sort by it
        customers_df = customers_df.sort_values(by='ลำดับที่', ascending=True).reset_index(drop=True)
        customers_df['ลำดับที่'] = range(1, len(customers_df) + 1)

    except FileNotFoundError:
        st.error(f"ไม่พบไฟล์ '{CUSTOMERS_FILE}' กรุณาตรวจสอบว่ามีไฟล์นี้อยู่ในโฟลเดอร์เดียวกับโปรแกรม")
        # Create an empty DataFrame if file is not found, with 'ลำดับที่' column
        customers_df = pd.DataFrame(columns=["ลำดับที่", "NAME", "AmountDue"])

    customer_amounts = dict(zip(customers_df["NAME"], customers_df["AmountDue"]))

    if os.path.exists(PAYMENTS_FILE):
        payments_df = pd.read_excel(PAYMENTS_FILE)
    else:
        # Create an empty DataFrame with necessary columns if file doesn't exist
        payments_df = pd.DataFrame(columns=["ชื่อลูกค้า", "วันที่จ่าย", "จำนวนเงิน", "หมายเหตุ"])

    # Ensure 'วันที่จ่าย_dt' column exists and is of datetime.date type
    if "วันที่จ่าย" in payments_df.columns and not payments_df["วันที่จ่าย"].empty:
        payments_df['วันที่จ่าย_dt'] = pd.to_datetime(payments_df['วันที่จ่าย'], errors='coerce').dt.date
    else:
        payments_df['วันที่จ่าย_dt'] = pd.Series(dtype='object')

    return customers_df, payments_df, customer_amounts

# --- Function to Save Customers DataFrame ---
def save_customers_df(df):
    """Saves the customers DataFrame to Excel, ensuring 'ลำดับที่' is sequential."""
    if not df.empty:
        df['ลำดับที่'] = range(1, len(df) + 1) # Re-index for sequential numbering
    df.to_excel(CUSTOMERS_FILE, index=False)

# --- Function to Save Payments DataFrame ---
def save_payments_df(df):
    """Saves the payments DataFrame to Excel."""
    # Remove 'วันที่จ่าย_dt' column before saving to Excel if it exists
    if 'วันที่จ่าย_dt' in df.columns:
        df = df.drop(columns=['วันที่จ่าย_dt'])
    df.to_excel(PAYMENTS_FILE, index=False)

# --- Function to Generate PDF Receipt ---
def generate_pdf_receipt(customer_name, payment_date, amount_paid, note, total_due, total_paid_all_time, total_remaining, yearly_summary_for_pdf):
    """Creates a PDF receipt with detailed information and a structured layout."""
    receipt_name = f"ใบเสร็จ_{customer_name}_{payment_date.strftime('%Y%m%d')}.pdf"
    pdf = FPDF("P", "mm", "A4")
    pdf.add_page()
    
    try:
        pdf.add_font('THSarabunNew', '', TH_FONT_PATH, uni=True)
        pdf.add_font('THSarabunNew', 'B', TH_FONT_PATH, uni=True) # Use same file for Bold if no separate bold font
        pdf.set_font('THSarabunNew', '', 12)
    except RuntimeError as e:
        st.warning(f"ไม่พบฟอนต์ภาษาไทย! PDF อาจแสดงผลไม่ถูกต้อง: {e}")
        pdf.set_font('Arial', '', 12)

    # --- Header ---
    pdf.set_font('THSarabunNew', 'B', 30) # Larger font for main header
    pdf.cell(0, 20, "ใบเสร็จรับเงิน", ln=True, align='L')
    pdf.ln(3)

    # --- Customer and Date Info ---
    pdf.set_font('THSarabunNew', '', 14)
    pdf.cell(0, 8, f"วันที่: {payment_date.strftime('%d %B %Y')}", ln=1, align='L')
    pdf.ln(2)
    pdf.cell(0, 8, f"เรียน: {customer_name}", ln=1)
    pdf.cell(0, 8, f"ได้ชำระเงินตามสัญญาดังนี้", ln=1)
    pdf.ln(5)

    # --- Payment Details Table ---
    col_widths = [140, 50] # Description, Amount
    pdf.set_font('THSarabunNew', 'B', 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(col_widths[0], 10, "รายการ", 1, 0, 'L', 1)
    pdf.cell(col_widths[1], 10,"บาท", 1, 1, 'R',1)

    pdf.set_font('THSarabunNew', '', 14)
    pdf.cell(col_widths[0], 10, "ชำระหนี้ตามสัญญา", 1, 0, 'L')
    pdf.cell(col_widths[1], 10, f"{amount_paid:,.2f}", 1, 1, 'R')
    
    pdf.ln(10)

    # --- Yearly Payment Status and Penalty for the relevant fiscal year ---
    # Determine the fiscal year string for the current payment date
    payment_fiscal_year_string = get_fiscal_year_string(payment_date)
    
    payment_fiscal_year_info = None
    for year_data in yearly_summary_for_pdf:
        if year_data['ปีงบประมาณ'] == payment_fiscal_year_string:
            payment_fiscal_year_info = year_data
            break

    pdf.set_font('THSarabunNew', 'B', 16)
    pdf.cell(0, 10, "สรุปสถานะการชำระสำหรับปีงบประมาณที่เกี่ยวข้อง", ln=1)
    pdf.set_font('THSarabunNew', '', 14)
    
    summary_cols_width_label = 90
    summary_cols_width_value = 50
    summary_cols_width_unit = 20

    if payment_fiscal_year_info:
        pdf.cell(summary_cols_width_label, 8, "ปีงบประมาณ:", 0, 0, 'L')
        pdf.cell(summary_cols_width_value + summary_cols_width_unit, 8, payment_fiscal_year_info['ปีงบประมาณ'], 0, 0, 'C')

        pdf.ln(7)

        pdf.cell(summary_cols_width_label, 8, "ยอดที่ต้องจ่ายในปีนี้:", 0, 0, 'L')
        pdf.cell(summary_cols_width_value, 8, f"{payment_fiscal_year_info['ยอดที่ต้องจ่าย']:,.2f}", 0, 0, 'R')
        pdf.cell(summary_cols_width_unit, 8, "บาท", 0, 1, 'L')


        pdf.cell(summary_cols_width_label, 8, "ยอดที่จ่ายแล้วในปีนี้:", 0, 0, 'L')
        pdf.cell(summary_cols_width_value, 8, f"{payment_fiscal_year_info['ยอดที่จ่ายแล้ว']:,.2f}", 0, 0, 'R')
        pdf.cell(summary_cols_width_unit, 8, "บาท", 0, 1, 'L')

        pdf.cell(summary_cols_width_label, 8, "ยอดคงเหลือในปีนี้:", 0, 0, 'L')
        pdf.cell(summary_cols_width_value, 8, f"{payment_fiscal_year_info['ยอดคงเหลือ']:,.2f}", 0, 0, 'R')
        pdf.cell(summary_cols_width_unit, 8, "บาท", 0, 1, 'L')

        pdf.cell(summary_cols_width_label, 8, "สถานะค่าปรับสำหรับปีนี้:", 0, 0, 'L')
        pdf.cell(summary_cols_width_value + summary_cols_width_unit, 8, payment_fiscal_year_info['สถานะค่าปรับ'], 0, 1, 'R')
    else:
        pdf.cell(0, 8, "ไม่พบข้อมูลปีงบประมาณที่เกี่ยวข้องสำหรับวันที่ชำระนี้", ln=1)

    pdf.ln(10)

    # --- Overall Debt Summary ---
    pdf.set_font('THSarabunNew', 'B', 16)
    pdf.cell(0, 10, "สรุปยอดหนี้คงเหลือทั้งหมด", ln=1)
    pdf.set_font('THSarabunNew', '', 14)
    
    pdf.cell(summary_cols_width_label, 8, "ยอดหนี้ทั้งหมดตามสัญญา:", 0, 0, 'L')
    pdf.cell(summary_cols_width_value, 8, f"{total_due:,.2f}", 0, 0, 'R')
    pdf.cell(summary_cols_width_unit, 8, "บาท", 0, 1, 'L')

    pdf.cell(summary_cols_width_label, 8, "ยอดชำระสะสมทั้งหมด:", 0, 0, 'L')
    pdf.cell(summary_cols_width_value, 8, f"{total_paid_all_time:,.2f}", 0, 0, 'R')
    pdf.cell(summary_cols_width_unit, 8, "บาท", 0, 1, 'L')

    pdf.cell(summary_cols_width_label, 8, "ยอดหนี้คงเหลือปัจจุบัน:", 0, 0, 'L')
    pdf.cell(summary_cols_width_value, 8, f"{total_remaining:,.2f}", 0, 0, 'R')
    pdf.cell(summary_cols_width_unit, 8, "บาท", 0, 1, 'L')

    pdf.ln(20)

    # --- Signatures ---
    pdf.set_font('THSarabunNew', '', 14)
    pdf.cell(95, 10, "ผู้รับเงิน.........................................", 0, 0, 'L')
    pdf.ln(30)
    pdf.cell(95, 10, "ผู้ชำระเงิน.......................................", 0, 0, 'L')
    

    return receipt_name, pdf.output(dest='S').encode('latin-1')

# --- Function to Display Customer Summary (หน้าตาสวยงามขึ้น) ---
def display_customer_summary(customer_name, customer_amounts, payments_df):
    """Calculates and displays the summary for the selected customer, including penalties."""
    st.markdown("<br><hr>", unsafe_allow_html=True) # Separator with more space
    st.markdown(f"<h3 style='text-align: center;'>📊 สรุปข้อมูลหนี้ของ <span style='color:#007bff;'>{customer_name}</span></h3>", unsafe_allow_html=True)
    
    total_due = customer_amounts.get(customer_name, 0)
    required_yearly = total_due / 4 if total_due > 0 else 0

    total_paid_all_time = payments_df[payments_df["ชื่อลูกค้า"] == customer_name]["จำนวนเงิน"].sum()
    total_remaining = total_due - total_paid_all_time

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**ยอดหนี้ทั้งหมด**\n\n### {total_due:,.2f} บาท")
    with col2:
        st.success(f"**ยอดชำระสะสม**\n\n### {total_paid_all_time:,.2f} บาท")
    with col3:
        st.warning(f"**ยอดหนี้คงเหลือรวม**\n\n### {total_remaining:,.2f} บาท")

    st.markdown("<br><hr>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center;'>🗓️ สรุปยอดชำระตามปีงบประมาณและค่าปรับ</h4>", unsafe_allow_html=True)

    summary_data = [] 
    penalties_incurred_display = [] 

    start_contract_fiscal_year = 2025 
    today = datetime.today().date()
    
    for i in range(4):
        fiscal_start_year = start_contract_fiscal_year + i
        fiscal_end_year_for_period = fiscal_start_year + 1 
        
        start_date_fiscal = date(fiscal_start_year, 4, 5) 
        end_date_fiscal = date(fiscal_end_year_for_period, 3, 5)     

        penalty_check_date = date(fiscal_end_year_for_period, 3, 3) 
        
        # Filter DataFrame for the current fiscal year
        # Ensure 'วันที่จ่าย_dt' is used and handle potential NaT values during filtering
        df_year = payments_df[
            (payments_df["ชื่อลูกค้า"] == customer_name) &
            (payments_df["วันที่จ่าย_dt"].apply(lambda x: x is not pd.NaT and x >= start_date_fiscal)) & # Check for NaT before comparison
            (payments_df["วันที่จ่าย_dt"].apply(lambda x: x is not pd.NaT and x <= end_date_fiscal))
        ]
        paid_this_fiscal_year = df_year["จำนวนเงิน"].sum()
        
        remaining_this_fiscal_year = max(0, required_yearly - paid_this_fiscal_year)

        penalty_status_text = "ไม่มี"
        penalty_amount = 0

        if remaining_this_fiscal_year > 0:
            if today > penalty_check_date: 
                penalty_amount = remaining_this_fiscal_year * 0.15
                penalty_status_text = f"{penalty_amount:,.2f} บาท" # แสดงตัวเลขตรงๆ
                penalties_incurred_display.append({
                    "ปีงบประมาณ": f"{fiscal_start_year}-{fiscal_end_year_for_period}",
                    "ยอดค้างชำระ": f"{remaining_this_fiscal_year:,.2f}",
                    "ค่าปรับ (15%)": f"{penalty_amount:,.2f}"
                })
            else: 
                penalty_status_text = "ยังไม่ถึงกำหนดคิดค่าปรับ"

        summary_data.append({
            "ปีงบประมาณ": f"{fiscal_start_year}-{fiscal_end_year_for_period}",
            "ยอดที่ต้องจ่าย": required_yearly,
            "ยอดที่จ่ายแล้ว": paid_this_fiscal_year,
            "ยอดคงเหลือ": remaining_this_fiscal_year,
            "สถานะค่าปรับ": penalty_status_text
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    # Custom styling for dataframe
    def color_status(val):
        if 'ยังไม่ถึงกำหนด' in str(val):
            return 'background-color: yellow'
        elif 'บาท' in str(val) and float(val.replace(' บาท', '').replace(',', '')) > 0:
            return 'background-color: #ffcccc' # Light red for penalties
        return ''

    st.dataframe(
        summary_df.style.format({
            "ยอดที่ต้องจ่าย": "{:,.2f}",
            "ยอดที่จ่ายแล้ว": "{:,.2f}",
            "ยอดคงเหลือ": "{:,.2f}"
        }).applymap(color_status, subset=['สถานะค่าปรับ']), # Apply color to status column
        use_container_width=True
    )

    if penalties_incurred_display:
        st.error("🚨 **รายการค่าปรับที่เกิดขึ้นแล้ว**")
        penalties_df = pd.DataFrame(penalties_incurred_display)
        st.dataframe(penalties_df, use_container_width=True)
    else:
        current_fiscal_start_year = today.year if today.month >= 4 else today.year - 1
        current_fiscal_end_year_for_period = current_fiscal_start_year + 1
        current_fiscal_penalty_check_date = date(current_fiscal_end_year_for_period, 3, 3)
        
        # Ensure 'วันที่จ่าย_dt' is used and handle potential NaT values during filtering
        current_year_payments = payments_df[
            (payments_df["ชื่อลูกค้า"] == customer_name) &
            (payments_df["วันที่จ่าย_dt"].apply(lambda x: x is not pd.NaT and x >= date(current_fiscal_start_year, 4, 5))) &
            (payments_df["วันที่จ่าย_dt"].apply(lambda x: x is not pd.NaT and x <= date(current_fiscal_end_year_for_period, 3, 5)))
        ]["จำนวนเงิน"].sum()
        
        current_year_remaining = max(0, required_yearly - current_year_payments)

        if current_year_remaining > 0 and today <= current_fiscal_penalty_check_date:
            st.info(f"ℹ️ ปีงบประมาณปัจจุบัน ({current_fiscal_start_year}-{current_fiscal_end_year_for_period}) มียอดค้างชำระ {current_year_remaining:,.2f} บาท แต่ยังไม่ถึงกำหนดคิดค่าปรับ (หลังวันที่ 3 มีนาคม {current_fiscal_end_year_for_period})")
        else:
            st.success("✅ ไม่มีค่าปรับเกิดขึ้นในงวดปีงบประมาณที่ผ่านมา และไม่มีค้างชำระในงวดปัจจุบันที่ต้องแจ้งเตือน")
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    return summary_data # Return summary_data for PDF creation

# --- Main App Logic ---
def main():
    st.set_page_config(page_title="ระบบจัดการลูกหนี้", layout="wide")

    # Initialize session state for selected customer if not exists
    if 'selected_customer_add' not in st.session_state:
        st.session_state.selected_customer_add = None
    if 'selected_customer_edit' not in st.session_state:
        st.session_state.selected_customer_edit = None
    if 'pdf_download_info' not in st.session_state:
        st.session_state.pdf_download_info = None

    # Load data for initial display and operations
    customers_df, payments_df, customer_amounts = load_data()

    st.title("🏡 ระบบจัดการข้อมูลลูกหนี้ (สัญญา 4 ปี)")
    st.markdown("##### จัดการบันทึกการชำระหนี้ สร้างใบเสร็จ และดูสรุปสถานะหนี้")

    menu = st.sidebar.radio("เมนูหลัก", ["📄 กรอกข้อมูลการชำระ", "✏️ แก้ไขข้อมูลย้อนหลัง", "👤 จัดการลูกค้า"])

    # Always get the latest customer names from the loaded DataFrame
    customer_names = customers_df["NAME"].tolist()

    # --- Page 1: Add New Payment ---
    if menu == "📄 กรอกข้อมูลการชำระ":
        st.header("บันทึกข้อมูลการชำระเงินใหม่")
        
        if not customer_names:
            st.warning("ไม่พบข้อมูลลูกค้า กรุณาเพิ่มลูกค้าในหน้า 'จัดการลูกค้า' ก่อน")
            return

        # Determine initial selection
        if st.session_state.selected_customer_add is None or st.session_state.selected_customer_add not in customer_names:
            st.session_state.selected_customer_add = customer_names[0] if customer_names else None # Handle empty list
        
        # Use on_change callback to update session state and clear PDF info
        selected_customer = st.selectbox(
            "เลือกชื่อลูกค้า", 
            options=customer_names, 
            key="customer_select_form",
            index=customer_names.index(st.session_state.selected_customer_add) if st.session_state.selected_customer_add in customer_names else 0,
            on_change=lambda: st.session_state.update(selected_customer_add=st.session_state.customer_select_form, pdf_download_info=None) 
        )

        # Only show form if a customer is selected
        if selected_customer:
            with st.form("payment_form", clear_on_submit=True):
                payment_date = st.date_input("วันที่ชำระ", value=datetime.today())
                amount_paid = st.number_input("จำนวนเงินที่จ่าย (บาท)", min_value=0.0, step=100.0)
                note = st.text_input("หมายเหตุ (ถ้ามี)", "")
                submit_btn = st.form_submit_button("💾 บันทึกข้อมูลและสร้างใบเสร็จ")

            if submit_btn:
                st.cache_data.clear() # Clear cache to ensure fresh data for next load
                customers_df_latest, payments_df_latest, customer_amounts_latest = load_data()

                new_row = pd.DataFrame([{
                    "ชื่อลูกค้า": selected_customer,
                    "วันที่จ่าย": payment_date.strftime("%Y-%m-%d"), # Store as YEAR-MM-DD string
                    "จำนวนเงิน": amount_paid,
                    "หมายเหตุ": note
                }])
                
                # Use pd.concat for adding new rows
                payments_df_latest = pd.concat([payments_df_latest, new_row], ignore_index=True)
                
                save_payments_df(payments_df_latest) # Use the new save function for payments
                st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว!")

                # Load data again immediately after saving to ensure we get the absolute latest state,
                # including the newly saved payment in the summary calculations for PDF.
                st.cache_data.clear() 
                customers_df_after_save, payments_df_after_save, customer_amounts_after_save = load_data()

                # Prepare data for PDF based on the NEWLY SAVED data
                total_paid_after_save = payments_df_after_save[payments_df_after_save["ชื่อลูกค้า"] == selected_customer]["จำนวนเงิน"].sum()
                total_due_for_pdf = customer_amounts_after_save.get(selected_customer, 0)
                total_remaining_for_pdf = total_due_for_pdf - total_paid_after_save
                
                # Recalculate yearly summary based on latest data for PDF
                yearly_summary_for_pdf_temp = display_customer_summary(
                    selected_customer, 
                    customer_amounts_after_save, 
                    payments_df_after_save # Pass the payments_df that includes the new entry
                )
                
                receipt_name, pdf_bytes = generate_pdf_receipt(
                    selected_customer, 
                    payment_date, 
                    amount_paid, 
                    note, 
                    total_due_for_pdf, 
                    total_paid_after_save, 
                    total_remaining_for_pdf,
                    yearly_summary_for_pdf_temp # Pass the freshly calculated yearly summary
                )
                # Store PDF info in session state to display download button after rerun
                st.session_state.pdf_download_info = {
                    'file_name': receipt_name, 
                    'data': pdf_bytes, 
                    'mime': "application/pdf"
                }
                st.rerun() # Force rerun to refresh all displays and show download button

            # Always display download button if info is in session state (after a successful save and rerun)
            if st.session_state.pdf_download_info:
                st.download_button(
                    "📥 ดาวน์โหลดใบเสร็จ (PDF)", 
                    st.session_state.pdf_download_info['data'], 
                    file_name=st.session_state.pdf_download_info['file_name'], 
                    mime=st.session_state.pdf_download_info['mime']
                )
                # Clear download info after displaying the button once
                st.session_state.pdf_download_info = None

            # Display summary for the currently selected customer at the bottom
            # This will always use the latest data because of the on_change callback or initial load
            st.cache_data.clear() # Ensure the latest data is loaded for summary display
            customers_df_current, payments_df_current, customer_amounts_current = load_data()
            if selected_customer and selected_customer in customers_df_current["NAME"].tolist(): # Only display if a customer is selected and still exists
                display_customer_summary(selected_customer, customer_amounts_current, payments_df_current)


    # --- Page 2: Edit Past Data ---
    elif menu == "✏️ แก้ไขข้อมูลย้อนหลัง":
        st.header("แก้ไขข้อมูลการชำระย้อนหลัง")
        
        if not customer_names:
            st.warning("ไม่พบข้อมูลลูกค้า กรุณาเพิ่มลูกค้าในหน้า 'จัดการลูกค้า' ก่อน")
            return

        # Determine initial selection
        if st.session_state.selected_customer_edit is None or st.session_state.selected_customer_edit not in customer_names:
            st.session_state.selected_customer_edit = customer_names[0] if customer_names else None # Handle empty list

        customer_name_to_edit = st.selectbox(
            "เลือกชื่อลูกค้า", 
            options=customer_names, 
            key="edit_customer_select",
            index=customer_names.index(st.session_state.selected_customer_edit) if st.session_state.selected_customer_edit in customer_names else 0,
            on_change=lambda: st.session_state.update(selected_customer_edit=st.session_state.edit_customer_select) # Update session state on change
        )
        
        # Load fresh data for displaying summary and for the edit form
        st.cache_data.clear() 
        customers_df_latest_for_edit, payments_df_latest_for_edit, customer_amounts_latest_for_edit = load_data()

        # Filtering data for the selected customer to display in the selectbox for editing
        edit_df = payments_df_latest_for_edit[payments_df_latest_for_edit["ชื่อลูกค้า"] == customer_name_to_edit].copy()

        if not edit_df.empty:
            # Create a temporary 'label' for the selectbox, which includes the original DataFrame index (row.name)
            edit_df["label"] = edit_df.apply(
                lambda row: f"ID {row.name}: {row['วันที่จ่าย']} - {row['จำนวนเงิน']:,.2f} บาท", axis=1
            )
            
            record_to_edit_label = st.selectbox("เลือกรายการที่ต้องการแก้ไข", options=edit_df["label"].tolist(), key="record_to_edit_select")
            
            if record_to_edit_label:
                # Retrieve the original DataFrame index from the label
                selected_index_from_label = int(record_to_edit_label.split(":")[0].replace("ID ", ""))
                
                # Check if the index still exists in the original payments_df_latest_for_edit
                if selected_index_from_label in payments_df_latest_for_edit.index:
                    with st.form("edit_form"):
                        st.info(f"กำลังแก้ไขรายการ ID: **{selected_index_from_label}**")
                        
                        original_date_str = payments_df_latest_for_edit.at[selected_index_from_label, "วันที่จ่าย"]
                        # Ensure original_date is a valid date before passing to st.date_input
                        try:
                            original_date = datetime.strptime(original_date_str, "%Y-%m-%d").date()
                        except (ValueError, TypeError):
                            original_date = datetime.today().date() # Default to today if invalid

                        new_date = st.date_input("แก้ไขวันที่จ่าย", value=original_date)
                        new_amount = st.number_input("แก้ไขจำนวนเงิน (บาท)", value=float(payments_df_latest_for_edit.at[selected_index_from_label, "จำนวนเงิน"]))
                        new_note = st.text_input("แก้ไขหมายเหตุ", value=str(payments_df_latest_for_edit.at[selected_index_from_label, "หมายเหตุ"]))
                        
                        update_btn = st.form_submit_button("💾 บันทึกการแก้ไข")
                    
                    if update_btn:
                        st.cache_data.clear() # Clear cache before modifying
                        # Load data again to ensure we modify the most current state of the DataFrame
                        customers_df_to_modify, payments_df_to_modify, customer_amounts_to_modify = load_data()

                        payments_df_to_modify.at[selected_index_from_label, "วันที่จ่าย"] = new_date.strftime("%Y-%m-%d")
                        payments_df_to_modify.at[selected_index_from_label, "จำนวนเงิน"] = new_amount
                        payments_df_to_modify.at[selected_index_from_label, "หมายเหตุ"] = new_note
                        
                        save_payments_df(payments_df_to_modify) # Use the new save function for payments
                        st.success(f"✅ แก้ไขข้อมูล ID **{selected_index_from_label}** เรียบร้อยแล้ว!")
                        st.rerun() # Force rerun to refresh all displays
                else:
                    st.warning("รายการที่เลือกเพื่อแก้ไขไม่ถูกต้อง หรือถูกลบไปแล้ว กรุณาเลือกรายการใหม่")
        else:
            st.info("ℹ️ ลูกค้าที่เลือกยังไม่มีข้อมูลการชำระในระบบ")
        
        # Display summary for the currently selected customer at the bottom
        # It's important to pass the latest data loaded (payments_df_latest_for_edit)
        if customer_name_to_edit and customer_name_to_edit in customers_df_latest_for_edit["NAME"].tolist():
            display_customer_summary(customer_name_to_edit, customer_amounts_latest_for_edit, payments_df_latest_for_edit)

    # --- Page 3: Manage Customers (New Functionality) ---
    elif menu == "👤 จัดการลูกค้า":
        st.header("จัดการรายชื่อและยอดหนี้ลูกค้า")

        # Load the latest customer data
        st.cache_data.clear() # Clear cache to ensure we get the absolute latest customer data
        customers_df_manage, payments_df_manage, customer_amounts_manage = load_data()

        st.subheader("เพิ่มลูกค้าใหม่")
        with st.form("add_customer_form", clear_on_submit=True):
            new_customer_name = st.text_input("ชื่อลูกค้าใหม่")
            new_customer_total_due = st.number_input("ยอดหนี้ทั้งหมด (บาท)", min_value=0.0, step=1000.0)
            add_customer_btn = st.form_submit_button("➕ เพิ่มลูกค้า")

            if add_customer_btn:
                if new_customer_name and new_customer_total_due > 0:
                    if new_customer_name in customers_df_manage["NAME"].tolist():
                        st.warning(f"⚠️ ลูกค้าชื่อ '{new_customer_name}' มีอยู่ในระบบแล้ว")
                    else:
                        # Calculate next_id based on current max 'ลำดับที่'
                        next_id = 1
                        if not customers_df_manage.empty and 'ลำดับที่' in customers_df_manage.columns:
                            next_id = customers_df_manage['ลำดับที่'].max() + 1
                        
                        new_customer_row = pd.DataFrame([{
                            "ลำดับที่": next_id, # Add the new 'ลำดับที่'
                            "NAME": new_customer_name,
                            "AmountDue": new_customer_total_due
                        }])
                        customers_df_manage = pd.concat([customers_df_manage, new_customer_row], ignore_index=True)
                        save_customers_df(customers_df_manage) # Use the new save function
                        st.success(f"✅ เพิ่มลูกค้า '{new_customer_name}' ยอดหนี้ {new_customer_total_due:,.2f} บาท เรียบร้อยแล้ว!")
                        st.cache_data.clear() # Clear cache to reload customers data
                        st.rerun() # Rerun to update selectboxes
                else:
                    st.warning("กรุณากรอกชื่อลูกค้าและยอดหนี้ทั้งหมดให้ถูกต้อง")

        st.markdown("---")
        st.subheader("แก้ไขยอดหนี้ลูกค้าเก่า")
        
        customer_names_for_edit = customers_df_manage["NAME"].tolist() # Get current names
        if customer_names_for_edit:
            customer_to_edit_debt = st.selectbox(
                "เลือกชื่อลูกค้าที่ต้องการแก้ไขยอดหนี้", 
                options=customer_names_for_edit, 
                key="edit_customer_debt_select"
            )

            if customer_to_edit_debt:
                current_amount_due = customers_df_manage[customers_df_manage["NAME"] == customer_to_edit_debt]["AmountDue"].iloc[0]
                
                with st.form("edit_debt_form"):
                    updated_amount_due = st.number_input(
                        f"แก้ไขยอดหนี้ทั้งหมดของ '{customer_to_edit_debt}' (บาท)", 
                        value=float(current_amount_due), 
                        min_value=0.0, 
                        step=1000.0
                    )
                    update_debt_btn = st.form_submit_button("✏️ บันทึกการแก้ไขยอดหนี้")

                    if update_debt_btn:
                        st.cache_data.clear() # Clear cache before modifying
                        customers_df_to_modify, _, _ = load_data() # Load fresh customer data

                        # Find the index of the customer to update
                        idx_to_update = customers_df_to_modify[customers_df_to_modify["NAME"] == customer_to_edit_debt].index[0]
                        customers_df_to_modify.at[idx_to_update, "AmountDue"] = updated_amount_due
                        
                        save_customers_df(customers_df_to_modify) # Use the new save function
                        st.success(f"✅ แก้ไขยอดหนี้ของ '{customer_to_edit_debt}' เป็น {updated_amount_due:,.2f} บาท เรียบร้อยแล้ว!")
                        st.cache_data.clear() # Clear cache again after saving
                        st.rerun() # Rerun to reflect changes
        else:
            st.info("ℹ️ ยังไม่มีลูกค้าในระบบ")
        
        st.markdown("---")
        st.subheader("ลบข้อมูลลูกหนี้")

        customer_names_for_delete = customers_df_manage["NAME"].tolist() # Get current names for delete selectbox
        if customer_names_for_delete:
            customer_to_delete = st.selectbox(
                "เลือกชื่อลูกค้าที่ต้องการลบ",
                options=customer_names_for_delete,
                key="delete_customer_select"
            )

            if customer_to_delete:
                st.warning(f"คุณแน่ใจหรือไม่ว่าต้องการลบลูกค้า '{customer_to_delete}'? การกระทำนี้ไม่สามารถย้อนกลับได้!")
                
                delete_payments_too = st.checkbox(
                    f"ลบข้อมูลการชำระเงินทั้งหมดของ '{customer_to_delete}' ด้วย (ถาวร)",
                    key="delete_payments_checkbox"
                )

                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("ยืนยันการลบ", key="confirm_delete_btn", type="secondary"):
                        st.cache_data.clear() # Clear ALL cached data for a fresh start
                        customers_df_to_delete, payments_df_to_delete, _ = load_data() # Load current state

                        # Remove the customer from customers_df
                        customers_df_to_delete = customers_df_to_delete[customers_df_to_delete["NAME"] != customer_to_delete]
                        save_customers_df(customers_df_to_delete)
                        
                        # If checkbox is ticked, also remove payments
                        if delete_payments_too:
                            payments_df_to_delete = payments_df_to_delete[payments_df_to_delete["ชื่อลูกค้า"] != customer_to_delete]
                            save_payments_df(payments_df_to_delete)
                            st.success(f"✅ ลบลูกค้า '{customer_to_delete}' และข้อมูลการชำระเงินทั้งหมดเรียบร้อยแล้ว!")
                        else:
                            st.success(f"✅ ลบลูกค้า '{customer_to_delete}' จากรายชื่อเรียบร้อยแล้ว (ข้อมูลการชำระเงินยังคงอยู่).")
                        
                        # Explicitly update session state if the deleted customer was selected
                        if st.session_state.selected_customer_add == customer_to_delete:
                            st.session_state.selected_customer_add = None
                        if st.session_state.selected_customer_edit == customer_to_delete:
                            st.session_state.selected_customer_edit = None
                            
                        st.cache_data.clear() # Clear cache again after saving to force reload everywhere
                        st.rerun() # Rerun the script to update all displayed elements
                with col_cancel:
                    if st.button("ยกเลิก", key="cancel_delete_btn"):
                        st.info("ยกเลิกการลบลูกค้า")
        else:
            st.info("ไม่มีลูกค้าให้ลบ")

        st.markdown("---")
        st.subheader("รายชื่อลูกค้าปัจจุบัน")
        # Ensure this display uses the latest `customers_df_manage` after any add/edit/delete operation
        st.cache_data.clear() # Clear cache one last time to ensure this table is absolutely fresh
        customers_df_manage_display, _, _ = load_data() # Load data again for display
        if not customers_df_manage_display.empty:
            # Define columns to display and their order
            display_cols = ["ลำดับที่", "NAME", "AmountDue"]
            # Filter to only include columns that actually exist in the dataframe
            existing_cols = [col for col in display_cols if col in customers_df_manage_display.columns]
            customers_df_manage_display = customers_df_manage_display[existing_cols]

            st.dataframe(
                customers_df_manage_display.style.format({
                    "AmountDue": "{:,.2f}",
                    "ลำดับที่": "{:.0f}" # Format as integer without decimals
                }),
                use_container_width=True
            )
        else:
            st.info("ไม่มีข้อมูลลูกค้าในระบบ")


# Run the main app
if __name__ == "__main__":
    main()