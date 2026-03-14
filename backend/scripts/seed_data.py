"""
DiaIntel — Seed Data Script
Inserts 50 realistic sample posts as fallback data covering all 8 target drugs.

Only runs if raw_posts table has fewer than 10 rows — never overwrites real data.

Populates:
- raw_posts (50 rows)
- processed_posts (50 rows)
- drug_mentions (50+ rows)
- ae_signals (80+ rows)
- sentiment_scores (50 rows)
- drug_ae_graph (edge weights)
- drug_stats_cache (8 drugs)

Usage:
    python scripts/seed_data.py
"""

import os
import sys
import json
import random
from datetime import datetime, timedelta, timezone

# CRITICAL: Set before any HuggingFace import
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import psycopg2
from psycopg2.extras import execute_values


# Database connection
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://diaintel:diaintel_pass@localhost:5432/diaintel"
)

# Target drugs with their brand/generic variants
DRUGS = {
    "metformin": {"normalized": "metformin", "class": "Biguanide", "brands": ["Glucophage", "Glumetza", "Fortamet"]},
    "ozempic": {"normalized": "semaglutide", "class": "GLP-1 RA", "brands": ["Ozempic", "Wegovy"]},
    "jardiance": {"normalized": "empagliflozin", "class": "SGLT2 Inhibitor", "brands": ["Jardiance"]},
    "januvia": {"normalized": "sitagliptin", "class": "DPP-4 Inhibitor", "brands": ["Januvia"]},
    "farxiga": {"normalized": "dapagliflozin", "class": "SGLT2 Inhibitor", "brands": ["Farxiga"]},
    "trulicity": {"normalized": "dulaglutide", "class": "GLP-1 RA", "brands": ["Trulicity"]},
    "victoza": {"normalized": "liraglutide", "class": "GLP-1 RA", "brands": ["Victoza"]},
    "glipizide": {"normalized": "glipizide", "class": "Sulfonylurea", "brands": ["Glucotrol"]},
}

# Adverse events
AE_TERMS = [
    "nausea", "bloating", "dizziness", "fatigue", "weight loss",
    "diarrhea", "stomach cramps", "headache", "vomiting",
    "constipation", "abdominal pain", "hypoglycemia",
    "muscle pain", "joint pain", "appetite loss",
]

SEVERITIES = ["mild", "moderate", "severe"]
SEVERITY_WEIGHTS = [0.5, 0.35, 0.15]

SUBREDDITS = ["diabetes", "diabetes_t2", "Ozempic", "Semaglutide"]

# Sentiment distribution: 40% negative, 35% neutral, 25% positive
SENTIMENTS = [
    ("negative", -0.7, 0.85),
    ("negative", -0.5, 0.78),
    ("negative", -0.8, 0.92),
    ("negative", -0.6, 0.80),
    ("negative", -0.4, 0.72),
    ("negative", -0.9, 0.95),
    ("negative", -0.55, 0.76),
    ("negative", -0.65, 0.83),
    ("negative", -0.75, 0.88),
    ("negative", -0.45, 0.74),
    ("negative", -0.85, 0.91),
    ("negative", -0.3, 0.68),
    ("negative", -0.7, 0.86),
    ("negative", -0.6, 0.79),
    ("negative", -0.5, 0.75),
    ("negative", -0.8, 0.90),
    ("negative", -0.55, 0.77),
    ("negative", -0.65, 0.82),
    ("negative", -0.4, 0.71),
    ("negative", -0.75, 0.87),
    ("neutral", 0.0, 0.65),
    ("neutral", 0.1, 0.70),
    ("neutral", -0.1, 0.60),
    ("neutral", 0.05, 0.68),
    ("neutral", -0.05, 0.62),
    ("neutral", 0.15, 0.72),
    ("neutral", -0.15, 0.58),
    ("neutral", 0.0, 0.66),
    ("neutral", 0.1, 0.69),
    ("neutral", -0.1, 0.63),
    ("neutral", 0.05, 0.67),
    ("neutral", 0.0, 0.64),
    ("neutral", -0.05, 0.61),
    ("neutral", 0.1, 0.71),
    ("neutral", 0.15, 0.73),
    ("neutral", -0.15, 0.59),
    ("neutral", 0.0, 0.65),
    ("positive", 0.6, 0.82),
    ("positive", 0.7, 0.88),
    ("positive", 0.5, 0.76),
    ("positive", 0.8, 0.91),
    ("positive", 0.65, 0.85),
    ("positive", 0.55, 0.78),
    ("positive", 0.75, 0.89),
    ("positive", 0.45, 0.73),
    ("positive", 0.85, 0.93),
    ("positive", 0.6, 0.81),
    ("positive", 0.7, 0.87),
    ("positive", 0.5, 0.75),
    ("positive", 0.4, 0.72),
]

