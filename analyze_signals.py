import psycopg2
import pandas as pd

# connect to postgres
conn = psycopg2.connect(
    host="localhost",
    database="diaintel",
    user="diaintel",
    password="diaintel"
)

# load posts
query = "SELECT body FROM raw_posts;"
df = pd.read_sql(query, conn)

print("Rows loaded from database:", len(df))
print(df.head())

# drug list
drugs = [
    "metformin",
    "ozempic",
    "semaglutide",
    "jardiance",
    "januvia",
    "farxiga",
    "trulicity",
    "victoza"
]

# adverse events
events = [
    "nausea",
    "vomit",
    "diarrhea",
    "constipation",
    "headache",
    "fatigue",
    "dizziness",
    "stomach pain",
    "hypoglycemia"
]

results = []

for drug in drugs:
    for event in events:
        count = df["body"].str.contains(drug, case=False, na=False) & \
                df["body"].str.contains(event, case=False, na=False)
        results.append({
            "drug": drug,
            "event": event,
            "count": count.sum()
        })

signals = pd.DataFrame(results)

# create pivot table
heatmap = signals.pivot(index="drug", columns="event", values="count")

print("\nDrug → Side Effect Signal Matrix\n")
print(heatmap)