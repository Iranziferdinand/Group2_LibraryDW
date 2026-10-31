import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Library DW Dashboard",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# SECURITY & RBAC (Required by FA)
# ============================================================
if "role" not in st.session_state:
    st.session_state.role = None

def login_screen():
    st.title("🔒 Library DW System Login")
    st.write("Please select your role to access the dashboard (Demonstrating RBAC).")
    role = st.selectbox("Role", ["Admin", "Analyst", "Department Head (Engineering)"])
    if st.button("Login"):
        st.session_state.role = role
        st.rerun()

if st.session_state.role is None:
    login_screen()
    st.stop() # Stops the app from loading the rest of the code until logged in

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #4da6ff; margin-bottom: 0; }
    .sub-header { color: #a0a0a0; font-size: 1.1rem; margin-top: 0; }
    div[data-testid="stMetricValue"] { font-size: 2rem; color: #4da6ff; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATABASE CONNECTION
# ============================================================
@st.cache_resource
def get_engine():
    return create_engine('mysql+mysqlconnector://root:@localhost/library_dw')

@st.cache_data(ttl=600)
def run_query(sql: str) -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql(text(sql), engine)

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.image("https://img.icons8.com/color/96/books.png", width=80)
st.sidebar.title("📚 Library DW")
st.sidebar.markdown(f"**Logged in as:** `{st.session_state.role}`")

if st.sidebar.button("Logout"):
    st.session_state.role = None
    st.rerun()

st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate",
    ["🏠 Overview", "📈 Monthly Trends", "🏛️ Departments", 
     "🕐 Peak Times", "📖 Top Books", "🏢 Room Analytics", "🔍 Explorer"]
)

# ============================================================
# HEADER
# ============================================================
st.markdown('<p class="main-header">Library Data Warehouse</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Interactive analytics on physical, digital & room usage</p>', unsafe_allow_html=True)
st.divider()

# ============================================================
# PAGE: OVERVIEW
# ============================================================
if page == "🏠 Overview":
    kpi_sql = """
        SELECT 
            SUM(download_count) AS total_downloads,
            SUM(loan_days) AS total_loan_days,
            ROUND(SUM(duration_hours), 1) AS total_room_hours,
            COUNT(*) AS total_events
        FROM library_usage_fact
    """
    kpi = run_query(kpi_sql).iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📥 Total Downloads", f"{int(kpi['total_downloads']):,}")
    c2.metric("📚 Loan Days", f"{int(kpi['total_loan_days']):,}")
    c3.metric("🕐 Room Hours", f"{kpi['total_room_hours']:,.1f}")
    c4.metric("📊 Total Events", f"{int(kpi['total_events']):,}")

    st.divider()

    q1 = run_query("""
        SELECT d.year, d.month,
               SUM(f.loan_days) AS physical_loan_days,
               SUM(f.download_count) AS digital_downloads,
               ROUND(SUM(f.duration_hours), 1) AS room_hours
        FROM library_usage_fact f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY d.year, d.month ORDER BY d.year, d.month
    """)
    q1['month_name'] = pd.to_datetime(q1['month'].astype(str), format='%m').dt.strftime('%B')

    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.line(q1, x="month_name", y="digital_downloads", title="Digital Downloads by Month",
                      markers=True, color_discrete_sequence=["#2E86AB"])
        st.plotly_chart(fig, width='stretch')
    with col_b:
        fig = px.bar(q1, x="month_name", y="physical_loan_days", title="Physical Loan Days by Month",
                     color_discrete_sequence=["#A23B72"])
        st.plotly_chart(fig, width='stretch')

    st.divider()
    fig = px.area(q1, x="month_name", y="room_hours", title="Room Usage Hours by Month",
                  color_discrete_sequence=["#F18F01"])
    st.plotly_chart(fig, width='stretch')

# ============================================================
# PAGE: MONTHLY TRENDS
# ============================================================
elif page == "📈 Monthly Trends":
    q1 = run_query("""
        SELECT d.year, d.month, SUM(f.loan_days) AS physical_loan_days,
               SUM(f.download_count) AS digital_downloads, ROUND(SUM(f.duration_hours), 1) AS room_hours
        FROM library_usage_fact f JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY d.year, d.month ORDER BY d.year, d.month
    """)
    q1['month_name'] = pd.to_datetime(q1['month'].astype(str), format='%m').dt.strftime('%B')

    st.subheader("All-Service Monthly Trends")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=q1["month_name"], y=q1["physical_loan_days"], mode="lines+markers", name="Physical Loans (Days)", line=dict(color="#A23B72", width=3)))
    fig.add_trace(go.Scatter(x=q1["month_name"], y=q1["digital_downloads"], mode="lines+markers", name="Digital Downloads", line=dict(color="#2E86AB", width=3)))
    fig.add_trace(go.Scatter(x=q1["month_name"], y=q1["room_hours"], mode="lines+markers", name="Room Hours", line=dict(color="#F18F01", width=3)))
    fig.update_layout(xaxis_title="Month", yaxis_title="Volume", hovermode="x unified", height=500)
    st.plotly_chart(fig, width='stretch')

    st.subheader("Raw Data")
    st.dataframe(q1, width='stretch')

