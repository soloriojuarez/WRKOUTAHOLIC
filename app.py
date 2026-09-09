"""
app.py
Streamlit dashboard - the interactive front end. Tabs mirror a typical
workout tracker (Log, History, Exercises) plus an Analytics tab that
replaces the paywalled "Store" tab you'd see in apps like Strong.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import db
import analytics
from datetime import date

st.set_page_config(page_title="Workout Analytics Tracker", layout="wide")
db.init_db()

st.title("🏋️ Workout Analytics Tracker")
st.caption("Python + SQL + Pandas/NumPy + Streamlit/Plotly")

tab_log, tab_history, tab_exercises, tab_analytics = st.tabs(
    ["➕ Log Workout", "📜 History", "📋 Exercises", "📊 Analytics"]
)

# ---------------- LOG WORKOUT ----------------
with tab_log:
    st.subheader("Log a set")
    exercises = db.get_all_exercises()
    exercise_names = [e[1] for e in exercises]

    if not exercise_names:
        st.warning("No exercises yet. Add one in the Exercises tab first.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            workout_date = st.date_input("Date", value=date.today())
        with col2:
            selected_exercise = st.selectbox("Exercise", exercise_names)
        with col3:
            weight = st.number_input("Weight (lbs)", min_value=0.0, step=2.5)
        with col4:
            reps = st.number_input("Reps", min_value=1, step=1, value=8)

        if st.button("Log Set", type="primary"):
            workout_id = db.add_workout(workout_date.isoformat())
            exercise_id = [e[0] for e in exercises if e[1] == selected_exercise][0]
            db.log_set(workout_id, exercise_id, 1, weight, int(reps))
            st.success(f"Logged {weight} lbs x {reps} reps for {selected_exercise}")

# ---------------- HISTORY ----------------
with tab_history:
    st.subheader("Full workout history")
    rows = db.get_all_sets_with_details()
    if rows:
        df = pd.DataFrame(rows, columns=["Date", "Exercise", "Muscle Group", "Set #", "Weight", "Reps"])
        st.dataframe(df.sort_values("Date", ascending=False), use_container_width=True)
    else:
        st.info("No workouts logged yet.")

# ---------------- EXERCISES ----------------
with tab_exercises:
    st.subheader("Exercise library")
    st.caption("⭐ = niche exercise not typically found in mainstream tracker apps")
    exercises = db.get_all_exercises()
    if exercises:
        df = pd.DataFrame(exercises, columns=["id", "Name", "Muscle Group", "Niche"])
        df["Niche"] = df["Niche"].apply(lambda x: "⭐" if x else "")
        st.dataframe(df[["Name", "Muscle Group", "Niche"]], use_container_width=True)

    with st.expander("Add a new exercise"):
        new_name = st.text_input("Exercise name")
        new_group = st.text_input("Muscle group")
        new_niche = st.checkbox("Niche exercise (not in mainstream apps)")
        if st.button("Add Exercise"):
            if new_name and new_group:
                db.add_exercise(new_name, new_group, new_niche)
                st.success(f"Added {new_name}")
                st.rerun()

# ---------------- ANALYTICS ----------------
with tab_analytics:
    st.subheader("Analytics & Insights")
    st.caption("This tab replaces the 'Store' tab in apps like Strong — insights are free and computed live from your data.")

    exercises = db.get_all_exercises()
    exercise_names = [e[1] for e in exercises]

    if not exercise_names:
        st.info("Log some workouts first to see analytics.")
    else:
        selected = st.selectbox("Choose an exercise to analyze", exercise_names, key="analytics_select")

        best_set_df = analytics.best_set_over_time(selected)
        volume_df = analytics.volume_over_time(selected)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**{selected} — Estimated 1RM Over Time**")
            if not best_set_df.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=best_set_df["workout_date"], y=best_set_df["est_1rm"],
                    mode="lines+markers", line=dict(color="#7c5cff")
                ))
                fig.update_layout(height=320, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data yet for this exercise.")

        with col2:
            st.markdown(f"**{selected} — Total Volume Per Session**")
            if not volume_df.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=volume_df["workout_date"], y=volume_df["volume"],
                    mode="lines+markers", line=dict(color="#7c5cff")
                ))
                fig.update_layout(height=320, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data yet for this exercise.")

        st.divider()
        st.markdown("### 💡 Insights")

        trend = analytics.progressive_overload_trend(selected)
        pr = analytics.personal_records(selected)
        is_plateaued = analytics.detect_plateau(selected)

        i1, i2, i3 = st.columns(3)
        with i1:
            if pr:
                st.metric("Personal Record (est. 1RM)", f"{pr['est_1rm']} lbs",
                           help=f"Set on {pr['date']}: {pr['weight']} lbs x {pr['reps']} reps")
        with i2:
            st.metric("Trend", trend["message"] if trend["slope"] is None else f"{trend['slope']:+.1f} lbs/session")
        with i3:
            st.metric("Plateau flag", "⚠️ Yes" if is_plateaued else "✅ No")

        if trend["slope"] is not None:
            st.write(trend["message"])
        if is_plateaued:
            st.warning(f"No new PR in your last several {selected} sessions — consider a deload, a rep-range change, or a form check.")

        st.divider()
        st.markdown("### ⚖️ Muscle Group Balance (last 30 days)")
        balance_df = analytics.muscle_group_balance(days=30)
        if not balance_df.empty:
            fig = go.Figure(data=[go.Bar(
                x=balance_df["muscle_group"], y=balance_df["volume"],
                marker_color="#7c5cff"
            )])
            fig.update_layout(height=320, margin=dict(l=20, r=20, t=20, b=20),
                               yaxis_title="Total Volume (lbs)")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(balance_df.rename(columns={
                "muscle_group": "Muscle Group", "volume": "Total Volume", "pct_of_total": "% of Total"
            }), use_container_width=True)
        else:
            st.info("Not enough recent data to compute muscle balance.")
