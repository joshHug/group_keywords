import sqlite3
import os

DATABASE = 'words.db'

# The raw data dumped from your previous command
RAW_DATA = """
2     | soccer               | 7.0    | micahkeegan@berkeley.edu | Active (No Decay)
7     | zedd                 | 7.0    | h.ding3500@berkeley.edu | Active (No Decay)
9     | pokemon              | 5.0    | dinhtai@berkeley.edu | Active (No Decay)
10    | dance                | 2.0    | dinhtai@berkeley.edu | Active (No Decay)
11    | volleyball           | 5.0    | aiattoni@berkeley.edu | Active (No Decay)
12    | clash_royale         | 10.0   | aiattoni@berkeley.edu | Active (No Decay)
13    | 49ers                | 11.0   | sanatan_mishra@berkeley.edu | Active (No Decay)
14    | space                | 6.0    | ella_tovali@berkeley.edu | Active (No Decay)
15    | hes                  | 3.0    | h___@berkeley.edu    | Active (No Decay)
16    | coffee_shops         | 18.0   | shyla_awasthi@berkeley.edu | Active (No Decay)
17    | travel               | 10.0   | shyla_awasthi@berkeley.edu | Active (No Decay)
18    | horror               | 7.0    | ella_tovali@berkeley.edu | Active (No Decay)
19    | robotics             | 13.0   | ella_tovali@berkeley.edu | Active (No Decay)
20    | central_asia         | 2.0    | jamil_shirinov@berkeley.edu | Active (No Decay)
21    | math                 | 18.0   | owen.jiang@berkeley.edu | Active (No Decay)
22    | matcha               | 12.0   | audrey06kramer@berkeley.edu | Active (No Decay)
23    | gym                  | 7.0    | nmareedu@berkeley.edu | Active (No Decay)
24    | 6_7                  | 2.0    | nmareedu@berkeley.edu | Active (No Decay)
25    | brawl_stars          | 3.0    | rajbir_longia@berkeley.edu | Active (No Decay)
26    | piano                | 2.0    | rajbir_longia@berkeley.edu | Active (No Decay)
27    | music                | 11.0   | claire_lu@berkeley.edu | Active (No Decay)
28    | pop_music            | 2.0    | claire_lu@berkeley.edu | Active (No Decay)
32    | projectsekai         | 3.0    | jamil_shirinov@berkeley.edu | Active (No Decay)
33    | filipino             | 3.0    | kamryn_murillo@berkeley.edu | Active (No Decay)
34    | asian                | 11.0   | kamryn_murillo@berkeley.edu | Active (No Decay)
35    | astro                | 6.0    | sathvikmalla17@berkeley.edu | Active (No Decay)
36    | chocolate            | 6.0    | sathvikmalla17@berkeley.edu | Active (No Decay)
37    | football             | 3.0    | sathvikmalla17@berkeley.edu | Active (No Decay)
38    | drake                | 5.0    | vaibhavhariram@berkeley.edu | Active (No Decay)
39    | malatang             | 9.0    | mbhan@berkeley.edu   | Active (No Decay)
40    | noodles              | 10.0   | mbhan@berkeley.edu   | Active (No Decay)
41    | over_25_yo           | 2.0    | bryce_g@berkeley.edu | Active (No Decay)
42    | deltarune            | 5.0    | alice_kuznetsov@berkeley.edu | Active (No Decay)
43    | stem                 | 5.0    | rosielu@berkeley.edu | Active (No Decay)
44    | fleetwood            | 5.0    | hongfan@berkeley.edu | Active (No Decay)
45    | powerlifting         | 3.0    | hongfan@berkeley.edu | Active (No Decay)
46    | running              | 5.0    | ceciliasun@berkeley.edu | Active (No Decay)
47    | cdramas              | 2.0    | ceciliasun@berkeley.edu | Active (No Decay)
48    | minecraft            | 6.0    | wesley_tan@berkeley.edu | Active (No Decay)
49    | eight                | 4.0    | rmedha_08@berkeley.edu | Active (No Decay)
50    | stove                | 1.0    | rmedha_08@berkeley.edu | 2026-01-13 07:14:22.313132
51    | blahaj               | 7.0    | siwenjadenlong@berkeley.edu | Active (No Decay)
52    | climbing             | 5.0    | briansu242@berkeley.edu | Active (No Decay)
53    | jazz                 | 5.0    | briansu242@berkeley.edu | Active (No Decay)
54    | queer                | 2.0    | siwenjadenlong@berkeley.edu | Active (No Decay)
55    | trans                | 2.0    | siwenjadenlong@berkeley.edu | Active (No Decay)
56    | basketball           | 2.0    | aydinkhalaji@berkeley.edu | Active (No Decay)
57    | sushi                | 4.0    | aydinkhalaji@berkeley.edu | Active (No Decay)
60    | persian              | 2.0    | aydinkhalaji@berkeley.edu | Active (No Decay)
61    | celeste              | 2.0    | david-yuan@berkeley.edu | Active (No Decay)
62    | factorio             | 1.0    | david-yuan@berkeley.edu | 2026-01-13 03:36:51.775160
63    | indie_games          | 10.0   | laurier_ke@berkeley.edu | Active (No Decay)
65    | food                 | 2.0    | skr25324@berkeley.edu | Active (No Decay)
66    | webnovels            | 1.0    | briansu242@berkeley.edu | 2026-01-13 03:19:55.994564
68    | wingsoffire          | 4.0    | tienpham@berkeley.edu | Active (No Decay)
69    | secretcow            | 2.0    | tienpham@berkeley.edu | Active (No Decay)
70    | wasian               | 1.0    | aiattoni@berkeley.edu | 2026-01-13 03:30:31.488103
72    | spiderverse          | 3.0    | nidhiimarar@berkeley.edu | Active (No Decay)
73    | arcane               | 2.0    | nidhiimarar@berkeley.edu | Active (No Decay)
74    | nature               | 2.0    | zoyab@berkeley.edu   | Active (No Decay)
75    | urban                | 1.0    | zoyab@berkeley.edu   | 2026-01-13 05:07:37.335395
76    | cog_sci              | 2.0    | laurier_ke@berkeley.edu | Active (No Decay)
77    | econ                 | 1.0    | adyakadam@berkeley.edu | 2026-01-13 05:44:03.910243
78    | athlete              | 2.0    | adyakadam@berkeley.edu | Active (No Decay)
79    | bay_area             | 1.0    | kadenma@berkeley.edu | 2026-01-13 06:25:56.481920
80    | singing              | 2.0    | dylan.yamzon@berkeley.edu | Active (No Decay)
81    | ethics               | 2.0    | catherine.boland@berkeley.edu | Active (No Decay)
82    | linguistics          | 4.0    | jayjiang@berkeley.edu | Active (No Decay)
83    | shanghai             | 1.0    | jayjiang@berkeley.edu | 2026-01-13 08:14:37.626847
87    | cr7_fans             | 1.0    | jamil_shirinov@berkeley.edu | 2026-01-13 12:27:14.040308
88    | tennis               | 1.0    | knguyen7@berkeley.edu | 2026-01-13 19:18:57.721368
89    | shopping             | 1.0    | lavanyakrishna@berkeley.edu | 2026-01-13 19:28:43.593337
90    | indian               | 1.0    | lavanyakrishna@berkeley.edu | 2026-01-13 19:31:48.575532
91    | funny                | 1.0    | lavanyakrishna@berkeley.edu | 2026-01-13 19:32:10.074073
"""

