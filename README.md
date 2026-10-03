# SmartPlate (built from the team guide)

    pip3 install -r requirements.txt
    python3 generate_demo_data.py            # 200 SIMULATED rows -> meal_history_demo.csv
    python3 -m streamlit run streamlit_app.py

Student app = main page. "Manager dashboard" = sidebar page (preview of the Power BI metrics).
Outside breakfast hours, tick "Demo mode: ignore the clock" in the sidebar and pick Breakfast.

| Guide step | Where |
|---|---|
| 1 Login (name + Panther ID, prototype only) | streamlit_app.py |
| 2 Date, time, meal-period aware | live_menu.py (determine_meal_period: test rules, not official hours) |
| 5 Live menu with menu.csv fallback | live_menu.py pulls the day's menu automatically from DineOnCampus (no typing). Response format checked on the real site; the app itself was tested with a saved copy, run it once on your laptop to confirm. Falls back to menu.csv on any failure |
| 6-7 Hunger level + recommendation engine | recommendation.py |
| 8 Build my own plate | streamlit_app.py |
| 9 Confirm, Recommended vs Custom | streamlit_app.py |
| 10 Post-meal feedback | streamlit_app.py |
| 11 SmartPoints 20/10/5/0 | streamlit_app.py |
| 12 Data -> meal_history.csv (same 10 columns as before) | streamlit_app.py |
| 13 ~200 simulated records + dashboard metrics | generate_demo_data.py, pages/Manager_dashboard.py |

Real data goes to meal_history.csv. Simulated data goes to meal_history_demo.csv. Never mix them.

## Live menu (automatic)
No setup. live_menu.py calls the same address the DineOnCampus website uses for 8th Street
Campus Kitchen (apiv4.dineoncampus.com, periods then menu). Test it: `python3 live_menu.py`
(prints source: live). Condiments, dressings, desserts and 0-calorie items are filtered out.
Caveats: unofficial/undocumented address that may change; ask FIU Dining before real use;
calories come from DineOnCampus, serving sizes are per listed portion.

## Put it online (Streamlit Community Cloud, free)
1. Create a free GitHub account, then a new PUBLIC repository named smartplate.
2. On the repo page click "Add file" > "Upload files", drag in everything inside this folder
   (including the pages folder), then "Commit changes".
3. Go to share.streamlit.io, sign in with GitHub, click "Create app", pick the repo,
   branch main, main file path streamlit_app.py, then Deploy.
4. Open the link it gives you. Check the sidebar says the menu is live; if it says menu.csv,
   DineOnCampus blocked the cloud server (the app still works with the fallback).
Notes: files saved online (meal_history.csv) are erased when the app restarts, so online
data is demo-only. Public site: use fake names and IDs.