# Realistic sample posts
SAMPLE_POSTS = [
    ("metformin", "Been on Metformin 500mg twice daily for 3 months now. The nausea was terrible the first two weeks but it's gotten better. My A1C dropped from 8.2 to 6.9 which is amazing. Still dealing with some stomach cramps after meals though.", ["nausea", "stomach cramps"]),
    ("metformin", "Doc just increased my Metformin to 1000mg. The bloating is real, I feel like a balloon after every meal. Anyone else experience this? My blood sugar numbers are great though so I don't want to switch.", ["bloating"]),
    ("metformin", "I've been taking glucophage for over a year now. Initially had diarrhea but that stopped after month 2. Lost about 15 pounds which was a nice bonus. Fatigue is still an issue though, not sure if it's the med or my blood sugar.", ["diarrhea", "fatigue", "weight loss"]),
    ("metformin", "Metformin extended release has been a game changer for me. Way less GI issues compared to the regular version. Only side effect I notice is some mild headache occasionally. A1C went from 9.1 to 7.2!", ["headache"]),
    ("metformin", "Starting Fortamet tomorrow, nervous about the side effects I've read about. My doctor says it's basically metformin but easier on the stomach. Anyone have experience with it? Worried about the nausea everyone talks about.", ["nausea"]),
    ("metformin", "6 months on Metformin 850mg. The dizziness was unexpected - nobody warned me about that. Also getting stomach cramps almost daily. Considering asking my doc about switching drugs.", ["dizziness", "stomach cramps"]),
    ("ozempic", "Just started Ozempic 0.25mg weekly. First injection went smoothly but the nausea hit me hard on day 2. Couldn't eat much for the next 3 days. Lost 4 pounds in the first week though.", ["nausea", "weight loss"]),
    ("ozempic", "Week 8 on Ozempic, now at 0.5mg dose. The weight loss has been incredible - down 18 pounds. But the fatigue is brutal. I need to nap every afternoon. Also dealing with constant bloating.", ["weight loss", "fatigue", "bloating"]),
    ("ozempic", "Been on semaglutide (Ozempic) for 4 months. Nausea comes and goes, worst after eating fatty foods. Noticed some dizziness when standing up too quickly. My A1C dropped to 6.5 from 8.8 so I'm sticking with it.", ["nausea", "dizziness"]),
    ("ozempic", "Ozempic 1mg dose gave me the worst stomach cramps of my life. Had to go back to 0.5mg. Also experiencing headaches almost daily. The appetite suppression is real though - I barely want to eat.", ["stomach cramps", "headache"]),
    ("ozempic", "Wegovy (same as Ozempic but for weight loss) has been transformative. Down 30 pounds in 5 months. The nausea was bad weeks 1-3 but manageable now. Occasional diarrhea still happens though.", ["nausea", "weight loss", "diarrhea"]),
    ("ozempic", "PSA: Ozempic can cause serious fatigue. I've been dragging myself through work every day since starting it 2 months ago. My endo says it should improve but I'm skeptical. At least my blood sugar is under control.", ["fatigue"]),
    ("jardiance", "Jardiance 10mg has been working great for my T2D. Only real side effect is I'm peeing WAY more often. Some mild dizziness when I don't drink enough water. A1C dropped from 7.8 to 6.4.", ["dizziness"]),
    ("jardiance", "Started empagliflozin last month. The weight loss is a nice bonus - down 8 pounds. But I've had this persistent fatigue that won't go away. Also getting headaches that I never used to get.", ["weight loss", "fatigue", "headache"]),
    ("jardiance", "3 months on Jardiance 25mg. Got a UTI in the first month which my doctor said is a known risk. Other than that, some bloating and occasional nausea but nothing too bad. Blood sugars are great.", ["bloating", "nausea"]),
    ("jardiance", "Love Jardiance but the dizziness is annoying. My blood pressure dropped too low a few times. Also noticed some stomach cramps in the evening. Overall though my diabetes management has never been better.", ["dizziness", "stomach cramps"]),
    ("januvia", "Januvia 100mg has been pretty mild for me side-effect wise. Occasional headache and some joint pain. Nothing dramatic but also nothing dramatic in terms of A1C reduction either - only went from 7.5 to 7.1.", ["headache"]),
    ("januvia", "Been on sitagliptin for 6 months now. Minimal side effects which is nice - just some mild nausea occasionally and a bit of fatigue. My numbers are slowly improving. Not as dramatic as some of the newer drugs.", ["nausea", "fatigue"]),
    ("januvia", "Januvia combined with Metformin has been my combo for 2 years. The Januvia adds some stomach cramps on top of the Metformin GI issues. But it's manageable and my A1C stays around 6.8.", ["stomach cramps"]),
    ("januvia", "Doctor switched me from Januvia to Ozempic because Januvia wasn't doing enough. While on Januvia I had mild dizziness and bloating but nothing severe. Just wasn't strong enough for my blood sugar levels.", ["dizziness", "bloating"]),
    ("farxiga", "Farxiga 10mg started 2 weeks ago. Already noticing more frequent urination and some dizziness. Lost 3 pounds which is encouraging. Hoping the side effects settle down soon.", ["dizziness", "weight loss"]),
    ("farxiga", "Dapagliflozin has been great for my T2D and blood pressure. Main complaint is fatigue and occasional headaches. Also some bloating after larger meals. A1C went from 8.1 to 6.7 in 4 months.", ["fatigue", "headache", "bloating"]),
    ("farxiga", "Been on Farxiga for 8 months. The nausea was rough in the beginning but went away. Still dealing with muscle pain that my doc thinks might be related. Considering adding it to my list of side effects to report.", ["nausea"]),
    ("farxiga", "Farxiga + Metformin combo. The diarrhea from this combination was intense for the first month. Now it's better but I still get stomach cramps. Blood sugar control is excellent though so I deal with it.", ["diarrhea", "stomach cramps"]),
    ("trulicity", "Trulicity 1.5mg weekly injection. The nausea is REAL with this one. First 3 weeks I could barely eat. Lost 12 pounds but not in a healthy way. It's getting better now at week 6. My endo says give it time.", ["nausea", "weight loss"]),
    ("trulicity", "Switched from Victoza to dulaglutide (Trulicity). Less daily hassle with weekly injections. Side effects are similar though - bloating, fatigue, and occasional dizziness. A1C improved from 7.3 to 6.6.", ["bloating", "fatigue", "dizziness"]),
    ("trulicity", "Trulicity has been a disaster for me. Constant stomach cramps, vomiting, and I can't keep food down some days. My doctor wants me to try a lower dose before giving up on it. At least my blood sugar is better.", ["stomach cramps", "nausea"]),
    ("trulicity", "3 months on Trulicity. The headaches are persistent - almost daily. Also getting some diarrhea that comes and goes. The weight loss has been good (10 lbs) but I'm not sure the trade-off is worth it.", ["headache", "diarrhea", "weight loss"]),
    ("victoza", "Victoza 1.2mg daily for 2 months. Nausea was bad the first week but I powered through. Now I mainly deal with fatigue and occasional bloating. My A1C dropped 1.5 points which is amazing.", ["nausea", "fatigue", "bloating"]),
    ("victoza", "Been on liraglutide for a year now. The weight loss plateaued around 15 pounds but the blood sugar control is still excellent. Main ongoing issues are mild stomach cramps and headaches from time to time.", ["weight loss", "stomach cramps", "headache"]),
    ("victoza", "Switching from Victoza to Ozempic because weekly injections sound way better than daily. While on Victoza I had constant nausea and dizziness for the first 3 months. It did get better eventually.", ["nausea", "dizziness"]),
    ("victoza", "Victoza 1.8mg dose. The injection site sometimes gets red and itchy. Also dealing with fatigue that makes my afternoon slumps worse. Diarrhea happened a lot in the first month but is rare now.", ["fatigue", "diarrhea"]),
    ("glipizide", "Glipizide 5mg twice daily. Had a scary hypoglycemia episode last week - blood sugar dropped to 55. Also getting dizziness and fatigue regularly. Doc says I need to be more careful about eating regularly.", ["dizziness", "fatigue"]),
    ("glipizide", "Been on Glucotrol for 3 months. The weight gain is frustrating - up 6 pounds. Also getting headaches more frequently. My blood sugar is controlled but I'm not happy about the weight change.", ["headache"]),
    ("glipizide", "Glipizide makes me so bloated. Like uncomfortable bloating after every meal. Also had some nausea in the beginning that comes back if I take it on an empty stomach. Blood sugars are good though.", ["bloating", "nausea"]),
    ("glipizide", "On glipizide 10mg. The stomach cramps are annoying but manageable. More concerning is the dizziness - happens almost daily especially after lunch. Considering asking about newer diabetes medications.", ["stomach cramps", "dizziness"]),
    ("metformin", "Glumetza extended release 1500mg. Much better GI tolerance than regular metformin. Still some mild nausea and occasional diarrhea but way less than before. A1C is at 6.5 and holding steady.", ["nausea", "diarrhea"]),
    ("ozempic", "Ozempic changed my life. A1C from 10.2 to 6.8 in 6 months. Lost 25 pounds. Yes I had nausea at first and still get fatigue but the benefits far outweigh the side effects. Highly recommend.", ["nausea", "fatigue", "weight loss"]),
    ("jardiance", "Jardiance has been my best diabetes med so far. Minimal side effects compared to Metformin. Just some dizziness if I don't stay hydrated and mild headaches. My kidney function has actually improved.", ["dizziness", "headache"]),
    ("januvia", "Sitagliptin is ok for mild T2D but wasn't enough for me. Had mild bloating and stomach cramps as side effects. Doc is adding Metformin to see if the combination works better.", ["bloating", "stomach cramps"]),
    ("farxiga", "Farxiga 5mg dose is perfect for me. Lower dose means fewer side effects. Just mild dizziness and fatigue. My blood sugar and weight are both trending in the right direction.", ["dizziness", "fatigue"]),
    ("trulicity", "Dulaglutide 0.75mg as a starting dose. The nausea lasted about 10 days then cleared up. Now at week 4, I mainly notice some weight loss and occasional stomach cramps. Overall very manageable.", ["nausea", "weight loss", "stomach cramps"]),
    ("victoza", "Victoza at 0.6mg starter dose. Headaches are my main complaint. Also some bloating that seems to come and go. Going to increase to 1.2mg next week and hoping the side effects don't get worse.", ["headache", "bloating"]),
    ("glipizide", "Glipizide ER 10mg. The hypoglycemia risk is real - I've learned to always carry glucose tablets. Fatigue and nausea are daily battles. Thinking about asking about GLP-1 drugs instead.", ["fatigue", "nausea"]),
    ("metformin", "Just got prescribed Metformin 500mg to start. Reading all these posts about side effects has me anxious but I know I need to manage my T2D. Any tips for reducing the nausea? Taking with food? Extended release?", ["nausea"]),
    ("ozempic", "3 months post-Ozempic start. The vomiting episodes have decreased thankfully. Still deal with diarrhea occasionally and persistent fatigue. Down 20 lbs and A1C is 7.0, so I'm cautiously optimistic.", ["diarrhea", "fatigue", "weight loss"]),
    ("jardiance", "Empagliflozin 25mg for nearly a year now. Best A1C I've ever had at 6.2. The constant thirst and frequent urination are annoying but I've adapted. Occasional nausea but rare. Would recommend.", ["nausea"]),
    ("trulicity", "Anyone else get crazy bloating on Trulicity? I look 6 months pregnant after dinner. Also the fatigue is dragging me down. Week 10 and hoping it improves. My sugars are great so I want to stick with it.", ["bloating", "fatigue"]),
    ("victoza", "Liraglutide 1.8mg daily for 8 months. The nausea comes in waves - some weeks are fine, others are rough. Weight loss of 12 pounds. The stomach cramps are my least favorite part. But A1C at 6.7 is worth it.", ["nausea", "weight loss", "stomach cramps"]),
    ("glipizide", "Glucotrol XL 5mg. Working well for blood sugar but the dizziness after taking it is consistent. Also some headaches and general fatigue. Old school med but it gets the job done for me.", ["dizziness", "headache", "fatigue"]),
]


