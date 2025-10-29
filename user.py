import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Farm Equipment Financing Calculator",
    page_icon="🚜",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2e8b57;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2e8b57;
        border-bottom: 2px solid #2e8b57;
        padding-bottom: 0.5rem;
        margin-top: 1.5rem;
    }
    .center-header {
        font-size: 1.8rem;
        color: #ff7f0e;
        text-align: center;
        margin: 2rem 0;
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .highlight-box {
        background-color: #f0fff0;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2e8b57;
        margin-bottom: 1.5rem;
    }
    .result-box {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        margin-bottom: 1.5rem;
    }
    .metric-box {
        background-color: #e9f5e9;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .slider-container {
        padding: 1rem;
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .stSlider > div > div {
        color: #2e8b57;
    }
    .centered-content {
        display: flex;
        justify-content: center;
        margin: 2rem 0;
    }
    .chart-container {
        display: flex;
        justify-content: center;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# App title and description
st.markdown('<h1 class="main-header">🚜 Farm Equipment Financing Calculator</h1>', unsafe_allow_html=True)
st.markdown("""
This calculator helps farmers determine financing options for agricultural equipment purchases. 
Enter the equipment details, your down payment, and loan terms to calculate your EMI payment schedule.
""")

# Initialize session state
if 'calculate_clicked' not in st.session_state:
    st.session_state.calculate_clicked = False

# Main calculator layout
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<h3 class="sub-header">Equipment Details</h3>', unsafe_allow_html=True)
    
    equipment_name = st.text_input("Equipment Name", "John Deere Tractor")
    
    st.markdown("**Equipment Price (₹)**")
    # Changed max_value to 2000000 (20 lakh)
    equipment_price = st.slider(
        "Select equipment price", 
        min_value=100000, 
        max_value=2000000, 
        value=1500000, 
        step=50000,
        label_visibility="collapsed"
    )
    st.write(f"**₹{equipment_price:,.2f}**")
    
    equipment_lifespan = st.slider("Expected Lifespan (years)", min_value=1, max_value=20, value=10)
    
    st.markdown('<h3 class="sub-header">Financing Options</h3>', unsafe_allow_html=True)
    
    down_payment = st.slider("Down Payment (%)", min_value=0, max_value=100, value=20)
    down_payment_amount = (down_payment / 100) * equipment_price
    st.write(f"Down Payment Amount: **₹{down_payment_amount:,.2f}**")
    
    loan_amount = equipment_price - down_payment_amount
    st.write(f"Loan Amount: **₹{loan_amount:,.2f}**")
    
    interest_rate = st.slider("Annual Interest Rate (%)", min_value=1.0, max_value=20.0, value=8.5, step=0.1)
    
    loan_term = st.slider("Loan Term (years)", min_value=1, max_value=10, value=5)

with col2:
    st.markdown('<h3 class="sub-header">EMI Calculation</h3>', unsafe_allow_html=True)
    
    # Calculate monthly payment (EMI)
    monthly_interest = interest_rate / 100 / 12
    num_payments = loan_term * 12
    
    if interest_rate > 0:
        monthly_payment = (loan_amount * monthly_interest * (1 + monthly_interest)**num_payments) / ((1 + monthly_interest)**num_payments - 1)
    else:
        monthly_payment = loan_amount / num_payments
    
    # Calculate total values
    total_payment = monthly_payment * num_payments
    total_interest = total_payment - loan_amount
    
    # Display results in metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric("EMI", f"₹{monthly_payment:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric("Total Interest", f"₹{total_interest:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric("Total Payment", f"₹{total_payment:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Calculate amortization schedule
    if st.button("Calculate Payment Schedule", type="primary", use_container_width=True):
        st.session_state.calculate_clicked = True
    
    if st.session_state.calculate_clicked:
        balance = loan_amount
        schedule_data = []
        
        for month in range(1, num_payments + 1):
            interest_payment = balance * monthly_interest
            principal_payment = monthly_payment - interest_payment
            balance -= principal_payment
            
            schedule_data.append({
                "Month": month,
                "Beginning Balance": round(balance + principal_payment, 2),
                "EMI": round(monthly_payment, 2),
                "Principal": round(principal_payment, 2),
                "Interest": round(interest_payment, 2),
                "Outstanding Balance": round(max(0, balance), 2)
            })
        
        # Create DataFrame
        schedule_df = pd.DataFrame(schedule_data)
        
        # Display amortization schedule
        st.markdown("**Amortization Schedule**")
        st.dataframe(
            schedule_df.head(12).style.format({
                "Beginning Balance": "₹{:,.2f}",
                "EMI": "₹{:,.2f}",
                "Principal": "₹{:,.2f}",
                "Interest": "₹{:,.2f}",
                "Outstanding Balance": "₹{:,.2f}"
            }),
            height=400,
            use_container_width=True
        )
        
        # Create a rounded version for CSV export
        schedule_df_rounded = schedule_df.copy()
        for col in ["Beginning Balance", "EMI", "Principal", "Interest", "Outstanding Balance"]:
            schedule_df_rounded[col] = schedule_df_rounded[col].round(2)
        
        # Show download option
        csv = schedule_df_rounded.to_csv(index=False)
        st.download_button(
            label="Download Full Schedule as CSV",
            data=csv,
            file_name="emi_schedule.csv",
            mime="text/csv",
            use_container_width=True
        )

# EMI Chart Section - Centered
if st.session_state.calculate_clicked:
    st.markdown("---")
    st.markdown('<h3 class="center-header">📊 Amortization Schedule Chart</h3>', unsafe_allow_html=True)
    
    # Prepare data for the chart
    chart_data = schedule_df.head(12).copy()
    
    # Create centered charts using columns with different weights
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Create two columns for the charts within the centered container
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Create a stacked bar chart for EMI breakdown
            fig = go.Figure()
            
            # Add principal portion
            fig.add_trace(go.Bar(
                x=chart_data['Month'],
                y=chart_data['Principal'],
                name='Principal',
                marker_color='#2e8b57',  # Green color
                hovertemplate='Month: %{x}<br>Principal: ₹%{y:,.2f}<extra></extra>'
            ))
            
            # Add interest portion
            fig.add_trace(go.Bar(
                x=chart_data['Month'],
                y=chart_data['Interest'],
                name='Interest',
                marker_color='#ff7f0e',  # Orange color
                hovertemplate='Month: %{x}<br>Interest: ₹%{y:,.2f}<extra></extra>'
            ))
            
            # Update layout
            fig.update_layout(
                barmode='stack',
                title='EMI Breakdown (First 12 Months)',
                xaxis_title='Month',
                yaxis_title='Amount (₹)',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
            )
            
            # Display the chart
            st.plotly_chart(fig, use_container_width=True)
        
        with chart_col2:
            # Create a line chart for balance over time
            fig2 = go.Figure()
            
            fig2.add_trace(go.Scatter(
                x=chart_data['Month'],
                y=chart_data['Outstanding Balance'],
                mode='lines+markers',
                name='Outstanding Balance',
                line=dict(color='#1f77b4', width=3),
                hovertemplate='Month: %{x}<br>Balance: ₹%{y:,.2f}<extra></extra>'
            ))
            
            # Update layout
            fig2.update_layout(
                title='Outstanding Balance Over Time (First 12 Months)',
                xaxis_title='Month',
                yaxis_title='Balance (₹)',
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
            )
            
            # Display the chart
            st.plotly_chart(fig2, use_container_width=True)

# Additional information
st.markdown("---")
st.markdown('<h3 class="sub-header">Financing Tips for Farmers</h3>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="highlight-box">
        <h4>💰 Government Schemes</h4>
        <p>Check for agricultural subsidies and low-interest loan programs offered by the government for farmers.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="highlight-box">
        <h4>📈 Seasonal Considerations</h4>
        <p>Time your purchase to align with harvest seasons when cash flow is typically better.</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="highlight-box">
        <h4>🔧 Maintenance Costs</h4>
        <p>Remember to factor in ongoing maintenance costs which can be 2-5% of equipment value annually.</p>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("*This calculator is for estimation purposes only. Actual loan terms may vary based on creditworthiness and lender policies.*")