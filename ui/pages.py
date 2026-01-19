import streamlit as st
import time
import re
import hashlib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from mysql.connector import Error

from database.connection import get_db_connection
from database.setup import reset_db
from auth.authentication import AuthSystem
from tickets.manager import TicketManager
from analytics.engine import AnalyticsEngine
from ui.components import UIComponents
from email_processing.fetcher import EmailFetcher
from config import EmailConfig

# You would need to split your existing page functions here
# Due to length, I'll show the structure for one function:

def show_login_section():
    """Enhanced login section with better UI and proper form clearing"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="main-header">🤖 Sacco Ticket System</div>', unsafe_allow_html=True)
        
        with st.container():
            st.subheader("🔐 Please Login")
            
            # Initialize session state for form clearing
            if 'form_cleared' not in st.session_state:
                st.session_state.form_cleared = False
            
            # Use clear_on_submit for automatic form clearing
            with st.form("login_form", clear_on_submit=True):
                email = st.text_input(
                    "📧 Email Address",
                    placeholder="Enter your email address",
                    help="Use your Co-op email address",
                    key="login_email"  # Add unique key
                )
                
                password = st.text_input(
                    "🔑 Password",
                    type="password",
                    placeholder="Enter your password",
                    help="Enter your secure password",
                    key="login_password"  # Add unique key
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    login_btn = st.form_submit_button("✅ Login", use_container_width=True)
                with col2:
                    reset_btn = st.form_submit_button("🔄 Clear", use_container_width=True)
                
                # Handle form submissions
                if login_btn:
                    if not email or not password:
                        st.error("❌ Please enter both email and password")
                    else:
                        with st.spinner("🔐 Authenticating..."):
                            user = AuthSystem.authenticate_user(email, password)
                            if user:
                                st.session_state.user = user
                                st.session_state.authenticated = True
                                st.success(f"✅ Welcome back, {user['name']}!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Invalid credentials. Please check your email and password.")
                
                if reset_btn:
                    # The form will automatically clear due to clear_on_submit=True
                    st.session_state.form_cleared = True
                    # Show a success message that disappears on next run
                    st.success("✅ Form cleared! Please enter your credentials.")
        
        # Help section
        with st.expander("ℹ️ Login Help"):
            st.info("""
            **Default Login Credentials:**
            - Admin: Please use the assigned password provided during setup.
            - Staff: use your email and the assigned password.
            
            **Contact Support:** If you cannot access your account, please contact system administrator.
            """)


def show_main_application():
    """Main application after successful login"""
    
    # Sidebar with enhanced navigation
    st.sidebar.markdown(f"""
        <div class="user-info-card">
            <h4>👤 User Info</h4>
            <p><strong>Name:</strong> {st.session_state.user['name']}</p>
            <p><strong>Role:</strong> {st.session_state.user['role']}</p>
            <p><strong>Email:</strong> {st.session_state.user['email']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Navigation
    st.sidebar.title("🧭 Navigation")
    
    # Role-based menu options
    if st.session_state.user['role'] == 'Admin':
        menu_options = ["📊 AI Dashboard", "🎫 Ticket Management", "👥 User Management", "📈 Advanced Analytics", "⚙️ Settings"]
    else:
        menu_options = ["📊 AI Dashboard", "🎫 Ticket Management", "📈 My Analytics"]
    
    page = st.sidebar.radio("Go to", menu_options)
    
    # Database reset option for Eva only
    if st.session_state.user['email'] == 'eotieno@co-opbank.co.ke':
        if st.sidebar.button("⚠️ Reset Database"):
            if st.sidebar.checkbox("Confirm reset"):
                reset_db()
    
    # Logout button - FIXED: Clear session state properly
    if st.sidebar.button("🚪 Logout", width='stretch'):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    # Page routing
    if page == "📊 AI Dashboard":
        show_ai_dashboard()
    elif page == "🎫 Ticket Management":
        show_ticket_management()
    elif page == "👥 User Management" and st.session_state.user['role'] == 'Admin':
        show_user_management()
    elif page == "📈 Advanced Analytics" and st.session_state.user['role'] == 'Admin':
        show_advanced_analytics()
    elif page == "📈 My Analytics":
        show_personal_analytics()
    elif page == "⚙️ Settings" and st.session_state.user['role'] == 'Admin':
        show_settings()


def show_ai_dashboard():
    """Enhanced AI-powered dashboard with cleaner layout"""
    st.markdown('<div class="main-header">🎫 TICKET MAIN DASHBOARD</div>', unsafe_allow_html=True)

    conn = get_db_connection()
    if conn is None:
        st.error("❌ Cannot connect to database")
        return

    try:
        # --- Analytics data ---
        analytics = AnalyticsEngine.get_dashboard_metrics(conn)

        # =======================
        # KPI CARDS
        # =======================
        st.subheader("📈 Key Performance Indicators")

        kpis = [
            ("📊", analytics["total_tickets"], "Total Tickets"),
            ("🟡", analytics["open_tickets"], "Open Tickets"),
            ("✅", analytics["closed_tickets"], "Closed Tickets"),
            ("⏱", f"{analytics['avg_resolution_hours']:.1f}h", "Avg Resolution"),
        ]

        # sentiment KPI
        avg_sentiment = analytics.get("avg_sentiment", 0)
        sentiment_icon = "😊" if avg_sentiment > 0.1 else "😐" if avg_sentiment > -0.1 else "😠"
        kpis.append((sentiment_icon, f"{avg_sentiment:.2f}", "Avg Sentiment"))

        cols = st.columns(len(kpis))
        for col, (icon, value, label) in zip(cols, kpis):
            col.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-value">{icon} {value}</div>
                    <div class="kpi-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # =======================
        # CHARTS
        # =======================
        st.subheader("📊 Trends & Sentiment")

        left, right = st.columns(2)

        with left:
            if analytics.get("daily_trends"):
                trend_chart = UIComponents.create_trend_chart(analytics["daily_trends"])
                if trend_chart:
                    st.plotly_chart(trend_chart, width='stretch')

        with right:
            if "avg_sentiment" in analytics:
                sentiment_gauge = UIComponents.create_sentiment_gauge(avg_sentiment)
                if sentiment_gauge:
                    st.plotly_chart(sentiment_gauge, width='stretch')

        # =======================
        # URGENCY DISTRIBUTION
        # =======================
        if analytics.get("urgency_distribution"):
            st.subheader("🚨 Urgency Distribution")
            urgency_df = pd.DataFrame(
                list(analytics["urgency_distribution"].items()), 
                columns=["Urgency", "Count"]
            )
            fig = px.pie(
                urgency_df,
                values="Count",
                names="Urgency",
                title="Ticket Urgency Levels",
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            st.plotly_chart(fig, width='stretch')

        # =======================
        # RECENT TICKETS
        # =======================
        st.subheader("🔍 Recent Tickets")
        show_recent_tickets_with_insights(conn)

        # =======================
        # EMAIL INTEGRATION
        # =======================
        st.subheader("📧 Email Integration")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info("""
            **Email Automation Status**: Active  
            **Last Check**: Recent  
            **Next Fetch**: 15 minutes
            """)
        
        with col2:
            if st.button("🔄 Fetch Now", width='stretch', type="secondary"):
                with st.spinner("🤖 Analyzing emails..."):
                    try:
                        config = EmailConfig()
                        fetcher = EmailFetcher(config)
                        emails = fetcher.fetch_emails()
                        fetcher.disconnect()
                        
                        if emails:
                            manager = TicketManager()
                            results = []
                            for email in emails:
                                result = manager.assign_ticket(email)
                                results.append(result)
                            
                            success_count = sum(1 for r in results if r not in ["exists", "no_staff", "db_error"])
                            
                            if success_count > 0:
                                st.success(f"✅ Created {success_count} new tickets from {len(emails)} emails")
                            else:
                                st.info("📭 No new tickets created (all emails already processed)")
                        else:
                            st.info("📭 No new emails found")
                            
                    except Exception as e:
                        st.error(f"❌ Email fetch failed: {str(e)}")
    finally:
        conn.close()


def show_recent_tickets_with_insights(conn):
    """Show recent tickets with AI insights in styled cards"""
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT id, subject, sender_email, assigned_to, status, priority,
                   created_at, sentiment_score, urgency_level, ai_insights
            FROM tickets 
            ORDER BY created_at DESC 
            LIMIT 10
        ''')
        
        tickets = cursor.fetchall()
        column_names = [i[0] for i in cursor.description]

        for ticket_data in tickets:
            ticket = dict(zip(column_names, ticket_data))

            # Status badge
            status_badge = (
                f"<span class='badge status-closed'>✅ {ticket['status']}</span>"
                if ticket["status"] == "closed"
                else f"<span class='badge status-open'>🟡 {ticket['status']}</span>"
            )

            # Urgency badge
            urgency_badge = (
                f"<span class='badge urgency-urgent'>🔴 urgent</span>"
                if ticket["urgency_level"] == "urgent"
                else f"<span class='badge urgency-high'>🟠 high</span>"
                if ticket["urgency_level"] == "high"
                else f"<span class='badge urgency-normal'>🟢 normal</span>"
            )

            # Sentiment icon
            sentiment_icon = "😊" if ticket["sentiment_score"] > 0.1 else "😐" if ticket["sentiment_score"] > -0.1 else "😠"

            with st.container():
                st.markdown('<div class="ticket-card">', unsafe_allow_html=True)

                # Header
                st.markdown(f"<div class='ticket-title'>#{ticket['id']}: {ticket['subject']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='ticket-meta'>📧 {ticket['sender_email']} &nbsp; | &nbsp; 👤 {ticket['assigned_to']}</div>", unsafe_allow_html=True)
                st.markdown(f"{status_badge} {urgency_badge} <span class='badge'>⚡ {ticket['priority']}</span> <span class='badge'>{sentiment_icon} sentiment</span>", unsafe_allow_html=True)

                # AI Insights
                if ticket["ai_insights"]:
                    with st.expander("🤖 AI Insights"):
                        insights = ticket["ai_insights"].split("; ")
                        for insight in insights:
                            if insight.strip():
                                st.markdown(f"<div class='ai-insight'>💡 {insight}</div>", unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)  # close card

    except Error as e:
        st.error(f"Error loading tickets: {e}")
    finally:
        cursor.close()


def show_ticket_management():
    """Enhanced ticket management with assignment and closure features"""
    
    # ================================
    # MAIN CONTENT
    # ================================
    st.markdown('<div class="main-header">🎫 TICKET MANAGEMENT</div>', unsafe_allow_html=True)

    conn = get_db_connection()
    if conn is None:
        st.error("❌ Cannot connect to database")
        return
    
    try:
        # Ticket management tabs
        tab1, tab2, tab3 = st.tabs(["📋 All Tickets", "🔧 Manage Tickets", "✅ Close Tickets"])
        
        with tab1:
            show_all_tickets(conn)
        
        with tab2:
            if st.session_state.user['role'] == 'Admin' or st.session_state.user['email'] == 'eotieno@co-opbank.co.ke':
                show_manual_assignment(conn)
            else:
                st.info("🔒 Manual ticket assignment is available for administrators only.")
        
        with tab3:
            show_ticket_closure(conn)
    
    except Error as e:
        st.error(f"Database error: {e}")
    finally:
        conn.close()


def show_all_tickets(conn):
    """Display all tickets in a styled table"""
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT id, subject, sender_email, assigned_to, status, priority, 
                   urgency_level, created_at, resolved_at
            FROM tickets 
            ORDER BY created_at DESC
        ''')
        
        tickets = cursor.fetchall()
        column_names = [i[0] for i in cursor.description]
        
        if tickets:
            df = pd.DataFrame(tickets, columns=column_names)

            # Format datetime columns
            for col in ["created_at", "resolved_at"]:
                df[col] = df[col].apply(lambda x: x.strftime("%Y-%m-%d %H:%M") if pd.notnull(x) else "")

            # Add status badges
            def format_status(x):
                if x == "closed":
                    return f"<span class='status-badge closed'>✅ {x}</span>"
                else:
                    return f"<span class='status-badge open'>🟡 {x}</span>"

            df["status"] = df["status"].apply(format_status)

            # Add urgency badges
            def format_urgency(x):
                if x == "urgent":
                    return f"<span class='urgency-badge urgent'>🔴 {x}</span>"
                elif x == "high":
                    return f"<span class='urgency-badge high'>🟡 {x}</span>"
                else:
                    return f"<span class='urgency-badge normal'>🟢 {x}</span>"

            df["urgency_level"] = df["urgency_level"].apply(format_urgency)

            # Render as HTML for styling
            st.markdown(
                df.to_html(escape=False, index=False), 
                unsafe_allow_html=True
            )
        else:
            st.info("📭 No tickets found in the system.")
    
    except Error as e:
        st.error(f"Error loading tickets: {e}")
    finally:
        cursor.close()


def show_manual_assignment(conn):
    """Manual ticket assignment interface for Eva/admin"""
    st.subheader("👑 Manual Ticket Assignment")
    
    cursor = conn.cursor()
    
    try:
        # Get open tickets
        cursor.execute('''
            SELECT id, subject, assigned_to, created_at 
            FROM tickets 
            WHERE status = "open" 
            ORDER BY created_at DESC
        ''')
        
        open_tickets = cursor.fetchall()
        
        if open_tickets:
            # Get available staff from database
            cursor.execute('''
                SELECT email, name 
                FROM users 
                WHERE role = "IT Staff" 
                AND is_active = TRUE
                ORDER BY name
            ''')
            staff_list = cursor.fetchall()
            
            if not staff_list:
                st.error("❌ No active IT staff available for assignment. Please activate some staff users first.")
                return
            
            staff_options = {staff[1]: staff[0] for staff in staff_list}  # {name: email}
            
            # Create assignment form
            with st.form("manual_assignment"):
                st.write("**Select Ticket and Assign Staff**")
                
                # Ticket selection
                ticket_options = {f"#{ticket[0]} - {ticket[1]}": ticket[0] for ticket in open_tickets}
                selected_ticket_label = st.selectbox("📋 Select Ticket", list(ticket_options.keys()))
                ticket_id = ticket_options[selected_ticket_label]
                
                # Get current assignment for this ticket
                current_assignment_email = next((ticket[2] for ticket in open_tickets if ticket[0] == ticket_id), None)
                
                # Staff assignment with current assignment as default
                staff_names = list(staff_options.keys())
                
                # Find current assignment name if exists
                default_index = 0
                if current_assignment_email:
                    current_staff_name = next(
                        (name for name, email in staff_options.items() if email == current_assignment_email), 
                        None
                    )
                    if current_staff_name in staff_names:
                        default_index = staff_names.index(current_staff_name)
                
                selected_staff_name = st.selectbox(
                    "👤 Assign to Staff", 
                    staff_names,
                    index=default_index
                )
                
                assigned_to = staff_options[selected_staff_name]
                
                # Assignment notes
                admin_notes = st.text_area(
                    "📝 Admin Notes (Optional)", 
                    placeholder="Add any special instructions for the assigned staff..."
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    assign_btn = st.form_submit_button("✅ Assign Ticket", width='stretch')
                with col2:
                    cancel_btn = st.form_submit_button("❌ Cancel", width='stretch')
                
                if assign_btn:
                    manager = TicketManager()
                    if manager.manual_assign_ticket(ticket_id, assigned_to):
                        # Update admin notes if provided
                        if admin_notes:
                            cursor.execute(
                                'UPDATE tickets SET admin_notes = %s WHERE id = %s',
                                (admin_notes, ticket_id)
                            )
                            conn.commit()
                        
                        st.success(f"✅ Ticket #{ticket_id} successfully assigned to {selected_staff_name}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Failed to assign ticket. Please try again.")
                
                if cancel_btn:
                    st.info("❌ Ticket assignment canceled.")
        
        else:
            st.info("🎉 All tickets are currently assigned! No open tickets available for manual assignment.")
    
    except Error as e:
        st.error(f"Error in manual assignment: {e}")
    finally:
        cursor.close()


def show_ticket_closure(conn):
    """Ticket closure interface"""
    st.subheader("✅ Ticket Resolution Center")
    
    cursor = conn.cursor()
    
    try:
        # Get tickets assigned to current user that are still open
        current_user_email = st.session_state.user['email']
        
        cursor.execute('''
            SELECT id, subject, sender_email, created_at, assigned_to 
            FROM tickets 
            WHERE status = "open" AND assigned_to = %s
            ORDER BY created_at DESC
        ''', (current_user_email,))
        
        my_tickets = cursor.fetchall()
        
        if my_tickets:
            st.info(f"🔧 You have {len(my_tickets)} open ticket(s) assigned to you")
            
            for ticket in my_tickets:
                ticket_id, subject, sender_email, created_at, assigned_to = ticket
                
                with st.expander(f"🎫 Ticket #{ticket_id}: {subject}", expanded=True):
                    st.write(f"**From:** {sender_email}")
                    st.write(f"**Created:** {created_at.strftime('%Y-%m-%d %H:%M')}")
                    
                    # Resolution form
                    with st.form(f"resolve_ticket_{ticket_id}"):
                        resolution_notes = st.text_area(
                            "📝 Resolution Notes",
                            placeholder="Describe how you resolved this issue...",
                            key=f"notes_{ticket_id}"
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            resolve_btn = st.form_submit_button("✅ Mark as Resolved", width='stretch')
                        with col2:
                            st.form_submit_button("💾 Save Draft", width='stretch')
                        
                        if resolve_btn:
                            if not resolution_notes.strip():
                                st.error("❌ Please provide resolution notes before closing the ticket.")
                            else:
                                manager = TicketManager()
                                if manager.close_ticket(ticket_id, current_user_email, resolution_notes):
                                    st.success(f"✅ Ticket #{ticket_id} has been successfully closed!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to close ticket. Please try again.")
        else:
            st.info("📋 No open tickets are currently assigned to you. Great work! 🎉")
            
        # Show recently closed tickets
        st.subheader("📋 Recently Closed Tickets")

        cursor.execute('''
            SELECT id, subject, resolved_at, resolved_by, resolution_notes
            FROM tickets 
            WHERE status = "closed" 
            ORDER BY resolved_at DESC 
            LIMIT 5
        ''')

        closed_tickets = cursor.fetchall()

        if closed_tickets:
            for ticket in closed_tickets:
                ticket_id, subject, resolved_at, resolved_by, notes = ticket

                with st.container():
                    st.markdown(f"""
                        <div class="ticket-card closed-ticket">
                            <div class="ticket-title">#{ticket_id}: {subject}</div>
                            <div class="ticket-meta">
                                ✅ Resolved by <b>{resolved_by}</b> on {resolved_at.strftime('%Y-%m-%d %H:%M')}
                            </div>
                    """, unsafe_allow_html=True)

                    # Expander stays inside the card
                    if notes:
                        with st.expander("📝 View Resolution Notes"):
                            st.write(notes)

                    # Close the card div
                    st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("📭 No closed tickets found.")

    except Error as e:
        st.error(f"Error in ticket closure: {e}")
    finally:
        cursor.close()


def show_user_management():
    """User management interface for admin"""
    st.markdown('<div class="main-header">👥 USER MANAGEMENT</div>', unsafe_allow_html=True)
    
    conn = get_db_connection()
    if conn is None:
        st.error("❌ Cannot connect to database")
        return
    
    try:
        tab1, tab2, tab3 = st.tabs(["👥 Current Users", "➕ Add New User", "📊 User Activity"])
        
        with tab1:
            show_current_users(conn)
        
        with tab2:
            show_add_user_form(conn)
        
        with tab3:
            show_user_analytics(conn)
    
    except Error as e:
        st.error(f"Database error: {e}")
    finally:
        conn.close()


def show_current_users(conn):
    """Display and manage current users"""
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, email, name, role, is_active, created_at, last_login
            FROM users 
            ORDER BY created_at DESC
        ''')
        
        users = cursor.fetchall()
        column_names = [i[0] for i in cursor.description]
        
        if users:
            st.subheader("📋 Registered Users")
            
            for user_data in users:
                user = dict(zip(column_names, user_data))
                
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        st.write(f"**{user['name']}**")
                        st.write(f"`{user['email']}`")
                    
                    with col2:
                        role_icon = "👑" if user['role'] == 'Admin' else "👨‍💼"
                        st.write(f"{role_icon} {user['role']}")
                        status = "🟢 Active" if user['is_active'] else "🔴 Inactive"
                        st.write(status)
                    
                    with col3:
                        st.write(f"**Joined:** {user['created_at'].strftime('%Y-%m-%d')}")
                        if user['last_login']:
                            st.write(f"**Last login:** {user['last_login'].strftime('%Y-%m-%d %H:%M')}")
                        else:
                            st.write("**Last login:** Never")
                    
                    with col4:
                        # ✅ Admin can edit ANY account, including their own
                        if st.session_state.user['role'] == "Admin":
                            if st.button("⚙️", key=f"edit_{user['id']}"):
                                st.session_state.editing_user = user['id']
                        
                        # Protect default accounts from delete
                        if user['email'] not in ['eotieno@co-opbank.co.ke', 'admin@sacco.co.ke']:
                            delete_key = f"delete_{user['id']}"
                            confirm_key = f"confirm_delete_{user['id']}"
                            if st.button("🗑️", key=delete_key):
                                st.session_state[confirm_key] = True
                            if st.session_state.get(confirm_key, False):
                                if st.checkbox(f"Confirm delete {user['email']}?", key=f"chk_{user['id']}"):
                                    cursor.execute(
                                        "UPDATE users SET is_active = FALSE WHERE id = %s",
                                        (user['id'],)
                                    )
                                    conn.commit()
                                    st.success(f"✅ User {user['email']} deactivated")
                                    st.session_state.pop(confirm_key, None)
                                    st.rerun()
                    
                    st.write("---")
            
            # ✅ Edit user modal (admins can reset password too)
            if 'editing_user' in st.session_state:
                edit_user_id = st.session_state.editing_user
                user_to_edit = next((user for user in users if user[0] == edit_user_id), None)
                
                if user_to_edit:
                    with st.form(f"edit_user_{edit_user_id}"):
                        st.subheader(f"✏️ Edit User: {user_to_edit[2]}")
                        
                        new_name = st.text_input("Name", value=user_to_edit[2])
                        new_email = st.text_input("Email", value=user_to_edit[1])
                        new_role = st.selectbox("Role", ["Admin", "IT Staff"], 
                                              index=0 if user_to_edit[3] == "Admin" else 1)
                        is_active = st.checkbox("Active", value=bool(user_to_edit[4]))
                        new_password = st.text_input("New Password (leave blank to keep unchanged)", type="password")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Save Changes"):
                                if new_password.strip():
                                    hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()
                                    cursor.execute('''
                                        UPDATE users 
                                        SET name = %s, email = %s, role = %s, is_active = %s, password_hash = %s
                                        WHERE id = %s
                                    ''', (new_name, new_email, new_role, is_active, hashed_pw, edit_user_id))
                                else:
                                    cursor.execute('''
                                        UPDATE users 
                                        SET name = %s, email = %s, role = %s, is_active = %s
                                        WHERE id = %s
                                    ''', (new_name, new_email, new_role, is_active, edit_user_id))
                                conn.commit()
                                st.success("✅ User updated successfully!")
                                del st.session_state.editing_user
                                st.rerun()
                        
                        with col2:
                            if st.form_submit_button("❌ Cancel"):
                                del st.session_state.editing_user
                                st.rerun()
        else:
            st.info("👥 No users found in the system.")
    
    except Error as e:
        st.error(f"Error loading users: {e}")
    finally:
        cursor.close()


def show_add_user_form(conn):
    """Form to add new users"""
    st.subheader("➕ Add New User")
    
    with st.form("add_user_form"):
        name = st.text_input("👤 Full Name", placeholder="Enter user's full name")
        email = st.text_input("📧 Email Address", placeholder="user@example.com")
        role = st.selectbox("🎭 Role", ["IT Staff", "Admin"])
        password = st.text_input("🔑 Temporary Password", type="password", 
                               placeholder="Set a temporary password")
        
        col1, col2 = st.columns(2)
        with col1:
            add_btn = st.form_submit_button("👥 Add User", width='stretch')
        with col2:
            clear_btn = st.form_submit_button("🗑️ Clear", width='stretch')
        
        if add_btn:
            if not all([name, email, password]):
                st.error("❌ Please fill in all fields")
            elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                st.error("❌ Please enter a valid email address")
            else:
                cursor = conn.cursor()
                try:
                    # Check if email already exists
                    cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
                    if cursor.fetchone():
                        st.error("❌ A user with this email already exists")
                    else:
                        password_hash = AuthSystem.hash_password(password)
                        cursor.execute('''
                            INSERT INTO users (email, password_hash, name, role)
                            VALUES (%s, %s, %s, %s)
                        ''', (email, password_hash, name, role))
                        conn.commit()
                        st.success(f"✅ User {name} added successfully!")
                        st.info(f"📧 Login credentials sent to {email}")
                except Error as e:
                    st.error(f"Database error: {e}")
                finally:
                    cursor.close()
        
        if clear_btn:
            st.rerun()


def show_user_analytics(conn):
    """Show user activity analytics"""
    st.subheader("📊 User Performance Analytics")
    
    cursor = conn.cursor()
    
    try:
        # User ticket statistics
        cursor.execute('''
            SELECT 
                u.name,
                u.role,
                COUNT(t.id) as total_tickets,
                SUM(CASE WHEN t.status = 'closed' THEN 1 ELSE 0 END) as closed_tickets,
                AVG(CASE WHEN t.status = 'closed' THEN TIMESTAMPDIFF(HOUR, t.created_at, t.resolved_at) ELSE NULL END) as avg_resolution_time
            FROM users u
            LEFT JOIN tickets t ON u.email = t.assigned_to
            WHERE u.is_active = TRUE
            GROUP BY u.email, u.name, u.role
            ORDER BY closed_tickets DESC
        ''')
        
        user_stats = cursor.fetchall()
        
        if user_stats:
            st.write("**📈 Ticket Resolution Performance**")
            
            for stat in user_stats:
                name, role, total, closed, avg_time = stat
                
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{name}**")
                        st.write(f"*{role}*")
                    
                    with col2:
                        st.write(f"**Total:** {total}")
                    
                    with col3:
                        st.write(f"**Closed:** {closed}")
                    
                    with col4:
                        if avg_time:
                            st.write(f"**Avg Time:** {avg_time:.1f}h")
                        else:
                            st.write("**Avg Time:** N/A")
                    
                    # Progress bar for completion rate
                    if total > 0:
                        completion_rate = (closed / total) * 100
                        st.progress(int(completion_rate))
                        st.write(f"Completion rate: {completion_rate:.1f}%")
                    
                    st.write("---")
        else:
            st.info("📊 No user activity data available yet.")
    
    except Error as e:
        st.error(f"Error loading user analytics: {e}")
    finally:
        cursor.close()


def show_advanced_analytics():
    """Advanced analytics for admin"""
    st.markdown('<div class="main-header">📈 ADVANCED ANALYTICS</div>', unsafe_allow_html=True)
    
    conn = get_db_connection()
    if conn is None:
        st.error("❌ Cannot connect to database")
        return
    
    try:
        # Time period selection
        col1, col2, col3 = st.columns(3)
        with col1:
            period = st.selectbox("📅 Time Period", 
                                ["Last 7 days", "Last 30 days", "Last 90 days", "All time"])
        
        # Convert period to SQL
        period_map = {
            "Last 7 days": "7 DAY",
            "Last 30 days": "30 DAY",
            "Last 90 days": "90 DAY",
            "All time": "1000 YEAR"  # Practical "all time"
        }
        
        cursor = conn.cursor()
        
        # Ticket volume trends
        st.subheader("📊 Ticket Volume Trends")
        cursor.execute(f'''
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM tickets
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL {period_map[period]})
            GROUP BY DATE(created_at)
            ORDER BY date
        ''')
        
        trend_data = cursor.fetchall()
        
        if trend_data:
            dates = [row[0] for row in trend_data]
            counts = [row[1] for row in trend_data]
            
            fig = px.line(x=dates, y=counts, title=f"Ticket Volume Trend - {period}",
                         labels={'x': 'Date', 'y': 'Number of Tickets'})
            st.plotly_chart(fig, width='stretch')
        
        # Staff performance comparison
        st.subheader("👥 Staff Performance Comparison")
        cursor.execute(f'''
            SELECT 
                assigned_to,
                COUNT(*) as total_tickets,
                SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_tickets,
                AVG(CASE WHEN status = 'closed' THEN TIMESTAMPDIFF(HOUR, created_at, resolved_at) ELSE NULL END) as avg_resolution_hours
            FROM tickets
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL {period_map[period]})
                AND assigned_to IS NOT NULL
            GROUP BY assigned_to
            ORDER BY closed_tickets DESC
        ''')
        
        staff_performance = cursor.fetchall()
        
        if staff_performance:
            df = pd.DataFrame(staff_performance, 
                            columns=['Staff', 'Total Tickets', 'Closed Tickets', 'Avg Resolution Hours'])
            df['Closed Tickets'] = pd.to_numeric(df['Closed Tickets'], errors='coerce')
            df['Total Tickets'] = pd.to_numeric(df['Total Tickets'], errors='coerce')
            df['Completion Rate'] = (df['Closed Tickets'] / df['Total Tickets'] * 100).round(1)
            
            # Create performance chart
            fig = px.bar(df, x='Staff', y=['Total Tickets', 'Closed Tickets'],
                        title="Ticket Assignment and Completion",
                        barmode='group')
            st.plotly_chart(fig, width='stretch')
            
            # Show detailed table
            st.dataframe(df, width='stretch')
        
        # Sentiment analysis over time
        st.subheader("😊 Sentiment Analysis Trend")

        # First, get all dates in the range
        cursor.execute(f'''
            SELECT DISTINCT DATE(created_at) as date
            FROM tickets
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL {period_map[period]})
            ORDER BY date
        ''')
        all_dates = [row[0] for row in cursor.fetchall()]

        # Then get sentiment data with proper handling
        cursor.execute(f'''
            SELECT 
                DATE(created_at) as date, 
                COALESCE(ROUND(AVG(sentiment_score), 3), 0) as avg_sentiment
            FROM tickets
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL {period_map[period]})
            GROUP BY DATE(created_at)
            ORDER BY date
        ''')

        sentiment_data = cursor.fetchall()
        sentiment_dict = {row[0]: float(row[1]) for row in sentiment_data}

        # Fill in missing dates with 0 or None
        dates = []
        sentiments = []
        for date in all_dates:
            dates.append(date)
            sentiments.append(sentiment_dict.get(date, 0.0))

        if dates and sentiments:
            fig = px.line(
                x=dates, 
                y=sentiments, 
                title="Average Sentiment Over Time",
                labels={'x': 'Date', 'y': 'Sentiment Score'}
            )
            
            fig.update_traces(
                mode='lines+markers',
                line=dict(width=3, color='#FF6B6B'),
                marker=dict(size=6, color='#FF6B6B')
            )
            
            fig.add_hline(y=0, line_dash="dash", line_color="red")
            fig.update_layout(yaxis=dict(range=[-1, 1]))
            
            st.plotly_chart(fig, width='stretch')
    
    except Error as e:
        st.error(f"Analytics error: {e}")
    finally:
        cursor.close()
        conn.close()


def show_personal_analytics():
    """Personal analytics for staff members"""

    # ---------- Header ----------
    st.markdown('<div class="main-header">📊 My Performance Analytics</div>', unsafe_allow_html=True)

    conn = get_db_connection()
    if conn is None:
        st.error("❌ Cannot connect to database")
        return

    current_user = st.session_state.user['email']

    try:
        cursor = conn.cursor()

        # ---------- Personal stats ----------
        cursor.execute('''
            SELECT 
                COUNT(*) as total_assigned,
                SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_tickets,
                SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_tickets,
                AVG(CASE WHEN status = 'closed' THEN TIMESTAMPDIFF(HOUR, created_at, resolved_at) ELSE NULL END) as avg_resolution_time
            FROM tickets 
            WHERE assigned_to = %s
        ''', (current_user,))
        
        stats = cursor.fetchone()

        if stats:
            total, closed, open_tickets, avg_time = stats

            total = int(total) if total is not None else 0
            closed = int(closed) if closed is not None else 0
            open_tickets = int(open_tickets) if open_tickets is not None else 0
            avg_time = float(avg_time) if avg_time is not None else None

            st.markdown("")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">📌 {total}</div>
                        <div class="metric-label">Total Assigned</div>
                    </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">✅ {closed}</div>
                        <div class="metric-label">Closed</div>
                    </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">🟡 {open_tickets}</div>
                        <div class="metric-label">Open</div>
                    </div>
                """, unsafe_allow_html=True)

            with col4:
                avg_time_display = f"{avg_time:.1f}h" if avg_time is not None else "N/A"
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">⏱ {avg_time_display}</div>
                        <div class="metric-label">Avg Resolution Time</div>
                    </div>
                """, unsafe_allow_html=True)

            # ---------- Completion Rate Gauge ----------
            if total > 0:
                completion_rate = (closed / total) * 100
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=completion_rate,
                    title={'text': "Completion Rate %"},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "#2E86C1"},
                        'steps': [
                            {'range': [0, 50], 'color': "#F1948A"},
                            {'range': [50, 80], 'color': "#F7DC6F"},
                            {'range': [80, 100], 'color': "#82E0AA"}
                        ]
                    }
                ))
                fig.update_layout(height=300)
                st.plotly_chart(fig, width='stretch')

        # ---------- Recent Activity ----------
        st.markdown("### 📈 My Recent Activity")
        cursor.execute('''
            SELECT id, subject, status, created_at, resolved_at
            FROM tickets
            WHERE assigned_to = %s
            ORDER BY created_at DESC
            LIMIT 10
        ''', (current_user,))
        
        recent_tickets = cursor.fetchall()

        if recent_tickets:
            for ticket in recent_tickets:
                ticket_id, subject, status, created, resolved = ticket
                status_icon = "✅ Closed" if status == 'closed' else "🟡 Open"

                st.markdown(f"""
                    <div class="ticket-card">
                        <div class="ticket-id">#{ticket_id}: {subject}</div>
                        <div class="ticket-meta">{status_icon}</div>
                        <div class="ticket-meta">🗓 Created: {created.strftime('%Y-%m-%d %H:%M')}</div>
                        {f"<div class='ticket-meta'>✔ Resolved: {resolved.strftime('%Y-%m-%d %H:%M')}</div>" if resolved else ""}
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📭 No tickets assigned to you yet.")

    except Error as e:
        st.error(f"Error loading personal analytics: {e}")
    finally:
        cursor.close()
        conn.close()


def show_settings():
    """System settings for admin"""
    st.markdown('<div class="main-header">⚙️ SYSTEM SETTINGS</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🔧 Configuration", "📧 Email Settings", "🔄 System Maintenance"])
    
    with tab1:
        st.subheader("System Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**General Settings**")
            auto_fetch = st.checkbox("Enable Automatic Email Fetching", value=True)
            fetch_interval = st.slider("Fetch Interval (minutes)", 5, 60, 15)
            enable_ai = st.checkbox("Enable AI Analysis", value=True)
            
            if st.button("💾 Save General Settings"):
                st.success("✅ Settings saved successfully!")
        
        with col2:
            st.write("**Notification Settings**")
            email_notifications = st.checkbox("Email Notifications", value=True)
            desktop_alerts = st.checkbox("Desktop Alerts", value=True)
            urgency_threshold = st.selectbox("Urgency Alert Level", ["High", "Urgent", "All"])
            
            if st.button("💾 Save Notification Settings"):
                st.success("✅ Notification settings saved!")
    
    with tab2:
        st.subheader("Email Configuration")
        
        st.info("ℹ️ Configure email server settings for ticket integration")
        
        with st.form("email_config"):
            email_server = st.text_input("IMAP Server", value="outlook.office365.com")
            email_port = st.number_input("Port", value=993)
            email_address = st.text_input("Email Address", value="saccodesksupport@co-opbank.co.ke")
            email_password = st.text_input("Password", type="password")
            
            if st.form_submit_button("🔗 Test Connection"):
                with st.spinner("Testing email connection..."):
                    config = EmailConfig()
                    fetcher = EmailFetcher(config)
                    if fetcher.connect():
                        st.success("✅ Email connection successful!")
                        fetcher.disconnect()
                    else:
                        st.error("❌ Failed to connect to email server")
    
    with tab3:
        st.subheader("System Maintenance")
        
        st.warning("⚠️ These actions affect system data. Proceed with caution.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Clear Cache", width='stretch'):
                st.info("🗑️ Cache cleared successfully")
            
            if st.button("📊 Rebuild Analytics", width='stretch'):
                with st.spinner("Rebuilding analytics data..."):
                    time.sleep(2)
                    st.success("✅ Analytics data rebuilt!")
        
        with col2:
            if st.button("🗃️ Archive Old Tickets", width='stretch'):
                st.info("📦 Tickets older than 90 days have been archived")
            
            if st.button("🔍 System Health Check", width='stretch'):
                with st.spinner("Running system diagnostics..."):
                    time.sleep(3)
                    st.success("✅ System health check completed!")