def get_connection():
    """Create a database connection."""
    # Parse the DATABASE_URL for psycopg2
    db_url = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
    return psycopg2.connect(db_url)


def check_should_seed(conn) -> bool:
    """Only seed if raw_posts has fewer than 10 rows."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM raw_posts")
        count = cur.fetchone()[0]
        if count >= 10:
            print(f"Database already has {count} rows in raw_posts. Skipping seed.")
            return False
        print(f"Database has {count} rows in raw_posts. Proceeding with seed.")
        return True


def seed_data(conn):
    """Insert all seed data."""
    now = datetime.now(timezone.utc)
    drug_names = list(DRUGS.keys())

    raw_post_ids = []
    processed_post_ids = []
    drug_ae_counts = {}  # (drug, ae) -> count

    with conn.cursor() as cur:
        # ============================================================
        # Insert raw_posts
        # ============================================================
        print("\nInserting raw_posts...")
        raw_posts_data = []
        for i, (drug, body, _) in enumerate(SAMPLE_POSTS):
            # Spread timestamps over last 6 months
            days_ago = random.randint(1, 180)
            created = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            subreddit = random.choice(SUBREDDITS)

            raw_posts_data.append((
                f"seed_{i:04d}",  # reddit_id
                subreddit,
                body,
                random.randint(1, 500),  # score
                random.randint(0, 50),   # comment_count
                created,
                now,  # scraped_at
                True,  # processed
                "seed_data.py"  # source_file
            ))

        execute_values(
            cur,
            """INSERT INTO raw_posts
               (reddit_id, subreddit, body, score, comment_count,
                created_utc, scraped_at, processed, source_file)
               VALUES %s
               ON CONFLICT (reddit_id) DO NOTHING
               RETURNING id""",
            raw_posts_data
        )
        raw_post_ids = [row[0] for row in cur.fetchall()]
        print(f"  Inserted {len(raw_post_ids)} raw posts")

        if not raw_post_ids:
            print("  No new rows inserted (all reddit_ids already exist). Aborting.")
            conn.rollback()
            return

        # ============================================================
        # Insert processed_posts
        # ============================================================
        print("Inserting processed_posts...")
        processed_data = []
        for idx, raw_id in enumerate(raw_post_ids):
            body = SAMPLE_POSTS[idx][1]
            word_count = len(body.split())
            days_ago = random.randint(1, 180)
            processed_at = now - timedelta(days=days_ago)

            processed_data.append((
                raw_id,
                body.lower().strip(),  # simple cleaning for seed
                "en",
                word_count,
                processed_at
            ))

        execute_values(
            cur,
            """INSERT INTO processed_posts
               (raw_post_id, cleaned_text, language, word_count, processed_at)
               VALUES %s
               RETURNING id""",
            processed_data
        )
        processed_post_ids = [row[0] for row in cur.fetchall()]
        print(f"  Inserted {len(processed_post_ids)} processed posts")

        # ============================================================
        # Insert drug_mentions
        # ============================================================
        print("Inserting drug_mentions...")
        drug_mentions_data = []
        for idx, post_id in enumerate(processed_post_ids):
            drug = SAMPLE_POSTS[idx][0]
            drug_info = DRUGS[drug]
            dosages = ["500mg", "1000mg", "10mg", "25mg", "0.25mg", "0.5mg", "1mg", "1.5mg", "1.8mg", "5mg", "100mg", "850mg", None]

            drug_mentions_data.append((
                post_id,
                drug,
                drug_info["normalized"],
                random.choice(dosages),
                random.choice(["daily", "twice daily", "weekly", "once daily", None]),
                round(random.uniform(0.75, 0.99), 2),
                now - timedelta(days=random.randint(1, 180))
            ))

        execute_values(
            cur,
            """INSERT INTO drug_mentions
               (post_id, drug_name, drug_normalized, dosage, frequency,
                confidence, detected_at)
               VALUES %s""",
            drug_mentions_data
        )
        print(f"  Inserted {len(drug_mentions_data)} drug mentions")

        # ============================================================
        # Insert ae_signals
        # ============================================================
        print("Inserting ae_signals...")
        ae_signals_data = []
        for idx, post_id in enumerate(processed_post_ids):
            drug = SAMPLE_POSTS[idx][0]
            ae_terms = SAMPLE_POSTS[idx][2]

            for ae in ae_terms:
                severity = random.choices(SEVERITIES, weights=SEVERITY_WEIGHTS, k=1)[0]
                confidence = round(random.uniform(0.6, 0.98), 2)
                detected_at = now - timedelta(days=random.randint(1, 180))

                ae_signals_data.append((
                    post_id,
                    drug,
                    ae,
                    ae,  # ae_normalized
                    severity,
                    confidence,
                    random.choice(["after starting", "within first week", "ongoing", "recently", None]),
                    detected_at,
                    random.choice([True, False])
                ))

                # Track for graph
                key = (drug, ae)
                drug_ae_counts[key] = drug_ae_counts.get(key, 0) + 1

        execute_values(
            cur,
            """INSERT INTO ae_signals
               (post_id, drug_name, ae_term, ae_normalized, severity,
                confidence, temporal_marker, detected_at, is_new_signal)
               VALUES %s""",
            ae_signals_data
        )
        print(f"  Inserted {len(ae_signals_data)} AE signals")

        # ============================================================
        # Insert sentiment_scores
        # ============================================================
        print("Inserting sentiment_scores...")
        sentiment_data = []
        for idx, post_id in enumerate(processed_post_ids):
            drug = SAMPLE_POSTS[idx][0]
            label, score, confidence = SENTIMENTS[idx % len(SENTIMENTS)]

            sentiment_data.append((
                post_id,
                drug,
                label,
                score,
                confidence,
                now - timedelta(days=random.randint(1, 180))
            ))

        execute_values(
            cur,
            """INSERT INTO sentiment_scores
               (post_id, drug_name, sentiment_label, sentiment_score,
                confidence, scored_at)
               VALUES %s""",
            sentiment_data
        )
        print(f"  Inserted {len(sentiment_data)} sentiment scores")

        # ============================================================
        # Insert drug_ae_graph
        # ============================================================
        print("Inserting drug_ae_graph edges...")
        graph_data = []
        for (drug, ae), weight in drug_ae_counts.items():
            first_detected = now - timedelta(days=random.randint(30, 180))
            graph_data.append((
                drug, ae, weight, first_detected, now
            ))

        execute_values(
            cur,
            """INSERT INTO drug_ae_graph
               (drug_name, ae_term, edge_weight, first_detected, last_updated)
               VALUES %s
               ON CONFLICT (drug_name, ae_term)
               DO UPDATE SET edge_weight = drug_ae_graph.edge_weight + EXCLUDED.edge_weight,
                            last_updated = EXCLUDED.last_updated""",
            graph_data
        )
        print(f"  Inserted {len(graph_data)} graph edges")

        # ============================================================
        # Insert drug_stats_cache
        # ============================================================
        print("Inserting drug_stats_cache...")
        for drug_name, drug_info in DRUGS.items():
            # Count posts for this drug
            drug_post_count = sum(1 for d, _, _ in SAMPLE_POSTS if d == drug_name)

            # Get top AEs for this drug
            drug_aes = {}
            for (d, ae), weight in drug_ae_counts.items():
                if d == drug_name:
                    drug_aes[ae] = weight
            top_aes = sorted(drug_aes.items(), key=lambda x: x[1], reverse=True)[:5]
            top_ae_json = json.dumps([{"ae_term": ae, "count": cnt} for ae, cnt in top_aes])

            # Compute avg sentiment for this drug
            drug_sentiments = [s[1] for i, s in enumerate(SENTIMENTS)
                               if i < len(SAMPLE_POSTS) and SAMPLE_POSTS[i][0] == drug_name]
            avg_sentiment = sum(drug_sentiments) / len(drug_sentiments) if drug_sentiments else 0.0

            cur.execute(
                """INSERT INTO drug_stats_cache
                   (drug_name, total_posts, top_ae_json, avg_sentiment, last_computed)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (drug_name)
                   DO UPDATE SET total_posts = EXCLUDED.total_posts,
                                top_ae_json = EXCLUDED.top_ae_json,
                                avg_sentiment = EXCLUDED.avg_sentiment,
                                last_computed = EXCLUDED.last_computed""",
                (drug_name, drug_post_count, top_ae_json, round(avg_sentiment, 3), now)
            )
        print(f"  Inserted/updated {len(DRUGS)} drug stats cache entries")

    conn.commit()

    # ============================================================
    # Print summary
    # ============================================================
    print("\n" + "=" * 60)
    print("Seed Data Summary")
    print("=" * 60)
    with conn.cursor() as cur:
        tables = [
            "raw_posts", "processed_posts", "drug_mentions",
            "ae_signals", "sentiment_scores", "drug_ae_graph",
            "drug_stats_cache"
        ]
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  {table}: {count} rows")
    print("=" * 60)


def main():
    """Main entry point."""
    print("=" * 60)
    print("DiaIntel — Seed Data Script")
    print("=" * 60)

    conn = get_connection()
    try:
        if check_should_seed(conn):
            seed_data(conn)
            print("\n✓ Seed data inserted successfully!")
        else:
            print("\n✓ Database already has data. No seeding needed.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