# ============================================================
# PAGE: DEPARTMENTS (Includes RBAC Data Filtering)
# ============================================================
elif page == "🏛️ Departments":
    st.subheader("Library Usage by Department")

    # RBAC Implementation
    if st.session_state.role == "Department Head (Engineering)":
        st.info("🔒 Security Filter Applied: You are only viewing Engineering department data.")
        where_clause = "WHERE s.department = 'Engineering'"
    else:
        where_clause = "WHERE s.department IS NOT NULL"

    q2 = run_query(f"""
        SELECT s.department, COUNT(*) AS usage_events,
               SUM(f.download_count) AS downloads, SUM(f.loan_days) AS loan_days
        FROM library_usage_fact f
        JOIN dim_student s ON f.student_key = s.student_key
        {where_clause}
        GROUP BY s.department ORDER BY usage_events DESC
    """)

    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.bar(q2, x="usage_events", y="department", orientation="h", title="Usage Events", color="usage_events", color_continuous_scale="Blues")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, width='stretch')
    with col_b:
        fig = px.pie(q2, values="usage_events", names="department", title="Usage Share", hole=0.4)
        st.plotly_chart(fig, width='stretch')

    q5 = run_query(f"""
        SELECT s.department, ROUND(AVG(f.loan_days), 2) AS avg_loan_days, COUNT(*) AS loans
        FROM library_usage_fact f
        JOIN dim_student s ON f.student_key = s.student_key
        {where_clause} AND f.loan_days > 0
        GROUP BY s.department ORDER BY avg_loan_days DESC
    """)
    
    if not q5.empty:
        fig = px.bar(q5, x="department", y="avg_loan_days", title="Average Loan Duration (Days)", color="avg_loan_days", color_continuous_scale="Viridis")
        st.plotly_chart(fig, width='stretch')

    st.subheader("Detailed Breakdown")
    st.dataframe(q2, width='stretch')

# ============================================================
# PAGE: PEAK TIMES
# ============================================================
elif page == "🕐 Peak Times":
    q3 = run_query("""
        SELECT t.time_slot, COUNT(*) AS bookings
        FROM library_usage_fact f JOIN dim_time t ON f.time_key = t.time_key
        WHERE f.time_key IS NOT NULL GROUP BY t.time_slot ORDER BY bookings DESC
    """)

    st.subheader("Room Booking Peak Times")
    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.pie(q3, values="bookings", names="time_slot", title="Booking Distribution", color_discrete_sequence=["#ff9999","#66b3ff","#99ff99"])
        st.plotly_chart(fig, width='stretch')
    with col_b:
        fig = px.bar(q3, x="time_slot", y="bookings", title="Bookings per Slot", color="time_slot", color_discrete_sequence=["#ff9999","#66b3ff","#99ff99"])
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width='stretch')
    st.dataframe(q3, width='stretch')