def rebuild_database():
    # Remove existing db if it exists to ensure a clean start
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
        print(f"Removed existing {DATABASE}")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # 1. Create Tables (Matching app.py logic)
    # We include decay_start and description here directly to avoid needing ALTER TABLE later
    print("Creating tables...")
    cursor.execute('''
        CREATE TABLE words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL UNIQUE,
            weight REAL NOT NULL DEFAULT 1, 
            decay_start TIMESTAMP, 
            created_by TEXT,
            description TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE upvotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            word_id INTEGER NOT NULL,
            UNIQUE(user_email, word_id),
            FOREIGN KEY(word_id) REFERENCES words(id) ON DELETE CASCADE
        )
    ''')

    # 2. Parse and Insert Data
    print("Inserting data...")
    lines = RAW_DATA.strip().split('\n')
    
    count = 0
    for line in lines:
        if not line.strip(): 
            continue
            
        # Split by pipe '|' and strip whitespace
        parts = [p.strip() for p in line.split('|')]
        
        # Unpack columns
        # Format: ID | Text | Weight | Created By | Decay Start
        if len(parts) < 5:
            print(f"Skipping malformed line: {line}")
            continue

        word_id = int(parts[0])
        text = parts[1]
        weight = float(parts[2])
        created_by = parts[3]
        decay_raw = parts[4]

        # Handle "Active (No Decay)" -> NULL
        if "Active" in decay_raw:
            decay_start = None
        else:
            decay_start = decay_raw

        try:
            # We explicitly insert the ID to maintain consistency with the dump
            cursor.execute('''
                INSERT INTO words (id, text, weight, created_by, decay_start)
                VALUES (?, ?, ?, ?, ?)
            ''', (word_id, text, weight, created_by, decay_start))
            count += 1
        except sqlite3.IntegrityError as e:
            print(f"Error inserting {text}: {e}")

    conn.commit()
    conn.close()
    print(f"Successfully rebuilt {DATABASE} with {count} records.")

if __name__ == "__main__":
    rebuild_database()