# ============================================================
# PAGE: TOP BOOKS
# ============================================================
elif page == "📖 Top Books":
    q4 = run_query("""
        SELECT r.resource_id AS BookISBN, r.category AS BookCategory, COUNT(*) AS times_borrowed
        FROM library_usage_fact f JOIN dim_resource r ON f.resource_key = r.resource_key
        WHERE r.resource_type = 'Physical Book'
        GROUP BY r.resource_id, r.category ORDER BY times_borrowed DESC LIMIT 10
    """)

    st.subheader("Top 10 Most Borrowed Books")
    fig = px.bar(q4, x="times_borrowed", y="BookISBN", orientation="h", color="BookCategory", text="times_borrowed", title="Top 10 Books")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, width='stretch')
    st.dataframe(q4, width='stretch')

# ============================================================
# PAGE: ROOM ANALYTICS
# ============================================================
elif page == "🏢 Room Analytics":
    q_rooms = run_query("""
        SELECT r.room_number, t.time_slot, COUNT(*) AS bookings, ROUND(SUM(f.duration_hours), 1) AS total_hours
        FROM library_usage_fact f
        JOIN dim_room r ON f.room_key = r.room_key
        JOIN dim_time t ON f.time_key = t.time_key
        WHERE f.room_key IS NOT NULL
        GROUP BY r.room_number, t.time_slot ORDER BY bookings DESC
    """)

    st.subheader("Room Utilization")
    fig = px.bar(q_rooms.head(20), x="room_number", y="bookings", color="time_slot", barmode="group", title="Top 20 Rooms by Bookings")
    st.plotly_chart(fig, width='stretch')

    q_room_hours = run_query("""
        SELECT r.room_number, ROUND(SUM(f.duration_hours), 1) AS total_hours
        FROM library_usage_fact f JOIN dim_room r ON f.room_key = r.room_key
        WHERE f.room_key IS NOT NULL GROUP BY r.room_number ORDER BY total_hours DESC LIMIT 10
    """)
    fig = px.bar(q_room_hours, x="room_number", y="total_hours", title="Top Rooms by Total Hours", color="total_hours", color_continuous_scale="Oranges")
    st.plotly_chart(fig, width='stretch')
    st.dataframe(q_rooms, width='stretch')

# ============================================================
# PAGE: EXPLORER (OLAP)
# ============================================================
elif page == "🔍 Explorer":
    st.subheader("OLAP Drill-Down Explorer")

    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("Year", [2024, 2025])
    with col2:
        metric = st.selectbox("Metric", ["downloads", "loan_days", "room_hours"])

    metric_sql = {
        "downloads": "SUM(f.download_count)",
        "loan_days": "SUM(f.loan_days)",
        "room_hours": "ROUND(SUM(f.duration_hours), 1)"
    }[metric]

    drill = run_query(f"""
        SELECT d.year, d.quarter, d.month, {metric_sql} AS value
        FROM library_usage_fact f JOIN dim_date d ON f.date_key = d.date_key
        WHERE d.year = {year} GROUP BY d.year, d.quarter, d.month ORDER BY d.quarter, d.month
    """)
    
    drill['month_name'] = pd.to_datetime(drill['month'].astype(str), format='%m').dt.strftime('%B')

    fig = px.bar(drill, x="month_name", y="value", color="quarter", title=f"{metric.replace('_',' ').title()} for {year}", text="value")
    st.plotly_chart(fig, width='stretch')

    qsum = drill.groupby("quarter")["value"].sum().reset_index()
    fig = px.pie(qsum, values="value", names="quarter", title="Quarterly Breakdown", hole=0.3)
    st.plotly_chart(fig, width='stretch')
    st.dataframe(drill, width='stretch')

# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption("📚 Library Data Warehouse — ETL → Star Schema → Interactive Analytics")